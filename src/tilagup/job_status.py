"""Sticky bottom status bar + per-run timing tracker."""

from __future__ import annotations

import atexit
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tilagup.timing_stats import (
    STAGE_ORDER,
    clean_unit_samples,
    estimate_seconds,
    fmt_duration,
    load_history,
    mark_sample_complete,
    record_sample,
    sample_is_complete,
)


@dataclass
class StageState:
    name: str
    label: str
    status: str = "pending"  # pending | running | done | skipped
    t0: float | None = None
    t1: float | None = None
    n_units: int = 0
    units_done: int = 0
    unit_samples: list[float] = field(default_factory=list)
    last_unit_t0: float | None = None

    @property
    def elapsed(self) -> float | None:
        if self.t0 is None:
            return None
        end = self.t1 if self.t1 is not None else time.monotonic()
        return end - self.t0


class StickyBar:
    """Reserve bottom N lines; verbose log scrolls above."""

    def __init__(self, height: int = 8):
        self.height = height
        self.active = False
        self._rows = 24
        self._cols = 80
        self._scroll_bottom = 16

    def start(self) -> None:
        if not sys.stderr.isatty():
            self.active = False
            return
        size = shutil.get_terminal_size(fallback=(80, 24))
        self._cols = size.columns
        self._rows = size.lines
        if self._rows < self.height + 6:
            self.active = False
            return
        self._scroll_bottom = self._rows - self.height
        # scroll region = lines 1 .. scroll_bottom
        sys.stderr.write(f"\033[1;{self._scroll_bottom}r")
        sys.stderr.write(f"\033[{self._scroll_bottom};1H\n")
        sys.stderr.flush()
        self.active = True
        atexit.register(self.stop)

    def stop(self) -> None:
        if not self.active:
            return
        try:
            sys.stderr.write("\033[r")  # reset scroll region
            # clear status area
            for i in range(self.height):
                row = self._scroll_bottom + 1 + i
                sys.stderr.write(f"\033[{row};1H\033[2K")
            sys.stderr.write(f"\033[{self._rows};1H\n")
            sys.stderr.flush()
        except Exception:
            pass
        self.active = False

    def draw(self, lines: list[str]) -> None:
        if not self.active:
            return
        # re-read size occasionally? keep simple
        cols = max(20, self._cols - 1)
        padded = (lines + [""] * self.height)[: self.height]
        sys.stderr.write("\0337")  # save cursor
        for i, line in enumerate(padded):
            row = self._scroll_bottom + 1 + i
            # strip control chars, clip width
            safe = "".join(ch if ord(ch) >= 32 or ch in "\t" else "?" for ch in line)
            if len(safe) > cols:
                safe = safe[: cols - 1] + "…"
            sys.stderr.write(f"\033[{row};1H\033[2K{safe}")
        sys.stderr.write("\0338")  # restore
        sys.stderr.flush()


