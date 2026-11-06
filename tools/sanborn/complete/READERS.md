# Reader instructions for the complete set (Part 1, 6 November 2026)

Each reader agent got this text with SCRATCH set to the jobs folder (tools/sanborn/complete/prep.py), PYTHON to the
Python used, and GROUP to its group: A00-A38 the first read, B00-B38 the second (the same jobs, shuffled within each
plate, so no job had the same pair of reader contexts). Each group is one plate's jobs, 6-19 of them.

---

You are a map reader picking street crossings on 1922 Sanborn fire-insurance plates (Cincinnati). Your reads are compared with another reader's, so work independently: do NOT open any file except your job list and the images you render yourself (no .json, picks or report files anywhere, nothing under the repository's data/ folder, nothing in the scratch folder except your job list and your own renders).

YOUR JOB LIST: SCRATCH/lists/GROUP.txt (read it first with the Read tool).

TOOL. Render part of a job's region with a red pixel grid labelled in ORIGINAL plate pixels:

    "PYTHON" "SCRATCH/crop.py" JOB OUT.jpg                  (the whole region)
    "PYTHON" "SCRATCH/crop.py" JOB x0 y0 x1 y1 OUT.jpg      (a zoom; box in ORIGINAL plate pixels, inside the job's region box)

Render ONLY into SCRATCH/work_GROUP/ (create it), reuse two or three file names, look at each with the Read tool. x to the right, y down, original plate pixels as the grid labels show. White in a region is outside the plate.

WHAT TO PICK (the project's rules, docs/sanborn INSTRUCTIONS22): the point where the two street CENTRELINES cross: the middle of the open crossing between the block corners, not a corner and not a label; for a T, where the side street's centreline meets the through street's centreline. Precision about 10 px: find the streets on the whole region first, then zoom with crops of 600-1,000 px, then 300-500 px, and read the centre off the grid. The streets are given by TODAY's names: the plate may print an older name, another suffix (Street / Avenue / Place), or no East/West prefix; say what the plate prints. The crossing is expected near the given point, but the position can be 100-200 px off. If the two streets meet more than once in the region, pick the meeting nearest the expected point and list the others. Railroads, sidings, the canal bed, creeks, inclines, park, cemetery and estate drives, factory lanes, private lanes and the grey/pink boundary bands are not streets; large spaced lettering is subdivision or estate names; numbers in circles are plate numbers. Pipe lines ("6" W. PIPE") and dashed sewers run inside streets: they are not street edges. If one of the streets is not on the plate here (it did not exist in 1922, or the plate shows something else), say not found and what you see. Say if the crossing is at or cut by the page edge or gutter.

OUTPUT: write SCRATCH/reads/GROUP.json, a JSON list with one object per job in your list:
  {"job": "66_000", "found": true, "x": .., "y": .., "kind": "cross" or "T" or "bend", "printed": ["street 1 as printed", "street 2 as printed"], "plate_edge": false, "confidence": "high" | "medium" | "low", "same_names_elsewhere": [{"x": .., "y": .., "note": ".."}], "note": ".."}
(found false: x and y null, say in the note what is there.) Names in "printed" as the plate prints them, abbreviations expanded (St. -> Street, Av. -> Avenue). Then delete the images in your work folder and reply with one line: how many found, how many not.
