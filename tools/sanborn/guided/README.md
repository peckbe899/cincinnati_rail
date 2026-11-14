# Guided reading of a 1922 plate (13-14 November 2026)

Ben, 14 November 2026: the plate reader must do the work for every plate; fixes are made in the reader, not as
per-plate hand entries. This folder is that reader. Every pass is read twice, by readers A and B working apart, and
only what both agree on is used. All run from `data/sanborn`; crops go to a scratch folder and are not committed.

| Step | Command | What the readers do |
|---|---|---|
| 0 | a first fit (blind strip picks, a GeoTIFF, or neighbouring plates) | places today's streets on the plate to within ~30 m |
| 1 crossings | `guide.py N A SEED CROPS` | every crossing on today's map that falls on the plate (edge streets included): mark its centre, or say it is not drawn |
| 2 stations | `trace.py N stations CROPS` | a point every 60 m along every today's street: mark the street's centre line by the cross, or say it is not drawn |
| 3 merge | `merge_guided.py N` | (no readers) controls, runs, names; writes `sbg/picks22/s22-N_*.json` |
| 4 ends | `trace.py N ends CROPS`, then merge again; repeat | from the last traced point, follow the street to where it ends on the plate; rounds until every run end is read |
| 5 build | `cufp/fit.py N`, `joint/newplates.py 22-N --write`, `apply/apply.py stage`, `newsets N` | |
| 6 review | `review.py N data/sanborn/deckpage/basin.json CROPS` | each section with the built lines drawn on it: list printed streets with no line, and lines with no street |
| 7 | merge, build again | |

Briefs for every pass: `briefs.py N trace|ends|review CROPS BRIEFS [per brief]` (the crossing briefs follow the same
pattern; `brief_example.txt`).

Rules (all in `merge_guided.py`, the same on every plate):
- A street is identified by today's street id (`streets.py`: one connected run of OSM ways of one exact name), never by
  a name key: Rose Hill Avenue and Rose Hill Lane, or two runs of one name, stay apart.
- Controls: crossings both readers place within 30 px. Two of today's crossings at one plate point are one control.
  A crossing both readers mark "low" is not a control. Screening: repeatedly drop the control a thin-plate fit of the
  others misses most, while it misses by more than 8 m; one missed by more than 20 m is the wrong crossing and is not
  drawn either. A jog (both readers, different legs) puts both points in both streets, as no control.
- A street's stations and crossings, in order along it, split where both readers say "not drawn", are its runs.
- Ends are read, not guessed. A reader who follows a street onto another street ends it at that street; one who
  turns back along it is ignored.
- Two runs of different streets along the same printed line (Ross east of Imwalle is Tennessee Avenue today) are one
  street: the shorter is dropped.
- Names: the plate's printed name when two or more read copies agree on a whole name (a name cut by the crop, like
  CARTHA or WICK, is not used); else the 1922 alias in `cufp/config.json`; else today's name.
- Review: a missing street both readers report is added (the stretch both report); a missing stretch at the end of a
  run of the same name extends it; one already traced is noted. A wrong line both report: its points near the place
  are taken out, or the run is cut there.
- Fit (`cufp/fit.py`): guided crossings match OSM by today's names (`osm_a`, `osm_b`). Build (`cufp/build.py`): points
  are grouped by street id (`sid_a`, `sid_b`, `sid`) when they carry one.