class JobTracker:
    def __init__(
        self,
        *,
        run_id: str = "",
        dry_run: bool = True,
        n_tiles: int = 0,
        agent: str = "both",
        enabled: bool = True,
    ):
        self.run_id = run_id
        self.dry_run = dry_run
        self.n_tiles = n_tiles
        self.agent = agent
        self.history = load_history()
        self.t_start = time.monotonic()
        self.bar = StickyBar(height=8)
        self.enabled = enabled
        self._plan: list[str] = []
        self.stages: dict[str, StageState] = {}
        self._build_plan()
        if enabled:
            self.bar.start()
            self.refresh()

    def _build_plan(self) -> None:
        names = ["init", "base_prompt", "split", "tile_prompts"]
        if not self.dry_run:
            names.append("upscale")
        self._plan = names
        labels = {
            "init": "init",
            "base_prompt": "base prompt",
            "split": "split tiles",
            "tile_prompts": "tile prompts",
            "upscale": "SD upscale",
        }
        for n in names:
            nu = self.n_tiles if n in ("tile_prompts", "upscale") else 0
            self.stages[n] = StageState(name=n, label=labels.get(n, n), n_units=nu)

    def set_n_tiles(self, n: int) -> None:
        self.n_tiles = n
        for name in ("tile_prompts", "upscale"):
            if name in self.stages:
                self.stages[name].n_units = n
        self.refresh()

    def set_run_id(self, run_id: str) -> None:
        self.run_id = run_id
        self.refresh()

    def stage_start(self, name: str, *, n_units: int | None = None) -> None:
        st = self.stages.get(name)
        if not st:
            st = StageState(name=name, label=name)
            self.stages[name] = st
            if name not in self._plan:
                self._plan.append(name)
        st.status = "running"
        st.t0 = time.monotonic()
        st.t1 = None
        if n_units is not None:
            st.n_units = n_units
        st.units_done = 0
        st.unit_samples.clear()
        st.last_unit_t0 = time.monotonic()
        self.refresh()

    def stage_unit(self, name: str, units_done: int | None = None) -> None:
        """Mark one unit finished (or set absolute units_done). Records duration sample."""
        st = self.stages.get(name)
        if not st or st.status != "running":
            return
        now = time.monotonic()
        if st.last_unit_t0 is not None:
            dt = now - st.last_unit_t0
            if dt > 0.05:
                st.unit_samples.append(dt)
        if units_done is not None:
            st.units_done = units_done
        else:
            st.units_done += 1
        st.last_unit_t0 = now
        self.refresh()

    def stage_end(self, name: str, *, skipped: bool = False) -> None:
        st = self.stages.get(name)
        if not st:
            return
        st.t1 = time.monotonic()
        st.status = "skipped" if skipped else "done"
        if not skipped and st.n_units and st.units_done == 0 and st.elapsed:
            # whole stage as one unit sample for per-tile stages if no units fired
            pass
        self.refresh()

    def tick(self) -> None:
        """Refresh elapsed clocks (e.g. from heartbeats)."""
        self.refresh()

    def _stage_eta_remaining(self, st: StageState) -> float:
        if st.status == "done" or st.status == "skipped":
            return 0.0
        if st.status == "pending":
            if st.name == "tile_prompts":
                return estimate_seconds(
                    self.history,
                    "tile_prompts",
                    n_units=max(st.n_units, self.n_tiles, 1),
                )
            if st.name == "upscale":
                return estimate_seconds(
                    self.history,
                    "upscale",
                    n_units=max(st.n_units, self.n_tiles, 1),
                )
            return estimate_seconds(self.history, st.name, n_units=1)

        # running
        if st.n_units > 0:
            left = max(0, st.n_units - st.units_done)
            if st.unit_samples:
                return estimate_seconds(
                    self.history,
                    f"{st.name}",
                    n_units=left,
                    run_unit_samples=st.unit_samples,
                )
            # blend history per-unit
            key = (
                "tile_prompts_per_tile"
                if st.name == "tile_prompts"
                else "upscale_per_tile"
                if st.name == "upscale"
                else st.name
            )
            return estimate_seconds(self.history, key, n_units=max(left, 1))
        # running non-unit stage: no unit data — use prior minus elapsed floor
        est = estimate_seconds(self.history, st.name)
        el = st.elapsed or 0
        return max(0.0, est - el)

    def overall_remaining(self) -> float:
        total = 0.0
        for name in self._plan:
            st = self.stages[name]
            total += self._stage_eta_remaining(st)
        return total

    def overall_elapsed(self) -> float:
        return time.monotonic() - self.t_start

    def render_lines(self) -> list[str]:
        el = self.overall_elapsed()
        rem = self.overall_remaining()
        total_est = el + rem
        pct = 0.0
        if total_est > 0:
            pct = min(99.0, 100.0 * el / total_est)

        # find current
        current = None
        for name in self._plan:
            if self.stages[name].status == "running":
                current = self.stages[name]
                break

        mode = "dry-run" if self.dry_run else "full (incl upscale)"
        line0 = (
            f"── tilagup {self.run_id or '…'}  [{mode}]  "
            f"elapsed {fmt_duration(el)}  ETA {fmt_duration(total_est)}  "
            f"left ~{fmt_duration(rem)} ──"
        )

        # done summary
        done_bits = []
        for name in self._plan:
            st = self.stages[name]
            if st.status == "done":
                done_bits.append(f"{st.label} {fmt_duration(st.elapsed)}")
            elif st.status == "skipped":
                done_bits.append(f"{st.label} skip")
        line1 = "Done: " + (" · ".join(done_bits) if done_bits else "(none yet)")

        # now
        if current:
            if current.n_units > 0:
                sub = f"  {current.units_done}/{current.n_units}"
                if current.unit_samples:
                    sub += f"  ~{fmt_duration(sum(current.unit_samples)/len(current.unit_samples))}/ea"
            else:
                sub = ""
            step_i = self._plan.index(current.name) + 1
            line2 = (
                f"Now:  step {step_i}/{len(self._plan)} {current.label}{sub}  "
                f"step left ~{fmt_duration(self._stage_eta_remaining(current))}"
            )
        else:
            line2 = "Now:  (between steps)"

        # upcoming
        up = []
        for name in self._plan:
            st = self.stages[name]
            if st.status == "pending":
                up.append(
                    f"{st.label} ~{fmt_duration(self._stage_eta_remaining(st))}"
                )
        line3 = "Next: " + (" · ".join(up[:4]) if up else "(none)")

        # bar
        width = 28
        filled = int(width * pct / 100)
        bar = "█" * filled + "░" * (width - filled)
        line4 = f"Overall [{bar}] {pct:.0f}%"

        # history hint (complete live-agent medians only)
        agg = self.history.get("aggregates") or {}
        tp = (agg.get("tile_prompts_per_tile") or {}).get("median_s")
        up = (agg.get("upscale_per_tile") or {}).get("median_s")
        n_tp = (agg.get("tile_prompts_per_tile") or {}).get("count", 0)
        n_up = (agg.get("upscale_per_tile") or {}).get("count", 0)
        bits = []
        if tp:
            bits.append(f"prompt~{fmt_duration(tp)}/tile×{n_tp}")
        if up:
            bits.append(f"sd~{fmt_duration(up)}/tile×{n_up}")
        line5 = "Timing: " + (
            " · ".join(bits) + "  (complete runs, outliers dropped)"
            if bits
            else "priors only until a complete live run finishes"
        )

        line6 = f"Agent={self.agent}  tiles={self.n_tiles or '?'}"
        line7 = "Verbose log scrolls above · sticky status pinned here"

        return [line0, line1, line2, line3, line4, line5, line6, line7]

    def refresh(self) -> None:
        if not self.enabled:
            return
        lines = self.render_lines()
        if self.bar.active:
            self.bar.draw(lines)
        # if no sticky (pipe), don't spam every refresh

    def snapshot(self) -> dict[str, Any]:
        stages_out: dict[str, Any] = {}
        for name, st in self.stages.items():
            info: dict[str, Any] = {
                "status": st.status,
                "seconds": st.elapsed,
                "n_units": st.n_units,
                "units_done": st.units_done,
            }
            if st.unit_samples:
                cleaned = clean_unit_samples(st.unit_samples, stage=name)
                info["unit_samples"] = st.unit_samples[-50:]
                if cleaned:
                    info["per_unit_s"] = float(sum(cleaned) / len(cleaned))
                    info["per_unit_median_s"] = float(
                        __import__("statistics").median(cleaned)
                    )
            stages_out[name] = info
        snap = {
            "run_id": self.run_id,
            "dry_run": self.dry_run,
            "n_tiles": self.n_tiles,
            "agent": self.agent,
            "elapsed_s": self.overall_elapsed(),
            "stages": stages_out,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return mark_sample_complete(snap)

    def finish(self, *, persist: bool = True, run_dir: Path | None = None) -> None:
        snap = self.snapshot()
        if run_dir is not None:
            try:
                p = run_dir / "timing.json"
                p.write_text(
                    __import__("json").dumps(snap, indent=2) + "\n", encoding="utf-8"
                )
            except Exception:
                pass
        # Only persist usable samples; incomplete/stub still may write run timing.json
        if persist and sample_is_complete(snap):
            try:
                record_sample(snap)
            except Exception:
                pass
        self.bar.stop()
        from tilagup import log

        flag = "complete" if snap.get("complete") else "incomplete (not used for ETA)"
        log.say(
            f"timing: elapsed {fmt_duration(self.overall_elapsed())}  "
            f"{flag}  history → timing_history.json"
        )


# process-global tracker for heartbeats / worker parsers
_TRACKER: JobTracker | None = None


def get_tracker() -> JobTracker | None:
    return _TRACKER


def set_tracker(t: JobTracker | None) -> None:
    global _TRACKER
    _TRACKER = t
