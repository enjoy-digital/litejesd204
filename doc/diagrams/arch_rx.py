#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# RX core: PHYs, crossings, link layers, skew FIFOs, transport, test pattern checker, LMFC.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 300)
    d.add(Container(120, 20, 520, 260, title="RX core", title_pos="bl"))
    phy  = d.add(Box(15,  110, 85,  56, label="PHYs", fill=COLOR_HARDWARE, stack=2))
    cdc  = d.add(Box(140, 110, 95,  56, label="Crossing", fill=COLOR_ACCENT_LIGHT, stack=2))
    link = d.add(Box(265, 110, 95,  56, label="Link RX", fill=COLOR_ACCENT, stack=2))
    skew = d.add(Box(390, 110, 100, 56, label="Skew\nFIFO", fill=COLOR_ACCENT, stack=2))
    tr   = d.add(Box(520, 110, 100, 56, label="Transport\nRX", fill=COLOR_ACCENT))
    stpl = d.add(Box(520, 40,  100, 46, label="STPL\nchecker"))
    smp  = d.add(Box(660, 110, 85,  56, label="Converter\nsamples", fill=COLOR_ACCENT_LIGHT))
    lmfc = d.add(Box(390, 205, 100, 40, label="LMFC"))
    d.add(Arrow((phy.x + phy.w + 10, phy.cy), (cdc, "l"), kind="accent"))
    d.add(Arrow((cdc.x + cdc.w + 10, cdc.cy), (link, "l"), kind="accent"))
    d.add(Arrow((link.x + link.w + 10, link.cy), (skew, "l"), kind="accent"))
    d.add(Arrow((skew.x + skew.w + 10, skew.cy), (tr, "l"), kind="accent"))
    d.add(Arrow((tr, "r"), (smp, "l"), kind="accent"))
    d.add(Arrow((tr, "t"), (stpl, "b"), kind="data"))
    d.add(Arrow((lmfc, "t"), (lmfc.cx, skew.y + skew.h), kind="control", label="release",
        label_pos=(448, 186), label_anchor="start"))
    d.add(Arrow((lmfc.cx, 295), (lmfc, "b"), kind="control", label="SYSREF", label_pos=(448, 266),
        label_anchor="start"))
    d.add(Arrow((300, link.y - 10), (300, 8), kind="control", label="SYNC~ (204B)",
        label_pos=(308, 50), label_anchor="start"))
    return d
