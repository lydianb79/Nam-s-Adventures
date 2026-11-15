#!/usr/bin/env python3
"""Generates levels 2-25, the ending scene and the theme table.

    python3 Tools/gen_levels.py

Writes  Assets/Resources/Levels/level<N>.txt  (N = 2..25),  ending.txt  and  themes.txt.
Level 1 is hand-made (Tools/gen_level.py). Every level has its own theme: sky, light, water, ground,
scenery, enemy cast, props and music. Layouts are assembled from hand-tuned chunks (pits, rafts, crumbling
planks, spikes, climbs, tunnels ...) whose sizes follow Nam's jump metrics, with difficulty rising per level.

Jump metrics (see Player.cs): jump height 3.5 tiles; walk jump clears a 4-tile gap, run jump 6;
drum bounce 8.7; ducked height 0.85 (fits a 1-tile tunnel).
"""
import os, random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "Assets", "Resources", "Levels")
H = 26

# ------------------------------------------------------------------------------------------------ themes
# decor entries: (model, z depth behind the lane, scale, footprint in tiles)
DEFAULT = dict(
    sky="2680E6,60B4F5,ECF7FF", sun="FFF0D1", sunI=1.0, sunDir="40,32", ambSky="6680B8", ambGround="574D42",
    fog="B8E0F7", fogStart=34, fogEnd=300, water="4DDBE6,0A57A0,F2FFFF", waterSky="CCEEFF,4090F0", night=0,
    top="grass", face="earth", topTint="FFFFFF", faceTint="FFFFFF", blades=1, bladeA="5CB33D", bladeB="BDF25C", bladeH=1.0,
    scatter="grass,flower,rice,rock", trees="palm,palm,banana,bamboo,frangipani",
    hills="terrace", hillModel="terrace", hillColors="7FCB58,6ABC4E", crowns="wat,chedi_gold", hillProps="hut",
    pads="lotuspad", islands="E9DCA6,86CC55", floaters="boat", extras="buffalo", far="karst", mountains="7FA9D2,8DB4D8",
    clouds=16, cloudCol="FFFFFF", fore="palm,banana", flutter="butterfly_a,butterfly_b,butterfly_c", particles="petal",
    enemies="monkey,crab,cobra,mosquito,durian,ghost", exposure=0.08, stars=0, lanterns=0, music="music_level",
)

T = lambda name, sub, decor, **kw: dict(DEFAULT, name=name, sub=sub, decor=decor, **kw)
NIGHT = dict(night=1, stars=1, sun="A9C4FF", sunI=0.42, sunDir="48,-25", ambSky="2A3566", ambGround="1E1A2E", fog="161A3A", fogStart=26, fogEnd=210,
             sky="050818,10184A,3A2E6E", water="2E5FA8,060B2E,BFD8FF", waterSky="3A3A7A,0A0F3A", cloudCol="3A4270", clouds=8, exposure=0.25,
             flutter="firefly", particles="firefly")
DUSK = dict(sky="3B2A7A,D4587A,FFC27A", sun="FFB070", sunI=0.95, sunDir="22,60", ambSky="7A5A8E", ambGround="5A3A3A", fog="F2A77E", fogStart=30, fogEnd=260,
            water="E8907A,3A2A6E,FFE6C8", waterSky="FFC89A,7A4A9A", cloudCol="FFB8A0", exposure=0.12)

