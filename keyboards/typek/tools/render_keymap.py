#!/usr/bin/env python3
"""Render ASCII diagrams of every layer in the TypeK VIA keymap.

Parses keymaps/via/keymap.c live so the output never drifts from the firmware.
Reflects Kyle's *physical* board: the two switches that exist in the firmware
LAYOUT but not on the board (top-right Delete, and the MO(1) key right of
RShift) are drawn as absent (x).

Run from the keyboard dir:  make show-layers
"""
import re
import sys
from pathlib import Path

KB = Path(__file__).resolve().parent.parent          # keyboards/typek
KEYMAP = KB / "keymaps" / "via" / "keymap.c"

# Array indices (LAYOUT() order) of positions with no physical switch on the board.
MISSING = {41, 66}            # 41 = Delete (top-right corner), 66 = MO(1) right of RShift

CW = 5                        # cell width

LABELS = {
    "KC_TRNS": "▽", "KC_NO": "·",
    "QK_GESC": "GEsc", "CTL_ESC": "C/Esc", "QK_BOOT": "BOOT", "EE_CLR": "EEclr",
    "KC_MPLY": "Play", "KC_VOLD": "Vol-", "KC_VOLU": "Vol+",
    "UG_TOGG": "UGtog", "UG_VALD": "Val-", "UG_VALU": "Val+",
    "UG_SATD": "Sat-", "UG_SATU": "Sat+", "UG_HUED": "Hue-", "UG_HUEU": "Hue+",
    "KC_LEFT": "←", "KC_RGHT": "→", "KC_UP": "↑", "KC_DOWN": "↓",
    "KC_SPC": "Spc", "KC_BSPC": "Bspc", "KC_ENT": "Enter", "KC_DEL": "Del",
    "KC_LSFT": "LSft", "KC_RSFT": "RSft", "KC_LCTL": "LCtl", "KC_RCTL": "RCtl",
    "KC_LALT": "LAlt", "KC_RALT": "RAlt", "KC_LGUI": "LGUI", "KC_RGUI": "RGUI",
    "KC_PAUS": "Paus", "KC_SCRL": "Scrl", "KC_CAPS": "Caps", "KC_TAB": "Tab", "KC_ESC": "Esc",
    "KC_GRV": "`", "KC_MINS": "-", "KC_EQL": "=", "KC_BSLS": "\\", "KC_LBRC": "[", "KC_RBRC": "]",
    "KC_SCLN": ";", "KC_QUOT": "'", "KC_COMM": ",", "KC_DOT": ".", "KC_SLSH": "/",
}

# 18-column grid per row.  Ints = array index; None = empty/gap; "X" = missing switch.
# cols: 0 far-left fn | 1 gap | 2-8 left main (7) | 9 split | 10-16 right main (7) | 17 far-right
G, X = None, "X"
GRID = [
    [ 0, G,  1,  2,  3,  4,  5,  6, 60, G,  7,  8,  9, 10, 11, 12, 13,  X],  # numbers
    [14, G, 15, 16, 17, 18, 19, 20,  G, G, 21, 22, 23, 24, 25, 26, 27, 64],  # QWERT
    [28, G, 29, 30, 31, 32, 33, 34,  G, G, 35, 36, 37, 38, 39, 40,  G, 65],  # home
    [42, G, 43, 44, 45, 46, 47, 48,  G, G, 49, 50, 51, 52, 53, 54, 55,  X],  # ZXCVB
    [ G, G, 56,  G,  G,  G, 57, 58, 59, G, 61, 62, 63,  G,  G,  G,  G, 67],  # thumbs
]
assert all(len(r) == 18 for r in GRID), [len(r) for r in GRID]


def parse_layers(src: str):
    layers = []
    for m in re.finditer(r"\[(\d+)\]\s*=\s*LAYOUT\(\s*(?:/\*(.*?)\*/)?\s*(.*?)\n\s*\)",
                         src, re.DOTALL):
        name = (m.group(2) or "").strip()
        body = re.sub(r"/\*.*?\*/", "", m.group(3), flags=re.DOTALL)
        toks = [t.strip() for t in body.split(",")]
        toks = [t for t in toks if t]
        if len(toks) != 68:
            sys.exit(f"layer [{m.group(1)}]: expected 68 keys, got {len(toks)}")
        layers.append((int(m.group(1)), name, toks))
    return layers


def short(tok: str) -> str:
    if tok in LABELS:
        return LABELS[tok]
    mo = re.fullmatch(r"MO\((\d+)\)", tok)
    if mo:
        return "MO" + mo.group(1)
    return tok[3:] if tok.startswith("KC_") else tok


def cell(item, toks):
    if item == X:
        return "✗".center(CW)
    if item is G:
        return " " * CW
    return short(toks[item]).center(CW)


def render(name, toks):
    out = []
    for row in GRID:
        out.append(" ".join(cell(it, toks) for it in row).rstrip())
    # red underglow LED marker under the far-left column
    out.insert(4, "  ▌".ljust(CW))
    return "\n".join(out)


def main():
    layers = parse_layers(KEYMAP.read_text())
    print("TypeK — VIA keymap layers (physical board: no Delete, no key right of RShift)")
    print("  ▽ = transparent (falls through)   ✗ = no physical switch   ▌ = underglow LED\n")
    for idx, name, toks in layers:
        title = f"Layer [{idx}]" + (f"  —  {name}" if name else "")
        reach = {0: "always active",
                 1: "UNREACHABLE (its MO(1) key is the missing one right of RShift)",
                 2: "VIA-selectable (GUI/Alt swapped)",
                 3: "hold MO(3)  (left thumb)"}.get(idx, "")
        print(title + (f"   [{reach}]" if reach else ""))
        print(render(name, toks))
        print()


if __name__ == "__main__":
    main()
