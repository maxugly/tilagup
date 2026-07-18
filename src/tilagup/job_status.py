"""Sticky bottom status bar + per-run timing tracker.

Updates every second while a job is running so elapsed / remaining / unit
ETAs tick live — not only when something logs.
"""

from __future__ import annotations

import atexit
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tilagup.timing_stats import (
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
    current_unit_label: str = ""  # e.g. tile r02_c03

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
        self._lock = threading.Lock()

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
        sys.stderr.write(f"\033[1;{self._scroll_bottom}r")
        sys.stderr.write(f"\033[{self._scroll_bottom};1H\n")
        sys.stderr.flush()
        self.active = True
        atexit.register(self.stop)

    def stop(self) -> None:
        if not self.active:
            return
        with self._lock:
            try:
                sys.stderr.write("\033[r")
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
        with self._lock:
            try:
                # refresh terminal size (user resized)
                size = shutil.get_terminal_size(fallback=(self._cols, self._rows))
                self._cols = size.columns
                cols = max(20, self._cols - 1)
                padded = (lines + [""] * self.height)[: self.height]
                sys.stderr.write("\0337")
                for i, line in enumerate(padded):
                    row = self._scroll_bottom + 1 + i
                    safe = "".join(
                        ch if ord(ch) >= 32 or ch in "\t" else "?" for ch in line
                    )
                    if len(safe) > cols:
                        safe = safe[: cols - 1] + "…"
                    sys.stderr.write(f"\033[{row};1H\033[2K{safe}")
                sys.stderr.write("\0338")
                sys.stderr.flush()
            except Exception:
                pass


def _fmt_clock(seconds: float | None) -> str:
    """Always show m:ss or h:mm:ss so numbers don't look 'stuck' as 0s."""
    if seconds is None:
        return "--:--"
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


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
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._build_plan()
        if enabled:
            self.bar.start()
            self.refresh()
            self._thread = threading.Thread(
                target=self._tick_loop, name="tilagup-status", daemon=True
            )
            self._thread.start()

    def _tick_loop(self) -> None:
        while not self._stop.wait(1.0):
            try:
                self.refresh()
            except Exception:
                pass

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

    def set_unit_label(self, name: str, label: str) -> None:
        """e.g. set_unit_label('tile_prompts', 'r02_c03') while agent runs."""
        st = self.stages.get(name)
        if not st:
            return
        st.current_unit_label = label
        if st.last_unit_t0 is None and st.status == "running":
            st.last_unit_t0 = time.monotonic()
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
        st.current_unit_label = ""
        self.refresh()

    def stage_unit(self, name: str, units_done: int | None = None) -> None:
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
        st.current_unit_label = ""
        self.refresh()

    def stage_end(self, name: str, *, skipped: bool = False) -> None:
        st = self.stages.get(name)
        if not st:
            return
        st.t1 = time.monotonic()
        st.status = "skipped" if skipped else "done"
        st.current_unit_label = ""
        self.refresh()

    def tick(self) -> None:
        self.refresh()

    def _per_unit_est(self, st: StageState) -> float | None:
        if st.unit_samples:
            cleaned = clean_unit_samples(st.unit_samples, stage=st.name)
            if cleaned:
                return float(sum(cleaned) / len(cleaned))
        if st.name == "tile_prompts":
            return estimate_seconds(self.history, "tile_prompts_per_tile", n_units=1)
        if st.name == "upscale":
            return estimate_seconds(self.history, "upscale_per_tile", n_units=1)
        return None

    def _stage_eta_remaining(self, st: StageState) -> float:
        if st.status in ("done", "skipped"):
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

        # running multi-unit: remaining full units + residual current unit
        if st.n_units > 0:
            left_full = max(0, st.n_units - st.units_done)
            per = self._per_unit_est(st) or estimate_seconds(
                self.history,
                "tile_prompts_per_tile"
                if st.name == "tile_prompts"
                else "upscale_per_tile"
                if st.name == "upscale"
                else st.name,
                n_units=1,
            )
            # time left on current unit
            cur_left = per
            if st.last_unit_t0 is not None:
                spent = time.monotonic() - st.last_unit_t0
                cur_left = max(0.0, per - spent)
            # units_done finished; if a unit is in progress, left_full includes current
            # so: (left_full - 1) * per + cur_left when working on a unit
            if st.current_unit_label or (st.units_done < st.n_units):
                remaining_after_current = max(0, left_full - 1)
                return remaining_after_current * per + cur_left
            return left_full * per

        est = estimate_seconds(self.history, st.name)
        el = st.elapsed or 0
        return max(0.0, est - el)

    def overall_remaining(self) -> float:
        return sum(self._stage_eta_remaining(self.stages[n]) for n in self._plan)

    def overall_elapsed(self) -> float:
        return time.monotonic() - self.t_start

    def render_lines(self) -> list[str]:
        el = self.overall_elapsed()
        rem = self.overall_remaining()
        total_est = el + rem
        pct = min(99.0, 100.0 * el / total_est) if total_est > 0 else 0.0

        current = None
        for name in self._plan:
            if self.stages[name].status == "running":
                current = self.stages[name]
                break

        mode = "dry-run" if self.dry_run else "full+upscale"
        # Line 0 — full job clocks (tick every second)
        line0 = (
            f"JOB  {self.run_id or '…'}  [{mode}]  "
            f"elapsed {_fmt_clock(el)}  |  remaining {_fmt_clock(rem)}  |  "
            f"total est {_fmt_clock(total_est)}"
        )

        # Line 1 — overall bar
        width = 32
        filled = int(width * pct / 100)
        bar = "█" * filled + "░" * (width - filled)
        line1 = f"     [{bar}] {pct:.0f}%"

        # Line 2 — step
        n_steps = len(self._plan)
        if current:
            step_i = self._plan.index(current.name) + 1
            step_left = self._stage_eta_remaining(current)
            line2 = (
                f"STEP {step_i}/{n_steps}  {current.label}  "
                f"step elapsed {_fmt_clock(current.elapsed)}  "
                f"step left ~{_fmt_clock(step_left)}"
            )
        else:
            done_n = sum(
                1 for n in self._plan if self.stages[n].status in ("done", "skipped")
            )
            line2 = f"STEP {done_n}/{n_steps}  (between steps)"

        # Line 3 — unit subdivision (tile/prompt)
        if current and current.n_units > 0:
            u_done = current.units_done
            u_tot = current.n_units
            # display "working on" as next index (1-based)
            u_now = min(u_done + 1, u_tot) if u_done < u_tot else u_tot
            per = self._per_unit_est(current)
            unit_spent = 0.0
            if current.last_unit_t0 is not None and u_done < u_tot:
                unit_spent = time.monotonic() - current.last_unit_t0
            unit_left = max(0.0, (per or 0) - unit_spent) if per else None
            label = current.current_unit_label or "…"
            kind = "tile" if current.name in ("tile_prompts", "upscale") else "unit"
            line3 = (
                f"UNIT {kind} {u_now}/{u_tot}  ({u_done} done)  "
                f"id={label}  "
                f"this {_fmt_clock(unit_spent)}"
            )
            if unit_left is not None:
                line3 += f"  left ~{_fmt_clock(unit_left)}"
            if per:
                line3 += f"  avg {_fmt_clock(per)}/ea"
        elif current:
            line3 = f"UNIT  (single-shot stage — no sub-items)"
        else:
            line3 = "UNIT  —"

        # Line 4 — done
        done_bits = []
        for name in self._plan:
            st = self.stages[name]
            if st.status == "done":
                done_bits.append(f"{st.label} {_fmt_clock(st.elapsed)}")
            elif st.status == "skipped":
                done_bits.append(f"{st.label} skip")
        line4 = "DONE " + (" · ".join(done_bits) if done_bits else "(none yet)")

        # Line 5 — upcoming
        up = []
        for name in self._plan:
            st = self.stages[name]
            if st.status == "pending":
                up.append(f"{st.label} ~{_fmt_clock(self._stage_eta_remaining(st))}")
        line5 = "NEXT " + (" · ".join(up[:4]) if up else "(none)")

        # Line 6 — history medians
        agg = self.history.get("aggregates") or {}
        tp = (agg.get("tile_prompts_per_tile") or {}).get("median_s")
        upm = (agg.get("upscale_per_tile") or {}).get("median_s")
        bits = []
        if tp:
            bits.append(f"hist prompt {_fmt_clock(tp)}/tile")
        if upm:
            bits.append(f"hist sd {_fmt_clock(upm)}/tile")
        line6 = "HIST " + (" · ".join(bits) if bits else "priors only (need complete live runs)")

        line7 = f"agent={self.agent}  tiles={self.n_tiles or '?'}  ·  status updates every 1s"

        return [line0, line1, line2, line3, line4, line5, line6, line7]

    def refresh(self) -> None:
        if not self.enabled:
            return
        lines = self.render_lines()
        if self.bar.active:
            self.bar.draw(lines)

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
                    import statistics

                    info["per_unit_s"] = float(sum(cleaned) / len(cleaned))
                    info["per_unit_median_s"] = float(statistics.median(cleaned))
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
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        snap = self.snapshot()
        if run_dir is not None:
            try:
                p = run_dir / "timing.json"
                p.write_text(
                    __import__("json").dumps(snap, indent=2) + "\n", encoding="utf-8"
                )
            except Exception:
                pass
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


_TRACKER: JobTracker | None = None


def get_tracker() -> JobTracker | None:
    return _TRACKER


def set_tracker(t: JobTracker | None) -> None:
    global _TRACKER
    _TRACKER = t
