#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Transport mapping, L = 2, M = 4, N' = 16, S = 1: four samples into two 4-octet lane words.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 250)
    x0, cw, ys, yl = 105, 80, 40, 150
    d.add(Text(15, ys + 20, "Samples", anchor="start"))
    d.add(Text(15, yl + 20, "Lanes", anchor="start"))
    for c in range(4):
        fill = COLOR_ACCENT if c < 2 else COLOR_ACCENT_LIGHT
        for h, part in enumerate(("[15:8]", "[7:0]")):
            x = x0 + (2*c + h)*cw
            d.add(Box(x, ys, cw, 40, label=f"C{c} {part}", radius=0, fill=fill))
            d.add(Arrow((x + cw/2, ys + 40), (x + cw/2, yl), kind="data"))
    for lane in range(2):
        fill = COLOR_ACCENT if lane == 0 else COLOR_ACCENT_LIGHT
        for o in range(4):
            x = x0 + (4*lane + o)*cw
            d.add(Box(x, yl, cw, 40, label=f"octet {o}", radius=0, fill=fill))
            d.add(Text(x + cw/2, yl + 52, f"bits {8*o + 7}:{8*o}", size=FONT_SIZE_SM))
        d.add(Text(x0 + (4*lane + 2)*cw, yl + 80, f"lane{lane}", italic=True))
    for c in range(4):
        d.add(Text(x0 + (2*c + 1)*cw, ys - 14, f"converter{c}", size=FONT_SIZE_SM))
    return d
