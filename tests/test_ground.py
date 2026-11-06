"""region.ground: the ground by year reproduces the stored surfaces, and parametric works daylight correctly."""
import numpy as np
import pytest
from shapely.geometry import box

from region.ground import Corridor, Pad, compose, sample, works_for_year
from region.ground import layers as L
from region.ground.raster import Target, read

EMB = (711000, 4330000, 714000, 4332500)        # the Embankment at the Mill Creek mouth, riverworks window


def test_1912_is_the_canon_1912_raster():
    g = compose(1912, EMB)
    c = read(L.CANON_1912, g.target).astype(float); c[c == L.ND] = np.nan
    assert np.allclose(np.nan_to_num(g.z * 10, nan=-1), np.nan_to_num(c, nan=-1))
    assert [a for a, _ in g.applied] == ["ohio_embankment_1912"]


def test_real_1912_differs_only_on_the_riverworks():
    c, r = compose(1912, EMB, "canon"), compose(1912, EMB, "real")
    d = np.nan_to_num(c.z - r.z)
    assert (d != 0).sum() > 1000 and (d != 0).sum() < 0.1 * d.size
    assert (r.src == L.SRC["real_1912"]).sum() == (d != 0).sum()


def test_works_by_year():
    p30, s30 = works_for_year(1930)
    # the deck by 1913 (Ben, 6 November); the fluid zones are always offered and compose picks the dated ones
    assert {w.id for w in p30} == {"ohio_embankment_1912", "ohio_embankment_rest", "mill_creek_deck", "ky_terraces", "real_works_kept"}
    assert ("lunken_levees", "built 1941") in s30 and ("canon_interstates", "built 1965") in s30
    p26, _ = works_for_year(2026)
    assert "real_works_kept" in {w.id for w in p26} and "canon_interstates" in {w.id for w in p26}


def test_2026_reproduces_map3_inside_the_works():
    g = compose(2026, EMB)
    m3 = read(L.MAP3, g.target).astype(float); m3[m3 == L.ND] = np.nan; m3 /= 10
    d = np.abs(g.z - m3)
    names = g.code_names()
    for code in np.unique(g.src[g.src >= 10]):
        m = g.src == code
        agree = (d[m] <= 0.051).mean()
        assert agree > 0.95, (names[code], agree)


def test_embankment_rises_between_1912_and_1930():
    z12, z30, z26 = (sample(y, [(712300, 4330900)])[0] for y in (1912, 1930, 2026))
    assert z30 > z12 + 2 and z26 == pytest.approx(z30)


def test_pad_daylights_at_the_slope():
    tgt = Target(0, 0, 200, 200)
    flat = np.full(tgt.shape, 100.0, np.float32)
    pad = Pad("p", box(80, 80, 120, 120), level=110.0, cut_slope=0.5, fill_slope=0.5)
    new, changed = pad.apply(flat, tgt)
    assert new[50, 50] == 110.0                                    # inside
    # 10 m rise at 1 in 2 daylights 20 m out: changed to about 20 m beyond the edge
    assert np.isclose(new[50, 60 + 5], 110 - 0.5 * 11, atol=1.0)   # about 11 m out: 104.5
    assert new[50, 60 + 12] == 100.0                                # 24 m out: untouched
    assert pad.stats["fill_m3"] > 40 * 40 * 10 and pad.stats["cut_m3"] == 0
    cut = Pad("c", box(80, 80, 120, 120), level=90.0, cut_slope=1.0, fill_slope=0.5)
    new2, _ = cut.apply(flat, tgt)
    assert new2[50, 50] == 90.0 and new2[50, 60 + 3] == pytest.approx(97.0, abs=1.0) and new2[50, 60 + 8] == 100.0


def test_corridor_embankment_and_cutting():
    tgt = Target(0, 0, 300, 100)
    ground = np.full(tgt.shape, 100.0, np.float32)
    c = Corridor("c", [(0, 50, 104), (300, 50, 96)], half_width=5, cut_slope=1.0, fill_slope=0.5)
    new, changed = c.apply(ground, tgt)
    assert new[25, 10] == pytest.approx(104 - 8 * 20 / 300, abs=0.3)       # on the formation at x = 20
    assert new[25, 140] == pytest.approx(96 + 8 * (300 - 280) / 300, abs=0.3)
    assert new[25 - 6, 10] > 100 and new[25 - 2, 140] < 100              # fill beyond the formation at one end, the cutting at the other
    assert c.stats["fill_m3"] > 0 and c.stats["cut_m3"] > 0 and c.stats["length_m"] == 300


def test_extra_works_compose_on_the_year():
    pad = Pad("test_pad", box(712400, 4331000, 712500, 4331100), level=170.0)
    from region.ground.sample import sample_grid
    g = compose(1930, EMB, extra_works=[pad])
    assert sample(1930, [(712450, 4331050)])[0] < 160 and sample_grid(g, [(712450, 4331050)])[0] == pytest.approx(170.0)
    assert (g.src == pad.code).sum() > 2500 and pad.stats["fill_m3"] > 0


def test_a_date_change_is_one_record_edit(tmp_path):
    """Dates, layers and zones live in the ledger and the zone files, never in code."""
    import json
    from region.ground import layers as L
    led = json.loads((L.GROUND / "works_ledger.json").read_text())
    deck = next(w for w in led["works"] if w["id"] == "mill_creek_deck")
    assert deck["built_by"] == 1913 and deck["apply"]["kind"] == "target_mode" and deck["apply"]["part_value"] == 2
    deck["built_by"] = 1950
    p = tmp_path / "ledger.json"; p.write_text(json.dumps(led))
    present, _ = works_for_year(1930, ledger=L.load_ledger(p))
    assert "mill_creek_deck" not in {w.id for w in present}
    g13, g30 = compose(1913, EMB), compose(1930, EMB)
    assert (g13.src == next(w.code for w in L.load_ledger() if w.id == "mill_creek_deck")).sum() > 100000   # the deck is there in 1913


def test_zone_years_are_per_zone(tmp_path):
    import json
    import importlib; C = importlib.import_module("region.ground.compose")
    from region.ground import layers as L
    zones = L.GROUND / "zones/zones_post1912_works.geojson"
    ids = [zid for zid, _ in C._load_zones(zones)]
    yrs = tmp_path / "years.json"; yrs.write_text(json.dumps({"zones": {ids[0]: {"built_by": 1925}}}))
    g_early = C._zones_geom(zones, None, yrs, 1930); g_none = C._zones_geom(zones, None, yrs, 1920); g_all = C._zones_geom(zones, None, yrs, 2026)
    assert g_none.is_empty and 0 < g_early.area < g_all.area
