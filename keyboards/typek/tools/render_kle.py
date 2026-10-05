#!/usr/bin/env python3
"""Build a keyboard-layout-editor.com (KLE) layout of the TypeK and render it to SVG.

Geometry comes from the official VIA definition (tools/typek-via-layout.json, the
"layouts" block of the-via/keyboards v3/typek/typek.json @ ed5794cb), which has
the real rotated alpha clusters (+/-10 degrees).  Layout options are resolved to
this board's build (see VIA_EEPROM_LAYOUT_OPTIONS_DEFAULT in config.h): 2u
backspace, split left space, unsplit 3u right space, 2.25u right shift.

Legends come live from keymaps/via/keymap.c: the base layer (layer 0) as the
main legend, the Fn layer (layer 3, held on the left thumb) in red bottom-right.

Outputs:
  typek.kle.json        (keyboard dir) paste into keyboard-layout-editor.com > Raw data
  .build/typek.svg      (repo root) rendered layout; images are gitignored repo-wide
                        and `qmk lint` rejects ignored files in the keyboard dir

Run from the keyboard dir:  make kle
"""
import json
import math
from html import escape

from render_keymap import KB, KEYMAP, LABELS, parse_layers, short

# Chosen value per VIA layout option, in typek.json label order:
# split backspace, split left space, split right space, split right shift.
LAYOUT_OPTIONS = (0, 1, 0, 0)
FN_LAYER = 3

SHIFTED = {
    "KC_GRV": "~", "KC_1": "!", "KC_2": "@", "KC_3": "#", "KC_4": "$", "KC_5": "%",
    "KC_6": "^", "KC_7": "&", "KC_8": "*", "KC_9": "(", "KC_0": ")", "KC_MINS": "_",
    "KC_EQL": "+", "KC_LBRC": "{", "KC_RBRC": "}", "KC_BSLS": "|", "KC_SCLN": ":",
    "KC_QUOT": '"', "KC_COMM": "<", "KC_DOT": ">", "KC_SLSH": "?",
}
BASE_NAMES = {
    "QK_GESC": ("Esc", "` ~"), "CTL_ESC": ("Ctrl", "tap Esc"), "MO(3)": ("Fn", ""),
    "KC_TRNS": ("", ""), "KC_PAUS": ("Pause", ""), "KC_SCRL": ("ScrLk", ""),
    "KC_BSPC": ("Backspace", ""), "KC_ENT": ("Enter", ""), "KC_TAB": ("Tab", ""),
    "KC_SPC": ("", ""), "KC_LSFT": ("Shift", ""), "KC_RSFT": ("Shift", ""),
    "KC_LALT": ("Alt", ""), "KC_RALT": ("Alt", ""), "KC_LGUI": ("Super", ""),
    "KC_RGUI": ("Super", ""), "KC_LCTL": ("Ctrl", ""), "KC_RCTL": ("Ctrl", ""),
}
FN_COLOR = "#c0392b"


# --- KLE (de)serialization, a port of @ijprest/kle-serial ---------------------

def kle_deserialize(rows):
    keys = []
    cur = dict(x=0.0, y=0.0, w=1.0, h=1.0, r=0.0, rx=0.0, ry=0.0, c="#cccccc", t="#000000", a=4)
    cluster = dict(x=0.0, y=0.0)
    for row in rows:
        for item in row:
            if isinstance(item, str):
                keys.append(dict(cur, label=item))
                cur["x"] += cur["w"]
                cur["w"] = cur["h"] = 1.0
                continue
            if "r" in item:
                cur["r"] = item["r"]
            if "rx" in item:
                cur["rx"] = cluster["x"] = item["rx"]
                cur["x"], cur["y"] = cluster["x"], cluster["y"]
            if "ry" in item:
                cur["ry"] = cluster["y"] = item["ry"]
                cur["x"], cur["y"] = cluster["x"], cluster["y"]
            cur["x"] += item.get("x", 0)
            cur["y"] += item.get("y", 0)
            for p in ("w", "h", "c", "t", "a"):
                if p in item:
                    cur[p] = item[p]
        cur["y"] += 1
        cur["x"] = cur["rx"]
    return keys


