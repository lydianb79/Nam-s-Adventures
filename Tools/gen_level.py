#!/usr/bin/env python3
"""Builds Assets/Resources/Levels/level1.txt  ("Paddy Field Dash").
Grid legend (row 0 = bottom):
  # ground   = bamboo one-way   C crumble   ^ spikes   D drum spring   B brazier (flame jet)
  o coin  L lotus  S som tam  G sangsom  H chili  M mango
  P start  K checkpoint  X goal gong
  m monkey  c cobra  q mosquito  r crab  d durian  g ghost
After the grid come object lines:  raft x y dx dy seconds   /   decor name x y
"""
import os, sys
W, H = 218, 20
g = [[" "] * W for _ in range(H)]
objs = []

def put(x, y, ch):
    assert g[y][x] in " " or ch == g[y][x], (x, y, ch, g[y][x])
    g[y][x] = ch
def ground(x0, x1, top):
    for x in range(x0, x1 + 1):
        for y in range(top): g[y][x] = "#"
def row(x0, x1, y, ch):
    for x in range(x0, x1 + 1): put(x, y, ch)
def coins(x0, x1, y, step=1):
    for x in range(x0, x1 + 1, step): put(x, y, "o")
def arc(x0, x1, y):
    n = x1 - x0
    for i in range(n + 1):
        put(x0 + i, y + (1 if 0 < i < n else 0), "o")
def raft(x, y, dx, dy, t): objs.append("raft %g %g %g %g %g" % (x, y, dx, dy, t))
def decor(name, x, y, z=None, yaw=None, sc=None):
    objs.append("decor %s %g %g" % (name, x, y) + ("" if z is None else " %g %g %g" % (z, 90 if yaw is None else yaw, 1 if sc is None else sc)))

