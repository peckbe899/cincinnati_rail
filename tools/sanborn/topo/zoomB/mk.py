try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json
P={"13": {"TL": [354, 595], "TR": [9583, 622], "BL": [369, 7306], "BR": [9556, 7287]}, "14": {"TL": [354, 629], "TR": [9577, 618], "BL": [386, 7350], "BR": [9582, 7280]}, "15": {"TL": [365, 620], "TR": [9598, 660], "BL": [364, 7320], "BR": [9559, 7303]}, "16": {"TL": [335, 608], "TR": [9540, 624], "BL": [337, 7320], "BR": [9518, 7297]}, "17": {"TL": [331, 600], "TR": [9550, 655], "BL": [315, 7303], "BR": [9500, 7302]}, "18": {"TL": [345, 622], "TR": [9544, 655], "BL": [337, 7359], "BR": [9510, 7338]}, "19": {"TL": [362, 621], "TR": [9556, 662], "BL": [351, 7349], "BR": [9542, 7308]}, "20": {"TL": [357, 608], "TR": [9549, 641], "BL": [310, 7330], "BR": [9492, 7319]}, "21": {"TL": [311, 619], "TR": [9511, 662], "BL": [299, 7334], "BR": [9482, 7313]}, "22": {"TL": [351, 626], "TR": [9535, 680], "BL": [323, 7337], "BR": [9502, 7310]}, "23": {"TL": [348, 634], "TR": [9522, 662], "BL": [343, 7338], "BR": [9507, 7314]}, "24": {"TL": [346, 647], "TR": [9527, 681], "BL": [333, 7307], "BR": [9492, 7295]}}
L={ # x_left, x_right, y_top, y_bottom
"13":("17000 E","28000 E","34000 N","26000 N"),
"14":("17000 E","28000 E","26000 N","18000 N"),
"15":("17000 E","28000 E","18000 N","10000 N"),
"16":("17000 E","28000 E","10000 N","2000 N"),
"17":("17000 E","28000 E","2000 N","6000 S"),
"18":("6000 E","17000 E","6000 S","14000 S"),
"19":("6000 E","17000 E","2000 N","6000 S"),
"20":("6000 E","17000 E","10000 N","2000 N"),
"21":("6000 E","17000 E","18000 N","10000 N"),
"22":("6000 E","17000 E","26000 N","18000 N"),
"23":("6000 E","17000 E","34000 N","26000 N"),
"24":("6000 E","17000 E","42000 N","34000 N")}
N={
"13":"All labels clear. TL: several parallel street/building lines run just inside the left neatline; outermost line taken as border. BL x label printed '17000·E' (stray dot). Diagonal neighbor tags: TL (Sheet 24), BL (Sheet 22), BR (Sheet 11).",
"14":"All labels clear. Bottom border not level: BL y~7350 vs BR y~7280 (70 px), larger skew than other sheets. Neighbor tags: TL (Sheet 23), BL (Sheet 21), BR (Sheet 10).",
"15":"All labels clear. Neighbor tags: TL (Sheet 22), TR (Sheet 11), BL (Sheet 20), BR (Sheet 9).",
"16":"All labels clear. Neighbor tags: TL (Sheet 21), TR (Sheet 10), BL (Sheet 19), BR (Sheet 8).",
"17":"All labels clear. Neighbor tags: TL (Sheet 20), TR (Sheet 9), BL (Sheet 18), BR (Sheet 7).",
"18":"All labels clear. Printer imprint '...CO., BALTO., MD.' just outside bottom border near BR. Neighbor tags: TL (Sheet 29), TR (Sheet 17).",
"19":"All labels clear. Neighbor tags: TL (Sheet 28), TR (Sheet 16), BL (Sheet 30).",
"20":"All labels clear. Neighbor tags: TL (Sheet 27), TR (Sheet 15), BL (Sheet 29), BR (Sheet 17).",
"21":"All labels clear. Neighbor tags: TL (Sheet 26), TR (Sheet 14), BL (Sheet 28), BR (Sheet 16).",
"22":"All labels clear. TR y label '26000 N' printed well below the corner (~y 710). Neighbor tags: TL (Sheet 25), TR (Sheet 13), BL (Sheet 27), BR (Sheet 15).",
"23":"All labels clear. TR: street lines run along just inside the right neatline; outermost line taken as border. Neighbor tags: TR (Sheet 12), BL (Sheet 26), BR (Sheet 14).",
"24":"All labels clear. BR: rail/street lines run along just inside the right neatline; outermost line taken as border. Printer imprint '...CO. BALTO., MD.' outside bottom border near BR. Neighbor tag: BR (Sheet 13)."}
out={}
for s,p in P.items():
    xl,xr,yt,yb=L[s]
    out[s]={"TL":{"px":p["TL"],"x":xl,"y":yt},"TR":{"px":p["TR"],"x":xr,"y":yt},
            "BL":{"px":p["BL"],"x":xl,"y":yb},"BR":{"px":p["BR"],"x":xr,"y":yb},"note":N[s]}
json.dump(out,open((_ws.DATA + "topo/comp/read_B.json"),"w"),indent=1)
print(len(out))