def kle_serialize(keys):
    """Emit KLE rows; every rotation cluster change restates r/rx/ry so it resets the cursor."""
    def r4(v):
        return round(v, 4) + 0.0

    keys = sorted(keys, key=lambda k: ((k["r"] + 360) % 360, k["rx"], k["ry"], r4(k["y"]), k["x"]))
    rows, row = [], []
    cur = dict(x=0.0, y=0.0, r=0.0, rx=0.0, ry=0.0, c="#cccccc", t="#000000", a=4)
    for k in keys:
        cluster_changed = (k["r"], k["rx"], k["ry"]) != (cur["r"], cur["rx"], cur["ry"])
        if row and (cluster_changed or r4(k["y"]) != r4(cur["y"])):
            rows.append(row)
            row = []
            cur["y"] += 1
            cur["x"] = cur["rx"]
        props = {}
        if cluster_changed:
            props.update(r=k["r"], rx=k["rx"], ry=k["ry"])
            cur.update(r=k["r"], rx=k["rx"], ry=k["ry"], x=k["rx"], y=k["ry"])
        if r4(k["y"] - cur["y"]):
            props["y"] = r4(k["y"] - cur["y"])
        if r4(k["x"] - cur["x"]):
            props["x"] = r4(k["x"] - cur["x"])
        for p in ("c", "t", "a"):
            if k[p] != cur[p]:
                props[p] = cur[p] = k[p]
        if k["w"] != 1:
            props["w"] = k["w"]
        if k["h"] != 1:
            props["h"] = k["h"]
        if props:
            row.append(props)
        row.append(k["label"])
        cur["x"], cur["y"] = k["x"] + k["w"], k["y"]
    if row:
        rows.append(row)
    return rows


# --- Build the layout -----------------------------------------------------------

def physical_keys():
    """VIA geometry filtered to the chosen layout options; each key gets its (row, col)."""
    via = json.loads((KB / "tools" / "typek-via-layout.json").read_text())
    out, groups = [], {}
    for k in kle_deserialize(via["keymap"]):
        parts = k["label"].split("\n")
        k["matrix"] = tuple(map(int, parts[0].split(",")))
        if len(parts) > 3 and parts[3]:
            opt, choice = map(int, parts[3].split(","))
            groups.setdefault((opt, choice), []).append(k)
            if LAYOUT_OPTIONS[opt] != choice:
                continue
        out.append(k)
    # Like VIA, draw a non-default choice where choice 0 sits: the definition parks
    # alternates off to the side, so shift each chosen group onto choice 0's top-left.
    for opt, choice in enumerate(LAYOUT_OPTIONS):
        if choice == 0:
            continue
        base, alt = groups[(opt, 0)], groups[(opt, choice)]
        dx = min(k["x"] for k in base) - min(k["x"] for k in alt)
        dy = min(k["y"] for k in base) - min(k["y"] for k in alt)
        for k in alt:
            k["x"] += dx
            k["y"] += dy
    return out


def legends(tok, fn_tok):
    """KLE label string for a=4 order: 0 top-left, 1 bottom-left, 2 top-right, 3 bottom-right."""
    if tok in SHIFTED:
        top, bottom = SHIFTED[tok], short(tok)
    elif tok in BASE_NAMES:
        top, bottom = BASE_NAMES[tok]
    else:
        top, bottom = short(tok), ""
    fn = "" if fn_tok == "KC_TRNS" else LABELS.get(fn_tok, short(fn_tok))
    return "\n".join([top, bottom, "", fn]).rstrip("\n")


def build():
    kbjson = json.loads((KB / "keyboard.json").read_text())
    index = {tuple(k["matrix"]): i for i, k in enumerate(kbjson["layouts"]["LAYOUT"]["layout"])}
    layers = {n: toks for n, _, toks in parse_layers(KEYMAP.read_text())}
    keys = []
    for k in physical_keys():
        i = index[k["matrix"]]
        label = legends(layers[0][i], layers[FN_LAYER][i])
        k = dict(k, label=label, t="#000000\n\n\n" + FN_COLOR)
        del k["matrix"]
        keys.append(k)
    return keys


# --- SVG render -------------------------------------------------------------------

