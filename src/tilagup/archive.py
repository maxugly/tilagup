"""Run archive: directory layout, run.json, events.log, atomic updates.

Layout (default):
  runs/<image_key>/<run_id>/
    run.json
    events.log
    source.*
    base_prompt.txt
    tiles/
    output.png
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tilagup import log


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def short_id(n: int = 4) -> str:
    return uuid.uuid4().hex[:n]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def image_key_from_path(source: Path) -> str:
    """Filesystem-safe folder name for an input image (stem + short hash of path)."""
    stem = source.stem.strip() or "image"
    stem = _SAFE_RE.sub("_", stem).strip("._-") or "image"
    # keep names readable; cap length
    if len(stem) > 80:
        stem = stem[:80].rstrip("._-")
    # disambiguate same stem from different paths
    digest = hashlib.sha256(str(source.resolve()).encode()).hexdigest()[:6]
    return f"{stem}__{digest}"


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    tmp.replace(path)


@dataclass
class RunArchive:
    root: Path

    @property
    def run_json(self) -> Path:
        return self.root / "run.json"

    @property
    def events_log(self) -> Path:
        return self.root / "events.log"

    @property
    def tiles_dir(self) -> Path:
        return self.root / "tiles"

    def load(self) -> dict[str, Any]:
        return json.loads(self.run_json.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        data["updated_at"] = utc_now()
        atomic_write_json(self.run_json, data)

    def event(self, message: str, **fields: Any) -> None:
        line = {"ts": utc_now(), "message": message, **fields}
        with self.events_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        # also mirror into run.json events tail (last 200)
        try:
            data = self.load()
        except FileNotFoundError:
            return
        events = data.setdefault("events", [])
        events.append(line)
        if len(events) > 200:
            data["events"] = events[-200:]
        self.save(data)
        # loud by default — human trail mirrors events.log
        extra = " ".join(f"{k}={v!r}" for k, v in fields.items() if k != "message")
        log.say(f"event  {message}" + (f"  {extra}" if extra else ""))

    def set_stage(self, stage: str) -> dict[str, Any]:
        data = self.load()
        data["stage"] = stage
        self.save(data)
        self.event("stage", stage=stage)
        return data


def new_run_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{short_id()}"


def create_run(
    runs_root: Path,
    source: Path,
    config: dict[str, Any],
    *,
    run_id: str | None = None,
) -> RunArchive:
    """Create runs/<image_key>/<run_id>/ with source copy + empty tiles/."""
    runs_root = runs_root.resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    source = source.resolve()
    image_key = image_key_from_path(source)
    rid = run_id or new_run_id()

    image_dir = runs_root / image_key
    image_dir.mkdir(parents=True, exist_ok=True)
    root = image_dir / rid
    if root.exists():
        raise FileExistsError(f"run dir already exists: {root}")
    root.mkdir(parents=True)
    tiles = root / "tiles"
    tiles.mkdir()

    suffix = source.suffix.lower() or ".png"
    dest_name = f"source{suffix}"
    dest = root / dest_name
    log.say(f"copying source → {dest}")
    shutil.copy2(source, dest)

    digest = sha256_file(dest)
    try:
        from PIL import Image

        with Image.open(dest) as im:
            width, height = im.size
            mode = im.mode
    except Exception as e:
        width = height = None
        mode = None
        log.say(f"warning: could not read image size ({e})")

    data: dict[str, Any] = {
        "run_id": rid,
        "image_key": image_key,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "stage": "init",
        "source": {
            "original_path": str(source),
            "path": dest_name,
            "sha256": digest,
            "width": width,
            "height": height,
            "mode": mode,
        },
        "config": config,
        "base_prompt": None,
        "negative_prompt": config.get("negative_prompt"),
        "tiles": [],
        "agents_used": [],
        "output": None,
        "error": None,
        "events": [],
    }
    arch = RunArchive(root)
    atomic_write_json(arch.run_json, data)
    log.banner(f"run {rid}")
    log.kv("image_key", image_key)
    log.kv("run_dir", root)
    log.kv("source", source)
    log.kv("size", f"{width}x{height}" if width else "?")
    arch.event("run_created", source=str(source), run_id=rid, image_key=image_key)
    return arch


def open_run(path: Path) -> RunArchive:
    path = path.resolve()
    if path.is_file() and path.name == "run.json":
        path = path.parent
    if not (path / "run.json").is_file():
        raise FileNotFoundError(f"no run.json under {path}")
    log.say(f"opening run: {path}")
    return RunArchive(path)

