"""Fountain Square geometry shared by the drawings (turned frame, metres; see fs_plan.py)."""
import os, re
import numpy as np
from matplotlib.offsetbox import DrawingArea, AnnotationBbox
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch
import matplotlib.transforms as mtrans
from svgpath2mpl import parse_path

HERE = os.path.dirname(os.path.abspath(__file__))
BADGE_DIR = os.path.join(HERE, 'badges') if os.path.isdir(os.path.join(HERE, 'badges')) else os.path.join(HERE, '..', 'badges')

NS = {'Race': (-206.5, -187.5), 'Vine': (-64.5, -44.5), 'Walnut': (77.5, 96.5), 'Main': (218.0, 236.5)}
EW = {'4th': (-207.0, -189.0), '5th': (-68.0, -47.0), '6th': (76.5, 92.0), '7th': (216.0, 232.5)}
PLAZA = (-44.5, 33.0, -47.0, 0.0)
COLS = {'1': '#ffce00', '2': '#98d4e2', '7': '#00a88f', 'A': '#e3051c', 'B': '#0064b0', 'D': '#009b3a'}

B2, EDGE = 9.45, 4.0
L1 = dict(axis='u', c=-57.5, a=8.8, b=168.8, level=-1)
L7 = dict(axis='u', c=84.25, a=-131.0, b=29.0, level=-1)
L2 = dict(axis='v', c=-54.5, a=-137.4, b=22.6, level=-2)
AD_C, AD_U = 14.9, -37.2
CAV_W, ISL, PILLAR = 19.0, 10.0, 8.0
AD = dict(a=AD_U - 100, b=AD_U + 100, south=(AD_C - PILLAR / 2 - CAV_W, AD_C - PILLAR / 2), north=(AD_C + PILLAR / 2, AD_C + PILLAR / 2 + CAV_W))
TB = dict(c=87.0, a=-18.4, b=181.6, w=21.0, isl=12.0)
BORE = 7.0                                   # TRI running tunnels beyond the caverns, one per direction

# platform level below the street, m (drawing values). TRI deepened 2026-10-04 so the caverns' crowns keep cover below
# Line 2's box (A/D) and below the A/D running tunnels (B).
DEPTH = {0: 0.0, -1: 5.36, -2: 12.06, -2.5: 17.5, -3: 28.0, -4: 42.0}

# Pan Am Tower (tracker: 62 stories, 1,050 ft, Vine-Race-5th-6th block, opened 9 August 1999). Proposal: shaft on the
# Race half, over the A/D running tunnels where they are two bores, not the 46 m wide cavern band; podium and basements
# over the whole block, the Vine west passage in its basement.
BLOCK_PA = (-187.5, -64.5, -47.0, 76.5)
TOWER = (-184.0, -138.0, 27.0, 74.8)   # 2026-10-05: moved north off the A/D caverns (north cavern edge v 23.6) to Line 7's box (v 74.8)

# passages (u0, u1, v0, v1, level)
# Châtelet layout (Ben, 2026-10-04, from Guillaumes' Châtelet cutaway and plan): a knot of short passages where 2, 7 and
# A/D meet at Vine; an exchange hall over both A/D caverns (Châtelet-Les Halles' salle d'échanges), Line 2 northbound opening
# straight into it as Les Halles' Line 4 does into the RER hall; trunks to the Walnut sector (Line 1, TRI B) and to Line 7.
CORR = {   # name: (u0, u1, v0, v1, level)
    'Exchange hall': (-44.5, 33.0, -47.0, 38.0, -2),                # under the plaza and on north over both A/D caverns
    'Fifth Street trunk': (-44.5, 97.0, -67.0, -48.0, -2),          # hall to the Walnut sector, under Line 1's box
    'Walnut passage': (79.0, 95.0, -48.0, 75.0, -2),
    'Sixth Street passage': (-44.5, 97.0, 75.0, 94.0, -2),
    'Line 7 trunk': (15.0, 25.0, 38.0, 75.0, -2),                   # hall north edge to the Sixth Street passage, under Line 7's east end
    'Vine east passage': (-44.5, -35.0, 38.0, 75.0, -2),
    'Vine west passage': (-80.0, -64.5, -47.0, 75.0, -2),           # in Pan Am Tower's lowest basement (Ben, 2026-10-04)
    'Sixth Street west passage': (-100.0, -64.5, 75.0, 94.0, -2),
    'Line 2 crossunder': (-80.0, -44.5, -42.0, -35.0, -2.5),
    'A/D to B link': (62.8, 88.0, -6.0, 36.0, -3),
}