U = 54          # px per key unit (KLE's own scale)
PAD = 18


def rot(px, py, k):
    a = math.radians(k["r"])
    dx, dy = px - k["rx"], py - k["ry"]
    return (k["rx"] + dx * math.cos(a) - dy * math.sin(a),
            k["ry"] + dx * math.sin(a) + dy * math.cos(a))


def render_svg(keys, title):
    corners = [rot(k["x"] + cx * k["w"], k["y"] + cy * k["h"], k) for k in keys
               for cx in (0, 1) for cy in (0, 1)]
    minx, miny = min(c[0] for c in corners), min(c[1] for c in corners)
    maxx, maxy = max(c[0] for c in corners), max(c[1] for c in corners)
    W = (maxx - minx) * U + 2 * PAD
    H = (maxy - miny) * U + 2 * PAD + 34
    ox, oy = PAD - minx * U, PAD + 34 - miny * U

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="100%" height="100%" fill="#eeeeee"/>',
           f'<text x="{PAD}" y="26" font-size="16" font-weight="bold" fill="#333">{escape(title)}</text>',
           f'<text x="{W - PAD:.0f}" y="26" font-size="12" fill="{FN_COLOR}" text-anchor="end">'
           f'red = Fn layer (hold Fn)</text>']
    for k in keys:
        x, y = ox + k["x"] * U, oy + k["y"] * U
        w, h = k["w"] * U, k["h"] * U
        cx, cy = ox + k["rx"] * U, oy + k["ry"] * U
        out.append(f'<g transform="rotate({k["r"]} {cx:.2f} {cy:.2f})">')
        out.append(f'<rect x="{x + 1:.2f}" y="{y + 1:.2f}" width="{w - 2:.2f}" height="{h - 2:.2f}" '
                   f'rx="5" fill="{shade(k["c"], 0.8)}" stroke="#00000055"/>')
        out.append(f'<rect x="{x + 6:.2f}" y="{y + 4:.2f}" width="{w - 12:.2f}" height="{h - 12:.2f}" '
                   f'rx="4" fill="{shade(k["c"], 1.08)}" stroke="#00000018"/>')
        labels = k["label"].split("\n") + [""] * 4
        colors = k["t"].split("\n") + [""] * 4
        tl, bl, _, br = labels[:4]
        if colors[0] in ("", "#000000") and luminance(k["c"]) < 0.5:
            colors[0] = "#ffffff"   # dark caps (Enter, top-left corner) get light legends
        fs = 12 if max(len(tl), len(bl)) <= 6 else 10
        if tl:
            out.append(text(x + 10, y + 19, tl, fs, colors[0] or "#000"))
        if bl:
            out.append(text(x + 10, y + 36, bl, fs if bl and len(bl) > 1 else 12, colors[0] or "#000"))
        if br:
            out.append(text(x + w - 10, y + h - 13, br, 9, colors[3] or FN_COLOR, anchor="end"))
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def text(x, y, s, size, fill, anchor="start"):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}">{escape(s)}</text>')


def luminance(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def shade(hexcolor, f):
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(min(255, int(v * f)) for v in (r, g, b))


def main():
    keys = build()
    rows = kle_serialize(keys)
    roundtrip = kle_deserialize(rows)
    def sig(ks):
        return sorted((k["label"], k["t"], k["c"], k["w"], k["r"], k["rx"], k["ry"],
                       round(k["x"], 4), round(k["y"], 4)) for k in ks)
    assert sig(roundtrip) == sig(keys), "KLE serialize/deserialize round-trip mismatch"
    meta = {"name": "gok TypeK", "author": "generated by keyboards/typek/tools/render_kle.py"}
    kle = "[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in [meta] + rows) + "\n]\n"
    (KB / "typek.kle.json").write_text(kle)
    svg = KB.parent.parent / ".build" / "typek.svg"
    svg.parent.mkdir(exist_ok=True)
    svg.write_text(render_svg(keys, f"gok TypeK  ({len(keys)} keys)  —  VIA keymap, base + Fn layer"))
    print(f"wrote {KB / 'typek.kle.json'} and {svg} ({len(keys)} keys)")


if __name__ == "__main__":
    main()
