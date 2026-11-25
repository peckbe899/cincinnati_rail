# Text-first stage: every report (25 November 2026)

Ben: "The identification of characters for letters and numbers needs to be run first, then double-checked by the code. If we can eliminate them from contention first, it will make the recognition of other things easier. The shapes matter here as well, because we want to be able to identify the street names and numbers too." Nothing downloaded or trained. Paths are in data/sanborn/bench_2026-11-25/text/ (not in git); scripts are copied beside this file, the hand-checked text truth is in truth/, the plan is text_first.md.

## research

I researched methods for finding and reading text on historical maps and tested the ones that need no download on plate 44. The best route for both jobs needs no download. It is to build the text-first stage from what is already installed:
- take the pieces of ink;
- peel off long lines first;
- sort each piece as character or not-character, then read it, with a small classifier fitted on our own glyphs (grouped by k-means, then labelled one cluster at a time) plus synthetic glyphs drawn from fonts already in C:/Windows/Fonts;
- group the characters into words along a fitted baseline;
- read them with formats and name lists, then check them by code;
- hand on a text mask.

This ranks first for (a), detection good enough to mask text, and for (b), reading house numbers, lot numbers and street names.

The published map spotters are the most accurate on typeset maps but fit this machine worst: mapKurator with Spotter-v2 or PALETTE, the ICDAR MapText 2024 winners built on DeepSolo, and TextFuseNet.
- They are built for Linux with CUDA, with detectron2 builds and custom CUDA operations.
- Their weights are large, and Spotter-v2's licence is non-commercial (CC-BY-NC).
- None was trained on Sanborn plates.

The general OCR tools (Tesseract 5, EasyOCR, PaddleOCR, docTR, TrOCR) were trained on photos of scenes and on documents. I expect them to read 1922 italic hand lettering poorly unless we fine-tune them (estimate).

If Ben approves one download, the most useful is the CRAFT weights (about 83 MB), as a second-opinion character detector. Next would be PARSeq (about 95 MB, plus the timm and pytorch-lightning packages), fine-tuned on synthetic Sanborn-style words to read word crops.

Nothing was downloaded or installed. No network was trained. The only fits were tiny ones on the CPU: an SVM on HOG features for each font (2,000 synthetic glyphs per font), and leave-one-out fits on 113 digits I read by eye. Repo files, edges_ben.json and rail_ben.json were not touched.

Sources (method references):
- https://arxiv.org/html/2506.15010v1 (PALETTE)
- https://github.com/knowledge-computing/mapkurator-system
- https://huggingface.co/ReadingMaps/Spotter-v2-english
- https://zenodo.org/records/13628614 (MapText 2024 slides)
- https://arxiv.org/html/2506.22589 (LIGHT, MapText comparison table)
- https://github.com/yyyyyxie/MapTextPipeline
- https://zenodo.org/records/14480731 (SynthMap+)
- https://github.com/mhliao/db
- https://huggingface.co/opencv/text_recognition_crnn
- https://huggingface.co/opencv/opencv_zoo/tree/main/models/text_detection_ppocr
- https://github.com/baudm/parseq
- https://github.com/mindee/doctr
- https://github.com/UB-Mannheim/tesseract/wiki
- https://github.com/Living-with-machines/MapReader (Spot-text docs)
- https://www.frontiersin.org/articles/10.3389/fenvs.2022.804155 (spot heights)
- https://spatial-computing.github.io/papers/chiang10icpr.pdf
- https://weinman.cs.grinnell.edu/research/maps.shtml
- https://www.github.com/ying09/TextFuseNet
- https://arxiv.org/pdf/2610.35606 (ArchiveLens, Sanborn)

### numbers

MEASURED on plate 44 (script in research/scripts/, results in research/out/):

What today's text bin holds (text_sizes.py)
- Bin 8 has 2,980,214 px, which is 44.5% of the ink, in 19,880 pieces. Plate 5 has 3,830,397 px in 23,662 pieces.
- Piece heights at the 5/25/50/75/95th percentiles: plate 44 6/12/21/29/49 px; plate 5 7/16/23/27/38 px.
- Text stroke width, median: 3.8 px on both plates.

Is a size rule enough? (label_sheets.py, read by eye)
- There are 7,508 single-glyph-sized bin-8 pieces on 44.
- I read a random 240 of them. 100 are not one readable character: merged digits (about 7%), fragments, hydrant dots, ticks, hatching, and rotated pieces I could not read.
- The other 140 are 113 upright digits, 24 upright capitals, 3 rotated digits.

Text the rule misses (missed_text.py)
- 9,411 character-sized pieces of ink are on 44. 2,342 of them are not in bin 8: 1,730 are in lot line, 414 in sewer, 159 in not sorted.
- Of a random 60 of those 2,342, 18 are clearly the italic digit 1 and 6 more may be. The rest are dashes of dashed lines.
- Estimate: 700-940 '1's on 44 sit outside bin 8.

Glyph clustering (glyph_cluster.py, cluster_purity.py)
- k-means with 80 clusters on all of plate 44 took 9.7 s wall time.
- Of the 60 largest clusters, 30 hold a single character (judged by eye). Those 30 hold 45.1% of the pieces.
- 82 of the 104 hand-read sample pieces that fell in those 30 clusters carry the cluster's label.

Fonts against real digits (font_test.py; 113 hand-read upright digits; about 0.04 either way is noise)
- SVM on HOG features, fitted only on 2,000 synthetic glyphs of one font: 0.40 to 0.88.
  - Best: ARIALNI.TTF 0.876; TCCM____.TTF slanted 0.858; OpenCV Hershey complex italic 0.832; FRAMDCN.TTF slanted, trebucit, timesi and bahnschrift slanted 0.823 each; ariali 0.814.
  - Worst: GILC 0.434, segoepr 0.496, segoesc 0.531.
- Mix of the top 5 fonts: 0.912 (103/113). Template matching on the same mix: 0.752.
- Fitted on the real digits alone, leave-one-out: 0.841 nearest neighbour, 0.805 SVM.
- Mix plus the real digits, leave-one-out: 0.912.
- The errors of the mix: 3 read as 5 twice; 0 as 5; 0 as 9; 1 as 4; 1 as 7; 2 as 1; 5 as 6; 8 as 1; 8 as 6.
- Stroke-to-height ratio of the real digits: 0.114.

The AMD GPU through DirectML (dml_ops.py, venv torch 2.4.1)
- These run on it: convolution with batch norm, attention, transformer layers, grid_sample, roi_align, deform_conv2d, ctc_loss.
- nn.LSTM and nn.GRU fail on it, even for inference only.

Stroke Width Transform and MSER (swt_mser.py)
- On 0.55 and 1.76 MP crops: SWT gave 193 and 307 boxes in 0.11 and 0.19 s; MSER took 0.03 and 0.09 s.
- SWT misses whole street names. This comes from the pictures; I made no score.

PUBLISHED (from the sources)
- PALETTE on Rumsey-309:
  - finding text: F 84.8 when trained only on synthetic maps, 90.3 when fine-tuned;
  - reading whole words: F 69.8 / 75.9 without a name list, 78.8 / 83.6 with a full name list.
- MapText 2024 Strong Pipeline: word-finding F 93.8 on Rumsey.
- MapText 2024 had 8 teams and 44 submissions. The organisers' takeaway: finding text works pretty well; reading and linking words have large room for improvement.
- A TrOCR-based MapText 2024 entry scored 18.46% on one leaderboard column, against 76% for the winner. I did not confirm which column.
- Spot heights on topographic maps (Mask TextSpotter v3):
  - 0% when trained only on public scene-text datasets;
  - 63% with 35 map examples, 82% with 245, 95.6% with 934 augmented examples.
- Chiang and Knoblock (2010), rotating each map string level before running a commercial OCR: characters 96.2% precision and 94.7% recall; words 80.6% and 84.1%.
- Weinman (2017): matching readings against place names cut word errors by 36%.
- SynthMap+ synthetic training set: 38.8 GB, licence CC-BY 4.0.
- Model sizes: opencv_zoo PP-OCRv3 text detector 2.42 MB; CRNN reader 33.8 MB; EasyOCR's CRAFT about 79 MiB and its English reader about 14 MiB; PARSeq 23.8 M parameters; docTR's CRNN 15.8 M parameters.

ESTIMATES (not measured)
- Tesseract installer about 50 MB; its eng best/fast data about 15 / 4 MB.
- TrOCR small / base / large about 0.25 / 1.3 / 2.2 GB.
- PaddlePaddle CPU wheel 100 MB or more.
- CRAFT on one full plate: 2-4 min on the CPU.
- The per-character route should reach 0.95 or better on clean digits once our own and synthetic glyphs are combined and the sequence checks are added.

### findings

- **R1 Today's text bin is a size rule: it lets non-text in and leaves text that touches lines out** - 44_bins.png: bin 8 is 44.5% of the ink (text_sizes.py).
- Of 240 random single-glyph-sized bin-8 pieces, 100 are not one readable character: merged digits, fragments, hydrant dots, ticks, hatching (label_sheets.py, by eye).
- 2,342 of 9,411 character-sized ink pieces lie in other bins. In a random 60, 18-24 are the italic digit 1, which gives an estimated 700-940 on the plate (missed_text.py, pics/missed_44.png).
- In the pictures (bins_overlay.py: pics/44_bins_houses.jpg, 44_bins_knowlton.jpg):
  - '6" W. PIPE' sits in the water-pipe bin and '12" SEWER' in the sewer bin;
  - digits touching building outlines are in the building bin;
  - in one block the lot numbers 151, 136, 158, 140, 137 and 149 are in the lot-line bin. So what: The text mask has to come from recognising characters, not from the size of the piece. The italic '1' has the same shape as one dash of a dashed line, so context must decide: a regular row of dashes along a line, or a mark next to other digits or inside a building (a story height). Pipe labels should be text and also tell the pipe rule which line they name.
- **R2 Lettering measurements every method must fit** - Text pieces: median height 21 px on 44 and 23 px on 5. 95% are under 49 and 38 px. Stroke width about 3.8 px (text_sizes.py).
- Real digits: stroke-to-height 0.114 (font_test.py).
- In the full-size crops (look44.py, pics/44_crop_*.jpg) the lettering comes in these styles:
  - upright monoline capitals for street names, often rotated 90 degrees or diagonal;
  - condensed italic digits for house and lot numbers and dimensions (25', 126.84');
  - italic capitals for owner names and pipe labels;
  - bold upright block numbers;
  - estate names letter-spaced 1.5-2 letter heights apart along a diagonal ('L U D L O W ' S  E S T.');
  - lowercase 'Creek' spread along the curving creek;
  - bearings such as N 22° 30' W. So what: - Detectors must run on the full 300 dpi scan without shrinking it.
- Word grouping needs a long reach but strict alignment along a straight or curved line.
- Reading needs the baseline angle, plus a check of 0/90/180/270 degrees for vertical street names.
- **R3 Fonts already on this machine can stand in for Sanborn digits (synthetic training with no download)** - Synthetic glyphs only (2,000 per font), SVM on HOG features, tested on 113 hand-read upright digits of 44 (font_test.py, out/font_test.json, pics/font_samples.png):
  - Arial Narrow Italic 0.876; Tw Cen MT Condensed slanted 0.858; OpenCV Hershey complex italic 0.832; Franklin Gothic Medium Condensed slanted, Trebuchet italic, Times italic and Bahnschrift slanted 0.823 each; Arial Italic 0.814.
  - Handwriting-style fonts do badly: Segoe Print 0.50, Segoe Script 0.53, Gill Sans Condensed 0.43.
  - The five best fonts together reach 0.912.
- Street-name capitals, judged by eye only (font_caps.py, pics/font_caps.png): wide monoline gothic, closest to OpenCV Hershey Simplex, Arial and Bahnschrift. Franklin Gothic is too heavy and Century Gothic too light. So what: Synthetic Sanborn-style characters and words can be drawn locally, with italic slant and Sanborn's stroke weight, to train the character classifier or a small reader. Use several fonts together, not one.
- **R4 Glyph clustering makes hand labelling cheap** - 7,508 single-glyph pieces on 44 went into 80 k-means clusters in 9.7 s (glyph_cluster.py, pics/clusters_44_0..3.png).
- 30 of the 60 largest clusters hold one character (judged by eye), with 45% of all pieces.
- 82 of the 104 hand-read sample pieces in those clusters carry the cluster's label (cluster_purity.py).
- '2' alone fills at least 5 clusters. The mixed clusters come from rotated text, digits touching their neighbours, and symbols. So what: Labelling one cluster at a time gives hundreds of checked glyphs in about 30-60 decisions (estimate). To do better:
- turn text upright using its line direction before clustering;
- split pieces wider than about 0.8 of their height;
- keep the junk clusters (hydrant dots, ticks, hatching, dashes) as a 'not a character' class. That class is exactly what the text mask needs.
- **R5 Own glyphs vs synthetic: both land near 0.9 on clean digits; the rest must come from code checks** - Leave-one-out on 112 real digits: 0.841 (nearest neighbour) and 0.805 (SVM).
- Synthetic mix of five fonts: 0.912. Mix plus the real digits: also 0.912.
- The remaining errors: 3 read as 5 twice, 0 as 5, 0 as 9, 1 as 4, 1 as 7, 2 as 1, 5 as 6, 8 as 1, 8 as 6. Mostly blotted or crowded glyphs (font_test.py).
- This test set is only the pieces I could read. 42% of the sampled pieces were not single characters. So what: Per-character accuracy alone will not reach Ben's goal. The code checks he asked for are needed for the last 5-10%:
- house numbers along a block face rising in steps of 2, with odd and even sides and one hundred-block;
- dimension formats such as 25' and 126.84';
- pipe-label formats such as 6" W. PIPE;
- street names matched to a name list.
In published work, matching against a name list added about 8 points (PALETTE) and cut word errors by 36% (Weinman 2017).
- **R6 What the AMD GPU can run (DirectML, torch 2.4.1)** dml_ops.py, out/dml_ops.json:
- run on DirectML and match the CPU: convolution with batch norm, scaled dot-product attention, a transformer encoder layer, grid_sample, roi_align, deform_conv2d, ctc_loss;
- fail: nn.LSTM and nn.GRU (NotImplementedError aten::_thnn_fused_lstm_cell), even for inference only. So what: - Readers built on LSTMs would run on the CPU only: EasyOCR's reader, docTR's crnn, the opencv_zoo CRNN, and any small reader we write with an LSTM.
- These would run on the GPU: CRAFT, DB, PARSeq, TrOCR and our own U-nets.
- The DETR-style map spotters need custom CUDA attention code; grid_sample, which runs here, could stand in for it, but that port is a project of its own.
- **R7 Published map text spotting is strong on typeset maps but has never seen Sanborn lettering** - PALETTE (2025, used in mapKurator on 60,000+ Rumsey maps), on Rumsey-309:
  - finding text: F 84.8 trained on synthetic maps only, 90.3 fine-tuned;
  - reading whole words: F 69.8 / 75.9 without a name list, 78.8 / 83.6 with one.
- MapText 2024 (8 teams, 44 submissions): joint winners were MapTest (Tianjin) and the MapText Strong Pipeline (Bilibili; DeepSolo/DNTextSpotter with a ViTAEv2-S backbone; word-finding F 93.8 on Rumsey). The organisers say finding text works pretty well, while reading and linking words have large room for improvement.
- MapText 2025 added a Chinese-character map set and the synthetic SynthMap+ set (38.8 GB, CC-BY 4.0).
- Spotter-v2's weights are CC-BY-NC 2.0. mapKurator runs in Docker on Linux with a CUDA GPU. Its m_sanborn folder is geocoding, clustering and GeoJSON, not text reading.
- Spot heights on topographic maps: 0% from a model trained only on public datasets, 63% with 35 map examples, 82% with 245, 95.6% with 934 augmented ones. So what: No published model will read 1922 Sanborn italic digits out of the box. The few hundred examples of our own glyphs matter more than which model is chosen. Running the published spotters here would mean a Linux/CUDA port and a non-commercial licence, for training data unlike ours.
- **R8 General OCR: fit to this machine and this lettering** All from published pages except where marked:
- Tesseract 5:
  - CPU only, Apache-2.0, an installer of about 50 MB (estimate);
  - needs level, deskewed lines;
  - fine-tuning needs a Unix toolchain;
  - Chiang and Knoblock (2010) reached 80.6% precision and 84.1% recall on words only after rotating each map string level first.
- EasyOCR: CRAFT plus a CRNN reader; about 94 MB of weights, Apache-2.0; its GPU option is CUDA only; its LSTM reader would run on the CPU (measured).
- PaddleOCR: needs the PaddlePaddle framework (no AMD GPU route on Windows, estimate); PP-OCRv4 mobile detector 4.6 MB and English reader 7.4 MB; its DB detector as ONNX (2.42 MB, opencv_zoo, Apache-2.0) runs in the cv2.dnn already installed.
- docTR: Apache-2.0 (estimate); DB or FAST detectors with CRNN or PARSeq readers; assumes level pages unless told otherwise.
- TrOCR: 0.25-2.2 GB (estimate); needs the transformers package; slow on the CPU; one TrOCR-based MapText entry scored low.
- PARSeq: 23.8 M parameters, code Apache-2.0, weights licence not stated; transformer layers run on DirectML (measured).
- The opencv_zoo CRNN reader (33.8 MB) reads only 0-9 and a-z, so it cannot keep ' " . or -. So what: None is a drop-in answer for Sanborn lettering. A small, dependency-free download is the cv2.dnn route: the DB detector ONNX for finding text, and its CRNN reader. For reading, PARSeq fine-tuned on synthetic Sanborn-style words is the best general option, but only after our own route has been tried.
- **R9 Text detectors already inside OpenCV (SWT, MSER) are weak here** swt_mser.py on two crops of 44 (pics/swt_houses.jpg, swt_ludlow.jpg, mser_*.jpg): SWT boxes many single digits but misses whole street names such as KNOWLTON, and boxes pieces of lines and building corners. It took 0.1-0.2 s per crop. No score was made, because no text ground truth exists yet. So what: Use stroke width (about 4 px) only as one clue in the character classifier, not as the detector.
- **R10 Ranking** (a) Detection only, enough to mask text:
1. Rules plus our own character / not-character classifier (no download): peel lines, settle '1' against dash by context, glyphs from clusters plus fonts.
2. CRAFT (83 MB download): a character-level heat map that copes with spaced and curved letters; it runs on DirectML; use it as a second opinion or as a teacher.
3. Our own text-pixel U-net, trained on synthetic text pasted onto Sanborn paper plus route 1's mask (needs Ben's OK to train).
4. The PP-OCR DB detector ONNX in cv2.dnn (2.4 MB).
5. Detection from EasyOCR or docTR.
6. PALETTE, Spotter-v2 or the MapText winners.
7. TextFuseNet.
8. SWT or MSER.