# vertical links: (u, v, from_level, to_level, what), stairs or escalators between the two levels
LINKS = [
    (-72, 28.4, -2, -3, 'esc'), (-72, 1.4, -2, -3, 'esc'),          # Vine west passage down to both A/D islands (2 SB side)
    (-28, 28.4, -2, -3, 'esc'), (-3, 28.4, -2, -3, 'esc'), (22, 28.4, -2, -3, 'esc'),   # exchange hall: escalator banks all along
    (-28, 1.4, -2, -3, 'esc'), (-3, 1.4, -2, -3, 'esc'), (22, 1.4, -2, -3, 'esc'),       # both islands, as Châtelet-Les Halles' hall
    (84, 15, -3, -4, 'esc'), (87, 0, -2, -3, 'esc'),                # A/D-B link down to B; Walnut passage down to the link
    (87, -12, -2, -4, 'esc'), (87, 66, -2, -4, 'esc'),              # Walnut passage down to B (south end, and at 6th)
    (20, -46.0, -2, -1, 'stair'),                                   # exchange hall up to Line 1 westbound (north platform)
    (20, -63, -2, -1, 'stair'), (60, -63, -2, -1, 'stair'),         # Fifth Street trunk up to Line 1 eastbound
    (20, 79, -2, -1, 'stair'), (20, 90, -2, -1, 'stair'),           # Line 7 trunk / Sixth Street passage up to both Line 7 platforms
    (-10, 79, -2, -1, 'stair'), (-88, 79, -2, -1, 'stair'), (-88, 90, -2, -1, 'stair'),
    (-59.0, -38.5, -2, -2.5, 'stair'), (-50.0, -38.5, -2, -2.5, 'stair'),              # Line 2 crossunder, down from each side
]
PILLAR = [-87.2, -37.2, 12.8]                                       # cross-passages between the two A/D caverns, platform level
# same-level openings into Line 2's platforms (u, v, side)
OPEN2 = [(-43.0, -30, 'NB'), (-43.0, -57.5, 'NB'), (-43.0, 14, 'NB'), (-43.0, -8, 'NB'), (-66.0, 14, 'SB'), (-66.0, -30, 'SB')]
LEVEL_NAME = {-1: 'Lines 1 and 7', -2: 'Line 2, the concourse and passages', -2.5: 'Line 2 crossunder', -3: 'TRI A and D', -4: 'TRI B'}


def badge_box(name, size):
    t = open(os.path.join(BADGE_DIR, name + '.svg')).read(); k = size / 160.0
    da = DrawingArea(size, size, 0, 0)
    m = re.search(r'<circle class="bg"[^>]* r="([\d.]+)" fill="([^"]+)"', t)
    if m:
        da.add_artist(Circle((size / 2, size / 2), size / 2, fc=m[2], ec='white', lw=0.8))
    else:
        m = re.search(r'<rect class="bg"[^>]* rx="([\d.]+)" fill="([^"]+)"', t)
        da.add_artist(FancyBboxPatch((0, 0), size, size, boxstyle='round,pad=0,rounding_size=%.3f' % (float(m[1]) * k), fc=m[2], ec='white', lw=0.8))
    g = re.search(r'<path class="glyph" fill="([^"]+)" d="([^"]+)"', t)
    da.add_artist(PathPatch(mtrans.Affine2D().scale(k, -k).translate(0, size).transform_path(parse_path(g[2])), fc=g[1], ec='none'))
    return da


def put_badge(ax, name, xy, size=14, zo=9):
    ab = AnnotationBbox(badge_box(name, size), xy, frameon=False, pad=0); ab.set_zorder(zo); ax.add_artist(ab)
