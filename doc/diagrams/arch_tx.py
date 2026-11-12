#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# TX core: converter samples, test pattern generator, transport, link layers, crossings, PHYs, LMFC.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 300)
    d.add(Container(140, 20, 465, 260, title="TX core", title_pos="bl"))
    smp  = d.add(Box(15,  110, 105, 56, label="Converter\nsamples", fill=COLOR_ACCENT_LIGHT))
    stpl = d.add(Box(160, 40,  110, 46, label="STPL\ngenerator"))
    tr   = d.add(Box(160, 110, 110, 56, label="Transport\nTX", fill=COLOR_ACCENT))
    link = d.add(Box(310, 110, 110, 56, label="Link TX", fill=COLOR_ACCENT, stack=2))
    cdc  = d.add(Box(460, 110, 120, 56, label="Crossing", fill=COLOR_ACCENT_LIGHT, stack=2))
    phy  = d.add(Box(640, 110, 105, 56, label="PHYs", fill=COLOR_HARDWARE, stack=2))
    lmfc = d.add(Box(310, 205, 110, 40, label="LMFC"))
    d.add(Arrow((smp, "r"), (tr, "l"), kind="accent"))
    d.add(Arrow((stpl, "b"), (tr, "t"), kind="data", label="test pattern", label_pos=(223, 98),
        label_anchor="start"))
    d.add(Arrow((tr, "r"), (link, "l"), kind="accent"))
    d.add(Arrow((link.x + link.w + 10, link.cy), (cdc, "l"), kind="accent"))
    d.add(Arrow((cdc.x + cdc.w + 10, cdc.cy), (phy, "l"), kind="accent"))
    d.add(Arrow((lmfc, "t"), (lmfc.cx, link.y + link.h), kind="control", label="boundaries",
        label_pos=(373, 186), label_anchor="start"))
    d.add(Arrow((lmfc.cx, 295), (lmfc, "b"), kind="control", label="SYSREF", label_pos=(373, 266),
        label_anchor="start"))
    d.add(Arrow((395, 8), (395, link.y - 10), kind="control", label="SYNC~ (204B)",
        label_pos=(403, 50), label_anchor="start"))
    return d
