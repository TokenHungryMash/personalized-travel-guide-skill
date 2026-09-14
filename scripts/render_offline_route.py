# -*- coding: utf-8 -*-
"""
路线地图生成器 v2（修正版；原 generate_route_map.py 保留不动）

v2 修正点:
  1. 同坐标站点合并为一个编号圆点, 编号显示为 "1/5" 形式; 真实坐标不变。
  2. 长标签限宽自动换行(CJK 逐字换行, 不省略), 碰撞检测使用实际多行文字框。
  3. 绘制顺序: 底图 → 路线 → 引线 → 编号圆点 → 标签(文字最上层);
     标签候选位置会避开所有编号圆点与已放置标签。

用法:
  python generate_route_map_v2.py input.json [--tiles DIR] [--out PREFIX]
        [--zoom 17] [--label-px 22] [--label-max-w 230] [--preview-width 390]
离线: 仅读取本地瓦片缓存, 缓存缺失立即报错退出, 不联网。
"""
import argparse
import json
import math
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

BASE = pathlib.Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("input_json", nargs="?", default=str(BASE / "route_input.json"))
ap.add_argument("--tiles", required=True)
ap.add_argument("--font", required=True)
ap.add_argument("--attribution", required=True)
ap.add_argument("--out", default=str(BASE / "route_map_v2"))
ap.add_argument("--zoom", type=int, default=17)
ap.add_argument("--label-px", type=int, default=22)
ap.add_argument("--label-max-w", type=int, default=230)
ap.add_argument("--preview-width", type=int, default=390)
args = ap.parse_args()

TILE_DIR = pathlib.Path(args.tiles)
OUT_PREFIX = pathlib.Path(args.out)
TILE = 256
ZOOM = args.zoom
N = 2 ** ZOOM

cfg = json.loads(pathlib.Path(args.input_json).read_text(encoding="utf-8"))
W = int(cfg.get("width", 600))
H = int(cfg.get("height", 720))
TITLE = cfg.get("title", "")
STOPS = cfg["stops"]
if not 200 <= W <= 2400 or not 200 <= H <= 2400 or not 0 <= ZOOM <= 20:
    sys.exit("ERROR: invalid canvas size or zoom")
if not 12 <= args.label_px <= 48 or not 40 <= args.label_max_w <= W - 32:
    sys.exit("ERROR: invalid label size/width")
for stop in STOPS:
    if not str(stop.get("name", "")).strip() or not all(isinstance(stop.get(k), (int, float)) and math.isfinite(stop[k]) for k in ("latitude", "longitude")):
        sys.exit("ERROR: invalid stop name or coordinates")
    if abs(stop["latitude"]) > 85 or abs(stop["longitude"]) > 180:
        sys.exit("ERROR: coordinates outside supported range")
if len(STOPS) < 2:
    sys.exit("ERROR: 至少需要 2 个地点")


def lon_to_px(lon):
    return (lon + 180.0) / 360.0 * N * TILE


