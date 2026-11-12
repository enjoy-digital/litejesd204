#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204B TX link layer: scrambler, framer, alignment character inserter, CGS/ILAS/data selection.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 270)
    inp  = d.add(Box(15,  110, 90,  56, label="Lane\nword", fill=COLOR_ACCENT_LIGHT))
    scr  = d.add(Box(125, 110, 100, 56, label="Scrambler", fill=COLOR_ACCENT))
    frm  = d.add(Box(245, 110, 90,  56, label="Framer", fill=COLOR_ACCENT))
    ali  = d.add(Box(355, 110, 120, 56, label="Alignment\ninserter", fill=COLOR_ACCENT))
    sel  = d.add(Box(500, 110, 140, 56, label="Output\nselect"))
    cdc  = d.add(Box(665, 110, 80,  56, label="Crossing", fill=COLOR_ACCENT_LIGHT))
    cgs  = d.add(Box(470, 20,  90,  46, label="CGS\ngenerator"))
    ilas = d.add(Box(580, 20,  100, 46, label="ILAS\ngenerator"))
    fsm  = d.add(Box(500, 205, 140, 46, label="State machine"))
    d.add(Arrow((inp, "r"), (scr, "l"), kind="accent"))
    d.add(Arrow((scr, "r"), (frm, "l"), kind="accent"))
    d.add(Arrow((frm, "r"), (ali, "l"), kind="accent"))
    d.add(Arrow((ali, "r"), (sel, "l"), kind="accent"))
    d.add(Arrow((sel, "r"), (cdc, "l"), kind="accent"))
    d.add(Arrow((515, cgs.y + cgs.h), (515, sel.y), kind="data"))
    d.add(Arrow((620, ilas.y + ilas.h), (620, sel.y), kind="data"))
    d.add(Arrow((fsm, "t"), (fsm.cx, sel.y + sel.h), kind="control"))
    d.add(Arrow((360, fsm.cy), (fsm, "l"), kind="control", label="SYNC~, LMFC",
        label_pos=(430, fsm.cy - 12)))
    return d
