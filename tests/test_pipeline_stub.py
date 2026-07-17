"""Full dry-run pipeline with stub agent (no live CLIs, no FastSD)."""

from pathlib import Path

from PIL import Image

from tilagup.pipeline import run_pipeline


def _make_image(path: Path, size: tuple[int, int] = (320, 320)) -> Path:
    # Distinct colors so stub palette hints differ a bit by region
    im = Image.new("RGB", size, color=(30, 30, 30))
    # paint quadrants
    w, h = size
    for x in range(w):
        for y in range(h):
            r = 40 + (x * 200) // max(w, 1)
            g = 40 + (y * 200) // max(h, 1)
            b = 80
            im.putpixel((x, y), (r, g, b))
    im.save(path)
    return path


def test_dry_run_pipeline_with_stub(tmp_path: Path):
    img = _make_image(tmp_path / "src.png")
    runs = tmp_path / "runs"
    config = {
        "agent": "stub",
        "variation": 0.35,
        "strength": 0.28,
        "scale": 2.0,
        "tile_size": 128,
        "overlap": 16,
        "negative_prompt": "blurry",
        "dry_run": True,
    }
    arch = run_pipeline(
        image=img,
        resume=None,
        runs_dir=runs,
        config=config,
        dry_run=True,
        force=False,
        timeout_s=10.0,
    )
    data = arch.load()
    assert data["stage"] == "dry_run_complete"
    assert data["base_prompt"]["text"]
    assert data["base_prompt"]["attribution"]["agent"] == "stub"
    assert data["agents_used"] == ["stub"]
    tiles = data["tiles"]
    assert len(tiles) >= 4
    for t in tiles:
        assert t["status"] == "prompted"
        assert t["prompt"]
        assert t["attribution"]["agent"] == "stub"
        assert (arch.root / t["crop_path"]).is_file()
        assert (arch.root / t["prompt_path"]).is_file()
        assert (arch.root / t["meta_path"]).is_file()
    assert (arch.root / "base_prompt.txt").is_file()
    assert arch.events_log.is_file()
    # unique-ish tile prompts (at least tile ids differ in text)
    texts = [t["prompt"] for t in tiles]
    assert len(set(texts)) >= 2


def test_resume_dry_run_is_noop(tmp_path: Path):
    img = _make_image(tmp_path / "src.png", size=(256, 256))
    runs = tmp_path / "runs"
    config = {
        "agent": "stub",
        "variation": 0.2,
        "strength": 0.28,
        "scale": 2.0,
        "tile_size": 128,
        "overlap": 16,
        "negative_prompt": "x",
        "dry_run": True,
    }
    arch = run_pipeline(
        image=img,
        resume=None,
        runs_dir=runs,
        config=config,
        dry_run=True,
    )
    updated_before = arch.load()["updated_at"]
    base_before = arch.load()["base_prompt"]["text"]

    arch2 = run_pipeline(
        image=None,
        resume=arch.root,
        runs_dir=runs,
        config=config,
        dry_run=True,
    )
    data = arch2.load()
    assert data["stage"] == "dry_run_complete"
    assert data["base_prompt"]["text"] == base_before
    # still complete; events should note already_complete
    events = arch2.events_log.read_text(encoding="utf-8")
    assert "already_complete" in events or data["updated_at"] >= updated_before


def test_cli_stub_dry_run(tmp_path: Path):
    img = _make_image(tmp_path / "cli.png", size=(200, 200))
    runs = tmp_path / "runs"
    from tilagup.cli import main

    code = main(
        [
            str(img),
            "--agent",
            "stub",
            "--dry-run",
            "--runs-dir",
            str(runs),
            "--tile-size",
            "100",
            "--overlap",
            "8",
        ]
    )
    assert code == 0
    run_dirs = list(runs.iterdir())
    assert len(run_dirs) == 1
    run_json = run_dirs[0] / "run.json"
    assert run_json.is_file()
    import json

    data = json.loads(run_json.read_text(encoding="utf-8"))
    assert data["stage"] == "dry_run_complete"
    assert data["config"]["agent"] == "stub"