THEMES = [
    T("Paddy Field Dash", "Rice paddies", []),                                                                             # 1 (hand-made level)
    T("Banana Grove", "Plantation", [("banana", 1.8, 1.2, 2), ("crate", 2.2, 1.0, 2), ("wheelbarrow", 2.4, 1.0, 2), ("fence", 3.1, 1.0, 3), ("hut", 3.0, 0.9, 4)],
      trees="banana,banana,banana,palm", hills="blob", hillColors="6CC04A,58B040", hillProps="banana,banana,hut", scatter="grass,flower,fern,rock",
      fore="banana,banana", bladeA="4FA838", bladeB="A8E650", enemies="monkey,crab,cobra,mosquito,durian,ghost", music="music_l02"),
    T("Floating Market", "Canal boats", [("fruit_stall", 2.4, 1.0, 3), ("dock_post", 3.2, 1.0, 1), ("fruit_basket", 1.6, 1.0, 1), ("crate", 2.6, 1.0, 2), ("lanterns", 3.0, 1.0, 4)],
      top="wood", face="wood", blades=0, scatter="fruit_basket,crate", pads="lotuspad", floaters="boat_fruit,boat,boat_fruit", extras="",
      hills="city", buildings="pier_house,hut,pier_house", water="7AC8B8,1F5A66,F2FFFF", islands="", trees="palm,banana", fore="palm",
      enemies="rat,crab,cobra,dragonfly,flowerpot,ghost", music="music_l03"),
    T("Bamboo Forest", "Green silence", [("bamboo_tall", 2.6, 1.0, 2), ("stone_lantern", 2.0, 1.0, 1), ("fern", 1.4, 1.2, 1), ("bamboo", 3.0, 1.2, 2), ("rock", 1.8, 1.6, 2)],
      sky="6FB89A,A8DCC0,E8F8EC", fog="BFE8D0", fogStart=18, fogEnd=150, ambSky="6FA890", sun="F2FFE0", sunI=0.85, top="moss", scatter="fern,grass,rock,fern",
      trees="bamboo_tall,bamboo,bamboo_tall", hills="forest", hillProps="bamboo_tall,bamboo_tall,bamboo", hillColors="4E9A52,3F8A48", pads="", floaters="", extras="",
      far="", mountains="7FB89A,8FC4A8", fore="bamboo,bamboo", bladeA="3E8E3A", bladeB="8FD060", particles="leaf", water="6FC8A0,1F5A4A,E8FFF2",
      enemies="frog,crab,gecko,dragonfly,coconut,ghost", music="music_l04"),
    T("Elephant Trail", "Deep jungle", [("elephant", 2.6, 1.0, 5), ("jungle_tree", 2.8, 1.1, 4), ("fern", 1.5, 1.3, 1), ("banana", 2.0, 1.2, 2), ("rock", 1.7, 1.8, 2)],
      sky="3A8FD0,8FCBE8,E8F6E0", fog="CDE8C8", fogStart=22, fogEnd=190, top="mud", topTint="B8C27A", scatter="fern,fern,grass,rock", trees="jungle_tree,palm,banana",
      hills="forest", hillProps="jungle_tree,jungle_tree,palm", hillColors="4A9A48,3E8A40", far="karst", fore="jungle_tree,banana", bladeA="3F8E38", bladeB="96D858",
      particles="leaf", extras="elephant", enemies="monkey,scorpion,cobra,hornbill,coconut,ghost", music="music_l05"),
    T("Tea Hills", "Morning mist", [("tea_bush", 1.6, 1.0, 1), ("tea_bush", 2.2, 1.1, 1), ("tea_basket", 1.8, 1.0, 1), ("pine", 2.8, 1.2, 2), ("hut", 3.0, 0.9, 4)],
      sky="8FB8E0,C8E0F0,FFF4E0", sun="FFE8C0", sunI=0.9, sunDir="24,40", fog="E6F0F2", fogStart=14, fogEnd=140, ambSky="8FA8C8", trees="pine,pine,tea_bush",
      hills="terrace", hillModel="tea_terrace", hillProps="pine,hut", crowns="hut,pine", scatter="tea_bush,grass,flower,rock", pads="", floaters="", extras="",
      far="", mountains="8FB0C8,A8C4D8", fore="pine", bladeA="2F8A4A", bladeB="7FD070", particles="petal", water="A8DCE8,3A6E8E,FFFFFF",
      enemies="frog,crab,cobra,hornbill,coconut,ghost", music="music_l06"),
    T("Emerald Falls", "Seven tiers", [("waterfall", 3.0, 1.0, 5), ("pool_rock", 2.2, 1.0, 3), ("fern", 1.5, 1.3, 1), ("jungle_tree", 3.0, 1.0, 4), ("rock", 1.6, 2.0, 2)],
      water="5FE8D8,0E7A8A,FFFFFF", waterSky="D8FFF8,40C0D0", top="stone", topTint="D8E8D0", face="rock", faceTint="E8E0D0", blades=0, scatter="fern,rock,fern,flower",
      trees="jungle_tree,palm,bamboo", hills="cliff", hillProps="jungle_tree,palm", far="karst", fog="D0F0EC", fogStart=24, fogEnd=200, fore="jungle_tree",
      pads="", floaters="", extras="", particles="leaf", enemies="frog,crab,gecko,dragonfly,coconut,ghost", music="music_l07"),
    T("Sunflower Fields", "Golden rows", [("sunflower", 1.5, 1.0, 1), ("sunflower", 2.1, 1.15, 1), ("sunflower", 2.7, 1.25, 1), ("scarecrow", 2.4, 1.0, 2), ("haybale", 2.0, 1.0, 2)],
      sky="2C8AE8,7CC4F8,FFF6D0", sun="FFF2B8", sunI=1.1, scatter="sunflower,grass,flower,sunflower", trees="sunflower,palm", hills="blob", hillColors="F2C83A,E0B82E,8FC84A",
      hillProps="sunflower,sunflower,hut", pads="", floaters="", extras="buffalo", fore="sunflower,sunflower", bladeA="6FA838", bladeB="E8E050", far="", mountains="9FC0E0,B0CCE8",
      enemies="monkey,crab,cobra,dragonfly,durian,ghost", music="music_l08"),
    T("Monkey Temple", "Ancient prangs", [("prang", 2.8, 1.0, 4), ("ruin_wall", 2.6, 1.0, 3), ("ruin_column", 2.0, 1.0, 1), ("frangipani", 2.6, 1.2, 3), ("stone_lantern", 1.8, 1.0, 1)],
      top="stone", topTint="E0C8A8", face="brick", blades=0, scatter="rock,ruin_column,grass,flower", trees="frangipani,palm", hills="city", buildings="prang,ruin_wall,prang",
      sky="3A90E0,90C8F0,FFE8C8", fog="F0DCC0", fogStart=28, fogEnd=240, far="prang", pads="lotuspad", floaters="", extras="", fore="frangipani",
      enemies="monkey,scorpion,cobra,pigeon,coconut,ghost", music="music_l09"),
    T("Durian Orchard", "King of fruits", [("durian_tree", 2.4, 1.1, 3), ("crate", 2.0, 1.0, 2), ("wheelbarrow", 2.6, 1.0, 2), ("fence", 3.1, 1.0, 3), ("fruit_basket", 1.6, 1.0, 1)],
      trees="durian_tree,durian_tree,banana", hills="blob", hillColors="5CB048,4A9E40", hillProps="durian_tree,durian_tree,hut", scatter="grass,rock,flower,fern",
      fore="durian_tree", bladeA="4A9E3A", bladeB="A0E058", pads="", floaters="", enemies="monkey,scorpion,cobra,mosquito,durian,ghost", music="music_l10"),
    T("Railway Market", "Mind the train", [("train", 3.0, 1.0, 7), ("awning_stall", 2.2, 1.0, 3), ("fruit_basket", 1.5, 1.0, 1), ("crate", 1.9, 1.0, 2), ("fruit_stall", 2.4, 1.0, 3)],
      top="gravel", face="earth", faceTint="C8B8A8", blades=0, scatter="fruit_basket,crate,rock", trees="palm,banana", hills="city", buildings="shophouse,shophouse,hut",
      sky="4A98E0,A0D0F0,FFF0D8", pads="", floaters="", extras="", islands="", water="8AB8A8,2A4A4A,E8F8F0", fore="awning_stall", particles="petal", far="",
      enemies="soidog,rat,cobra,pigeon,flowerpot,ghost", music="music_l11"),
    T("Bangkok Rooftops", "Above the city", [("water_tank", 2.4, 1.0, 2), ("antenna", 2.8, 1.0, 1), ("clothesline", 2.2, 1.0, 3), ("crate", 1.8, 1.0, 2), ("flowerpot_big", 1.5, 1.0, 1)],
      **dict(DUSK, top="tile", face="concrete", blades=0, scatter="flowerpot_big,crate", trees="", hills="city", buildings="skyscraper,skyscraper,shophouse,skyscraper",
             far="skyscraper", mountains="", pads="", floaters="", extras="", islands="", water="C89AB0,3A2A5E,FFE0D0", fore="antenna", flutter="", particles="none", clouds=10,
             enemies="rat,crab,gecko,pigeon,flowerpot,ghost", music="music_l12")),
    T("Chinatown Night", "Yaowarat lights", [("neon_sign", 2.6, 1.0, 2), ("noodle_cart", 2.2, 1.0, 3), ("lantern_row", 3.0, 1.0, 4), ("shophouse", 3.3, 0.8, 5), ("stool", 1.5, 1.0, 1)],
      **dict(NIGHT, top="stone", topTint="8A8A9A", face="brick", faceTint="9A8A8A", blades=0, scatter="stool,crate", trees="", hills="city", buildings="shophouse,shophouse,shophouse",
             far="skyscraper", mountains="", pads="", floaters="", extras="", islands="", fore="neon_sign", flutter="", particles="spark", lanterns=0,
             enemies="rat,crab,gecko,bat,flowerpot,ghost", music="music_l13")),
    T("Songkran Splash", "Water festival", [("water_barrel", 1.8, 1.0, 1), ("pickup_truck", 2.8, 1.0, 5), ("flags", 2.8, 1.0, 5), ("awning_stall", 2.4, 1.0, 3), ("stool", 1.5, 1.0, 1)],
      top="stone", topTint="D8D0C0", face="concrete", faceTint="E0D8C8", blades=0, scatter="water_barrel,stool,flower", trees="palm,frangipani", hills="city",
      buildings="shophouse,wat,shophouse", sky="20A0F0,70D0FF,E8FAFF", sun="FFFFFF", sunI=1.15, pads="", floaters="", extras="", islands="", fore="palm", particles="drop",
      enemies="soidog,crab,cobra,pigeon,bucket,ghost", music="music_l14"),
    T("Ayutthaya Dusk", "Brick and gold", [("chedi", 2.6, 1.0, 3), ("ruin_wall", 2.4, 1.0, 3), ("brick_arch", 2.8, 1.0, 3), ("bodhi_tree", 3.0, 1.0, 5), ("ruin_column", 1.9, 1.0, 1)],
      **dict(DUSK, top="stone", topTint="D8A888", face="brick", blades=1, bladeA="7A8A3A", bladeB="D8C860", bladeH=0.7, scatter="rock,ruin_column,grass", trees="bodhi_tree,frangipani",
             hills="city", buildings="chedi,ruin_wall,prang,chedi", far="prang", pads="lotuspad", floaters="", extras="", fore="bodhi_tree", particles="leaf",
             enemies="monkey,scorpion,cobra,bat,coconut,ghost", music="music_l15")),
    T("Lantern Festival", "Yi Peng night", [("lanna_umbrella", 2.2, 1.0, 2), ("tung", 2.6, 1.0, 1), ("lantern_row", 3.0, 1.0, 4), ("sky_lantern", 1.9, 1.0, 1), ("stone_lantern", 1.7, 1.0, 1)],
      **dict(NIGHT, lanterns=70, scatter="grass,flower,stone_lantern", trees="frangipani,palm", hills="terrace", crowns="wat,chedi_gold", hillProps="hut,lanna_umbrella",
             fore="frangipani", bladeA="2A5A4A", bladeB="5A9A6A", particles="lantern", enemies="frog,crab,cobra,bat,coconut,wisp", music="music_l16")),
    T("Loy Krathong", "River of candles", [("krathong_stand", 2.0, 1.0, 2), ("lantern_row", 3.0, 1.0, 4), ("dock_post", 3.1, 1.0, 1), ("stone_lantern", 1.7, 1.0, 1), ("frangipani", 2.7, 1.2, 3)],
      **dict(NIGHT, top="wood", face="wood", blades=0, scatter="stone_lantern,flower", pads="krathong", floaters="boat", extras="", hills="city", buildings="wat,pier_house,chedi_gold",
             lanterns=20, fore="frangipani", particles="firefly", enemies="frog,crab,cobra,dragonfly,coconut,wisp", music="music_l17")),
    T("Cave of Light", "Hidden pavilion", [("stalagmite", 2.2, 1.0, 1), ("crystal", 1.8, 1.0, 1), ("pavilion", 2.8, 1.0, 4), ("stalagmite", 3.0, 1.4, 1), ("rock", 1.6, 2.0, 2)],
      sky="050608,14181E,3A4048", sun="FFF4D0", sunI=0.7, sunDir="70,10", ambSky="4A5466", ambGround="20222A", fog="1A1E26", fogStart=18, fogEnd=120, night=1, stars=0,
      top="stone", topTint="A8A8B0", face="rock", faceTint="B0A8A0", blades=0, scatter="stalagmite,rock,crystal", trees="stalagmite", hills="cliff", hillProps="crystal,stalagmite",
      far="", mountains="", clouds=0, pads="", floaters="", extras="", islands="", water="3A6A7A,05080C,BFE8FF", waterSky="2A3A4A,05080C", fore="stalagmite", flutter="firefly",
      particles="dust", exposure=0.3, enemies="scorpion,crab,gecko,bat,stalactite,wisp", music="music_l18"),
    T("Mangrove Maze", "Roots and mud", [("mangrove", 2.4, 1.0, 3), ("mangrove", 3.0, 1.2, 3), ("dock_post", 2.0, 1.0, 1), ("net_pile", 1.8, 1.0, 2), ("fern", 1.5, 1.2, 1)],
      top="mud", face="wood", faceTint="B8A888", blades=0, scatter="fern,rock,net_pile", trees="mangrove,mangrove,palm", hills="forest", hillProps="mangrove,mangrove",
      hillColors="5A7A4A,4A6A40", water="8AA878,2A3A2A,E0F0D8", waterSky="C8D8B8,5A8A6A", fog="C8D8C0", fogStart=20, fogEnd=170, pads="", floaters="kayak", extras="",
      far="", fore="mangrove", particles="leaf", enemies="mudskipper,crab,cobra,dragonfly,coconut,ghost", music="music_l19"),
    T("Monsoon Run", "Rain on rubber trees", [("rubber_tree", 2.4, 1.0, 2), ("rubber_tree", 3.0, 1.1, 2), ("water_barrel", 1.8, 1.0, 1), ("hut", 3.0, 0.9, 4), ("fern", 1.5, 1.2, 1)],
      sky="3A4658,6A7A8E,A8B4C0", sun="C8D4E8", sunI=0.6, sunDir="60,20", ambSky="5A6A82", ambGround="3A3E46", fog="7E8A9A", fogStart=14, fogEnd=130, cloudCol="5A6474",
      clouds=26, top="mud", topTint="9AA878", scatter="fern,grass,rock", trees="rubber_tree,rubber_tree,banana", hills="forest", hillProps="rubber_tree,rubber_tree",
      hillColors="4A7A4A,3E6A42", water="6A8A8E,1E2E3A,D8E8F0", pads="", floaters="", extras="", far="", fore="rubber_tree", flutter="", particles="rain", bladeA="3A7A3A",
      bladeB="7AB860", exposure=0.2, enemies="frog,crab,cobra,mosquito,coconut,ghost", music="music_l20"),
    T("Island Hopping", "Turquoise bays", [("beach_hut", 2.6, 1.0, 4), ("kayak", 2.0, 1.0, 3), ("palm", 2.4, 1.1, 2), ("starfish", 1.4, 1.0, 1), ("sunbed", 2.0, 1.0, 3)],
      top="sand", face="sandstone", blades=0, scatter="starfish,rock,shell", trees="palm,palm", hills="cliff", hillProps="palm,palm", far="karst", water="40E8E0,0A6AC8,FFFFFF",
      waterSky="E0FFFF,30A8F0", sky="109AF0,60C8FF,E8FBFF", pads="", floaters="boat,kayak,boat", extras="", islands="F2E6B8,F2E6B8", fore="palm,palm",
      enemies="hermit,crab_blue,squid,seagull,coconut,jellyfish", music="music_l21"),
    T("Coral Beach", "Sun and shells", [("sunbed", 2.0, 1.0, 3), ("sandcastle", 1.7, 1.0, 2), ("beach_hut", 2.8, 1.0, 4), ("palm", 2.4, 1.2, 2), ("starfish", 1.4, 1.0, 1)],
      top="sand", face="sandstone", blades=0, scatter="shell,starfish,rock,sandcastle", trees="palm,palm", hills="dune", hillColors="F2E0A8,EAD498", hillProps="palm,beach_hut",
      water="50F0E0,0A70D0,FFFFFF", waterSky="E8FFFF,38B0F8", sky="0C90F0,58C4FF,FFF8E0", pads="", floaters="kayak,boat", extras="", islands="F2E6B8,F2E6B8", far="",
      mountains="9FC8E8,B0D4F0", fore="palm", enemies="hermit,crab_blue,squid,seagull,coconut,jellyfish", music="music_l22"),
    T("Fishing Village", "Nets at dusk", [("pier_house", 2.8, 1.0, 4), ("fish_rack", 2.2, 1.0, 3), ("net_pile", 1.8, 1.0, 2), ("dock_post", 3.1, 1.0, 1), ("crate", 2.0, 1.0, 2)],
      **dict(DUSK, top="wood", face="wood", blades=0, scatter="net_pile,crate,shell", trees="palm", hills="city", buildings="pier_house,pier_house,hut", pads="", floaters="fishing_boat,boat,fishing_boat",
             extras="", islands="", far="karst", fore="fish_rack", particles="none", enemies="rat,crab_blue,squid,seagull,bucket,ghost", music="music_l23")),
    T("Night Market", "Grills and lights", [("market_stall", 2.4, 1.0, 3), ("grill_cart", 2.0, 1.0, 2), ("lantern_row", 3.0, 1.0, 4), ("tuktuk", 2.8, 1.0, 3), ("stool", 1.5, 1.0, 1)],
      **dict(NIGHT, top="stone", topTint="8E8A92", face="concrete", faceTint="8A8690", blades=0, scatter="stool,crate,fruit_basket", trees="palm", hills="city",
             buildings="market_stall,shophouse,market_stall", pads="", floaters="fishing_boat", extras="", islands="", far="", fore="market_stall", flutter="", particles="spark",
             enemies="soidog,rat,gecko,bat,flowerpot,wisp", music="music_l24")),
    T("Seafood Road", "Almost there!", [("lamp_post", 2.0, 1.0, 1), ("seafood_sign", 2.4, 1.0, 2), ("market_stall", 2.6, 1.0, 3), ("fish_rack", 2.2, 1.0, 3), ("lantern_row", 3.0, 1.0, 4)],
      **dict(NIGHT, top="wood", face="wood", blades=0, scatter="crate,net_pile,shell", trees="palm", hills="city", buildings="pier_house,market_stall,pier_house", pads="",
             floaters="fishing_boat,boat", extras="", islands="", far="karst", fore="lamp_post", lanterns=30, particles="lantern",
             enemies="soidog,crab_blue,squid,bat,bucket,wisp", music="music_l25")),
]
ENDING = T("The Seafood Restaurant", "Friends are waiting", [],
           **dict(NIGHT, top="wood", face="wood", blades=0, scatter="", trees="palm", hills="city", buildings="pier_house,market_stall,pier_house", pads="krathong",
                  floaters="fishing_boat,boat,fishing_boat", extras="", islands="", far="karst", fore="", lanterns=60, particles="lantern", flutter="firefly",
                  music="music_ending", exposure=0.32))