def lat_to_px(lat):
    s = math.sin(math.radians(lat))
    return (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * N * TILE


CLON = (min(s["longitude"] for s in STOPS) + max(s["longitude"] for s in STOPS)) / 2
CLAT = (min(s["latitude"] for s in STOPS) + max(s["latitude"] for s in STOPS)) / 2
X0 = lon_to_px(CLON) - W / 2
Y0 = lat_to_px(CLAT) - H / 2
TX0, TY0 = int(X0 // TILE), int(Y0 // TILE)
TX1, TY1 = int((X0 + W) // TILE), int((Y0 + H) // TILE)

# ---------------- 校验并加载本地缓存(绝不联网) ----------------
map_img = Image.new("RGB", ((TX1 - TX0 + 1) * TILE, (TY1 - TY0 + 1) * TILE))
missing = []
for tx in range(TX0, TX1 + 1):
    for ty in range(TY0, TY1 + 1):
        fp = TILE_DIR / f"z{ZOOM}_x{tx}_y{ty}.png"
        if not fp.exists():
            missing.append(fp.name)
            continue
        map_img.paste(Image.open(fp).convert("RGB"), ((tx - TX0) * TILE, (ty - TY0) * TILE))
if missing:
    sys.exit("ERROR: 本地缓存缺少 %d 块瓦片, 离线模式不补齐: %s..." % (len(missing), missing[:3]))

cx, cy = int(X0 - TX0 * TILE), int(Y0 - TY0 * TILE)
map_img = map_img.crop((cx, cy, cx + W, cy + H))
map_img = Image.blend(map_img, Image.new("RGB", map_img.size, (255, 255, 255)), 0.40)
map_img = ImageEnhance.Color(map_img).enhance(0.90)

img = map_img.convert("RGBA")
ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
dr = ImageDraw.Draw(ov)

PURPLE = (124, 58, 237, 255)
INK = (30, 27, 75, 255)
GRAY_LINE = (107, 114, 128, 220)
f_label = ImageFont.truetype(args.font, args.label_px)
f_num = ImageFont.truetype(args.font, 14)
f_attr = ImageFont.truetype(args.font, 12)

MEAS = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
LH = args.label_px + 8          # 行高
BOX_PAD_X, BOX_PAD_Y = 9, 6
ATTR_H = 24
R_NUM = 11                      # 圆点基础半径
GAP = 10
MARGIN = 6
EPS = 2.0                       # 同点合并阈值(px)

pts = [(lon_to_px(s["longitude"]) - lon_to_px(CLON) + W / 2,
        lat_to_px(s["latitude"]) - lat_to_px(CLAT) + H / 2) for s in STOPS]

# ---------------- 修正点1: 同坐标分组, 编号合并 "1/5" ----------------
if any(not (16 <= x <= W - 16 and 16 <= y <= H - 40) for x, y in pts):
    sys.exit("ERROR: route outside canvas; supply suitable lower-zoom cache")
groups = []  # {"anchor":(mx,my), "members":[stop_index...], "nums":"1/5", "rx":..}
for i, (mx, my) in enumerate(pts):
    for g in groups:
        if STOPS[i]["latitude"] == STOPS[g["members"][0]]["latitude"] and STOPS[i]["longitude"] == STOPS[g["members"][0]]["longitude"]:
            g["members"].append(i)
            break
    else:
        groups.append({"anchor": (mx, my), "members": [i]})
for g in groups:
    g["nums"] = "/".join(str(i + 1) for i in g["members"])
    tw = MEAS.textlength(g["nums"], font=f_num)
    g["rx"] = max(R_NUM, tw / 2 + 6)
    g["bbox"] = (g["anchor"][0] - g["rx"], g["anchor"][1] - R_NUM,
                 g["anchor"][0] + g["rx"], g["anchor"][1] + R_NUM)

# ---------------- 修正点2: 限宽换行, 实际文字框 ----------------
def wrap_cjk(text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        t = cur + ch
        if not cur or MEAS.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if ch in "，。！？；：、）】》」』":
                lines.append(cur[:-1])
                cur = cur[-1] + ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def label_box(name):
    lines = wrap_cjk(name, f_label, args.label_max_w)
    bw = max(int(MEAS.textlength(ln, font=f_label)) for ln in lines) + BOX_PAD_X * 2
    bh = len(lines) * LH + BOX_PAD_Y * 2
    return lines, bw, bh


def clamp(bx, by, bw, bh):
    bx = max(MARGIN, min(W - MARGIN - bw, bx))
    by = max(MARGIN, min(H - ATTR_H - MARGIN - bh, by))
    return bx, by


def intersects(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def candidates(mx, my, bw, bh, rx=R_NUM):
    """8 方向候选: 右/左/上/下 + 四个对角; rx 为圆点实际半宽"""
    raw = [(mx + rx + GAP, my - bh / 2),
           (mx - rx - GAP - bw, my - bh / 2),
           (mx - bw / 2, my - R_NUM - GAP - bh),
           (mx - bw / 2, my + R_NUM + GAP),
           (mx + rx + GAP, my - R_NUM - GAP - bh),
           (mx + rx + GAP, my + R_NUM + GAP),
           (mx - rx - GAP - bw, my - R_NUM - GAP - bh),
           (mx - rx - GAP - bw, my + R_NUM + GAP)]
    out, seen = [], set()
    for bx, by in raw:
        bx, by = clamp(bx, by, bw, bh)
        k = (round(bx), round(by))
        if k not in seen:
            seen.add(k)
            out.append((bx, by))
    return out


placed = []      # 已放置标签框
labels_meta = []
plans = []       # (stop_idx, group, lines, box)
for i, s in enumerate(STOPS):
    g = next(gr for gr in groups if i in gr["members"])
    mx, my = g["anchor"]
    lines, bw, bh = label_box(s["name"])
    chosen, note = None, ""
    for bx, by in candidates(mx, my, bw, bh, g["rx"]):
        box = (bx, by, bx + bw, by + bh)
        if any(intersects(box, gr["bbox"]) for gr in groups):     # 避让编号圆点
            continue
        if any(intersects(box, pb) for pb in placed):             # 避让已放标签
            continue
        chosen, note = (bx, by, box), ""
        break
    if chosen is None:
        best, best_n = None, 10 ** 9
        for bx, by in candidates(mx, my, bw, bh, g["rx"]):
            box = (bx, by, bx + bw, by + bh)
            n = sum(1 for gr in groups if intersects(box, gr["bbox"]))
            n += sum(1 for pb in placed if intersects(box, pb))
            if best is None or n < best_n:
                best, best_n = (bx, by, box), n
        chosen, note = best, "所有候选均有冲突, 取冲突最少者(%d处)" % best_n
    bx, by, box = chosen
    placed.append(box)
    plans.append((i, g, lines, box))
    labels_meta.append({"name": s["name"], "lines": len(lines),
                        "box": [round(v) for v in box],
                        "ok": not note, "note": note})

use_legend = any(not item["ok"] for item in labels_meta)
legend_plans = []
if use_legend:
    plans = []
    y = H + 12
    for i, stop in enumerate(STOPS):
        lines = wrap_cjk(str(i + 1) + ". " + stop["name"], f_label, W - 32)
        legend_plans.append((y, lines))
        y += len(lines) * LH + 12
    expanded = Image.new("RGBA", (W, y + 8), "white")
    expanded.paste(img, (0, 0))
    img = expanded
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
# ---------------- 修正点3: 绘制顺序 路线→引线→圆点→标签 ----------------
# 1) 路线(经过全部真实位置)
dr.line(pts, fill=(255, 255, 255, 255), width=8, joint="curve")
dr.line(pts, fill=PURPLE, width=5, joint="curve")
for p in (pts[0], pts[-1]):
    dr.ellipse((p[0] - 2.5, p[1] - 2.5, p[0] + 2.5, p[1] + 2.5), fill=PURPLE)

# 2) 引线(标签框未贴近圆点时, 从框边缘引向圆点)
for i, g, lines, box in plans:
    mx, my = g["anchor"]
    bx, by, bw_bh = box[0], box[1], (box[2] - box[0], box[3] - box[1])
    near = intersects(box, (mx - g["rx"] - GAP, my - R_NUM - GAP,
                            mx + g["rx"] + GAP, my + R_NUM + GAP))
    if not near:
        px = min(max(mx, box[0]), box[2])
        py = min(max(my, box[1]), box[3])
        dr.line((px, py, mx, my), fill=GRAY_LINE, width=1)

# 3) 编号圆点(合并显示)
for g in groups:
    mx, my = g["anchor"]
    rx, ry = g["rx"], R_NUM
    dr.ellipse((mx - rx, my - ry, mx + rx, my + ry), fill=PURPLE,
               outline=(255, 255, 255, 255), width=3)
    dr.text((mx, my - 1), g["nums"], font=f_num, fill=(255, 255, 255, 255), anchor="mm")

# 4) 标签(最上层)
for i, g, lines, box in plans:
    bx, by = box[0], box[1]
    bh = box[3] - box[1]
    dr.rounded_rectangle(box, radius=8, fill=(255, 255, 255, 243),
                         outline=(214, 205, 242, 255), width=1)
    ty0 = by + (bh - len(lines) * LH) / 2
    for k, ln in enumerate(lines):
        dr.text((bx + BOX_PAD_X, ty0 + k * LH), ln, font=f_label, fill=INK)

# ---------------- 署名条 ----------------
at = Image.new("RGBA", img.size, (0, 0, 0, 0))
da = ImageDraw.Draw(at)
da.rectangle((0, H - ATTR_H, W, H), fill=(255, 255, 255, 205))
da.text((8, H - ATTR_H + 5), args.attribution,
        font=f_attr, fill=(55, 65, 81, 255))
ov = Image.alpha_composite(ov, at)

dr = ImageDraw.Draw(ov)
for y, lines in legend_plans:
    for k, line in enumerate(lines):
        dr.text((16, y + k * LH), line, font=f_label, fill=INK)
final = Image.alpha_composite(img, ov).convert("RGB")
OUT_PREFIX.parent.mkdir(parents=True, exist_ok=True)
main_out = OUT_PREFIX.with_suffix(".png")
final.save(main_out, "PNG", optimize=True)
pw = args.preview_width
prev_out = pathlib.Path(str(OUT_PREFIX) + f"_preview{pw}.png")
final.resize((pw, round(final.height * pw / W)), Image.LANCZOS).save(prev_out, "PNG", optimize=True)

meta = {
    "script": "render_offline_route.py",
    "input_json": str(pathlib.Path(args.input_json).resolve()),
    "title": TITLE, "canvas": f"{W}x{H}", "zoom": ZOOM,
    "label_px": args.label_px, "label_max_w": args.label_max_w,
    "tiles_dir": str(TILE_DIR.resolve()),
    "network_used": False,
    "merged_markers": [{"nums": g["nums"], "members": [STOPS[i]["name"] for i in g["members"]]}
                       for g in groups if len(g["members"]) > 1],
    "main_png": str(main_out.resolve()),
    "main_kb": round(main_out.stat().st_size / 1024, 1),
    "preview_png": str(prev_out.resolve()),
    "preview_kb": round(prev_out.stat().st_size / 1024, 1),
    "labels": labels_meta,
    "layout": "numbered-legend" if use_legend else "inline-labels",
    "labels_needing_manual_fix": [],
}
pathlib.Path(str(OUT_PREFIX) + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False, indent=1))
