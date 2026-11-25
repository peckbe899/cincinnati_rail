"""Kinds of words from geometry and plate context alone (no reading). First match wins:
  junk           too small, off the paper, or a lone speck
  pipe_label     a word with an inch mark (two high strokes after it: 6", 12") in street ground with pipe or sewer ink
                 alongside (0.6-1.8 heights off its centre line), and the one or two words after it in the same phrase
                 (W. PIPE, W.P., SEWER): the second only if it carries periods or follows within 1.2 heights.
                 Or, as the inch mark often touches its figure: a word in street ground with pipe ink alongside that lies
                 more than PL_D heights from every block line (house numbers sit within about 1.5 heights of the face)
  street_name    street ground, tall (h >= ST_H) or widely spaced capitals, along the nearest of Ben's lines
  block_number   block ground, very tall (h >= BN_H), 1-3 characters, well away from every line
  lot_dimension  a feet or inch mark after the figures, or a decimal point inside (25', 18.72, 31'-6")
  house_number   2-9 characters of house-number height, within HN_D heights of a line and along it, not in a fill
  story_or_single  one character in a building fill (the story count)
  lot_number     block ground, 1-3 characters, no marks
  owner_or_note  4+ characters
  other          the rest
Thresholds are in scan px (about 300 dpi), set by eye on plate 44 (25 Nov 2026), not fitted."""
import numpy as np

# 25 Nov, after looking at Spring Grove on 44 (not a truth crop): italic house numbers there reach h 30 and were called
# street names, so below 40 px a street name must also stand clear of the line (0.9 h); owner names with commas and
# periods were called lot dimensions, so the mark rule takes 7 characters at most
ST_H = 30.0      # street-name capitals: our height (median glyph extent across the line, about 0.85 of the printed
                 # cap height) is 30 px and up on 44; house numbers 23-27, lot numbers 21-36, lot dimensions 16-26
BN_H = 45.0      # block numbers
HN_H = (19.0, 34.0)  # house numbers: any length (plate 5 writes whole runs, 227-225-223-221), in the street or hugging the face
HN_D = 2.6       # house numbers: centre within this many heights of a line
HN_A = 20.0      # ... and along it (degrees)
ST_A = 25.0
ST_H2 = 26.0     # smaller capitals (ALLEY, PERRY) count as a street name when 4+ long and mid-street (not hugging a line)
PL_D = 1.8
LD_H = 22.5      # figures smaller than this, 2+ characters, are lot dimensions even without a mark seen


def inch(w):
    """an inch mark after the word: two high strokes, or one high piece about as wide as it is long (two strokes touching)"""
    hm = [m for m in w['marks'] if m['place'] == 'high' and m['pos'] == 'after']
    return len(hm) >= 2 or any(m['s'] / max(m['t'], 1) < 1.6 and m['s'] >= 6 for m in hm)


def feet(w):
    """a feet mark: a short stroke, high, after the figures, running across the line of the text (not along it)"""
    h = w['h']
    return any(m['place'] == 'high' and m['pos'] == 'after' and 0.2 * h <= m['s'] <= 0.6 * h and m['s'] / max(m['t'], 1) >= 1.6
               and m['along'] <= 0.75 for m in w['marks'])


def decimal(w):
    """a decimal point: a small round mark, low, between two figures"""
    h = w['h']
    return any(m['place'] == 'low' and m['pos'] == 'inside' and m['s'] <= 0.35 * h and m['s'] / max(m['t'], 1) <= 2.2 for m in w['marks'])


def classify(recs, C):
    for r in recs:
        W = r['words']
        pipe_w = set()
        for k, w in enumerate(W):
            if inch(w) and w['block'] == 0 and w['pipe_side'] >= 0.25 and w['h'] <= 32:
                pipe_w.add(k)
                if k + 1 < len(W) and W[k + 1]['block'] == 0:
                    pipe_w.add(k + 1)
                    if k + 2 < len(W) and W[k + 2]['block'] == 0 and (W[k + 2]['m_low_in'] + W[k + 2]['m_low_after'] > 0 or (W[k + 1]['gap_next'] or 9) <= 1.2) and W[k + 2]['nch'] <= 6:
                        pipe_w.add(k + 2)
        for k, w in enumerate(W):
            if w['block'] == 0 and w['paper'] and w['pipe_side'] >= 0.35 and w['d_line'] > PL_D * w['h'] and 10 <= w['h'] <= 30 and w['nch'] >= 2: pipe_w.add(k)
        for k, w in enumerate(W):
            h, n = w['h'], w['nch']; blk = w['block'] == 1
            w['feet'] = feet(w); w['decimal'] = decimal(w)
            along = w['d_line'] <= HN_D * h and w['line_angle_diff'] <= HN_A
            if not w['paper'] or h < 8 or (r['n'] == 1 and h < 12): k_ = 'junk'
            elif k in pipe_w: k_ = 'pipe_label'
            elif not blk and (r['spaced'] or (h >= ST_H and n >= 2 and w['line_angle_diff'] <= ST_A and (h >= 40 or w['d_line'] >= 0.9 * h))
                              or (h >= ST_H2 and n >= 4 and w['line_angle_diff'] <= ST_A and w['d_line'] >= 0.9 * h)): k_ = 'street_name'
            elif blk and h >= BN_H and n <= 3 and w['d_line'] >= 1.5 * h: k_ = 'block_number'
            elif (w['feet'] or w['decimal']) and h <= 30 and n <= 7: k_ = 'lot_dimension'
            elif n >= 2 and HN_H[0] <= h <= HN_H[1] and along and w['fill'] < 0.5 and (not blk or w['d_line'] <= 1.2 * h): k_ = 'house_number'
            elif h < LD_H and n >= 2: k_ = 'lot_dimension'
            elif n == 1 and w['fill'] >= 0.5: k_ = 'story_or_single'
            elif blk and n <= 4: k_ = 'lot_number'
            elif n >= 4: k_ = 'owner_or_note'
            else: k_ = 'other'
            w['kind'] = k_
