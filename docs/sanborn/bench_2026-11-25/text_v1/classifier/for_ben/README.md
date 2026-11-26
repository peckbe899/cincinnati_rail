# Labelling sheets for the character-or-not classifier

26 Nov 2026. Three picture sheets, about 150 rows each. Each row is one group of look-alike glyphs.

Claude has already filled in a guess for every row, so you only correct the wrong ones.

## What is here

| sheet | pictures | the file you edit | rows |
|---|---|---|---|
| A: figures at lot-number size (24-48 px tall) | sheet_A_digits_p01.png to p06.png | labels_A_digits.csv | 150 |
| B: capitals (K O B U S D H G are the ones most wanted) | sheet_B_capitals_p01.png to p06.png | labels_B_capitals.csv | 145 |
| C: the marks ' " & and junk (hooks, ticks, hydrant dots, dashes, line stubs, lot-line corners, symbols) | sheet_C_marks_junk_p01.png to p06.png | labels_C_marks_junk.csv | 149 |

Leave members.npz and sheets.json alone. They tell Claude which glyphs each row stands for, so your label can go to every glyph in the row, not only the 26 shown.

## How to read a row in the picture

From left to right:
- the row number;
- Claude's guess, in big letters. 'mixed' means Claude thinks the row is not one thing;
- small grey text: 'cl:' is the classifier's own guess, shown only where Claude changed it by eye. 'p' is the classifier's average confidence, 'n' is how many glyphs are in the row, and 'px' is their usual height;
- the row's average glyph (blurred);
- 26 sample glyphs. Each is turned upright by the direction of its word, and the small grey number under it is its height in pixels.

## What to type

Open the sheet's CSV in Excel or Notepad, and change only the **label** column. The row number matches the picture.

- **Right:** leave it.
- **Wrong:** type the right one:
  - a character: 0-9, A-Z, a-z, or one of `'` `"` `.` `-` `&` `,`
  - `junk`, when nothing in the row is lettering
  - `pair`, for two figures that touch (for example 25)
- **Mixed:** clear the cell, so it is empty. A row is mixed when fewer than about 24 of the 26 glyphs are the same thing.

Then save the file as CSV, under the same name.

A letter turned on its side or upside down is still that letter. An E lying on its back is E, and an upside-down A is A. Words that read up or down the sheet come out like this.

## What Claude has already done

- **Sheet A:** the classifier's guesses look right on the two pages Claude checked. Only row 150 was changed, to mixed.
- **Sheet B:** Claude looked at all six pages. 47 guesses were changed, and 33 rows are marked mixed.
- **Sheet C:** Claude looked at pages 1-4 and 6. 34 guesses were changed, and 22 rows are marked mixed.
- The 'claude_looked' column says which rows Claude saw. Rows marked 'no' are the classifier's guess, unchecked.

The rows that matter most to the mask, because a figure 1 and a dash look the same:
- **Sheet C rows 19, 33, 35, 40, 95, 96, 98-100 and 142-149.** These are slanted strokes. Are they figure 1s, primes `'`, or dashes and line stubs? Claude guessed `1` for rows 98-100 and `'` for rows 145, 147 and 149, left rows 33 and 35 as junk, and marked the other rows mixed.
- **Sheet B rows 55-59.** These are long single bars, 60-90 px. Are they the letter I of street names, or pieces of line? Claude marked them mixed.
- **Sheet B rows 138-140.** These are crosses. Claude guessed junk.
- **Sheet B row 87.** These are thin circles, 60-80 px. Claude guessed junk, because hydrant circles are not text under the proposed convention.

## Conventions used

These are the plan's proposals, which you have not answered yet:
- ditto marks and story heights are text;
- hydrant circles, manhole O marks, hook marks and rail ticks are junk.

If you want them the other way, say so, and label those rows to match.

## Not on the sheets

Glyphs under 12 px are left out. The glyph cutter does not keep them at full size, so full stops, most primes and the hyphen are missing. Shape alone cannot tell those from specks and dashes anyway. Context decides them: the classifier's combiner and finder2's rules.

## How long it will take

These are estimates, at 4-6 s per row to check a guess and longer where you type:
- A: about 10-15 min, because nearly all guesses look right;
- B: about 15-20 min;
- C: about 10-15 min.

That is **about 35-50 min** in all.

## What happens next

Claude reads your CSVs with `python -B bench_2026-11-25/text_v1/classifier/scripts/read_ben_labels.py`, run from data/sanborn. It writes one label per glyph, and they go into the next fit of the classifier in place of Claude's cluster labels.
