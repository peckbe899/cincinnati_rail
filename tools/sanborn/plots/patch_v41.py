try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 41 (Ben, 16 October): CVG Express to the terminals from CVG Express Final.kmz ('Today'): deep-bored, five stations (T3, T2, T4, T1B, T1A;
# option 1), yard and maintenance building north-west of T1A; the 1969 line ('Original') drawn as a former line, cut by the 18L extension.
# Chain: ... patch_v40.py && patch_v41.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)

# ---- drawing: yard, maintenance building and station platforms under the lines; the former line; station markers
rep("    if (p.layer === 'lower_plat') fillPoly(f.geometry, C.lower, C.lower, 1, 0.38);\n  }",
    "    if (p.layer === 'lower_plat') fillPoly(f.geometry, C.lower, C.lower, 1, 0.38);\n"
    "    if (p.layer === 'cvg_yard') { ctx.setLineDash([6, 4]); fillPoly(f.geometry, C.cvg, C.cvg, 1.2, 0.12); ctx.setLineDash([]); }\n"
    "    if (p.layer === 'cvg_shop') fillPoly(f.geometry, C.civic, C.ink, 1, 0.9);\n"
    "    if (p.layer === 'cvg_plat') fillPoly(f.geometry, C.cvg, C.cvg, 1, 0.55);\n  }")
rep("    if (p.layer === 'apex') { ctx.strokeStyle = (p.kind === 'cvg' || /^CVG Express/.test(p.name || '')) ? C.cvg : C.apex; ctx.lineWidth = p.kind === 'region' && v.s < 0.2 ? 1.3 : lw; ctx.setLineDash(p.state === 'tunnel' ? [7, 4] : []); ctx.globalAlpha = 0.95; }",
    "    if (p.layer === 'apex' && p.state === 'former') { ctx.strokeStyle = C.muted; ctx.lineWidth = Math.max(1, lw * 0.9); ctx.setLineDash([3, 5]); ctx.globalAlpha = 0.9; }\n"
    "    else if (p.layer === 'apex') { ctx.strokeStyle = (p.kind === 'cvg' || /^CVG Express/.test(p.name || '')) ? C.cvg : C.apex; ctx.lineWidth = p.kind === 'region' && v.s < 0.2 ? 1.3 : lw; ctx.setLineDash(p.state === 'tunnel' ? [7, 4] : []); ctx.globalAlpha = 0.95; }")
rep("ctx.strokeStyle = p.kind === 'flag' ? C.warn : p.kind === 'region_station' ? C.apex : C.lower; ctx.lineWidth = 2;",
    "ctx.strokeStyle = p.kind === 'flag' ? C.warn : p.kind === 'region_station' ? C.apex : p.kind === 'cvg_station' ? C.cvg : C.lower; ctx.lineWidth = 2;")
rep("if (!(show || (S.layers.lab && p.kind === 'region_station')) || !t) continue;",
    "if (!(show || (S.layers.lab && p.kind === 'region_station') || (S.layers.lab && p.kind === 'cvg_station' && v.s > 0.06)) || !t) continue;")
rep("ctx.fillStyle = p.kind === 'flag' ? C.warn : p.kind === 'region_station' ? C.apex : (p.layer === 'label' && p.kind !== 'lower') ? C.ink : C.lower; ctx.fillText(t, lx, ly);",
    "ctx.fillStyle = p.kind === 'flag' ? C.warn : p.kind === 'region_station' ? C.apex : p.kind === 'cvg_station' ? C.cvg : (p.layer === 'label' && p.kind !== 'lower') ? C.ink : C.lower; ctx.fillText(t, lx, ly);")
# ---- picking and panel for the stations, yard and maintenance building
rep("  if (!area && S.layers.apt && S.airport) for (const L of ['cvg_building', 'cvg_runway', 'cvg_area'])",
    "  if (!area && S.layers.trk && S.tracks) for (const L of ['cvg_plat', 'cvg_shop', 'cvg_yard']) { for (const f of S.tracks.features) if (f.properties.layer === L && bbHit(f._bb || (f._bb = featBB(f)), [p[0], p[1], p[0], p[1]]) && inPoly(p, f.geometry.coordinates)) { area = f; break; } if (area) break; }\n"
    "  if (!area && S.layers.apt && S.airport) for (const L of ['cvg_building', 'cvg_runway', 'cvg_area'])")
rep("    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';",
    "    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';\n"
    "    if (L === 'cvg_plat') { const V = S.tracks.summary.cvg; kv('Platforms', fmt(V.plat) + ' m, side platforms with screen doors (this is the ' + p.side + ' one)'); kv('Rail', fmt(p.z, 1) + ' m, ' + fmt(p.depth, 1) + ' m under the ground (' + fmt(p.ground, 1) + ' m)'); kv('From CUT', fmt(p.km, 2) + ' km from the south end of platform M');\n"
    "      sub.textContent = 'CVG Express station, airside: deep-bored, GoA3 with platform screen doors (stop points from CVG Express Final.kmz)'; }\n"
    "    if (L === 'cvg_yard') sub.textContent = 'CVG Express yard (CVG Express Final.kmz); the line comes up to it from T1A; stabling tracks not drawn';\n"
    "    if (L === 'cvg_shop') sub.textContent = 'CVG Express maintenance building (CVG Express Final.kmz)';")
# ---- CUT approaches panel
old = src[src.index("  if (T.cvg) { const V = T.cvg; kv('CVG Express (M, 15-16)'"):]; old = old[:old.index('\n') + 1]
rep(old, "  if (T.cvg) { const V = T.cvg; kv('CVG Express (M, 15-16)', 'east of the APEx approach; at grade only across the Cardinal pair; own span beside the APEx bridge (' + fmt(V.span_gap, 1) + ' m between); beside the APEx through the hills, ' + fmt(V.g, 2) + '% up from ' + fmt(V.climb_from) + ' m past the bank, ' + fmt(V.over_apex.clear, 0) + ' m over the APEx before Erlanger, then level at ' + fmt(V.hold.z, 1) + ' m under the CS line, the RER B/E line and the creek valley, ' + fmt(V.rise.g, 2) + '% up to ' + fmt(V.z_deep, 1) + ' m under the airfield; stations ' + V.stations.map(s => s.name).join(', ') + ' (' + V.gaps.map(g => fmt(g)).join(', ') + ' m apart), then ' + fmt(V.yard.g_up, 1) + '% up to the yard'); }\n")
# ---- notes
rep("then climbs 1.7% from about 3.5 km past the bank, crosses over the APEx (15 m, a working value for bore over bore) just north of Erlanger, where it turns west, passes about 25 m under the CS line and runs on to CVG, the last 3.8 km on the TRIMET CVG line&rsquo;s levels. Where it goes from the end of the KMZ line to the terminals is not set: it is an airside train (the RER serves the terminals landside).",
    "then climbs 1.7% from about 3.5 km past the bank, crosses over the APEx (15 m, a working value for bore over bore) just north of Erlanger, where it turns west, and levels at 209.5 m, 40 m under the CS line. From there it is deep-bored (Ben, CVG Express Final.kmz): in its own bores under the RER B/E line to where the RER turns off north-west (E 707,285 N 4,323,668), under the creek valley east of the airport (floor about 222 m; 12 m rail to floor, a working value), then 0.76% up to 238.5 m and on under 18L/36R (762 m curve) to the terminals, an airside train with five stations (option 1): T3, T2 and T4 on a straight north-north-west, T4 under the shallow RER (working values: the RER about 12 m down, the CVG Express 15 m below it), then a 292 m curve (380 m in Ben&rsquo;s drawing, tightened so the T1B platform is straight) onto the 1969 line west through T1B and T1A. The stations are 150 m side platforms with screen doors (GoA3), at Ben&rsquo;s stop points, 366, 266, 818 and 672 m apart and 21 to 29 m below the ground; T3 is 15.3 km and T1A 17.4 km from the south end of platform M. Beyond T1A the line curves north (475 m) and comes up 2.0% to the yard and maintenance building north-west of T1A (portal about 880 m past T1A, under the tip of T1A&rsquo;s west pier). The 1969 line (Original in the KMZ, drawn as a former line) came in from the south-east on the line the RER now uses to about E 705,000 and ran west across the north end of 18L to T1A; extending 18L north cut it, and the new Terminals 2 and 3 took the line south in the bore, which joins the old line just east of T1B.")
rep("The RER stops at CVG Terminal 1 and CVG Terminal 2/3/4, landside.</p>",
    "The RER stops at CVG Terminal 1 and CVG Terminal 2/3/4, landside; the CVG Express (airside) stops under T3, T2, T4, T1B and T1A, and its yard is north-west of T1A.</p>")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v41', len(src))