(b) Reading street names and numbers:
1. Our own character classifier, plus word grouping, formats, name lists and number-sequence checks (no download).
2. Our own small reader that reads whole strings, trained from scratch on synthetic Sanborn strings (no download; needs Ben's OK to train).
3. PARSeq, fine-tuned.
4. Tesseract 5 with character whitelists on level word crops.
5. The opencv_zoo CRNN reader in cv2.dnn.
6. The EasyOCR, PaddleOCR or docTR readers.
7. TrOCR.
8. The end-to-end map spotters. So what: Build route 1 first for both jobs. It runs now, takes seconds per plate, and its 'not a character' class gives the text mask directly. Add CRAFT, if Ben approves the download, as an independent check on the mask. Train a reader only if touching digits and rotated names defeat the per-character route.
- **R11 Name lists and word labels already in the repo, for reading street names and checking them** - data/sanborn/streetmap/22-44.json gives 60 named street pieces on plate 44: Chase, Apple, Palm, Knowlton, Spring Grove, Vandalia, Fergus, Dane, Ludlow and others.
- data/sanborn/picks22_reads holds street names at crossings for plates 25, 28, 39, 40, 43, 44, 45 and 80. Each was read twice independently and the reads merged (README). So what: These give a name list for the matching step and a test set for street-name reading on 8 plates. A full list of 1922 Cincinnati street names would extend the list to every plate and allow the check across adjoining plates.

### needs Ben

Downloads. None is needed for the first build. Each would need Ben's own approval; sizes marked 'about' must be checked first.
1. CRAFT text detector weights, craft_mlt_25k.pth.
   - Source: the clovaai/CRAFT-pytorch README on GitHub, which links to Google Drive.
   - Size: about 79 MiB / 83 MB.
   - Licence: MIT (to confirm).
   - What it gives: a per-character text heat map that copes with curved, rotated and letter-spaced words. It runs with the installed torch, on DirectML. It would be a second opinion on the text mask.
2. PaddleOCR's DB text detector in ONNX form, text_detection_en_ppocrv3_2023may.onnx.
   - Source: huggingface.co/opencv/opencv_zoo.
   - Size: 2.42 MB. Licence: Apache-2.0.
   - What it gives: word boxes through the cv2.dnn already installed. Optionally also the CRNN reader text_recognition_CRNN_EN_2021sep.onnx (33.8 MB, Apache-2.0), which reads 0-9 and a-z only.
3. PARSeq text reader.
   - Source: github.com/baudm/parseq releases or torch.hub.
   - Size: about 95 MB, plus the pip packages timm and pytorch-lightning.
   - Licence: code Apache-2.0; weights licence not stated.
   - What it gives: a strong word reader to fine-tune on synthetic Sanborn words.
4. Tesseract 5.
   - Source: the UB Mannheim Windows installer.
   - Size: about 50 MB. Licence: Apache-2.0.
   - What it gives: a CPU line reader with character whitelists. Expected weak on italic hand lettering without fine-tuning.
5. Not recommended: mapKurator, Spotter-v2 or PALETTE (Linux/CUDA, Spotter-v2 non-commercial), TrOCR (0.25-2.2 GB), PaddlePaddle (no AMD route), TextFuseNet (detectron2 build), and the 38.8 GB SynthMap+ set.

Training. Two optional steps need Ben's OK. They are separate from the block U-nets he asked to hold.
- A small text-pixel U-net.
- A small reader that reads whole strings, trained from scratch on synthetic Sanborn strings.

Labels Ben could give, or check:
- Spot-check my reading of the 240 sampled glyphs in out/label_sample_44.json (pictures: pics/label_44_*.png).
- Name the 80 glyph clusters, about 30-60 decisions (pics/clusters_44_*.png); Claude can propose names for him to check.
- A list of 1922 Cincinnati street names, if he has one, for matching names and checking them across adjoining plates.

Conventions to decide:
1. Which marks count as text for the mask? Candidates are hydrant circles, the 'O' manhole marks, ditto marks ("), story heights inside buildings, and hook marks.
2. Should pipe and sewer labels be masked as text, linked to the line they name? I suggest yes.
3. Is a block side running through a row of house numbers still a side? This is round 2's question 3.
4. House-number rules for 1922 Cincinnati: are odd and even numbers always on opposite sides, numbered by hundred-blocks, and stepping by 2 (with ranges like 1424-22-20)?

### files

Everything is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/research/. A second copy of the scripts and out folders is in its _second_copy/ subfolder.

Scripts (run with python -B; dml_ops.py and swt_mser.py use the unet venv python):
- scripts/look44.py
- scripts/bins_overlay.py
- scripts/text_sizes.py
- scripts/glyph_cluster.py
- scripts/label_sheets.py
- scripts/cluster_purity.py (run it from the research folder)
- scripts/font_test.py
- scripts/font_caps.py
- scripts/missed_text.py
- scripts/swt_mser.py
- scripts/dml_ops.py

Results:
- out/options_ranked.json: every method with its download, size, licence, fit, evidence, and both rankings.
- out/font_test.json
- out/cluster_purity_44.json
- out/label_sample_44.json: hand labels of 240 glyphs, read by eye.
- out/missed_text_44.json
- out/text_sizes_44.json and out/text_sizes_5.json
- out/dml_ops.json
- out/glyphs_44.npz

Pictures:
- pics/44_overview.jpg
- pics/44_crop_*.jpg
- pics/44_bins_houses.jpg and pics/44_bins_knowlton.jpg
- pics/clusters_44_0..3.png
- pics/label_44_0..3.png
- pics/missed_44.png
- pics/font_samples.png
- pics/font_caps.png
- pics/swt_houses.jpg, pics/swt_ludlow.jpg, pics/mser_houses.jpg, pics/mser_ludlow.jpg

Copies of two downloaded PDFs read during the research are in the session scratchpad (C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/e0300a62-1bbe-41d3-b7f0-0f91cd3e9ee8/scratchpad/pdfs/) and are not part of the deliverable.

## inventory

I made the lettering inventory and the hand-checked text truth. Nothing was downloaded or installed, no network was trained, and nothing outside data/sanborn/bench_2026-11-25/text/inventory/ was written.

What was made:
- Thumbnails of the 8 plates.
- 107 catalogue examples on all 8 plates, with 1:1 crops and contact sheets:
  - title, scale notes and copyright;
  - the KEY;
  - adjoining sheet numbers;
  - straight, rotated and curved street and creek names;
  - house numbers, lot numbers and lot dimensions;
  - block numbers;
  - owner, estate and firm names;
  - building names;
  - pipe and sewer labels;
  - railroad names.
- Measurements of every truth word and catalogue example: glyph height, stroke width, joined to a line or not, glyphs merged, colour and orientation.
- A score of ink_bins bin 8 against the truth, with what it misses and what it wrongly takes.
- The bin 8 share of ink on all 8 plates.

The truth set:
- 6 crops of 1500 x 1000 px: T1, T2 and T3 on plate 44, T4 on 1A, T6 and T7 on 5.
- 1,012 words, each read by eye and typed as a centre line, then snapped by code.
- A per-pixel mask with four values: 0 paper, 1 non-text ink, 2 text ink, 3 don't care (where a glyph and a line share ink).
- Every check tile was looked at, and errors were fixed with exclude and don't-care boxes.
- truth/README.md says how it was made and how to score against it.
- A 7th crop, on plate 1A at Central Parkway, was planned but not annotated.

What it shows:
- All lettering is black. Colour cannot separate text from lines; only shape and size can.
- Bin 8 gets about 85% of the text with about 85% precision (F1 0.85).
- Its misses are mostly glyphs joined to lines, which go to the building-outline or lot-line bins. Most single "1"s (story heights) are lost, and half the ditto marks.
- What it wrongly takes is mostly bits of line rather than whole lines: hook marks and symbols, stubs cut off lines and outlines, thin dashes (some from sewers and pipes), streetcar bars and hydrant dots.

### numbers

MEASURED. Each number names the script in inventory/scripts/ that made it.

Truth set (build_truth.py):
- 6 crops, 1,012 words:
  - lot dimensions 284, lot numbers 258, story heights 188, house numbers 98, owner names 51, ditto marks 38;
  - railroad letters 26, street names 22, pipe labels 17, sewer labels 14, block numbers 7, building names 5;
  - other 3, adjoining sheet number 1.
- Flags: 85 words unsure, 92 partial, 21 runs (rows of house numbers boxed as one word).
- Text ink in each crop: 114k, 59k, 53k, 95k, 47k and 128k px.
- Text is 31-47% of the scored ink in each crop.
- The mask's ink agrees with N_bins.png's ink on 99.97-99.99% of pixels (bin8_eval.py).

Bin 8 against the truth (bin8_eval.py), pooled over the 6 crops:
- 419,451 text px found, 71,680 px wrongly called text, 76,079 text px missed.
- Precision 0.854, recall 0.846, F1 0.850. Per crop F1: T1 0.839, T2 0.860, T3 0.900, T4 0.840, T6 0.867, T7 0.835.

Where the missed text went:

| bin it went to | share of missed text |
|---|---|
| building outline | 51% |
| lot line | 30% |
| water pipe | 7% |
| block line | 5% |
| sewer | 3% |
| streetcar | 1% |
| railroad | 1% |

- Recall is 0.761 for words joined to a line and 0.926 for free words.

Recall by kind:

| kind | recall | words mostly missed |
|---|---|---|
| street names | 0.985 | |
| house numbers | 0.972 | 1 of 98 |
| railroad letters | 0.967 | |
| building names | 0.967 | |
| block numbers | 0.859 | |
| pipe labels | 0.796 | |
| lot dimensions | 0.791 | 47 of 279 (43 of them joined to a line) |
| sewer labels | 0.789 | |
| owner names | 0.772 | |
| lot numbers | 0.769 | 51 of 254 (45 joined) |
| story heights | 0.706 | 64 of 183: 31 of the 36 single "1"s and 25 of the 84 "3"s |
| ditto marks | 0.477 | 20 of 37 |

What bin 8 wrongly takes, by shape of the piece:

| class | what it is | share | pieces |
|---|---|---|---|
| marks | hook marks, symbols, curved bits | 39% | 486 |
| stubs | bits cut off lines and outlines | 27% | 224 |
| thin dashes | dashes of sewer, lot and building lines, rail ticks | 16% | 142 |
| heavy bars | streetcar dashes | 10% | 24 |
| blobs | hydrant dots | 8% | 10 |

- Of the thin-dash pixels, 4,466 px lie within 30 px of pipe or sewer ink.

Bin 8 share of all ink per plate (from N_bins.json, collected by bin8_eval.py):

| plate | bin 8 share of ink | median bin 8 piece (px) |
|---|---|---|
| 44 | 44.5% | |
| 1A | 39.5% | |
| 5 | 37.0% | |
| 90 | 39.0% | |
| 30 | 41.1% | |
| 60B | 42.2% | |
| 47 | 54.0% | 21 (others 49-134) |
| 54A | 38.5% | |

Glyph height in full px, median and p10-p90 (measure.py, truth words and catalogue, partial words and runs left out):

| kind | 100 ft | 200 ft | 400 ft |
|---|---|---|---|
| lot dimensions | 18 (11.5-21) | | 13 |
| sewer labels | 17 | 15 | |
| pipe labels | 19 | | |
| house numbers | 25 (22-27) | 17.5 (n=2) | |
| lot numbers | 27 (16-35) | 27 | 30 (n=5, numbers in parentheses) |
| story heights | 28 (19-31) | | |
| railroad letters | 30 | | |
| owner names | 31 (23-46) | 37.5 | 14 (n=2) |
| building names | 24 | | |
| street names | 45 (26-50) | 37 (32-40) | 24 (n=3) |
| block numbers | 51 (40-59) | 37 | |
| ditto marks | 9.5 | | |
| KEY entries | | 24 | |
| adjoining sheet numbers | 80 (n=1) | 133 (n=2) | 136 (n=1) |
| sheet numbers in the title | | 198-200 | 197 |

Stroke width in px (measure.py; even widths read 1 px low):
- 1-3 for lot dimensions;
- 3 for house numbers, lot numbers, story heights, owner and railroad lettering;
- about 6 (3-7.4) for street names at 100 ft, 5 at 200 ft;
- about 4 for block numbers;
- 8-10 for adjoining sheet numbers;
- 33 for sheet numbers.

Share of words joined to a line (measure.py):

| kind | joined to a line |
|---|---|
| pipe labels | 62% |
| lot dimensions | 57% |
| owner names | 50% |
| house numbers | 42% |
| lot numbers | 42% |
| block numbers | 38% |
| sewer labels | 36% |
| story heights | 33% |
| street names | 27% |
| ditto marks | 3% |

Share of words with fewer glyph pieces than characters (glyphs merged):
- sewer labels 55%, house numbers 29%, lot dimensions 28%, pipe labels 23%, lot numbers 20%, street names 18%.

Orientation at 100 ft (measure.py):

| kind | horizontal | vertical | oblique | curved |
|---|---|---|---|---|
| lot dimensions | 132 | 99 | 35 | |
| house numbers | 20 | 28 | 31 | 2 |
| street names | 13 | 4 | 5 | |
| lot numbers | 234 | 1 | 7 | |
| story heights | 179 | | | |

Colour (ink_colour.py, measure.py):
- Text stroke centres are L* 27-36, a* 0-6, b* -9 to +6.
- All ink is L* 34-37 (median per plate); paper is L* 76-84.
- Red-tinted ink is at most 0.07% of the ink on each plate. By eye, its largest pieces (152 px) are the centrefold crease through pink buildings. No red lettering was found.

Catalogue examples, share of their automatic (not hand-checked) text pixels in bin 8 (catalogue_bin8.py):

| kind | share in bin 8 |
|---|---|
| adjoining sheet numbers | 1.00 |
| scale notes | 0.99 |
| street names | 0.99 |
| title | 0.98 |
| KEY | 0.95 |
| building names | 0.93 |
| lot numbers | 0.87 |
| lot dimensions | 0.86 |
| block numbers | 0.79 |
| owner names | 0.78 (GROSBECK'S SUBDIV. 0.52) |

ESTIMATES:
- On 100 ft plates the true text share of ink is about the same as the bin 8 share, about 37-45%, because precision is about equal to recall on the crops.
- Plate 47's 54% is inflated by small closed building outlines and dashed boundary lines taken as text. That is by eye, from one region; its precision is not measured.

### findings

- **F1 All lettering is black, so text must be told from lines by shape alone** Text stroke centres are L* 27-36, a* 0-6, b* -9 to +6. All ink on the 8 plates is L* 34-37 (ink_colour.py, measure.py). Red-tinted ink is at most 0.07% of the ink, and its largest pieces are the centrefold crease in pink buildings (ink_colour_5.jpg, looked at). The KEY lists house numbers, lot dimensions, story heights, auditor's and actual lot numbers, block numbers and sheet numbers, all printed in black. So what: Colour cannot pull out the text. Shape, size and grouping must.
- **F2 The lettering falls into clear size classes** Glyph height at 100 ft: ditto marks about 10 px; lot dimensions and pipe and sewer labels 17-19; house numbers 25; lot numbers, story heights and corridor letters 27-30; owner names 31; street names 45; block numbers 51; adjoining sheet numbers 80-136; sheet numbers 200. Strokes are 1-3 px for small numbers and about 6 for street names. At 200 and 400 ft the street names shrink (37, then 24 px) and the numbers stay about the same (measure.py; 200 and 400 ft have few examples). So what: A text detector can use a few size bands rather than one cut-off. Today's TEXT_MAX of 130 keeps titles only because the margin ground is 'not known'. Single 1-px-stroke lot dimensions (11-21 px tall) are the smallest real text and look like dashes.
- **F3 Glyphs joined to lines are the main thing bin 8 misses** Recall is 0.761 for words joined to a line and 0.926 for free ones. Of the missed text, 51% went to building outline, 30% to lot line, 7% to water pipe and 5% to block line. 43 of the 47 mostly-missed lot dimensions and 45 of the 51 mostly-missed lot numbers are joined to a line. Share of words joined to a line: pipe labels 62%, lot dimensions 57%, house and lot numbers 42% (bin8_eval.py, measure.py). So what: A text-first stage has to separate glyphs from the lines they touch, not just sort whole pieces. The truth marks the shared ink as don't care (3), so this is scored fairly.
- **F4 Single figure 1s and ditto marks are lost to the dash rules** 31 of the 36 single "1" story heights are mostly missed; story heights overall have recall 0.706. Ditto marks have recall 0.477 (20 of 37 mostly missed). Story "3"s are lost when they touch building outlines (25 of 84). The pictures measure/bin8_err_T1.jpg and bin8_err_T7.jpg show them in red. So what: A straight 30-px stroke inside a building or lot is usually a figure 1, not a lot-line dash. The rule needs context: is there a building fill round it, are there other figures in a row, is it alone. This also bears on Ben's 'numbers resisted in training': these 1s are counted as line ink today.
- **F5 What bin 8 wrongly takes is mostly bits of line and symbols, not whole lines** Bin 8 wrongly takes 71,680 px. By shape of the piece: hook marks, symbols and curved bits 39%; stubs cut off lines and outlines 27%; thin dashes 16% (4,466 px of them within 30 px of pipe or sewer ink); heavy streetcar bars 10%; hydrant dots 8% (bin8_eval.py). On 400 ft plate 47, by eye, small closed building outlines and dashed boundary lines go to bin 8; its bin 8 is 54% of the ink, with a median piece of 21 px. So what: Removing text with bin 8 as it is would also remove sewer and pipe dashes, streetcar dashes and line ends. That would hurt exactly the rail and pipe rules it is meant to help. The text mask needs these as negatives; the truth labels them non-text.
- **F6 The house-number rows against block lines are found by bin 8 but come too late for the rail rule** House numbers have recall 0.972 in the truth crops. That includes T7, the George St and Sixth St rows that made 14 false tracks in the rail5 report. The digits are about 25 px tall, 42% of the words are joined to a line, and 29% have merged glyphs (measure.py). In ink_bins the rail rule runs before the small-piece text sort. So what: This supports Ben's order: run text first, then the rail and line rules on the ink that is left. On rows along a block face the text mask must keep the block line itself, so mask only the digits and mark the shared pixels as don't care.
- **F7 Orientation: numbers are mostly upright, labels along streets are rotated** Lot numbers are 234 of 242 horizontal; story heights 179 of 179. Lot dimensions: 132 horizontal, 99 vertical, 35 oblique. House numbers along street faces: 20 horizontal, 28 vertical, 31 oblique, 2 curved. Street names: 13 horizontal, 4 vertical, 5 oblique. The creek names ("Mill", "Creek") and some street runs are curved (measure.py, catalogue). So what: A reader must handle any angle for street names, house numbers and lot dimensions. Lot and story numbers can be read upright. House-number runs follow the block face, so the angle of the nearest block line is a good prior.
- **F8 Spaced names need wide grouping and must not be grouped across rail ticks** Many names are spaced capitals 50-120 px apart, often crossed by lot lines:
- estate and subdivision names (HOFFNER'S 6TH, LANGLAND, J.C. LUDLOW'S EST., LONGWORTH'S BLOCK 22, Wm WOLFF ET AL SUBDIV'N);
- railroad names inside the corridors (V A N D A L I A R. R., the B&O letters);
- THE AMERICAN CAN Co. and OUT LOT 77.
Automatic text pixels for owner names are only 0.78 in bin 8 (GROSBECK'S SUBDIV. 0.52; catalogue_bin8.py). Inside rail corridors, ticks about 20 px long sit beside letters 22-30 px tall (truth T2). So what: Group words along a line or gentle curve with a wide gap allowance. In a rail corridor, letters must be told from ticks by shape: a tick is a straight bar crossing the rail line. The truth boxes these letters one by one, with a g: group label giving the name.
- **F9 The 140 ink threshold breaks or drops faint glyph parts** One T1 ditto mark lies wholly above L 140, so it is not ink. Ink and words were looked at on the check tiles. Some words have more glyph pieces than characters (for example 4 of 15 numbers in a 400 ft example). Six truth words snapped to nothing: they are faint or misplaced and kept as typed. So what: A reader may want a second, looser threshold inside a found word box to complete the glyphs (an idea, not tested). The truth mask uses ink_bins' threshold, so scores stay comparable with N_bins.png.
- **F10 The margin lettering is easy and well separated** Automatic text pixels in bin 8 (catalogue_bin8.py): KEY 0.95, title 0.98, scale notes 0.99, adjoining sheet numbers 1.00. KEY lettering is 21-26 px tall in italic block capitals. Sheet numbers are 133-200 px with 8-33 px strokes. The uncut sheets 90, 30 and 47 carry them; the cut pieces 44, 1A, 5, 60B and 54A do not. So what: The title, scale and KEY can be found by fixed position and size and read once per sheet. The adjoining sheet numbers (big, isolated, near the edge) give a check on which plates adjoin, for the street-name consistency check.

### needs Ben

Downloads: none were made or needed. For the later reading step, Tesseract 5 is an option: from the UB Mannheim Windows build on GitHub, an installer of about 50-80 MB, Apache-2.0 licence. By judgement, untested, its general models read rotated italic map digits poorly. A small glyph classifier fitted on the truth glyphs may do better and needs no download.

Things to check by eye:
- **Readings I could not make sure of (85 words are flagged unsure in truth/T*_words.json):**
  - T2 (plate 44): the B&O corridor letters read "...T I M O R E E & O H I O R. R.", with two E's. A lone N stands in the lower corridor near (2950, 3228).
  - Plate 44: the big spaced name ending "R'S" near (3200-3300, 2600-2830). Which name is it?
  - Plate 5: a big W at about (1790, 4010) and an O at (1975, 3718) look like one spaced name. Which?
- **Conventions to confirm.** I counted as text:
  - ditto marks, primes, ±, °, ½, hyphens in number ranges, parentheses and "No";
  - story-height figures.

  I counted as not text:
  - hook marks on lot lines, hydrants and alarm boxes, the X of stables and rail ticks;
  - the valve sign inside "35" W. PIPE" (don't care).

  The title and scale underlines are kept as text in the catalogue only; the truth crops have none.
- **Runs.** Should dense house-number rows stay as one box per run, or be split one number per box? There are 21 runs, mostly on T7, and the mask is the same either way.
- **A 7th crop.** Plate 1A, 0,1200-1500,2200 (Central Parkway) was planned and not annotated. Do you want it?

Safety of the work: by the hard rule, everything is in one folder only, data/sanborn/bench_2026-11-25/text/inventory/. There is no second copy. You may want it pushed to your backup.

### files

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/inventory/

Truth set (for scoring):
- truth/README.md: how the truth was made, its format, conventions and limits.
- truth/crops.json: the 6 crop windows.
- truth/T1_mask.png, T2_mask.png, T3_mask.png, T4_mask.png, T6_mask.png, T7_mask.png: 0 paper, 1 non-text ink, 2 text ink, 3 don't care.
- truth/T1_words.json ... truth/T7_words.json: one entry per word, with reading, kind, flags, rotated box, axis box, angle, height and touches_line.
- truth/annot/T*.txt: the hand annotations.
- truth/work/T*_zoom_RC.jpg: the reading tiles.
- truth/work/T*_check_RC.jpg: the check tiles.

Inventory:
- catalogue.txt: 107 hand-placed examples across the 8 plates.
- crops/<plate>/NN_kind.png: 1:1 crops.
- crops/sheet_<plate>.jpg: contact sheets, with each example and its text pixels in red.
- thumbs/<plate>_s8.jpg: 1/8 thumbnails with a 1000 px grid.

Measurements:
- measure/words_truth.csv, measure/words_catalogue.csv: one row per word.
- measure/summary.md, measure/summary.json: by kind and scale.
- measure/bin8_eval.json: precision and recall, misses by bin and kind, wrong-text classes, the per-plate bin 8 shares.
- measure/bin8_err_T*.jpg: text found magenta, missed red, wrongly called text green.
- measure/catalogue_bin8.json.
- measure/ink_colour.json and measure/ink_colour_<plate>.jpg.

Scripts (scripts/, run with python -B from that folder):
- common.py, crop.py, thumbs.py, gridtiles.py, propose.py (an early, unused attempt);
- build_truth.py, wordpix.py, measure.py, bin8_eval.py, catalogue_bin8.py, ink_colour.py.

## finder

I built a character finder from rules, with nothing fitted and nothing downloaded. It is text/finder/scripts/finder.py and runs on the system python.

How it works:
1. Ink is Lab L < 140 on the paper, the same as ink_bins.
2. Line ink is the ink that a straight 61 px line fits, tried at 48 angles on the ink grown by 1 px. A thick bar under 131 px that touches no thin line ink is given back, because it is the stem of a big letter. So is a short free piece of line ink under 100 px.
3. The rest of the ink falls apart into pieces. The pieces cover glyphs that were touching lines and glyphs separated from each other.
4. Each piece gets rotation-free shape features: equivalent-bar length and thickness, stroke width, holes (Euler number), stroke density, and how much it touches line ink.
5. The pieces are sorted into glyph, cluster, stroke, dot, blob and bar. Box, ring and building outline are found from the outline. A building jog or porch is found because its outline runs along or across the nearby lines and has few corners.
6. Strokes that chain end to end, or that carry on a line, are dashes or line pieces. Two short parallel strokes side by side are a ditto mark.
7. Text is the glyphs plus the strokes and dots within 9-15 px of them, in 3 rounds. A free-standing thin stroke 12-45 px long is a lone figure 1 or story mark.
8. The output is a code image per plate: 0 paper, 1 line ink, 2 glyph, 3 stroke or dot taken in by a glyph, 4 lone stroke, 5 other ink. Each piece's features are saved with it.

All thresholds were set by eye on windows of plate 44 and on the line hits of 1A and 5. The truth crops were scored afterwards and nothing was tuned to them, except that I looked at T1 halfway through.

Results:
- Ben's line ink is almost never called text: 0.27-0.46% of the ink within 3 px of his lines. Bin 8 calls 1.5-6.4% of it text.
- On the inventory agent's 6 truth crops (T1-T3 on 44, T4 on 1A, T6-T7 on 5), the finder's text pixels are more accurate than ink_bins' bin 8: F1 0.906 against 0.850.
- Painting the finder's text out before running the unchanged ink_bins.py cut plate 5's false railroad by 65%: 9 groups became 2, and the 2 left are lot lines with hook marks. Plate 44 lost 1.4 points of Ben's railroad.
- Weak spots:
  - big lettering: street names about 60 px tall or more with thin strokes, block numbers and the adjoining sheet number; these lose strokes to line ink;
  - text written on top of a line;
  - small free-standing house outlines on the 200 and 400 ft plates, which are still often called glyphs.

I ran it on 9 plates (44, 1A, 5, 54A at 100 ft; 30, 60B, 90 at 200 ft; 47, 93A at 400 ft) and looked at the overlays. No repo file was changed. Everything is in data/sanborn/bench_2026-11-25/text/finder/, and the scripts have a second copy in _second_copy/scripts.

### numbers

Everything here is MEASURED on 25 Nov 2026 unless marked estimate. Run from data/sanborn; "-" means the final outputs in out/.

SPEED (finder.py, out/N_finder.json 'seconds')
- 7-76 s per whole plate on CPU, with other jobs running on the machine.

(a) BEN'S LINE INK CALLED TEXT (measure.py -> out/measure_-.json)
True line ink = ink within 3 px of his printed, drawn and sheet-edge lines (44: streetmap/22-44.json; 1A and 5: editor_lines with edges_ben.json, all 146 and 618 edits matched). Columns: finder | bin 8.

| plate | within 3 px | within 1 px | bin 8, 3 px | bin 8, 1 px |
|---|---|---|---|---|
| 44 | 2,044 of 692,874 px = 0.30% | 0.21% | 6.41% (44,431 px) | 6.73% |
| 1A | 896 of 327,795 = 0.27% | 0.13% | 6.05% | 5.61% |
| 5 | 5,826 of 1,275,964 = 0.46% | 0.19% | 1.49% | 1.26% |

By kind, within 3 px, on 44 / 1A / 5:
- printed: 0.13% / 0.25% / 0.36%
- drawn: 0.79% / 0.14% / 0.48%
- sheet edge: 1.83% / 1.05% / 1.60%

Line length cut: Ben's lines sampled every 2 px, where there is ink within 2 px but all of it is called text.
- finder: 0.35% (44), 0.22% (1A), 0.30% (5)
- bin 8: 8.05%, 4.64%, 1.33%
- The hits I looked at are mostly big block numbers and spaced letters lying across his lines (real text), and building corners.

(b) AGAINST INK_BINS BIN 8 (measure.py)
Share of bin 8 the finder calls text:
- 44: 77.5% of 2,980,214 px
- 1A: 74.2% of 912,520
- 5: 82.2% of 3,830,397

Bin 8 that the finder calls line ink: 512k px (44), 157k (1A), 418k (5).
- On 44, looked at: much of it is small building outlines and lot-line pieces that ink_bins puts in bin 8 (look/diag_44_bin8_vs_finder.jpg).

What the finder adds (text outside bin 8):
- 337k px (44) = 12.7% of its text; mostly ink_bins' lot line 222k and building outline 78k.
- 166k (1A) = 19.7%.
- 773k (5) = 19.7%; building outline 479k. On 5 that is mostly real lot numbers sitting in the pink fill (look/diag_5_bin8_vs_finder.jpg).

(c) TRUTH CROPS (measure_truth.py -> out/truth_-.json)
The inventory agent's hand-checked masks T1, T2, T3 (44), T4 (1A), T6, T7 (5); T5 was not ready. Scored on pixels the truth calls text or not-text.

| crop | finder P / R / F1 | bin 8 P / R / F1 |
|---|---|---|
| all 6 | 0.948 / 0.868 / 0.906 | 0.854 / 0.847 / 0.850 |
| T1 | 0.945 / 0.921 / 0.933 | 0.789 / 0.896 / 0.839 |
| T2 | 0.944 / 0.928 / 0.936 | 0.835 / 0.887 / 0.860 |
| T3 | 0.989 / 0.850 / 0.914 | 0.884 / 0.917 / 0.900 |
| T4 | 0.944 / 0.784 / 0.857 | 0.888 / 0.798 / 0.841 |
| T6 | 0.912 / 0.908 / 0.910 | 0.865 / 0.869 / 0.867 |
| T7 | 0.955 / 0.847 / 0.898 | 0.895 / 0.784 / 0.836 |

- Without the lone strokes: F1 0.903.

Recall by word kind (finder | bin 8):
- lot 0.93 | 0.76
- house 0.88 | 0.97
- lot dimension 0.91 | 0.79
- street 0.81 | 0.985
- owner 0.74 | 0.76
- story 0.94 | 0.71
- pipe 0.86 | 0.80
- sewer 0.74 | 0.79
- rail names 0.90 | 0.97
- block 0.64 | 0.85
- adjoining sheet number 0.28 | 0.92
- ditto 0.75 | 0.47

DOWNSTREAM: ink_bins.py unchanged, Ben's rail off, run with and without the finder's text painted out (rail_with_mask.py, rail_score.py -> rail/rail_score.json)

| | base | text out |
|---|---|---|
| plate 5 false railroad (no real railroad on 5) | 29,381 px in 9 groups | 10,220 px in 2 groups (-65%) |
| plate 5 clear ticks | 7,732 | 835 |
| plate 5 streetcar found / false | 81.4% / 948 px | 83.3% / 3,147 px |
| plate 44 Ben's railroad length found | 98.8% | 97.4% |
| plate 44 false railroad | 3,576 px | 1,415 px |
| plate 44 streetcar found / false | 85.2% / 1,086 px | 86.8% / 2,865 px |

- The 2 groups left on plate 5 are long lot lines with hook marks.
- On 44, the 124 lost railroad samples are one track that runs beside spaced lettering.

8+1 PLATES (out/N_finder.json): text share of ink, by scale
- 100 ft: 44 39.5%, 1A 36.5%, 5 37.9%, 54A 36.9%
- 200 ft: 30 36.2%, 60B 37.3%, 90 33.1%
- 400 ft: 47 34.2%, 93A 38.6%
- Line ink is 53-58% of the ink everywhere.

ESTIMATES (by eye, not measured)
- Small house outlines still called glyph on 90 and 30: roughly a third to half of the free-standing house boxes.
- On 47 (400 ft): small lot-dimension figures that sit on lines are partly lost.

### findings

- **F1 Taking line ink out first keeps Ben's street lines almost untouched** Within 3 px of his lines, the finder calls 0.30% (44), 0.27% (1A) and 0.46% (5) of the ink text, against 6.4%, 6.1% and 1.5% for bin 8. Only 0.22-0.35% of his inked line length would be cut by removing the text, against 1.3-8.1% for bin 8 (measure.py). An earlier version that gave back thick line pieces too freely called 4.1% (1A) text. The free-bar rule fixed that. So what: This meets the 'nearly 0' requirement. The text mask can be removed before the line, rail and outline steps without cutting the street sides. What is left is mostly big numbers and spaced letters that truly lie across his lines.
- **F2 The finder is more accurate than ink_bins' text rule on hand-checked crops** On 6 truth crops, F1 is 0.906 against 0.850 (precision 0.948 against 0.854, recall 0.868 against 0.847). It is better on every crop. The largest gains are on lot numbers (0.93 against 0.76), story heights (0.94 against 0.71), lot dimensions and ditto marks. So what: This is a better first text mask than bin 8 for the 'out of contention first' stage. Three of the six crops are on plate 44, where the thresholds were set by eye, so the 44 crops are not independent.
- **F3 Bin 8 has its own errors, so agreement with it understates the finder** On 44, much of the 512k px of bin 8 that the finder calls line ink is small building outlines and lot-line pieces. After the block lines are removed they become separate small pieces of 130 px or less, and the ink_bins rule calls them text (look/diag_44_bin8_vs_finder.jpg). On 5, 479k px the finder calls text sit in ink_bins' building-outline bin. By eye these are mostly real lot numbers in the pink fill (look/diag_5_bin8_vs_finder.jpg). So what: Do not score the finder or train the networks with bin 8 as text truth. Ben's earlier 'numbers as negatives' design used bin 8 grown 1 px, so it would teach some building outlines as text.
- **F4 Removing text first removes most of plate 5's false railroad** With ink_bins.py unchanged and Ben's rail off, painting out the finder's text cut plate 5's false railroad from 29,381 px in 9 groups to 10,220 px in 2 groups. The 2 left are long lot lines with hook marks. On 44, Ben's railroad found fell from 98.8% to 97.4% (one track beside spaced lettering), and the false railroad fell from 3,576 to 1,415 px. False streetcar rose: 948 to 3,147 px on 5, and 1,086 to 2,865 px on 44 (rail_score.py). So what: This is direct evidence for Ben's point that text should be eliminated first. The hook-mark lot lines need their own rule. The rise in false streetcar needs a look before the mask is used in the pipeline.
- **F5 Big lettering is the main weakness** Recall on truth crops: street names 0.81 (bin 8 0.985), with AVENUE on T3 0.35 and STREET on T4 0.28; block numbers 0.64; adjoining sheet number 39 0.28. Letters about 60 px or more with thin strokes have stems that a 61 px line fits. Where a thin line touches or crosses them, the giveback is refused. A looser 'along the axis only' giveback raised Ben's line ink called text to 0.43-1.25%, so it was dropped. So what: Street names matter for reading. The next step should rescue stems that have glyph arms attached or that sit in a row of letter-sized pieces, or a second pass at a longer line length inside word areas found by the grouping stage.
- **F6 Text on lines and tiny building outlines are the other misses and false finds** 1600 and 6"W.P., written on the pipe line on 44, are 0% found. House numbers against block lines on 1A: 0.79 recall. On 200 and 400 ft plates (90, 30, 47), small free-standing house outlines are still often called glyph (estimate by eye). The outline-only box rule ('straight sides') was switched off because it cost 0.6 points of recall on T1. The fill-edge rule, which needs a pink or yellow fill, helps little where the fill is pale. So what: There are no truth crops on 200 or 400 ft plates yet, so the false finds there are unmeasured. A truth crop on 90 or 47 would show the size. Colour, or knowing that a closed shape holds a single story figure, may be the way to separate house boxes.
- **F7 Scale handling** Lettering is about the same pixel size on 100, 200 and 400 ft plates (looked at 44, 30 and 47), so fixed pixel sizes work. Text is 33-40% of the ink and line ink 53-58% on all 9 plates. The 400 ft plates have many more tiny pieces (47: 36k dots against 9k on 44) and tiny house boxes. So what: No per-scale settings were needed for the letters themselves. The 400 ft plates need checking for small figures on lines and for house boxes.

### needs Ben

Downloads: none. The finder uses only the system python (cv2 4.13, numpy, scipy). Nothing was installed. If you later want a learned text detector to compare against, OpenCV's EAST or DB text-detection models would each need a model-file download of a few tens of MB, through cv2.dnn. I have not checked their exact sizes or licences. They are only worth that check after the reading stage needs them.

Conventions to decide:
- Should ditto marks, story-height figures and the building letters inside buildings (G, A, N, D and so on) count as text in the mask? I count them as text, like the KEY.
- The mask codes in out/N_finder.png are 0 paper, 1 line ink, 2 glyph, 3 stroke or dot taken in by a glyph, 4 lone stroke (lower confidence), 5 other ink. Should the later stages use codes 2-4, or only 2-3?

Labels that would help:
- A truth crop on a 200 ft plate (90 or 30) and one on a 400 ft plate (47), to measure the house-outline false finds.
- A few crops with big street names and block numbers, to tune the big-letter rescue.
- On plate 5, mark the 2 lot lines with hook marks that the rail rule still takes as railroad, as rejected, as in the round-2 sidecar idea.

### files

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/finder/. Second copy of the scripts: _second_copy/scripts/.

scripts/ (run from data/sanborn with python -B):
- finder.py: the finder. Run as: N [--win X0 Y0 X1 Y1] [--out DIR] [--pic] [--tag T]
- measure.py: (a) and (b) on 44, 1A and 5
- measure_truth.py: precision and recall on the inventory truth crops
- benlines.py: Ben's lines as a raster
- rail_with_mask.py: runs the unchanged ink_bins.py with the text painted out; writes are guarded to stay inside finder/
- rail_score.py: scores the railroad bins against Ben's tracks
- pic.py, kindpic.py, diffpic.py, looks.py: pictures

out/:
- N_finder.png, N_finder.json, N_pieces.npz and N_finder.jpg (half-size overlay) for plates 44, 1A, 5, 54A, 30, 60B, 90, 47 and 93A
- measure_-.json, truth_-.json, truth_-.log

rail/:
- 5 and 44, base and masked: bins png and json, logs
- rail_score.json
- 5_masked_false_rail.jpg, 44_lost_rail.jpg

look/:
- 2 overlay crops per plate
- truth_err_T1_left_v3.jpg, truth_err_T3.jpg, truth_err_T4.jpg, truth_err_T7.jpg
- diag_44_bin8_vs_finder.jpg, diag_5_bin8_vs_finder.jpg, diag_jog_test_sheet.jpg

scratch/: 104 MB of working versions v1-v9. It can be deleted when you are happy.

## words

I built a rules-only stage that groups character candidates into words and numbers, at any angle and along curves. Nothing was downloaded, installed or trained, and no repo file was changed (I checked: nothing new under tools/, unet_data/, picks22_guided/ or streetmap/).

How it works, in five steps:
1. **Chaining.** Each candidate piece is linked to the two neighbours that sit on opposite sides of it. The neighbours must be of the same height, share a centre band, and be close (gap at most 1.15 heights). Because the line may turn a little at each glyph, a chain can follow a curved street. Strings are then joined across word spaces (gap up to 1.7 heights). Widely spaced capitals (A  V  E) are linked as a separate case. Small marks (' " . -) are attached afterwards and their position (high, low or middle) is recorded.
2. **Which way up.** Each string's glyphs are compared, read one way and turned over, against the plate's own near-horizontal glyphs. Whichever way looks more upright wins. A two-piece string whose pieces look more upright turned a quarter is undone into two single pieces (this catches stacked digits).
3. **Rectifying.** Each string is resampled along a fitted centre line (straight, or quadratic/cubic along its length) into a horizontal strip, upright, with its own ink kept in a separate mask.
4. **Kinds from geometry.** Each word gets a kind from its height, character count and marks, plus Ben's lines (distance and angle to the nearest line, block or street ground), building fill and pipe/sewer ink beside it.
5. **Text mask.** A mask of all non-junk word ink is written for the later stages.

It runs on ink_bins bin 8 or on the finder agent's text, in about 12–62 s a plate on the CPU. It was run on 44, 5, 1A and 90.

Results against the inventory agent's 1,012 hand-read words in 6 crops (T1–T4, T6, T7):
- **Grouping.** With the finder's candidates, 58% of words come out exactly as one word and only 4% are missed. With bin 8, 54% are exact but 15% are missed.
- **Which way up.** For words of 2 or more pieces, 78–84% are right and at most 5.5% are upside down. For one-piece words only about 42–46% are right.
- **Kinds.** About 55% overall. House numbers are good (76–80%). Story counts, pipe labels, owner names and ditto marks are weak.
- **Curved names.** Curved street names on plate 90 straighten cleanly: Avalon, Woodbine, Ferndale, Glendale, Hunsford.

On Ben's main question, taking the finder's text out before the railroad rule runs:
- **Plate 5:** cuts the false railroad by 65% (29,381 to 10,220 px; 10 pieces to 2).
- **Plate 44:** keeps 97.7% of Ben's railroad (98.4% before) and cuts railroad ink away from his tracks from 2,122 to 512 px.

The main limit is that geometry cannot tell digits from letters. The strips are the input for the shapes agent's reader.

### numbers

Everything below is MEASURED unless marked as an estimate. Scripts are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/words/scripts/.

**A. Against the word truth** (measure.py, then summarize.py; files out/measure_final_bins.json, out/measure_final_finder.json, out/summary_final.json). Truth is 1,012 words in 6 crops.

How much I saw of each crop while building:
- T1 (44): I tuned the rules on it.
- T2 and T3 (44): I saw their totals while working.
- T4 (1A): I saw its error breakdown once (it motivated the two-piece check).
- T6 and T7 (plate 5): never seen before the final run.
- T5 did not exist yet.

How a truth word is scored:
- exact: all of its pieces are in one word of mine, and at least 80% of that word's ink is inside the truth box.
- split: its pieces are spread over two or more of my words.
- merged: one word of mine holds it plus more than 20% outside ink.
- missed: no candidate piece, or only in junk.

Finder candidates, all 6 crops:
- exact 583/1012 (57.6%); merged 121; split 225; split and merged 38; missed 45 (4.4%).
- kind right 525/967 (54.3%).
- Way up, words of 2+ pieces: 466/591 right (78.8%), 25 turned over (4.2%), 100 off by 30–150 degrees.
- Way up, one-piece words: 157/376 (41.8%).
- False words (under 20% on truth text): 100 of 1,424.

Bin-8 candidates, all 6 crops:
- exact 549 (54.2%); merged 127; split 144; split and merged 36; missed 156 (15.4%).
- kind 464/856 (54.2%).
- Way up, 2+ pieces: 375/479 (78.3%), 15 turned over (3.1%).
- Way up, one-piece words: 161/377 (42.7%).
- False words: 90 of 1,147.

Unseen crops T6+T7 only (plate 5, 375 words):

| | exact | missed | kind right | way up, 2+ pieces | one piece |
|---|---|---|---|---|---|
| finder | 214 (57.1%) | 18 | 198/357 (55.5%) | 155/199 (77.9%), 11 turned over | 70/158 |
| bins | 205 (54.7%) | 85 | 160/290 (55.2%) | 109/130 (83.8%), 4 turned over | 74/160 |

Kind right by truth kind, all 6 crops (bins / finder):

| truth kind | bins | finder |
|---|---|---|
| house numbers | 78/98 | 74/98 |
| street | 14/22 | 11/22 |
| lot dimension | 135/284 | 179/284 |
| lot number | 132/258 | 139/258 |
| story | 60/188 | 83/188 |
| pipe + sewer | 12/31 | 13/31 |
| owner | 10/51 | 7/51 |
| ditto | 0/38 (there is no ditto kind) | 0/38 |
| block | 3/7 | 2/7 |

Text-mask pixels against the truth mask, per crop:
- finder-based: recall 0.76–0.91, precision 0.91–0.99.
- bins-based: recall 0.77–0.90, precision 0.87–0.93.

**B. Orientation cues.** Measured with no truth needed, on near-horizontal strings assumed upright, plates 44/5/1A, inline check during development:
- The shapes test agreed on 96.0%, 97.7% and 91.9%, and on 99.2%, 99.2% and 95.3% for strings of 3+ glyphs.
- The marks vote agreed on 54.4%, 45.8% and 42.9%, which is chance. Marks were therefore dropped as a way-up cue.

**C. Railroad rule with the text taken out first** (rail_check.py, which imports the repo's ink_bins.railroad unchanged).

Plate 5 (out/rail_check_5.json). Plate 5 has no railroad, so every railroad px is false:

| ink given to the rule | false railroad px | pieces |
|---|---|---|
| all ink | 29,381 | 10 (same as diag/rail5 orig_nets) |
| less finder text | 10,220 | 2 |
| less my words on finder | 10,225 | 2 |
| less my words on bin 8 | 9,740 | 3 |
| less all bin 8 | 4,180 | 2 (circular: that bin 8 was sorted with Ben's rail) |

Plate 44 (out/rail_check_44.json):
- Ben's 19 railroad tracks found within 10 px: 98.4% with all ink, 97.7% with the finder's text taken out.
- Railroad px more than 25 px from his tracks: 2,122 with all ink, 512 with the text taken out.

**D. Per-plate output** (run_words.py; logs in out/final_runs.log):

| plate | glyphs | strings (2+ pieces) | words | strips | curved | spaced |
|---|---|---|---|---|---|---|
| 44 | 19,873 | 6,716 (2,690) | 8,004 | 3,313 | 57 | 12 |
| 5 | 23,627 | 7,784 (3,351) | 9,936 | 4,126 | 59 | 31 |
| 1A | 5,347 | 1,921 (857) | 2,317 | 1,069 | 21 | 5 |
| 90 | 17,690 | 5,537 (2,816) | 6,465 | 3,241 | 40 | 9 |

- Finder runs: 7,201 / 9,845 / 2,406 / 6,376 strings and 3,728 / 5,228 / 1,313 / 3,688 strips.
- Two-piece strings undone (bins): 164 / 329 / 51 / 133.
- Run times (bins): 44 33 s, 5 51 s, 1A 12 s, 90 34 s. Finder: 43 / 62 / 14 / 26 s.

**E. Estimates (not measured):**
- My heights are about 0.85 of the truth's printed heights (median ratio on T1 exact matches; an inline check).
- Height bands from T1 (estimate): lot dimensions ~16–26 px, lot numbers ~21–36, house numbers ~23–27, street names 30+.

**F. Development check, by eye.** Audit sheet of 40 random 1A strings before the last fixes (out/audit_1A_before_fix.jpg), by eye, an estimate:
- 26 of the 30 strings with strips were text; 18 of those were grouped right.
- About a third had the right kind.
- Single tall digits were read sideways. This was fixed by raising the threshold for treating one piece as several touching characters from 1.5 to 2.0.

### findings

- **W1 Text can be grouped into words at any angle and along curves without OCR or training** Chaining uses each piece's two neighbours on opposite sides (same height, shared centre band, gap at most 1.15 heights). Strings are joined across word spaces up to 1.7 heights, and evenly spaced capitals are linked as a separate case. Against 1,012 hand-read words: exact 57.6% with finder candidates, 54.2% with bin 8 (measure_final_*.json). Curved street names on 90 (Avalon, Woodbine, Ferndale, Glendale, Hunsford) come out as single strings and straighten into upright strips (pics/curved_street_names_90.png). So what: Ben's 'group the characters into words' step works well enough to hand strips to a reader. It is not good enough to trust word boundaries without the code checks.
- **W2 The remaining grouping errors are merges of neighbouring numbers and splits of marks and touching pieces** Merged: 121–127 of 1,012, mostly a story count beside a lot number, or a lot number beside a lot dimension. Split: 180 with bin 8 and 263 with finder candidates (split plus split-and-merged): a feet mark left as its own piece, a glyph broken by a line, letter-spaced estate names (T3: 23–25 splits of 70). Ditto marks are mostly missed with bin 8 (29 of 38). So what: A splitting rule at building-fill edges is already in. Next would be the reader's verdict, e.g. 'a single 2 or 3 in a building fill is a story count'. The checks agent's format rules (25', 18.72, 6" W. PIPE) should run on the phrase and re-split it.
- **W3 Which way up comes from the plate's own glyphs, not from marks** The shapes test matches each glyph, read one way and turned over, against the plate's near-horizontal glyphs. It agreed with upright on 96–98% of horizontal strings, against 43–54% for apostrophe and decimal-point positions. Final, words of 2+ pieces: 78–84% right, 3–5.5% turned over. One-piece words: only 42–46% right. So what: Multi-glyph strips are upright enough for the shapes agent. Lone pieces (single digits, and runs printed as one piece) need the reader to decide their turn, or must be treated as 4-way unknown.
- **W4 Kinds from geometry alone: good for house numbers, weak where reading is needed** Overall 54% right. House numbers 76–80% (they hug the block line in the street, along it). Street names 50–64%. Lot dimensions 48% with bin 8, 63% with finder. Lot numbers 51–54%. Story counts 32–44%. Pipe and sewer labels about 40%. Owner names 14–20%. Ditto marks 0% (there is no ditto kind). So what: The kind is a prior, not an answer. Telling digits from capitals is the missing piece. Once the shapes agent reads characters, most of these confusions resolve with simple rules.
- **W5 Taking text out first removes most of plate 5's false railroad and barely touches real railroad on 44** rail_check.py runs the repo's railroad() unchanged. Plate 5: 29,381 to 10,220 false px (10 pieces to 2) with the finder's text removed. Plate 44: Ben's railroad found 98.4% to 97.7%, and railroad px away from his tracks 2,122 to 512. So what: This directly supports Ben's 'eliminate them from contention first'. The remaining 10k px on plate 5 are worth a look by the rail agent, together with the rail5 rule changes.
- **W6 Finder candidates beat bin 8 for finding words, but split more** Missed: 45 with finder against 156 with bin 8 (of 1,012). Exact: 583 against 549. Split or split-and-merged: 263 against 180. Text-pixel precision 0.91–0.99 against 0.87–0.93. So what: Use the finder as the upstream. A gentler joining of touching and broken pieces (or the finder keeping glyph fragments together) is the next gain.
- **W7 Fixes found by eye, outside the truth crops** 1. On 1A's audit sheet, single tall digits were taken for runs and turned sideways. The threshold for treating one piece as several touching characters went from 1.5 to 2.0, and the 'undo two-piece strings whose pieces read upright across the link' check was added. 2. On 44's Spring Grove, italic house numbers of h≈30 were called street names, so street names under 40 px must now stand clear of the line. 3. Owner names with periods were called lot dimensions, so the mark rule is now limited to 7 characters. 4. Small building outlines on 90 still slip in as glyphs (only partly caught by the thin-ring test). So what: These are listed so that whoever extends the rules does not undo them. Building rings on the 200 ft plates need the finder's ring test.

### needs Ben

**Downloads:** none needed, and nothing was installed or downloaded. One optional thing to decide: an off-the-shelf OCR engine could read the rectified strips directly. Example: Tesseract 5, Apache-2.0 licence, from github.com/tesseract-ocr/tesseract (Windows installer from the UB Mannheim builds), about 50–80 MB with English data (size is an estimate). It would give character readings of the strips to compare with the shapes agent's no-download reader. Ben must approve any such download himself.

**Questions for Ben (conventions):**
1. **House numbers.** On 44 they sit in the street just outside the block-face line. On 5 they are written right against it, in long hyphenated runs (227-225-223-221). Should a hyphenated run be one 'house-number group', or split into one entry per number?
2. **Direction of reading.** I assume text near vertical reads bottom to top (FERGUS, 4155-57), and steep text reads rightwards and downhill (the Hamilton Ave numbers, AVE.). Is that the rule?
3. **Ditto marks.** Should ditto marks (") be their own kind? Today they are left as marks or junk.
4. **Whole street names.** Should a street name be kept whole (SPRING GROVE as one name)? The output has both the phrase and its words.

**Optional labels (5–10 minutes):**
- Glance at out/contact_1..4.jpg and mark strips that are wrongly grouped or upside down.
- Checking about 100 strips would give an independent set beyond the inventory truth.

### files

All of these are under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/words/ (325 MB). A second copy of the scripts is in scripts_second_copy/. Nothing outside this folder was written.

**Scripts** (scripts/; run from data/sanborn with python -B):
- wordlib.py: glyph pieces, support function, chaining, centre curve, strip sampling.
- group_words.py: candidates (bin 8 or finder), merging across word spaces, spaced capitals, marks, word split.
- context.py: Ben's lines, blocks, fill, pipe ink.
- orient.py: the shapes test and mark votes.
- run_words.py: the whole stage; `python -B .../run_words.py N [--src finder]`.
- classify.py: the kind rules.
- reclassify.py
- measure.py: against the inventory truth.
- summarize.py
- rail_check.py
- contact.py
- audit.py
- draw.py

**Outputs** (out/; the tag is N for bin 8, N_finder for the finder):
- TAG_words.json: every phrase with its words, glyph ids, marks, reading angle, how the way up was decided, centre line, strip file and features.
- TAG_glyphlab.png: glyph labels, 24-bit.
- TAG_textmask.png: 255 = ink of non-junk words, for the later stages.
- TAG_strings.json, TAG_kinds.json
- strips/TAG/pNNNNN.png: scan strip, row 0 = the text's top. strips/TAG/pNNNNN_m.png is the string's own ink.
- contact_1..4.jpg and contact_index.json: 200 strips from 44, 5, 1A and 90, finder candidates.
- contact_bins_1..4.jpg: 198 strips, bin-8 candidates.
- measure_final_bins.json, measure_final_finder.json, summary_final.json
- rail_check_5.json, rail_check_44.json
- final_runs.log
- audit_1A_before_fix.jpg
- measure_dev_v*.json: the development history.

**Pictures** (pics/):
- curved_street_names_90.png
- kinds_90_avalon_finder.jpg
- kinds_44_springgrove_finder.jpg and kinds_44_springgrove_bins.jpg
- kinds_5_finder.jpg

## shapes

I built a working prototype that reads Sanborn lettering by shape. Nothing was downloaded, nothing was installed and no U-net was trained. Everything is in data/sanborn/bench_2026-11-25/text/shapes/.

How it works:
1. Thin straight lines are taken out first. This frees street-name letters that a pipe or sewer line runs through.
2. The single glyphs are cut out of plates 44, 1A, 5, 3, 90 and 94 and turned upright by the direction of their word: 183,405 candidates.
3. The glyphs are clustered by shape (blurred pixels, HOG, size; k-means) and drawn as montage sheets, one cluster per row. There are two rounds: round 2 clusters again only what round 1 did not call junk.
4. I labelled by eye 261 clusters that were clearly one thing: 107 digit, 29 letter and 125 junk clusters. This gave 23,691 labelled digit glyphs, and a small k-NN reader was fitted on them.

Results:
- **House numbers** (3 block faces on plate 44, 80 figures, 23 numbers, my own by-eye truth): 67/80 figures (84%) and 15/23 numbers right. A reader that never saw any plate-44 glyph scored the same.
- **Street names**: the k-NN reader is weak (5/16 letters), because K, O, B and U were never labelled. Matching against fonts already on this machine reads KNOWLTON and BLUE ROCK at 15/16 letters, but it also turns 6 nearby bits of ink into letters.

The classifier is no longer the limit. About 50-100 labelled glyphs per digit is enough: more labels stop helping. What holds the reading back is cutting out the glyphs. Faint figures break into pieces, touching pairs such as 14, 15 and 25 stay as one glyph, figures on diagonal streets that stand alone stay tilted, and the word grouping joins neighbouring numbers. A simple rule check by code (parity, one direction, plausible steps) flagged every wrong number token, but also 4 of the 9 right ones.

### numbers

MEASURED (the script that made each number is named):
- extract_glyphs.py, glyph candidates of 4-130 px after line removal: 183,405 in total (44: 41,248; 1A: 10,341; 5: 50,258; 3: 30,482; 90: 28,965; 94: 22,111). About 13-19 s per plate on the CPU.
- cluster.py
  - Round 1: 450 clusters (tiny 30, small 300, large 120), 23 montage sheets.
  - Round 2 (--round2 pred_round1.npz): 86,996 glyphs kept, 400 clusters (small 300, large 100), 20 sheets.
- Labels (labels/claude_round1.json and claude_round2.json, mine by eye): 261 clusters.
  - Training glyphs after classify.py drops the 20% of each cluster's members furthest from its mean:
    - digits: 0: 2578, 1: 5781, 2: 4407, 3: 2468, 4: 2118, 5: 2037, 6: 1083, 7: 1553, 8: 583, 9: 1083;
    - letters (A C E L M N P R T W): 3,352;
    - junk: 41,075.
- classify.py, leave-one-plate-out agreement with the cluster labels: 0.996. This only shows that the k-NN reproduces the clusters; it is not an accuracy.
- eval_faces.py, truth read by me by eye: 3 block faces on 44 (80 figures, 23 house numbers) and 2 street names (16 letters).
  - knn_ctx (digits plus junk only, touching figures cut, no '?'): 67/80 figures (84%), 15/23 numbers. Same result in-sample (model.npz) and hold-out (model_no44.npz).
  - knn_nosplit: 61/80 figures, 11/23 numbers.
  - knn_rej ('?' when the distance is over 0.5): 61/80 figures, 11/23 numbers (in-sample 62/80, 12/23).
  - font templates: 58/80 figures, 6/23 numbers.
  - Street names: fonts 15/16 letters (KNOWLTON 7/8, K read as M; BLUE ROCK 8/8), plus 6 extra letters from nearby ink. k-NN 5/16. Hybrid (k-NN junk gate, then fonts) 11/16.
  - With fainter ink also kept (L < 165 joined to the L < 140 ink; extract_glyphs.py --weak 165): hold-out knn_ctx falls to 60/80 figures and 12/23 numbers, with 16 figures missed (eval_faces_holdout_weak165.json).
- fonts.py: 47 Windows fonts, upright fonts also slanted 0.25; 2,000 digit and 1,751 capital glyphs; the reference is the cluster labels.
  - Digits against digit templates only, all fonts pooled: 0.863.
  - Best single fonts for digits: Arial Narrow Bold 0.840, Arial Bold 0.832, Segoe UI Bold 0.821.
  - Per digit: 0 .93, 1 .54, 2 .80, 3 .99, 4 .89, 5 .95, 6 .97, 7 .87, 8 .94, 9 .74. The main confusion is 1 read as 7 (92 times).
  - Capitals against letter templates only: pooled 0.864, best Franklin Gothic Demi 0.865.
- learning_curve.py: trained on 5 plates, tested on 44, N labelled glyphs per class drawn at random.
  - T1 (agreement with the cluster labels, 5,531 plate-44 digit glyphs): N=3: 0.79-0.81; 5: 0.84-0.89; 10: 0.90-0.92; 20: 0.93-0.94; 50: 0.95-0.98; 100: 0.97-0.98; 200: 0.980; 500: 0.982; 1000: 0.982.
  - T2 (the 80 face figures): N=3: 54-58; 5: 50-66; 10: 56-67; 20: 61-64; 50: 64-67; 100: 64-65; 200: 65; 500: 68; 1000: 66.
- face_check.py, rule check on the hold-out knn_ctx reading: 20 tokens, 11 wrong. All 11 wrong were flagged; 4 of the 9 right were also flagged.
- sample_check.py: 26,232 plate-44 glyphs of 12-40 px read with no context and no cutting: 9,827 called digits, 14,804 junk.

BY EYE (my count, small sample):
- Of 100 random plate-44 glyphs that the hold-out reader called a digit (10 per digit), 55 are right.
  - Per digit: 0: 7, 1: 5, 2: 7, 3: 7, 4: 5, 5: 7, 6: 3, 7: 4, 8: 4, 9: 6 (out of 10 each).
  - Weighted by how often each digit is called, about 57% (estimate).
  - Rough split of the errors: touching pairs read as one figure about 17, pieces of broken figures or lines about 12, wrong digit about 10, letters 3.

ESTIMATES:
- Purity of my labelled clusters: about 90-95% of the glyphs in each one.
- Ben's labelling time: see needs_ben.

### findings

- **S1 Digits fall into clean clusters by shape** montage/small_05-09.png and montage2/small_00-13.png show whole rows of one digit, at about 24 of 26 shown glyphs or more: for example 3154-3163 are 2s, 3238-3241 are 3s, 3253-3257 are 5s, 3271-3275 are 4s and 3012-3024 are italic 1s. I labelled 107 digit clusters, which gave 23,691 training digits. A check by code: in the clusters I labelled '1', 57-71% of the glyphs share a word with another labelled digit, the same rate as the other digit clusters (59%). Vertical-bar clusters score 7-9%, so they are bits of line. So what: Ben can label digits a row at a time: one row carries about 150-770 glyphs. The 'shares a word with another digit' rate is a cheap check by code that a cluster is really digits.
- **S2 House numbers: 84% of figures, 15 of 23 numbers on three faces of 44** eval_faces_holdout.json, reader knn_ctx: 67/80 figures. The faces are Knowlton north side (1424-22-20 ... 1408), Blue Rock south side (1629 ... 1613) and the top row west of Hamilton (1563-61 ... 1549-47). A reader that never saw plate 44 gives the same score as one that did. Cutting touching figures adds 6 figures and 4 numbers. look/eval_holdout_knn_ctx_A/B/C.jpg show each reading on the scan. So what: A reader trained on other plates carries over to a new plate. What is still lost comes from cutting out the glyphs, not from the classifier.
- **S3 Street names read best by font templates, with no labels at all** Fonts already on the machine, matched shape for shape: KNOWLTON 7/8 letters (K read as M) and BLUE ROCK 8/8, plus 6 extra 'letters' made from dashes nearby. The k-NN with my few letter labels gets 5/16, because K, O, B and U were never labelled. fonts.py: letter templates agree with the labelled capitals 0.864 when pooled; Franklin Gothic Demi alone gives 0.865. So what: The street-name capitals are a regular block letter, so font templates plus a name list should read them. The k-NN junk gate cannot be used in front of the fonts yet: it calls the bold O junk (hybrid 11/16).
- **S4 Fonts are weaker for the hand-lettered italic figures** fonts.py, digits matched against digit templates: 0.863 pooled, Arial Narrow Bold 0.840. The 1 is only 0.54 (italic 1 read as 7 92 times) and the 9 0.74. On the faces, fonts get 58/80 figures and 6/23 numbers, against 67/80 and 15/23 for the labelled clusters. So what: Labelled shapes are needed for the figures; font templates for the capitals.
- **S5 About 50-100 labelled glyphs per digit is enough** learning_curve.py, held out on 44: agreement 0.80 with 3 per class, 0.91 with 10, 0.94 with 20, 0.96 with 50, 0.975 with 100, 0.98 with 200 to 1000. The face test levels off at about 64-68 of 80 figures from 50 per class on. So what: A reliable digit reader needs about 500-1000 digit glyphs in all, that is 3-6 clean rows per digit covering the sizes and weights. More labels do not raise the face score; better cutting of the glyphs does.
- **S6 Cutting out the glyphs is the bottleneck** Over the whole plate, with no context and no cutting, only 55 of 100 glyphs called digits are right (by eye, look/check44_digits_0/1.png); the errors are mostly touching pairs (14, 15, 16, 25, 61) and pieces of broken figures. On the faces, the misses come from: (1) faint figures that break apart, such as the 1 of 1410 (two pieces under 12 px), the 53 of 1555-53 and the 9 of 1629; (2) touching groups not cut, such as 1424-22-20 and the 15 of 1563; (3) word grouping that joins neighbouring numbers ('14161414'). Keeping fainter ink (L < 165) made it worse: 60/80 figures, 16 missed. So what: Next step: join broken strokes only along the word's direction, cut touching figures better (keeping a cut when the parts read better, which already helps), and split numbers at the gaps.
- **S7 Single glyphs on diagonal streets are left tilted** Clusters 1280-1287, 3074, 3092 and 3099 are tilted or turned 2s, 7s and 0s. Glyphs with no linked neighbour, including touching pairs, keep 0 degrees. Vertical house numbers on 44 do come out upright and are read ('4136 4132-30', '4137', '4133'). A word read upward would come out upside down; the reader tries both ways round for each word. So what: Lone glyphs should take the angle of nearby words or the street. Ben should say whether any plate has text that reads upward.
- **S8 Lot numbers and punctuation are not covered yet** The large italic lot numbers on 44 (about 35 px: 75, 76, 78) are misread; few labelled clusters are that size. The tiny band (under 12 px: ' " . and bits of line) cannot be told apart by shape alone (montage/tiny_*.png). So what: Ben should label a few clusters of lot-number-size digits. Apostrophes, ditto marks and full stops need context (they come after a number) rather than shape.
- **S9 A rule check by code catches the wrong numbers** face_check.py rules: 3-4 figures, one parity, one direction, steps of 40 or less, and a continuation equal to the number before it plus or minus 2. On the hold-out reading it flagged all 11 wrong tokens, and also 4 of the 9 right ones; those were flagged because their neighbours were wrong. So what: This is the 'double-checked by the code' step Ben asked for. It needs better splitting into numbers first; then it can propose fixes, such as 1410 between 1412 and 1408.
- **S10 Taking out thin lines first frees letters that lines run through** extract_glyphs.py keeps the ink that survives an opening with a 1 px line 51 px long (45 directions) only where the ink is 7 px thick or more. The sewer line through KNOWLTON and the dashes through BLUE ROCK are removed and the letters stay whole (look/44_lineremoval_test.png, 44_knowlton_zoom.png). It takes about 14 s per plate. So what: This step can feed the text mask and the line stages directly.

### needs Ben

LABELS
- labels/ben_label_sheet.json has 850 rows, one per cluster, giving the sheet file and row, the cluster size, the median glyph size and my label where I gave one.
- For each row, fill 'ben' with:
  - the character, when nearly every glyph in the row is that character;
  - 'junk', when none of it is lettering;
  - 'pair', for two touching figures;
  - nothing, when the row is mixed.
- Quickest useful pass: check my 107 digit rows and 29 letter rows (about 10 minutes, estimate).
- Then montage2/small_00-14.png: 300 rows of round 2, mostly lettering, about 20-25 minutes at 4-5 s a row (estimate).
- All 850 rows would take about 60-70 minutes (estimate).
- Most wanted: digits at lot-number size (about 35 px), and bold capitals K, O, B, U, S, D, H, G (as row labels, or as the names on a known street).

TRUTH TO CONFIRM
- The face and street-name truth was read by me, not by Ben. The faces, all on plate 44:
  - 1424-22-20 1418 1416 1414 1412 1410 1408 (Knowlton north side);
  - 1629 1625-23 1621 1613 (Blue Rock south side);
  - 1563-61 1559 1557 1555-53 1551 1549-47 (top row west of Hamilton).

CONVENTIONS TO DECIDE
- Does any plate have text that reads upward on north-south streets? (On 44 it reads downward.)
- Is '1424-22-20' one label covering three houses, as I scored it?
- Should 'pair' rows be labelled with the actual pair (for example '25'), since lot dimensions 25' are very common?

DOWNLOADS
- None used and none needed for this path. Optional ones that Ben would have to approve himself:
  - Tesseract OCR: Apache-2.0, Windows build from UB-Mannheim on GitHub, roughly 50-80 MB. It would give a general OCR baseline, but is likely weak on these hand-lettered italic figures without retraining.
  - EMNIST handwritten characters: from NIST, roughly 0.5 GB. It could pretrain a digit net, but our own clusters already give 23k labelled digits.

STORAGE
- I wrote only into my own folder (79 MB), so no second copy has been made.

### files

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/shapes/

SCRIPTS (run from data/sanborn with python -B)
- scripts/extract_glyphs.py: line removal, glyphs, words, angles. Writes glyphs/N.npz for 44, 1A, 5, 3, 90 and 94. --weak and --out are a test option (glyphs_weak165/).
- scripts/cluster.py: features and k-means. Round 1 writes clusters.npz and montage/; --round2 writes clusters2.npz and montage2/.
- scripts/classify.py: the k-NN reader. Writes model.npz and pred.npz; --holdout 44 --model-only writes model_no44.npz.
- scripts/read.py: reads a window of a plate, cutting touching figures, both ways round.
- scripts/fonts.py: font templates. Writes fonts_result.json and font_templates.npz.
- scripts/eval_faces.py: the face and street test. Writes eval_faces_insample.json, eval_faces_holdout.json and eval_faces_holdout_weak165.json.
- scripts/learning_curve.py: writes learning_curve.json.
- scripts/sample_check.py: the by-eye digit sample.
- scripts/face_check.py: the rule check.
- scripts/label_sheet.py: makes the label sheet.
- scripts/show_words.py: draws the words on a window, for debugging.

LABELS
- labels/claude_round1.json and labels/claude_round2.json: my labels.
- labels/ben_label_sheet.json: the sheet for Ben.
- labels/clusters_round1_backup.npz: a copy of the round-1 clusters my labels refer to.

MONTAGES
- montage/tiny_00-01, small_00-14, large_00-05.png (round 1).
- montage2/small_00-14, large_00-04.png (round 2).

PICTURES (look/)
- eval_holdout_knn_ctx_A/B/C.jpg and eval_holdout_font_A/B/C.jpg: readings drawn on the three faces.
- check44_digits_0.png and check44_digits_1.png: the 100-glyph sample checked by eye.
- font_templates.png: the templates of the best fonts.
- 44_lineremoval_test.png and 44_knowlton_zoom.png: line removal.
- face_*.png: the zoomed faces the truth was read from.
- 44_words_*.jpg: the word grouping.
- eval_*.txt: the printed evaluation output.

## checks

I built and tested the code checks that double-check what the text stage reads. They cover house numbers, street names, lot frontages and pipe labels, plus a confidence model that turns the check results into accept, flag for Ben, or reject.

The checks were tested on numbers and labels I read by eye in crops:
- 168 house-number labels on plate 44 (Chase, Lingo, Langland, Fergus), with the far side of Chase and the north end of Langland taken from plate 45, and 35 + 35 labels on West Sixth on plate 5;
- three lot-frontage block faces, one on 44 and two on 5;
- 16 pipe and sewer labels.

The street-name checks were tested on the 1,773 crossing reads already in the repo (picks22_reads, plates 25, 28, 39, 40, 43, 44, 45 and 80), against a name list built offline from repo data only.

What I found:
- **House numbers.** The checks catch almost every single-digit misread, including Ben's 3-for-8 and 1-for-7. A one-lot slip in the last digit (1515 read as 1513) cannot be caught by any sequence rule.
- **A real print oddity.** They also flag a genuine oddity, not a misread: Lingo Street south side is printed 1353 and 1351, opposite 1554-1548. That is a case to flag for Ben, not to reject.
- **Frontages.** The sum check catches errors of 5 ft or more, but it localises them poorly.
- **Pipe labels.** The label-beside-a-line check disagreed with the ink sorting only where the ink sorting was wrong. So it is useful feedback to the ink sorting, not grounds to reject a label.

Nothing in the repo was changed. Nothing was downloaded or trained. All output is in data/sanborn/bench_2026-11-25/text/checks/, with a second copy in _second_copy/.

### numbers

All are MEASURED unless marked ESTIMATE or ASSUMPTION. Scripts are in data/sanborn/bench_2026-11-25/text/checks/code/.

HOUSE NUMBERS (hn_checks.py; data/house_numbers.json; out/hn_true.json, out/hn_sim.json)
- True labels: 168 on 10 street sides; 2 flagged (Lingo S 1353, 1351, both printed so).
  - Without the segment-blame rule, 12 true labels were flagged (both sides of Lingo).
- Leave-one-out fit residual of the true labels, in house numbers: median 0.49, 90% 1.53, 95% 1.89, max 4.49.
- Parity held on all 10 sides.
- One-digit misreads, one label at a time, 11 confusion pairs: 1,331 variants change the value; 1,318 flagged (99.0%).
  - 3<->8: 76 variants, 100% flagged, 96.1% put right.
  - 1<->7: 162 variants, 98.8% flagged, 96.9% put right.
  - Ben's two pairs together: 238 variants, 99.2% flagged, 96.6% put right.
  - 6<->8: 85.0% flagged.
  - By digit: last digit 96.4%; other digits 100%.
- The 13 misses are all one-lot shifts of the last digit (1515->1513, 4148->4146, 508->506, ...).
- Flagged variants with exactly one candidate passing every check: right 1,260, wrong 4, no clear candidate 54.
- Which checks fire, as a share of flagged variants: fit 84%, order 72%, across 53%, join 43%, hundred 36%, parity 17%, across to plate 45 14%, range format 12%, duplicate 12%.
- CAVEAT: the tolerances (fit at least 3 numbers, or 1.5 lots' worth; across 8; join 8 + 25% rate slack; range steps 2-6) were set after looking at these same reads, so the true-label rates are optimistic. The confusion pairs other than 3/8 and 1/7 are an ASSUMPTION.

CONFIDENCE MODEL (confidence.py; out/confidence.json)
- Naive-Bayes log-odds. Likelihood ratios are counted from a multi-error simulation, 30 trials per street, fitted on 4 streets and tested on the 5th.
- Thresholds: accept at P >= 0.97, reject at P <= 0.10, flag in between.
- The reader's prior is set to 1-q (ASSUMPTION: no reader exists yet).
- q = 5%:
  - right reads: accept 96.3 / flag 3.3 / reject 0.4%;
  - wrong reads: accept 5.4 / flag 11.2 / reject 83.4%;
  - wrong among accepted 14 of 4,617 (0.30%);
  - correction proposals for flagged or rejected wrong reads: right 88.6%, wrong 0.4%, none 11.0%.
- q = 15%: right 89.9 / 8.9 / 1.2%; wrong 1.9 / 21.9 / 76.2%; wrong among accepted 0.39%; proposals right 73.9%.
- q = 30%: right 76.9 / 20.9 / 2.3%; wrong 1.8 / 40.5 / 57.7%; wrong among accepted 1.08%; proposals right 55.3%.
- Log likelihood ratios at q = 15%:
  - fit: pass +1.83, fail -2.70; order: +1.16 / -1.72; across: +1.18 / -3.06; join: +0.52 / -2.52;
  - parity, hundred and format: fail about -3.9.

LOT FRONTAGES (frontage_check.py; data/lot_frontages.json; out/frontage.json)
- Plate 44, Ben's block 4 (Chase S, 12 ft alley to Fergus): printed 350.5 ft; face 1,045.9 px.
  - At 3.000 px/ft it measures 348.6 ft (diff +1.9 ft); at 101.1 ft/in it measures 352.5 ft (diff -2.0 ft).
- Plate 5, W Sixth S west of John: printed 350.46 ft; face 1,044 px. Diff +2.5 / -2.1 ft.
- Scan scale from these two faces: 2.984 and 2.979 px/ft, i.e. 100.5-100.7 ft/in at 300 dpi.
- Plate 5, W Sixth S, John to Central: the last lot carries only '90' with no foot mark (a lot number by the KEY).
  - The check infers that lot as 86.6 ft (82.1 at nominal scale); by eye it is about 83 ft.
  - Read as 90 ft it fails at nominal scale (+7.9 ft) and passes at the measured scale (+3.4 ft).
- Misread variants on the two fully printed faces, flagged:
  - change of 5 ft or more: 56 of 56 (100%);
  - 2-5 ft: 50%;
  - 2 ft or less: 32%;
  - 3<->8: 6 of 6; 1<->7: 3 of 3.
- Localisation is weak. In 72 flagged cases a median 6 of 11-12 labels are named as suspects; 34 of 72 name the whole face.
- The face with an unlabelled lot is blind: 0 of 48 variants flagged.

PIPE LABELS (pipe_check.py; data/pipe_labels.json; out/pipes.json)
- Format: 16 of 16 true labels parse; 13 of 16 agree with the ink-bin kind of the nearest line beside or in line with them.
- By eye, all 3 disagreements are ink-bin errors (crops/bins44_lingo_sewer.png, bins44_bottom_pipes.png, bins44_p7.png):
  - 44-s1, Lingo '12" SEWER': the dashes are binned as text and water pipe;
  - 44-s7, '36" SEWER': the dashes are binned unsorted and pipe;
  - 44-p7, Powers '6" W. PIPE': the paper edge is binned as sewer and the pipe partly as text.
- Kind swapped (W. PIPE <-> SEWER): caught 13 of 16.
- Label moved 150 px across: caught 31 of 32.
- Diameter one-digit confusions: 39 of 52 (75%) caught by size plausibility or one size per street. 6<->8 and 12->42/72 pass. The size lists are an ASSUMPTION.

STREET NAMES (build_namelist.py -> data/name_list.json; name_checks.py -> out/names.json, out/names_stdout.txt)
- Name list: 4,775 keys.
  - 1,596 have a 1922 read (39 plates); 3,340 are in OSM today; 784 are in both; 20 rename aliases.
  - Of the keys with a 1922 read, 706 have no other source.
- T1, leave one plate out, 384 names: 72.9% exact; 17.7% same name with another suffix, direction or alias; 2.3% close spelling; 7.0% not found (27 names, mostly local streets or partial '?' reads).
- T2, noisy printed capitals, 341 names x 3 noise kinds, matched against the whole list (the truth is in the list by construction):
  - 1 swap 98.8%; 2 swaps 96.8%; 1 dropped letter 88.6% top-1;
  - 'confident' matches (score <= 0.25, margin >= 0.05) are right 99.7 / 97.8 / 93.7%;
  - plate-local lists hold only 82.4% of the true names.
- T3, a crossing read on two adjoining plates within 30 m: 409 pairs, 211 fully named, 193 agree (91.5%). Pairs 44/45: 66; 43/44: 22; 43/45: 76.
- T4, a read name against OSM ways within 40 m (aliases applied): match 75.7%; different name 9.8%; unnamed read 10.8%; no OSM street 2.7%; spelling differs slightly 1.0%.
- T5, margin sheet numbers of plate 44 against the world models:
  - top 45: agrees;
  - right 39: agrees;
  - left shows only '3' and the models say 43, which completes the read;
  - bottom 37: no world model for that plate.

### findings

- **C1 House-number checks catch nearly every one-digit misread, including 3-for-8 and 1-for-7** hn_checks.py on 168 labels read by eye (5 streets on plates 44, 45 and 5): 1,318 of 1,331 value-changing variants flagged (99.0%); Ben's pairs 236 of 238 (99.2%), 96.6% put right by the single candidate that passes every check. Proposals were right 1,260 times and wrong 4 times. The 13 misses all shift the last digit by one lot (1515->1513, 4148->4146, 1501->1507). So what: Parity, order, a straight-line fit along the side, the hundred-block, across-the-street and join checks are enough to stop digit misreads reaching later stages. A one-lot slip is invisible to any sequence rule, so it must be prevented by the reader's own confidence, not by the code.
- **C2 The checks flag a real print oddity, and blame the right side** Lingo St south side is printed 1353 and 1351 (crops/z_lingo_1353.png), opposite 1554-1548 and in line with Chase's 1563-1547. Without a blame rule, all 12 labels on both sides of Lingo were flagged. The segment-blame rule (a failed across or join relation is blamed on the segment whose other relations also fail) leaves 2 of 168 true labels flagged: exactly 1353 and 1351. So what: Checks must FLAG for Ben, not reject, when the evidence says the print itself is odd. The blame rule stops one odd block from casting doubt on good reads around it.
- **C3 The numbering rules seen on the plates** Along one side the number is a straight line in position: leave-one-out residual median 0.49 and max 4.49 numbers. Parity holds on all 10 sides. At a cross street, numbers either continue at the same rate (Chase across Langland: 1547 then 1529) or restart at a hundred (Langland at Chase: 4161 on 44, 4201 on 45; W Sixth at John: 500 then 438). Ranges are printed abbreviated (1529-27, 1516-12-10-08, 4120-22-24) and step by 2 or 4. Fergus and Langland do not share a numbering grid at the same y, so parallel streets are no check. So what: The reader must hand the checks each label's printed text and position, not only a value: abbreviations are expanded from neighbours, and a malformed range such as 1555-55 is itself a format error. Fergus and Langland do not share a grid, so no parallel-street rule was built; across-the-street and join carry that job.
- **C4 Adjoining plates join through the cufp world models** platemap.py carries plate 45 labels into 44's frame. Chase north side (19 labels on 45, a 200 ft/in plate) lines up with the south side on 44 (the across-other-plate check fires in 14% of flagged variants). Langland's 4161 on 44 continues as a hundred restart, 4201, on 45. Margin numbers on 44: 45 (top) and 39 (right) agree with the models. The left margin shows only '3' and the models put 43 there. Bottom 37 has no model. So what: The sheet-edge checks work wherever both plates have a world model (22 plates). Where they do not, the printed adjoining number is the only link and cannot itself be verified.
- **C5 Confidence model: checks combined as log-odds give a small, safe accept set** confidence.py, likelihood ratios counted from a multi-error simulation, leave one street out. At a 5% misread rate, 96.3% of right reads are accepted and 0.30% of accepted reads are wrong. At 15%: 89.9% and 0.39%. At 30%: 76.9% and 1.08%. Wrong reads are mostly rejected (83/76/58%) or flagged. Correction proposals for them are right 89/74/55% and wrong 0.4-0.8%. So what: The rule is: accept at P >= 0.97, flag between, reject at P <= 0.10. A rejected read with exactly one candidate that passes every check goes to Ben as a proposed correction. When the reader errs more, more goes to Ben rather than more errors getting through. A rejected READ still leaves its ink masked as text.
- **C6 Frontage sum check catches errors of 5 ft or more but cannot say which lot is wrong** frontage_check.py. Two fully printed faces pass, differing by 1.9-2.5 ft from Ben's face lengths. They give a scan scale of 2.98 px/ft (100.5-100.7 ft/in at 300 dpi). Changes of 5 ft or more: 56 of 56 flagged; 2-5 ft: 50%; under 2 ft: 32%. A median 6 of 11-12 labels are named as suspects. On W Sixth (John to Central) a bare '90' (a lot number by the KEY) leaves the last lot unlabelled; the sum then infers 86.6 ft (about 83 ft by eye) and is blind to errors (0 of 48). So what: Use the sum as a face-level check, with a tolerance of 2 ft or 1%. To find WHICH lot is wrong it needs the lot-line positions (ink bin 2) so each lot can be tested alone. A number without a foot mark must be tried both as a frontage and as a lot number.
- **C7 Pipe labels and ink bins check each other; disagreements so far were the bins' fault** pipe_check.py, label centred on its own text-bin pixels, line searched beside it and in line with it. 13 of 16 true labels sit next to a line of their own kind. By eye, the 3 that do not are bin errors: sewer dashes binned as text or pipe, a paper edge binned as sewer, a pipe binned partly as text. Moving a label 150 px is caught 31 of 32 times; swapping its kind 13 of 16. Diameter misreads: 75% caught (6<->8 and 12->42/72 pass). So what: Where a label disagrees with the bins, the label should fix the bins: relabel the line beside 'SEWER' as sewer. This is the text-first hand-off Ben asked for. Treat a disagreement as a flag, not a reason to reject the label.
- **C8 An offline street-name list from repo data covers about 93% of names on an unseen plate** build_namelist.py: 4,775 names from 1922 reads (sbg/picks22, picks22_reads, picks22_complete, Ben's 44 map, streets_marked), 1904/1912 picks, basin and LPH layers, OSM extracts, and 20 rename aliases (cufp fit.py, config.json, pick_fix.json, names_resolved.json). Leaving each plate out: 92.9% found (72.9% exact). Noisy printed capitals matched to the whole list: 98.8% right with 1 swap, 96.8% with 2, 88.6% with a dropped letter. Plate-local lists hold only 82.4% of the true names. So what: Match against the whole list and use nearness only to rank. About 7% of names will be new; flag them, do not reject them. A suffix that differs (Chase Avenue in reads and OSM, Chase Street in Ben's map) must count as consistent.
- **C9 The same crossing read on two plates agrees 91.5% of the time; the disagreements are real questions for Ben** name_checks.py T3: 211 fully named pairs, 193 agree. The 18 disagreements are Kirby vs Runnymeade and Westfork vs Virginia on Colerain (43/45), Lawrence vs Bertus and Martin vs Church on Carthage (40/80), Robb vs Kirbert (25/28), and 'Palm ?' (43/44). T4: 75.7% of read names match an OSM way within 40 m; 9.8% differ, mostly renamed or vanished streets (McMakin, Midland, Lehman, Hanifield). So what: The cross-sheet name check works on the repo's existing reads. Its failures are the renames and doubtful readings Ben should rule on. A rename he settles should be added to the alias list, so the same question is not raised again.

### needs Ben

DOWNLOADS: none were needed or made. One optional source, if Ben wants authoritative 1922 names and address ranges per block: the Williams' Cincinnati Directory for 1922. Its street guide lists street names and number ranges. Public-domain scans are held by the Public Library of Cincinnati digital library and archive.org. I did not check the size, the exact licence wording or the scan quality. It would need OCR, which is not installed. Ben must approve before anything is downloaded.

PLEASE LOOK AT, by eye:
- Lingo St south side, plate 44 at about (2343, 1170) and (2450, 1170): printed 1353 and 1351 opposite 1554-1548. Is that the print, or should it be 1553 and 1551? (crops/z_lingo_1353.png)
- Plate 45 Chase north side: 1564, 1562 and 1532 are hard to read at 200 ft/in (1566? 1569? 1537?). (crops/f45_chase_w_zoom.png, f45_chase_e_zoom.png)
- W Sixth south side, plate 5, John to Central: is the '90' on the last lot a lot number, as the KEY suggests, or a frontage? And is '20.92' on the face west of John 20.92 ft or 20'9 1/2"? (crops/f5_sixth_s_frontages.png)
- Langland E side, plate 44, near y 1820: 4120-22-24, or 4124 1/2? (crops/z_langland_e.png)
- The three pipe-label disagreements are ink-bin errors, not label errors: crops/bins44_lingo_sewer.png, bins44_bottom_pipes.png, bins44_p7.png.

CONVENTIONS TO SET:
1. May a read be corrected automatically when exactly one confusion candidate passes every check (wrong 0.4-0.8% in the simulation), or must every correction go to Ben?
2. Thresholds: accept at P >= 0.97, reject at P <= 0.10, flag in between.
3. A suffix change (Chase Street on the plate, Chase Avenue in OSM) counts as consistent.
4. Frontage sum tolerance: 2 ft or 1% of the face.
5. When a pipe label and the ink bins disagree, the label wins and re-labels the line.
6. Each rename Ben settles goes into the alias list (e.g. Kirby -> Runnymeade, already resolved 13 Nov).

FOR A FAIR TEST: the tolerances were tuned on these same by-eye reads. A held-out plate should come next: by-eye house numbers on plate 7 or 90, or Ben's own reads, before the numbers are trusted.

### files

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/checks/ (second copy of code/, data/ and out/ in _second_copy/).

CODE (run with system python -B):
- code/hn_checks.py: house-number checks and the one-misread simulation
- code/confidence.py: the accept/flag/reject model and the multi-error simulation
- code/frontage_check.py: lot-frontage sum check and localisation
- code/pipe_check.py: pipe-label format, beside-a-line check against unet_data/<P>_bins.png, and run consistency
- code/build_namelist.py: offline street-name list and aliases
- code/name_checks.py: tests T1 to T5
- code/platemap.py: plate-to-world-to-plate mapping through cufp/<N>/model.npz
- code/plot_hn.py, code/crop.py, code/bincrop.py: a chart and the crop tools

DATA:
- data/house_numbers.json: 168 labels by eye
- data/lot_frontages.json: 3 faces
- data/pipe_labels.json: 16 labels
- data/name_list.json: 4,775 names and 20 aliases

RESULTS:
- out/hn_true.json, out/hn_sim.json
- out/confidence.json, out/confidence_stdout.txt
- out/frontage.json
- out/pipes.json
- out/names.json, out/names_stdout.txt
- out/house_numbers_checks.png: number against position for each street, flagged labels ringed

CROPS LOOKED AT:
- crops/f44_*.png, f45_*.png, f5_*.png
- crops/z_lingo_1353.png, z_langland_e.png
- crops/bins44_*.png, bins5_sixth_pipes.png
- crops/m44_margins.png, m44_bottom_wide.png
- crops/overview_44.png, overview_5.png

## effect

Taking text out first would help the rail rule most. It is also the step where a careless text mask does the most damage. Nothing was trained, downloaded or installed, no repo file was changed, and Ben's edges_ben.json and rail_ben.json have the same sha256 as at the start. Everything is in data/sanborn/bench_2026-11-25/text/effect/.

RAIL
- Plate 5, as Ben saw it (23 false railroad tracks):
  - today's text bin (bin 8) taken first removes 14 of the 23;
  - bin 8 sorted with the rail rule switched off removes 21;
  - an idealised mask removes 22.
  - All 14 house-number rows and all 3 lot-number rows go. The one track left is a double lot line with hook marks and no lettering.
  - No new false track appears.
  - The real street side that the outline step dropped as 'on rail' comes back: 1 of 1 side, and 5 of 5 when there is no ground.
- Plate 44: the same kind of mask destroys real railroad.
  - The size rule calls railroad ticks 'text'. Bin 8 sorted with rail off holds 172 whole ticks, and railroad recall falls from 98.3% to 56.0% (9 of 19 of Ben's tracks missed).
  - Even today's bin 8 holds 312 tick tips. Taking it out first loses a 265 px branch (recall 96.0%).
  - With ticks kept out (16 px round Ben's tracks, which uses the truth, so it is an upper bound) nothing is lost: recall 98.2%, 0 false tracks. Streetcar recall rises 4.5-9 points on both plates.

LINES (plate 44)
- 16-26% of the false editor length lies on text. Text-dominated false lines: 17.5 per grid for the baseline, 30-43 for the new pairs.
- The right place to use a text mask is the outline step's ink test:
  - precision +0.9 to +4.5 points on all 6 grids for all five pairs;
  - recall +0.4 to +2.3 points;
  - text-dominated false lines cut by half to three-quarters;
  - only 0.7-2.7 of Ben's lines lost per grid.
- Masking the line network's output helps the new pairs a little, does nothing for the baseline, and loses true block lines where house numbers touch them.
- Word boxes cost the most: 6-10.5 of Ben's lines lost per grid.

INK BINS (plate 44)
- With text taken first, the lot-line bin shrinks 8.0%. Most of that is correct: digit '1's that today's sort files as dashed lot line.
- The pipe bin shrinks 4.7% and the sewer bin 1.7%, about half of each move correct.
- But 96-106k px of building outline wrongly become 'text', because the later size rule re-labels the pieces that removing the text sets free.

WHAT A TEXT MASK MUST GUARANTEE
- never take a rail tick or streetcar dash, not even the tip;
- never take line ink: broken grainy lines, curves, dashes;
- take whole characters, including the strokes glued to a line;
- hand over pixel strokes, not boxes;
- report symbols (hooks, dots, asterisks) as their own class;
- stop the later stages calling leftover small pieces 'text'.

### numbers

All are MEASURED unless marked ESTIMATE. Scripts are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/effect/code/ and are run from data/sanborn with python -B.

== Groundwork ==
- run_bins.py is a copy of ink_bins.py (sha 3b461d06, commit 0c4c205) with an in-memory 'text first' patch. Without a mask it reproduces earlier outputs exactly:
  - diag/rail5 orig_nets_bins.png: 0 px differ;
  - unet_data/44_bins.png: 0 px differ.
- Plate 5 tracks (run_tracks.py) match rail5: 23 tracks / 4,691 px, and 54 / 14,327 px with no ground.
- The bench hook (outlines_text.py, mode none) reproduces the stored baseline runs on all 6 grids (all headline scores identical).
- Bench runs: 41 in all (36 planned plus 5 with I2p), all exit 0.

== Masks (make_masks.py, make_masks2.py, make_boxes44.py, make_I2p44.py) ==
- S0 = today's bin 8.
- S1 = bin 8 with the railroad result discarded (text sorted before rail can take ink).
- I = S1 plus the non-line ink within 8 px of it, minus 10 px round Ben's tracks.
- I2 = S1 (or Sref on 44) with:
  - thin pieces on gap-tolerant straight lines dropped;
  - solid dots dropped;
  - glued strokes added;
  - 16 px round Ben's tracks taken out.
  I and I2 use the truth, so they are upper bounds.
- I2p = I2 with a 3 px keep-out round non-text line ink.
- B2 = word boxes from I2. B2L = B2 minus line ink.
- Sref = bin 8 of 44_bins.png.

How much ink they cover:
- Text is 44.9% of plate 44's ink (S0) and 37.8% of plate 5's.
- On 44, ink inside Ben's railroad band: S0 5,567 px; S1 59,983 px; I and I2 0.
- ben_rail_pieces44 (inline check, its code is under finding F2): S0 has 312 pieces mostly inside the band (median 10 px, the tick tips); S1 has 172 (median 241 px, whole ticks).

== Text-mask quality by eye (sample_bin8.py; 48 pixel-weighted samples each; MEASURED by eye) ==
- 44 Sref: 42 of 48 characters; 4 broken line pieces, 2 symbols.
- 5 S1: 43 of 48; 3 line pieces or dashes, 2 symbols (dot, asterisk).
- 44 I2: 44 of 48; 4 line corners or T-junctions.
- Sref pixels lying on Ben's printed lines: 24 of 24 sampled are pieces of grainy block line.
- Share of Ben's line length with mask pixels within 1 px:
  - 44 (ben_lines_text44.py): Sref 7.8% (printed lines 8.0%), I2 5.0%, B2 10.8%, B2L 3.4%;
  - plate 5 (ben_lines_text5.py): S1 3.1%, I2 2.4%.

== Rail, plate 5, networks' ground as Ben saw it (rail_summary.py, rail_compare.py, onrail5.py) ==
| mask | false tracks / px | house-number left (of 14) | hook left (of 6) | lot-number left (of 3) | railroad ink | streetcar recall at 10 px (found / partial / missed) |
|---|---|---|---|---|---|---|
| none | 23 / 4,691 | 14 | 6 | 3 | 29,381 | 76.2% (30/19/12) |
| S0 | 9 / 3,295 | 5 | 6 | 1 | 19,286 | 74.1% (27/22/12) |
| S1 | 3 / 897 | 0 | 2 | 0 | 4,180 | 74.1% |
| S1 grown 2 px | 3 / 904 | 0 | 2 | 0 | | 74.1% |
| I | 1 / 383 | 0 | 1 | 0 | | 81.0% (33/20/8) |
| I2 | 1 / 383 | 0 | 1 | 0 | 2,034 | 80.7% (33/20/8) |

- No new false tracks in any run. Streetcar precision is 100% in all runs.
- Unprotected masks cut 4 of Ben's streetcar tracks by 10-24 points; I2 lifts 12 and costs none.
- No ground: 54 / 14,327 becomes 14 / 5,855 (S1), 11 / 4,576 (I) and 8 / 4,835 (I2). Streetcar 78.8% becomes 76.9% (S1) and 83.2% (I2).
- Real block sides dropped as 'on rail': networks' ground 1 (102 px) becomes 0 with S0, S1 and I2; no ground 5 (2,543 px) becomes 0 with S1 and I2.

== Rail, plate 44, Ben's map ground, rule rail against Ben's 19 tracks (42,790 px) ==
| mask | railroad recall at 10 px | found / partial / missed | false tracks | streetcar recall |
|---|---|---|---|---|
| none | 98.3% (precision 98.8%) | 17/2/0 | 0 | 79.8% |
| S0 | 96.0% | 15/3/1 | 0 | 78.9% |
| S1 | 56.0% | 2/8/9 | 0 | 75.3% |
| S1 grown 2 px | 53.9% | | | |
| ideal with no protection | 55.4% | | | |
| I (10 px) | 97.0% | 16/3/0 | 1 (135 px) | 88.8% |
| I2r (16 px) | 98.2% (precision 99.4%) | 17/2/0 | 0 | 87.6% |

- Under S0 the lost branch runs from (2490,3457) to (2748,3400).
- Railroad ink more than 25 px from Ben's tracks: 2,436 px with no mask, 485 px with I2r.
- No ground: no mask 98.3% with 3 false tracks; S0 97.4% with 1 track missed; I2r 98.6%, 18/1/0, 0 false tracks.

== Lines, plate 44, stored runs, means of 6 grids (lines_score.py, lines_table.py) ==
| pair | false length (px) | false lines | of them mostly on text | share of false length on text (Sref / boxes) |
|---|---|---|---|---|
| baseline | 23,521 | 99.5 | 17.5 | 17.5% / 25.7% |
| V1S1 | 49,928 | 214.8 | 39.7 | 16.1% |
| V1S2 | 47,347 | 203.0 | 30.5 | 15.5% |
| V2S1 | 30,081 | 147.8 | 43.0 | 26.1% |
| V2S2 | 32,604 | 151.5 | 33.0 | 18.9% |

- Near-street text length: baseline 1,556 and V2S1 3,872. numbers_check.py had 1,496 and 3,834.
- Ben's lines touched by text (I2 ink within 2 px on 10% or more of the line): 81 of his 359 lines (40.8k px).

== Lines, masked runs: real outline step, 6 grids, paired with each pair's own stored run ==
Each cell: precision change / recall change (points). Draw = Ben's lines he would still have to draw; his lines lost per grid.
| mask | baseline | four new pairs | draw change (px) | Ben's lines lost per grid |
|---|---|---|---|---|
| ink test, I2 | +0.93 (6 of 6 grids) / +0.40 (6 of 6) | +1.4 to +4.5 / +0.6 to +2.3 | -16 to -5,418 | 0.7-2.7 |
| ink test, Sref | +0.87 / +0.28 | about the same as I2 | | |
| line map, I2 strokes | -0.09 / -0.21 | +0.9 to +2.4 / -0.1 to +0.6 | baseline +1,261 | |
| line map, I2p (keep-out) | | | baseline +332 | |
| line map, B2 boxes | +1.3 / -0.85 | +0.9 to +3.5 / -0.1 to -1.35 | +0.7k to +4.2k | 6-10.5 |
| line map, B2L | about 0 | about 0 | | |

- Ink test with I2:
  - delete length -1.4k to -4.9k px;
  - PQ -0.0005 to +0.0086;
  - false lines mostly on text: 17.5 to 8.2, 37.7 to 14.3, 30.7 to 13.7, 43.2 to 11.8 and 32.2 to 15.7.
- Line map with I2 strokes: baseline PQ -0.0023 (1 of 6 grids gain). New pairs PQ -0.003 to +0.008, delete length -2.0k to -3.3k px.
- Line map with boxes: delete length -2.3k to -6.1k px.
- ink_states.py, baseline: 'on print only' sides go from 89.8 to 77.3 per grid.

== Ink bins, plate 44, Ben's map and Ben's rail, against unet_data/44_bins.png (bins_compare.py) ==
| bin | reference px | I2 first | moved to text | moves that are right, by eye (sample of 24) |
|---|---|---|---|---|
| lot line | 1,121,745 | 1,031,879 (-8.0%) | 100.9k | 20 of 24 |
| water pipe | 465,705 | 443,751 (-4.7%) | 20.3k | 10 of 24 |
| sewer | 100,448 | 98,695 (-1.7%) | 3.8k (plus 1.6k from pipe) | 12 of 24 |
| building outline | 825,570 | 717,647 (-13%) | 96.4k | 6 of 24 |
| block line | | -0.9% | | |

- The reference's own bin 8 taken first (no new text at all) still moves 105.7k px of building outline, 27.7k of lot line and 20.2k of pipe into text: pure knock-on effect.
- ESTIMATE of correct moves: lot line about 84k of 101k; pipe about 8.5k; sewer about 1.9k; building about 24k right and 72k wrong.
- No-map sort (the outline step's own blocks, grid 0) against the map sort: block 74.8%, lot 94.6%, pipe 92.7%, sewer 94.3%. These equal the ink_bins docstring.
- With I2 first in both sorts: block 75.0%, lot 94.4%, pipe 92.9%, sewer 94.0%. Unchanged.

### findings

- **F1 Rail gains most: text first removes 21-22 of plate 5's 23 false railroad tracks, adds none, and saves the street sides dropped as 'on rail'** Measured: run_bins.py, run_tracks.py, score_rail_bench.py, rail_compare.py, onrail5.py.
- False tracks: 23 with no mask; 9 with today's bin 8 (S0); 3 with bin 8 sorted with rail off (S1); 1 with I or I2.
- By class: all 14 house-number rows and all 3 lot-number rows go with S1, I and I2. S0 leaves 5 and 1, because rail had already taken those digits before they could be sorted as text (crop rail_5_house_numbers_g4.png: 310-08-306, 304).
- Hook-mark lot lines: S1 removes 4 of 6, I2 removes 5 of 6. The one left, group 2 (lots 162-166 over 189-193), has no lettering.
- Railroad ink: 29,381 px becomes 4,180 (S1) and 2,034 (I2).
- No ground: 54 false tracks become 14 (S1) and 8 (I2).
- 'On rail' real sides: 1 becomes 0 on the networks' ground; 5 (2,543 px) become 0 with no ground. So what: Ben's point holds for rail.
- The house-number and lot-number false rail is fixed by taking text first. That is better than rail5's rule fix with no ground, where 10 house-number rows survived.
- Text must come before rail. Today's order, rail then text, cannot work, because rail takes the digits first.
- Hook-mark lot lines need a symbol class or a tick-shape test. Text first does not reliably fix them.
- **F2 The same step destroys real railroad on plate 44 unless the text mask leaves railroad ticks alone, tips included** Measured on Ben's 19 tracks.
- Recall drops:
  - from 98.3% to 56.0% with S1 (9 tracks missed);
  - to 53.9% with S1 grown 2 px;
  - to 55.4% with the ideal mask without protection;
  - to 96.0% with S0 (a 265 px branch near (2490,3457) lost).
- Cause: S1 holds 172 whole ticks (median 241 px). S0 holds 312 tick tips (median 10 px): the tips stick out beyond the 7 px railroad band, so today's sort calls them text. Crops: zoom44_branch_S0.png, rail_44_junction_S0_loss.png.
- With 10 px protection round Ben's tracks: 97.0%. With 16 px: 98.2%, 0 false tracks. No ground with 16 px: 98.6%, 0 false tracks against 3 with no mask.
- Streetcar: unprotected masks cost 1-4.5 points on 44 and cut 4 of Ben's plate-5 tracks by 10-24 points. Protected masks add 4.5-9 points.
The inline check behind the piece counts: connected components of the mask, counted as mostly in Ben's railroad band when at least half their pixels lie within 10 px of a track. So what: This is the main guarantee.
- A text stage must recognise a tick or a streetcar dash by its setting: one of an evenly spaced row of bars crossing or along a line. Size and shape alone will not do, because a lone tick looks like a '1' or a '/'.
- The 16 px protection used here needs Ben's tracks. On unchecked plates the text stage has to make this call itself, or run a tick-row finder in the same first stage and mark those bars as rail symbols, not text.
- **F3 Today's text bin is about 88-90% characters; the rest is grainy line pieces, dashes and symbols, and it lies on 8% of Ben's printed lines on 44** By eye (sample_bin8.py, 48 pixel-weighted samples each):
- 44 bin 8: 42 of 48 are characters;
- 5 bin 8 (rail off): 43 of 48;
- I2: 44 of 48.
The others are broken lot or block line pieces, T-junctions, dashes, a dot, an asterisk and a hook. Text-bin pixels on Ben's printed 44 lines: 24 of 24 sampled are pieces of grainy block line. The size rule sorts small pieces before the street-map band is applied, so a printed line that breaks up turns into 'text'.
Measured:
- the text bin lies within 1 px of 8.0% of Ben's printed line length on 44, 3.1% of his lines on plate 5 (I2: 4.6% and 2.4%);
- I2's straight-line filter took out 1,279 thin pieces (82k px) on 44 and 1,533 on 5.
Still missed by eye: curved lines (a creek-bank line, crop lines_V2S1__I2__ink_g0_false_6.png), dashes with gaps over 6 px, and L-shaped corners. So what: Bin 8 is a usable stand-in for a first test, not a mask to ship. A text stage must leave out anything that carries a line on: straight, curved, dotted or dashed. On plates without a street map nothing protects block lines at all.
- **F4 On 44, 16-26% of the false editor length lies on text; 18-43 false lines per grid are mostly text** Measured (lines_score.py, 6-grid means). Share of false length on text, then false lines mostly on text:
- baseline: 17.5%, 17.5 of 99.5;
- V1S1: 16.1%, 39.7 of 214.8;
- V1S2: 15.5%, 30.5 of 203.0;
- V2S1: 26.1%, 43.0 of 147.8;
- V2S2: 18.9%, 33.0 of 151.5.
With word boxes as the text area the shares are 21.5-36.6%. Near-street text length matches numbers_check.py within 4%. Crops show the classic case: a false line along the top of a row of house numbers (lines_base__I2__ink_g0_false_7.png: 1563-61, 1559, 1557) and one through lot figures just inside a block line (..._false_8.png). So what: Text is a real but secondary source of false lines. Water pipes and lot lines remain larger (diag ben-labels). The new pairs carry about twice the baseline's text false lines, which fits Ben's 'numbers confounding the ML'.
- **F5 For lines, use the text mask in the outline step's ink test, not on the line map, and never as boxes** Measured: bench44.py through outlines_text.py, real outline step, 6 grids, paired.
- Ink test with I2, all five pairs:
  - precision +0.9 to +4.5 points (6 of 6 grids each);
  - recall +0.4 to +2.3 points (5-6 of 6);
  - delete length -1.4k to -4.9k px;
  - text-dominated false lines 17.5 to 8.2 (baseline) and 43.2 to 11.8 (V2S1);
  - Ben's lines lost 0.7-2.7 per grid, gained 0.8-7.7.
  Today's bin 8 does about as well there.
- Line map with strokes: baseline PQ -0.0023 and draw +1,261 px. A lost 1,286 px block line has house numbers 4038-4024 written against it (lines_base__I2__lines_g0_true_0.png). A 3 px keep-out cuts that cost to +332 px and saved this line.
- Line map with boxes: recall -0.1 to -1.35 points, draw +0.7k to +4.2k px, Ben's lines lost 6-10.5 per grid. A 968 px block line is lost under the boxes round 4114-16 and 4118 (lines_base__B2__lines_g0_true_0.png). So what: Around numbers that touch a block line, the mask must never cover the line's own pixels and should keep 2-3 px off it when it touches a probability map. The ink test is safe because masking text only removes ink evidence: a true side on a printed line keeps its line ink.
- **F6 Ink bins: text first cleans the lot-line bin but, with today's later rules, turns about 100k px of building outline into 'text'** Measured (bins_compare.py, against 44_bins.png).
- With I2 first:
  - lot line -8.0% (100.9k px to text): 20 of 24 sampled right, mostly digit '1's that small_kinds calls a dashed lot line inside a block;
  - water pipe -4.7%: 10 of 24 right;
  - sewer -1.7% (3.8k to text): 12 of 24 right;
  - building outline -13% (96.4k to text): 6 of 24 right.
- With the reference's own bin 8 taken first, building outline still loses 105.7k px to text. The pieces that removing the text sets free are small, so the size rule (text up to 130 px across) calls them text.
- The no-map sort agrees with the map sort no better with text first: lot 94.6% vs 94.4%, pipe 92.7% vs 92.9%, sewer 94.3% vs 94.0%, block 74.8% vs 75.0%. So what: A text-first stage must replace the size rule's 'small means text'. After text is taken out, leftover small pieces must be sorted as line, building or dash, not text. Text first does not fix the no-map sort's main confusion, which is block line against lot line.
- **F7 Which stage gains most** Combined from F1-F6 (judgement on measured numbers).
- Rail: 23 to 1-3 false tracks on 5, and real sides saved. But it falls to 56% recall on 44 if ticks are not protected.
- Lines: 0.9-4.5 points of precision through the ink test, PQ within about ±0.009.
- Ink bins: lot-line bin cleaner, building bin damaged by the knock-on effect. So what: Do rail first, with the tick and dash guarantee. Use the same mask in the outline step's ink test. Leave the line map and the ink bins until the text stage hands over clean strokes and the later rules stop calling small pieces text.

### needs Ben

No downloads were needed and none are proposed for this measurement. The questions and checks below need Ben:

1. Symbols. Should hook marks, solid dots, asterisks and ditto marks be taken out with the text, as a symbol class? Text first leaves 1-2 hook-mark lot lines as false railroad on plate 5 (groups 2 and 8). One is a double lot line with no lettering at all.

2. Numbers on block lines. Please confirm the convention for house numbers written against a block line: the line stays a street side, and the digits are masked only 2-3 px clear of it. This sets the keep-out, which cut the baseline's extra drawing from 1,261 to 332 px.

3. Streetcar under street names. With lettering taken first, the rule's streetcar tracks run on under the letters (STREET, VINE, ELM on plate 5), where Ben's tracks stop at the lettering. Which way should these be drawn before scoring?

4. A second complete rail plate. Plate 1A's rail_ben.json is not marked complete (10 streetcar tracks, 3 unchecked rule tracks), so plate 5 is the only fully checked test plate for false rail, and it has now been studied closely.

5. Labels, if Ben approves the follow-up. About 300 hand-checked marks from plates 5 and 44 (character, rail tick, streetcar dash, hook, dot, broken line piece, dash) would let a tiny CPU classifier be fitted and tested. That classifier would make the 'never take a tick, never take line ink' test without his tracks. Not done here: no training in this task.

6. Bench timing. The 41 bench runs take about 1 GB in bench/ in the output folder, kept for checking. They can be deleted later if space matters.

### files

Everything is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/text/effect/ (about 1.3 GB). A second copy of the scripts and all JSON results is in .../text/effect/_second_copy/.

Scripts, in .../text/effect/code/ (run from data/sanborn with python -B):
- run_bins.py: guarded copy-run of ink_bins.py with --text MASK, --norail and --ground nets|none|map|nomap|nets44.
- run_tracks.py, score_rail_bench.py (copy of rail5's scorer), rail_compare.py, rail_summary.py, onrail5.py, crops_rail.py, overview5.py.
- make_masks.py, make_masks2.py (I2), make_masks_lines44.py, make_boxes44.py, make_I2p44.py, sample_bin8.py.
- outlines_text.py: hook into the real outlines.py, which is read, not changed.
- run_bench_text.py, lines_score.py, lines_table.py, lines_pics.py, ink_states.py.
- bins_compare.py, ben_lines_text44.py, ben_lines_text5.py, crops_masks44.py.
- orig/: byte copies of ink_bins.py and rail_tracks.py.

Results, in .../text/effect/scores/:
- rail_summary.json, rail_compare.json, onrail5.json, and *.json/*.txt per rail run (5_nets_*, 5_none_*, 44_map_*, 44_nomap_*).
- lines_score.json, lines_table.json, lines_table.txt, ink_states_*.json, bins_compare.json, ben_lines_text44.json, ben_lines_text5.json.

Masks (masks/: PNGs plus masks_*.json counts), runs (runs/: bins PNGs, logs, tracks JSON), bench runs (bench/<pair>__<mask>__<mode>/runs44/, run_bench.log).

Pictures checked by eye, in .../text/effect/crops/:
- overview5_text_first.jpg: plate 5's 23 false tracks coloured by which mask removes them.
- rail_5_house_numbers_g3.png and rail_5_house_numbers_g4.png: the house-number rows (g4 is where the outline step dropped a real side as 'on rail').
- rail_5_lot_numbers_g0.png, rail_5_hook_g2.png, rail_5_hook_g8.png: the lot-number and hook-mark places.
- rail_44_junction_S0_loss.png and zoom44_branch_S0.png: tick tips and whole ticks in the text masks on 44.
- sample_bin8_44*.png, sample_bin8_5*.png, sample_I2_44*.png, sample_removed_44*.png, sample_added_44*.png, sample_Sref_on_printed.png, sample_trans_tI2_*.png: the eye-check samples.
- masks44_*.png and zoom44_lotlines_bins.png: masks at house-number rows; grainy lot lines in bin 8.
- lines_base__I2__lines_g0_true_0.png: a block line lost where numbers touch it.
- lines_base__B2__lines_g0_true_0.png: a block line lost under the word boxes.
- lines_base__I2__ink_g0_false_7.png and ..._false_8.png: false lines along house numbers and lot figures removed by the ink-test mask.
- lines_*_overview.jpg: whole-plate views of what each mask removed and cost.

## skeptic

VERIFY REPORT (text-first stage, 25 Nov 2026). I measured everything on the CPU. Nothing was downloaded, installed or trained. No repo file and no other agent's folder was written to. Every output is in data/sanborn/bench_2026-11-25/text/verify/, with a second copy of the scripts and results in verify/_second_copy/.

## Headline
1. **Finder.** Its numbers reproduce exactly. But they are measured on the plates and crops it was tuned on.
   - The 0.2-0.5% "Ben's line ink called text" covers only block lines. The rate for all non-text ink is 3.6%.
   - It misses more of the lettering Ben most wants read than bin 8 does: street names, house numbers and block numbers.
2. **Effect agent.** Its rail and line numbers reproduce. But its best masks were built with Ben's truth (his rail and his street map).
   - Masks made without truth (its own Inp and S1) wreck plate 44's railroad.
   - The finder's mask, which uses no truth, keeps most of the rail and line gains.
3. **Shapes agent.** The 84% (67/80 figures) reproduces, but it was scored on the same 3 block faces used to debug the code.
   - On 271 numbers that the inventory agent read on plate 44, the same reader gets 32% of numbers exactly right and 50% of figures.
4. **Truth set.** Mostly right, with a few real errors per crop. It is good enough to compare methods that differ by about 2 points or more.
5. **Coloured lettering.** None found. Lettering on tinted fills is black ink and passes the ink threshold.

## 1. Finder
**Does it reproduce?** Yes. I re-ran finder.py on plates 44 and 5: 0 pixels differ from finder/out (verify/out/finder_rerun).

**Ben's line ink called text: CONFIRMED, but narrow.**
- I rebuilt Ben's 44 line raster with my own code (masks_vs_ben44.py): 902 px, 0.21% within 1 px; his lines are cut at 0.35% of points. Both match the finder's own figures.
- This only covers Ben's street and block lines: long straight lines, which the 61-px line rule is built to catch.
- The finder's own docstring says this exact metric chose a parameter on 44, 1A and 5.
- **Corrected general number:** on all non-text ink in the 6 truth crops (lot lines, outlines, dashes, ticks, symbols), the finder calls 3.55% text. Bin 8 calls 10.9% text (rescore_finder.py).

**Text recall: CONFIRMED overall, but the gain is smaller where it was not tuned.**
- I rescored independently against the current truth masks (rescore_finder.py).

  | | precision | recall | F1 |
  |---|---|---|---|
  | finder, all 6 crops | 0.949 | 0.868 | 0.907 |
  | bin 8, all 6 crops | 0.854 | 0.847 | 0.850 |

- The finder's own figures were 0.948 / 0.8675 / 0.906. They differ slightly because T4 and T7 were rebuilt at 12:49, after the finder scored at 12:44.
- The finder was tuned crop by crop on T1-T3 (scratch/truth_v3..v9: T1 F1 went 0.902 to 0.933). The split:

  | crops | finder P / R / F1 | bin 8 P / R / F1 |
  |---|---|---|
  | T1-T3, plate 44, tuned | 0.954 / 0.906 / 0.929 | 0.822 / 0.899 / 0.858 |
  | T4, T6, T7, not tuned crop by crop | 0.944 / 0.837 / 0.887 | 0.887 / 0.803 / 0.843 |

- 1A and 5 were still used for the line-ink tuning.

**By kind (pooled, measured): OVER-CLAIM RISK.** The finder is worse than bin 8 on exactly what Ben wants read:

| kind | finder | bin 8 |
|---|---|---|
| street names | 0.81 | 0.985 |
| house numbers | 0.88 | 0.965 |
| block numbers | 0.64 | 0.85 |
| adjoining sheet number (1 word) | 0.28 | 0.92 |
| railroad letters | 0.90 | 0.97 |
| sewer labels | 0.74 | 0.79 |

It is better on:

| kind | finder | bin 8 |
|---|---|---|
| lot numbers | 0.93 | 0.76 |
| lot dimensions | 0.91 | 0.79 |
| story heights | 0.94 | 0.71 |
| ditto marks | 0.75 | 0.47 |

- Looked at: on T4, STREET, Wm WOLFF, SUBDIV'N and the house numbers 2029-2035 along the street are mostly missed (pics/truth_T4_fin_r1c0.jpg).
- Big letters and block numbers with straight stems become line ink.

**Unseen plates: NOT MEASURED; by eye only (estimate).** I looked at 12 random windows on 90, 30, 60B, 54A, 47 and 93A (unseen_windows.py, pics/unseen_*.jpg).
- On the 100 and 200 ft plates it looks like the truth crops. Misses: block numbers 12, 70 and 71; the letters M, V, A and I; and story figures inside small boxed buildings, which go to the box rule.
- On the 400 ft plate 47 it is poor. In a dense lot block, many rotated lot numbers are missed and lot-line pieces are called text. AVE is missed. Spaced letters on a blue strip are partly missed.

## 2. Effect agent
**Rail: CONFIRMED as numbers; MISLEADING as gains unless the use of truth is stated.** I wrote my own track scorer (rail_recheck.py); it agrees with rail_summary.json.
- Plate 5, nets ground: false railroad tracks go from 23 to 1 with I, I2 or Inp, and to 3 with S1.
- But I and I2 cut out a 10-16 px band round Ben's tracks. Without that band, plate 44 breaks: Inp and S1 drop railroad recall from 0.98 to 0.55-0.56, with 9 of 19 tracks missed.
- The plate-5 streetcar gain (0.76 to 0.81) exists only with the band. Inp gives 0.74.

**The finder mask, with no truth (my track-level score of finder/rail):**

| plate | railroad | streetcar |
|---|---|---|
| 44 | recall 0.982 → 0.969; tracks found / partial / missed 17/2/0 → 16/3/0; 0 false | 0.797 → 0.817 |
| 5 | false tracks 23 → 3 (4,894 → 2,128 px) | 0.776 → 0.805, plus 1 false track |

- Looked at the 3 false tracks left on plate 5: all are lot lines with hook marks, not text (pics/finder_5_masked_false_rail.jpg).
- Caveat: plate 44 is the only railroad truth, and the finder's rules were checked against it (finder/rail/44_lost_rail.jpg).

**Lines: CONFIRMED (my own scorer reproduces lost and gained exactly); SMALL; built on truth.**
- On 44, Sref, S1, I2, I2p, B2 and B2L all come from a sorting made with Ben's street map. Sref and I2 also used his rail.
- The street map roughly halves the line ink in bin 8. Share of Ben's line ink inside each mask (1 px):

  | mask | share |
  |---|---|
  | bin 8, no map | 16.3% |
  | bin 8, with map (Sref) | 6.7% |
  | I2 | 4.3% |
  | finder | 0.21% |

- I ran the same bench with the finder mask, which uses no truth (bench_finder_mask.py, lines_recheck.py). "Ink" mode:

  | chain | false lines | Ben lines lost / gained | PQ | precision | recall |
  |---|---|---|---|---|---|
  | base | 99.5 → 91.2 | 0.8 / 0.8 | −0.0008 | +0.006 (6/6 grids) | +0.004 (6/6) |
  | V2S1 | 147.8 → 117.2 | 1.5 / 7.0 | +0.0019 | +0.035 (6/6) | +0.022 (6/6) |
  | I2 (truth), base, for comparison | 99.5 → 86.8 | | −0.0001 | +0.009 | |
  | I2 (truth), V2S1, for comparison | 147.8 → 111.8 | | +0.0034 | +0.045 | |

- PQ stays within ±0.008 in every run. "Lines" mode helps little, and slightly hurts on base.
- The honest, no-truth gain is about 60-85% of what I2 shows.

## 3. Shapes agent
**84%: REPRODUCED, but not a held-out score.** faces_repro.py gives 67/80 figures and 15/23 numbers.
- model_no44 really has no plate-44 glyphs (53,244 = 68,118 − 14,874).
- But the 3 faces steered the code. debug_faceC.png (12:17) came before edits to extract_glyphs.py (12:18) and read.py (12:34), and the final run was at 12:44.

**Independent test (read_truth44.py, model_no44, knn_ctx):** 271 numbers that the inventory agent read on T1-T3, leaving out unsure, partial and run words.

| kind | numbers exactly right |
|---|---|
| all | 86/271 (32%) |
| house numbers | 6/32 (19%) |
| lot numbers | 45/115 (39%) |
| lot dimensions | 13/82 (16%) |
| story heights | 22/42 (52%) |
| touching a line | 5/60 (8%) |
| free | 81/211 (38%) |

- Figures: 361/715 right (50%), 149 wrong, 205 missed, 55 extra. Of the figures actually read, 71% are right.
- The in-sample model gives 91/271 (34%). So the classifier is not the main limit. Glyph extraction, rotation and touching lines are.
- The font reader gets 50/271 (18%).
- I looked at a random 32 (pics/read_truth44_sheet.jpg). The boxes and the truth readings are right. Clean upright lot numbers read right; rotated, touching or crossed numbers fail.

**Letters: NOT SUPPORTED.**
- The k-NN has only 10 letter classes (A C E L M N P R T W), so it cannot read K, O, B, U, S, D, G and others.
- The 15/16 street letters (font reader) come from only 2 names.

**Knock-on for the checks agent:** its simulation assumes 5-30% of reads are wrong. The measured number-level misread rate on held-out 44 is about 68%, and the errors are systematic, not random. So its "0.3-1.1% wrong among accepted" does not apply to this reader yet.

## 4. Truth set
I looked at T1, T4 and T7 (12 tiles at 1:1 plus 6 zooms; truth_tiles.py, pics/truth_*.jpg, pics/zoom_*.jpg). The readings I checked are right. Errors found:
- **T1:** the lot lines round block "14", "151" and "N" are labelled text; "150" is labelled non-text; a lot-line corner above "A" is labelled text.
- **T4:** "119.10'" is partly non-text; a valve symbol is labelled text.
- **T7:** "83'" is non-text; "28", "165" and "82.66" are partly non-text.

Estimate, not counted: about 1-2% of text pixels are wrong. Scores for small kinds (block 7 words, adjoining sheet number 1, building names 5) are within this noise.

## 5. Coloured or tinted text
colour_text.py on 44, 5, 47, 90, 93A, 30 and 1A found glyph-sized coloured pieces above the ink threshold. Looking at the sheets for 5 and 1A, they are all slivers of fill or tinted strips, not lettering. Lettering on pink, yellow, blue and grey fills is black, for example "135" on a blue strip and "DAVIS" on grey. This confirms the inventory's finding of no red lettering.

## Files
Scripts are in verify/scripts/, results in verify/out/, pictures in verify/pics/ (paths relative to data/sanborn/bench_2026-11-25/text/).

Scripts:
- rescore_finder.py
- masks_vs_ben44.py
- rail_recheck.py
- bench_finder_mask.py
- lines_recheck.py
- read_truth44.py
- read_truth44_sheet.py
- faces_repro.py
- truth_tiles.py
- unseen_windows.py
- colour_text.py

Results:
- rescore_finder_out.json
- masks_vs_ben44.json
- rail_recheck.json
- lines_recheck.json
- read_truth44_*.json
- faces_repro.json
- colour_text.json
- finder_*_tracks.json

Bench runs: verify/bench/*__F__*. Finder mask: verify/masks/44_map_F.png.
