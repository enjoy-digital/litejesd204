#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Octet alignment: /R/ in octet 2 of a word; the output takes octets 2-3 of it and 0-1 of the next.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 230)
    x0, cw, yi, yo = 125, 70, 50, 160
    d.add(Text(15, yi + 20, "Input", anchor="start"))
    d.add(Text(15, yo + 20, "Output", anchor="start"))
    labels = ["data", "data", "/R/", "o1", "o2", "o3", "o4", "o5"]
    for i, label in enumerate(labels):
        sel  = 2 <= i <= 5
        fill = COLOR_ACCENT if label == "/R/" else (COLOR_ACCENT_LIGHT if sel else COLOR_FILL)
        d.add(Box(x0 + i*cw, yi, cw, 40, label=label, radius=0, fill=fill))
    for w, name in enumerate(("word n", "word n+1")):
        d.add(Text(x0 + (4*w + 2)*cw, yi - 16, name, italic=True))
    for j, label in enumerate(["/R/", "o1", "o2", "o3"]):
        x = x0 + (2 + j)*cw
        fill = COLOR_ACCENT if label == "/R/" else COLOR_ACCENT_LIGHT
        d.add(Arrow((x + cw/2, yi + 40), (x + cw/2, yo), kind="data"))
        d.add(Box(x, yo, cw, 40, label=label, radius=0, fill=fill))
        d.add(Text(x + cw/2, yo + 52, f"octet {j}", size=FONT_SIZE_SM))
    d.add(Text(x0 + 6*cw + 20, yo + 20, "alignment = 2", anchor="start"))
    return d
