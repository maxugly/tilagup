from tilagup.tiles import compute_tiles


def test_compute_tiles_basic_grid():
    tiles = compute_tiles(512, 512, tile_size=256, overlap=32)
    assert len(tiles) == 4
    assert tiles[0].id == "r00_c00"
    assert tiles[0].x == 0 and tiles[0].y == 0
    # non-edge includes overlap padding
    assert tiles[0].w == 256 + 32
    assert tiles[0].h == 256 + 32


def test_compute_tiles_edge_clamp():
    tiles = compute_tiles(300, 300, tile_size=256, overlap=16)
    assert len(tiles) == 4
    # last column starts at 256, width clamped to 44
    last = [t for t in tiles if t.col == 1 and t.row == 0][0]
    assert last.x == 256
    assert last.w == 44


def test_tile_ids_unique():
    tiles = compute_tiles(1024, 768, tile_size=256, overlap=32)
    ids = [t.id for t in tiles]
    assert len(ids) == len(set(ids))
