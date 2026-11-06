p='draw4.py'; s=open(p).read()
rep=[
("(4600, 'B and W closing up'),\n        (5000, 'compact: 10 tracks at 4.5 m'), (5468, 'Northside / Spring Grove island'), (6050, 'Ludlow curve, on fill')",
 "(4600, 'W and B on their one curve east'),\n        (5100, 'constant width, island spacing held to Northside'), (5468, 'Northside / Spring Grove island'), (6100, 'compact again on the fill')"),
("'5. North of Arlington: one curve each moves W and B 9 m east, then constant width'","'5. North of Arlington: straight, one curve, straight; W and B move east on the curve'"),
("(P(4500, -50), 'W and B: one curve each, 893-916 m, s 4,379-4,869')","(P(4500, -50), 'trunk curve 1 R 1,310 m (s 4,260-4,928); W and B one curve each, 1,200-1,223 m')"),
("(P(5369, 40), 'Ludlow: viaduct ends at the platform end (s 5,570)')","(P(5150, 40), 'straight s 4,928-5,354 through Ludlow'), (P(5570, 40), 'viaduct ends (s 5,570); trunk curve 2 R 800 m from s 5,354')"),
("constant 58.8 m deck, s 4,870-5,570","constant 58.8 m deck, s 4,880-5,570"),
("'6. Ludlow to the Mill Creek bridge (creek open north-east of Albone only)'","'6. Ludlow to the Mill Creek bridge: curve 2, 43 m straight, curve 3, straight'"),
("(P(5450, 40), 'pinch 1: OH-75 on the east, s ~5,450')","(P(5450, 40), 'OH-75 (east) and the culvert (west) hold the straight here')"),
("(P(6050, -75), 'pinch 2: the open creek bend, s ~6,050 (line 18 m east)')","(P(6050, -75), 'curve 3 (left, R 1,250 m): forced by the open creek bend and the bridge line')"),
("(P(6700, 45), \"back on today's line from s ~6,450\")","(P(6700, 45), \"straight on today's line from s 6,248\")"),
("'min radius 879 m (s 5,300-6,400); clear of the culvert south-west of Albone\\nblue dashes: today\\'s line'","'trunk: curve 1 R 1,310 | straight | curve 2 R 800 | 43 m straight | curve 3 R 1,250 | straight\\nclear of the culvert south-west of Albone; blue dashes: today\\'s line'"),
("(P(5300, -50), 'same width since s 4,870: no step-out')","(P(5300, -50), 'same width since s 4,880: no step-out')"),
("(P(5468, 30), 'Northside island on the 879 m curve')","(P(5468, 30), 'Northside island; curve 2 (R 800 m) starts s 5,354')"),
("(P(5570, 30), 'viaduct ends, fill north')","(P(5570, 30), 'viaduct ends; W and B SB in on one curve (~730 m)')"),
]
for a,b in rep:
    assert a in s, a; s=s.replace(a,b)
open(p,'w').write(s)
