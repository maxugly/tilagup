from pathlib import Path

from PIL import Image

from tilagup.archive import create_run, open_run


def test_create_run_copies_source(tmp_path: Path):
    img = tmp_path / "in.png"
    Image.new("RGB", (64, 48), color=(10, 20, 30)).save(img)
    runs = tmp_path / "runs"
    arch = create_run(
        runs,
        img,
        {"agent": "agy", "variation": 0.2, "strength": 0.3, "scale": 2.0,
         "tile_size": 256, "overlap": 32, "negative_prompt": "x", "dry_run": True},
    )
    data = arch.load()
    assert data["run_id"]
    assert data["stage"] == "init"
    assert (arch.root / data["source"]["path"]).is_file()
    assert data["source"]["width"] == 64
    assert data["source"]["height"] == 48
    arch.event("hello", n=1)
    assert arch.events_log.is_file()
    again = open_run(arch.root)
    assert again.load()["run_id"] == data["run_id"]