# ------------------------------------------------------------------------------------------------ builder
class Lv:
    def __init__(s, n, rng):
        s.n = n; s.r = rng; s.d = (n - 1) / 24.0
        s.g = [[" "] * 420 for _ in range(H)]
        s.objs = []; s.x = 0; s.h = 3; s.flats = []; s.lotus = 0

    # -- primitives
    def put(s, x, y, ch):
        if 0 <= y < H and s.g[y][x] == " ": s.g[y][x] = ch; return True
        return False
    def ground(s, w, h=None, record=True):
        if h is not None: s.h = h
        for x in range(s.x, s.x + w):
            for y in range(s.h): s.g[y][x] = "#"
            if record: s.flats.append((x, s.h))
        x0 = s.x; s.x += w; return x0
    def column(s, x, w, h):
        for xx in range(x, x + w):
            for y in range(h): s.g[y][xx] = "#"
    def coins(s, x0, x1, y, step=1):
        for x in range(x0, x1 + 1, step): s.put(x, y, "o")
    def arc(s, x0, x1, y):
        n = x1 - x0
        for i in range(n + 1): s.put(x0 + i, y + (1 if 0 < i < n else 0), "o")
    def raft(s, x, y, dx, t): s.objs.append("raft %g %g %g 0 %g" % (x, y, dx, t))
    def walker(s): return "m" if s.r.random() < 0.6 else "r"

    # -- chunks (each leaves s.x at the next free column on ground height s.h)
    def start(s):
        x = s.ground(12, 3); s.put(x + 3, 3, "P"); s.arc(x + 7, x + 10, 5)
    def flat(s, w=None):
        w = w or s.r.randint(6, 10); x = s.ground(w)
        if s.r.random() < 0.6: s.coins(x + 1, x + w - 2, s.h + 1 if s.r.random() < 0.5 else s.h + 2)
        if s.n >= 2 and s.r.random() < 0.25 + s.d * 0.55 and w >= 7: s.put(x + w - 3, s.h, s.walker())
    def rest(s): s.ground(s.r.randint(3, 5))
    def step(s):
        dh = s.r.choice([1, 1, 2, -1, -1, -2])
        nh = min(12, max(3, s.h + dh))
        s.ground(s.r.randint(4, 6), nh)
    def pit(s, lotus=False):
        gmax = 3 + (1 if s.d > 0.3 else 0) + (1 if s.d > 0.75 else 0)
        g = s.r.randint(2, gmax); x = s.x
        s.arc(x - 1, x + g, s.h + 2)
        if lotus: s.g[s.h + 3][x + g // 2] = "L"; s.lotus += 1
        elif s.d > 0.45 and g >= 3 and s.r.random() < s.d * 0.6: s.put(x + g // 2, s.h + 5, "q")
        s.x += g; s.ground(s.r.randint(4, 6))
    def islands(s):
        k = s.r.randint(2, 3 + (1 if s.d > 0.5 else 0)); h0 = s.h
        for i in range(k):
            g = s.r.randint(2, 3 + (1 if s.d > 0.6 else 0)); s.x += g
            hh = min(12, max(3, s.h + s.r.choice([-1, 0, 0, 1])))
            w = s.r.randint(2, 3); x = s.ground(w, hh, record=(w >= 3))
            s.put(x, hh + 2, "o"); s.put(x + w - 1, hh + 2, "o")
            if s.d > 0.5 and s.r.random() < 0.3: s.put(x + w - 1, hh + 5, "q")
        s.x += s.r.randint(2, 3); s.ground(s.r.randint(4, 6), min(12, max(3, s.h + s.r.choice([-1, 0, 1]))))
    def bridge(s):
        k = s.r.randint(2, 3); x = s.x
        for i in range(k):
            x += s.r.randint(2, 3)
            for xx in range(x, x + 3): s.g[s.h - 1][xx] = "="
            s.coins(x, x + 2, s.h + 1)
            x += 3
        x += s.r.randint(2, 3); s.x = x; s.ground(s.r.randint(4, 6))
    def rafts(s):
        w = s.r.randint(8, 11 + int(s.d * 3)); x = s.x
        a = x + 0.4; b = x + w - 3.4
        s.raft(a, s.h, b - a, max(1.9, 3.4 - s.d * 1.2) + (b - a) * 0.06)
        s.coins(x + 1, x + w - 2, s.h + 2, 2)
        if s.n >= 2 and s.r.random() < 0.3 + s.d * 0.5: s.put(x + w // 2, s.h + 4, "q")
        s.x += w; s.ground(s.r.randint(4, 6))
    def crumbles(s):
        k = s.r.randint(3, 4 + (1 if s.d > 0.5 else 0)); x = s.x + 2; row = s.h - 1
        for i in range(k):
            row = min(11, row + s.r.choice([0, 0, 1]))
            s.g[row][x] = "C"; s.g[row][x + 1] = "C"; s.coins(x, x + 1, row + 3)
            x += 2 + s.r.randint(2, 3 if s.d > 0.4 else 2)
        s.x = x; s.ground(s.r.randint(4, 6), row + 1)
    def spikes(s):
        k = s.r.randint(2, 3); x = s.ground(3)
        for i in range(k):
            w = s.r.randint(2, 3 + (1 if s.d > 0.6 else 0)); x = s.ground(w, record=False)
            for xx in range(x, x + w): s.g[s.h][xx] = "^"
            s.coins(x, x + w - 1, s.h + 3)
            x = s.ground(3)
            if s.d > 0.55 and s.r.random() < 0.35: s.put(x + 1, s.h, "r")
    def brazier(s):
        x = s.ground(7 + (4 if s.d > 0.6 else 0)); s.g[s.h][x + 3] = "B"
        if s.d > 0.6: s.g[s.h][x + 8] = "B"
    def tunnel(s, lotus=False):
        w = s.r.randint(3, 5); x = s.ground(w + 4)
        for xx in range(x + 2, x + 2 + w): s.g[s.h + 1][xx] = "#"
        if lotus: s.g[s.h][x + 2 + w // 2] = "L"; s.lotus += 1
        else: s.coins(x + 2, x + 1 + w, s.h)
        s.coins(x + 2, x + 1 + w, s.h + 3)
    def climb(s, lotus=False):
        if s.h > 6: return s.drop()
        x = s.ground(6); h = s.h
        for xx in (x + 1, x + 2): s.g[h + 2][xx] = "="
        s.coins(x + 1, x + 2, h + 4)
        tall = s.r.random() < 0.6
        if tall:
            for xx in (x + 4, x + 5): s.g[h + 5][xx] = "="
            s.coins(x + 4, x + 5, h + 7)
            if lotus:
                for xx in (x, x + 1): s.g[h + 8][xx] = "="
                s.g[h + 10][x] = "L"; s.lotus += 1
        s.ground(s.r.randint(6, 8), h + (8 if tall else 5))
        if s.d > 0.4 and s.r.random() < 0.5: s.put(s.x - 2, s.h, "c")
    def drop(s):
        x = s.ground(4); dh = min(s.h - 3, s.r.randint(3, 5))
        if dh <= 0: return
        x = s.ground(8, s.h - dh)
        s.coins(x + 1, x + 6, s.h + 1)
        if s.n >= 4:
            s.put(x + 2, s.h + 6, "d")
            if s.d > 0.5: s.put(x + 5, s.h + 6, "d")
    def drum(s, lotus=False):
        x = s.ground(6); s.g[s.h][x + 2] = "D"
        for xx in range(x + 4, x + 7): s.g[s.h + 6][xx] = "="
        if lotus: s.g[s.h + 8][x + 5] = "L"; s.lotus += 1
        else: s.put(x + 5, s.h + 8, "M" if s.r.random() < 0.4 else "o")
        s.coins(x + 4, x + 6, s.h + 7, 2)
        s.ground(4)
    def cobra(s):
        s.x += s.r.randint(2, 3); x = s.ground(7); s.put(x + 5, s.h, "c")
        s.coins(x + 1, x + 3, s.h + 1)
    def gauntlet(s, power=None):
        x = s.ground(4)
        if power: s.put(x + 1, s.h + 2, power)
        x = s.ground(14)
        for i, off in enumerate((3, 7, 11)):
            if i < 2 or s.d > 0.4: s.put(x + off, s.h, s.walker())
        if s.d > 0.3: s.put(x + 5, s.h + 4, "q")
        if s.d > 0.65: s.put(x + 10, s.h + 4, "q")
        s.coins(x + 2, x + 12, s.h + 2, 2)
    def ghost(s):
        x = s.ground(13); s.put(x + 9, s.h + 3, "g"); s.coins(x + 1, x + 11, s.h + 1, 2)
    def checkpoint(s):
        x = s.ground(6); s.put(x + 2, s.h, "K"); s.put(x + 4, s.h + 1, "M")
    def power(s, ch):
        x = s.ground(5); s.put(x + 2, s.h + 2, ch)
    def goal(s):
        x = s.ground(18); s.put(x + 11, s.h, "X"); s.coins(x + 2, x + 8, s.h + 2); s.put(x + 1, s.h + 1, "M")
        s.goal_x = x + 11

    # -- assemble
    def build(s):
        r = s.r; d = s.d; length = 150 + s.n * 5
        s.start()
        pool = [("flat", 3), ("step", 3), ("pit", 4), ("islands", 2 + d * 2), ("bridge", 2), ("rafts", 2 + d), ("crumbles", 1 + d * 2.5), ("spikes", 1 + d * 2),
                ("tunnel", 1.5), ("climb", 1.5), ("drop", 1), ("drum", 1), ("brazier", 0.6 + d * 1.6)]
        if s.n >= 4: pool.append(("cobra", 0.8 + d * 1.5))
        if s.n >= 3: pool.append(("gauntlet", 0.6 + d * 1.2))
        if s.n >= 8: pool.append(("ghost", 0.3 + d * 1.0))
        marks = {"cp1": 0.33, "cp2": 0.66, "l1": 0.2, "l2": 0.5, "l3": 0.8, "somtam": 0.14, "chili": 0.42, "sangsom": 0.72}
        done = set(); last = None
        while s.x < length:
            f = s.x / length
            for k, at in marks.items():
                if k in done or f < at: continue
                done.add(k)
                if k.startswith("cp"): s.checkpoint()
                elif k == "l1": s.tunnel(True) if r.random() < 0.5 else s.pit(True)
                elif k == "l2": s.drum(True)
                elif k == "l3": (s.climb(True) if s.h <= 6 else s.pit(True))
                elif k == "somtam": s.power("S")
                elif k == "chili": s.power("H")
                elif k == "sangsom": s.gauntlet("G")
            names = [p[0] for p in pool if p[0] != last]; weights = [p[1] for p in pool if p[0] != last]
            c = r.choices(names, weights)[0]; last = c
            getattr(s, c)()
            if c not in ("flat", "step") and r.random() < 0.5: s.rest()
        while s.lotus < 3: s.pit(True)
        s.rest(); s.goal()
        s.W = s.x

    def decorate(s, theme):
        r = s.r; decor = theme["decor"]
        if not decor: return
        x_next = 1
        for (x, h) in s.flats:
            if x < x_next or x >= s.W - 1: continue
            if any(s.g[yy][x + k] == "#" for yy in (h, h + 1, h + 2) for k in range(3) if x + k < s.W): continue      # under a tunnel roof / beside a wall
            model, z, sc, wd = r.choice(decor)
            # needs `wd` consecutive flat columns at the same height
            if any((x + k, h) not in s._flatset for k in range(wd)): continue
            if abs(x - getattr(s, "goal_x", -99)) < 3: continue
            xx = x + (wd - 1) / 2.0
            s.objs.append("decor %s %g %g %g %g %g" % (model, xx, h, z + r.uniform(-0.15, 0.25), 90 + r.uniform(-25, 25) if wd <= 2 else 90, sc * r.uniform(0.92, 1.1)))
            x_next = x + wd + r.randint(1, 4)

    def write(s, name, theme):
        s._flatset = set(s.flats)
        s.decorate(theme)
        with open(os.path.join(OUT, name + ".txt"), "w") as f:
            for y in range(H - 1, -1, -1): f.write("".join(s.g[y][:s.W]).rstrip() + "\n")
            f.write("---\n" + "\n".join(s.objs) + "\n")

def ending():
    s = Lv(26, random.Random(99)); s.h = 3
    x = s.ground(46, 3); s.put(x + 3, 3, "P"); s.W = s.x
    D = lambda m, xx, z, yaw=90, sc=1.0: s.objs.append("decor %s %g 3 %g %g %g" % (m, xx, z, yaw, sc))
    D("lamp_post", 2, 2.4); D("seafood_sign", 6, 2.6); D("lantern_row", 9.5, 3.1); D("lamp_post", 13, 2.4); D("market_stall", 16.5, 3.0)
    D("restaurant", 27, 2.9, 90, 1.15); D("lantern_row", 21, 1.4); D("lantern_row", 33, 1.4); D("lamp_post", 38, 2.4); D("palm", 41, 2.6, 60, 1.3); D("palm", 44, 3.0, 20, 1.5)
    D("seafood_table", 24.2, 0.9); D("seafood_table", 29.8, 0.9)
    for i, (m, xx, z, face) in enumerate((("friend_a", 22.6, 0.75, 1), ("friend_b", 25.6, 1.25, -1), ("friend_c", 28.2, 1.3, 1), ("friend_d", 31.4, 0.8, -1), ("friend_e", 26.9, 0.35, -1))):
        s.objs.append("friend %s %g 3 %g %d" % (m, xx, z, face))
    s.flats = []; s.write("ending", ENDING)

def themes_file():
    with open(os.path.join(OUT, "themes.txt"), "w") as f:
        for i, t in enumerate(THEMES + [ENDING]):
            f.write("[%d]\n" % (i + 1))
            for k, v in t.items():
                if k == "decor": continue
                f.write("%s=%s\n" % (k, v))
            f.write("\n")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for n in range(2, 26):
        lv = Lv(n, random.Random(1000 + n * 37)); lv.build(); lv.write("level%d" % n, THEMES[n - 1])
        cells = "".join("".join(row[:lv.W]) for row in lv.g)
        print("level %2d  %-18s width %3d  coins %3d  lotus %d  enemies %2d" % (n, THEMES[n - 1]["name"], lv.W, cells.count("o"), cells.count("L"), sum(cells.count(c) for c in "mrcqdg")))
    ending(); themes_file()
    print("wrote themes.txt (%d themes) and ending.txt" % (len(THEMES) + 1))
