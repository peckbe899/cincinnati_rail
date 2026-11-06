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
    assert {w.id for w in p30} == {"ohio_embankment_1912", "ohio_embankment_rest", "ky_terraces"}
    assert ("mill_creek_deck", "built 1933") in s30 and ("real_works_kept", "undated") in s30
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
        if names[code] == "ohio_bed_canon":
            continue                        # map 3 holds a different bed (known, ruling pending)
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