# ---- 1. village start --------------------------------------------------------
ground(0, 27, 3)
put(3, 3, "P")
decor("w2_0", 1, 3); decor("frangipani", 0.2, 3, 3.1, 60, 1.25); decor("lanterns", 2.6, 3, 3.2); decor("bamboo", 11.6, 3, 3.2, 40); decor("tuktuk", 5.0, 3, 2.9, 70); decor("spirit", 12.6, 3, 2.3, 80); decor("fence", 10.6, 3, 3.2); decor("w1_0", 7.9, 3); decor("w1_2", 9.5, 3); decor("w2_1", 11, 3); decor("w2_1", 12.2, 3)
arc(10, 13, 5)
ground(14, 17, 4); ground(18, 21, 5)
decor("w2_2", 15, 4); decor("flags", 16, 4, 2.7); decor("fence", 24.5, 3, 3.1); decor("buffalo", 34.5, 3, 2.4, 20); decor("w2_1", 19, 5); decor("w2_0", 20.5, 5)
coins(18, 21, 7)
put(25, 3, "m"); decor("w2_1", 23, 3); decor("w2_1", 26.5, 3)
arc(27, 31, 5)
# ---- 2. cobra plateau ---------------------------------------------------------
ground(31, 40, 3)
decor("w2_2", 32, 3); decor("w2_1", 36, 3)
row(33, 35, 5, "="); row(36, 38, 8, "=")
coins(33, 35, 6); put(37, 9, "S")
put(39, 3, "c")
ground(41, 44, 5); decor("w2_0", 42.5, 5)
arc(44, 48, 7)
ground(48, 52, 5); put(51, 5, "r"); decor("w2_1", 49, 5)
# ---- 3. klong crossing (rafts) --------------------------------------------------
raft(54, 4, 5, 0, 3.2)
put(57, 7, "q"); coins(55, 59, 6, 2)
ground(62, 63, 4); put(63, 4, "D")
put(63, 12, "L"); row(65, 66, 9, "="); coins(65, 66, 10)
raft(65.5, 4, 5.5, 0, 3.0)
put(69, 7, "q"); coins(67, 71, 6, 2)
# ---- 4. checkpoint + chili run ---------------------------------------------------
ground(75, 99, 3)
put(76, 3, "K"); decor("w2_0", 82.7, 3);
# a low tunnel: duck to creep through for the coins (or hop over it)
for x in range(78, 81): g[4][x] = "#"
coins(78, 80, 3); decor("spirit", 81.5, 3, 2.5, 100); decor("fence", 84, 3, 3.2); decor("fence", 88, 3, 3.2); decor("flags", 94.5, 3, 2.6); put(80, 5, "H")
put(84, 3, "m"); put(87, 3, "m"); put(89, 3, "r")
decor("w2_1", 82, 3); decor("w2_2", 86, 3); decor("w2_1", 90.5, 3)
row(92, 93, 3, "^"); row(96, 97, 3, "^")
arc(91, 94, 5); arc(95, 98, 5)
row(101, 102, 4, "C"); row(105, 106, 5, "C"); row(109, 110, 6, "C")
coins(101, 102, 6); coins(105, 106, 7); coins(109, 110, 8)
put(107, 9, "q")
# ---- 5. durian grove + bamboo climb ------------------------------------------------
ground(113, 120, 6)
put(114, 7, "M"); put(117, 6, "B"); decor("w2_1", 119.4, 6)
ground(121, 126, 3)
put(122, 9, "d"); put(125, 9, "d"); coins(122, 125, 4)
decor("w2_2", 123.5, 3)
ground(127, 132, 3)
row(128, 129, 5, "="); row(131, 132, 8, "="); row(127, 128, 11, "=")
coins(128, 129, 7); coins(131, 132, 10)
put(127, 13, "L"); put(130, 14, "q")
ground(133, 140, 11)
put(135, 11, "K"); put(138, 13, "G"); decor("w2_0", 136.5, 11); decor("w5_2", 134, 11); decor("flags", 137.5, 11, 2.8); decor("buffalo", 152.5, 8, 2.5, 150); decor("fence", 155, 8, 3.2)
# ---- 6. spike gauntlet (best with SangSom!) -----------------------------------------
ground(141, 166, 8)
row(144, 147, 8, "^"); row(151, 154, 8, "^"); row(158, 161, 8, "^")
put(149, 8, "r"); put(156, 8, "m"); put(164, 8, "c")
put(146, 12, "q"); put(153, 12, "q"); put(160, 12, "q")
coins(144, 147, 11); coins(151, 154, 11); coins(158, 161, 11)
decor("w5_0", 142, 8); decor("w5_0", 163, 8)
put(166, 11, "S")
# ---- 7. finale over the river ---------------------------------------------------------
row(168, 169, 8, "C"); row(172, 173, 9, "C")
coins(168, 169, 10); coins(172, 173, 11)
ground(176, 178, 9); put(177, 9, "B")
raft(180, 9, 5, 0, 2.8)
put(183, 12, "q"); put(186, 14, "g")
coins(181, 185, 11, 2)
ground(189, 190, 8); put(190, 8, "D")
row(192, 194, 14, "="); put(193, 16, "L"); coins(192, 194, 15, 2)
row(192, 193, 8, "C")
# ---- 8. temple & gong ---------------------------------------------------------------
ground(196, W - 1, 6)
put(198, 7, "M")
decor("w5_1", 199.5, 6); decor("w4_1", 203, 6); decor("w5_1", 205.5, 6)
decor("chedi_gold", 214.3, 6, 2.2); decor("flags", 203.5, 6, 3.0); decor("spirit", 198.3, 6, 2.6, 80); decor("w5_2", 201.5, 6); decor("w5_0", 208, 6); decor("w5_0", 212.4, 6)
put(210, 6, "X")
coins(200, 207, 8)

out = os.path.join(os.path.dirname(__file__), "..", "Assets", "Resources", "Levels", "level1.txt")
with open(out, "w") as f:
    for y in range(H - 1, -1, -1):
        f.write("".join(g[y]).rstrip() + "\n")
    f.write("---\n")
    f.write("\n".join(objs) + "\n")
print("wrote", out, W, "x", H)
for y in range(H - 1, -1, -1):
    print("".join(g[y]))
