#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204B RX link layer: aligner, then CGS checker, ILAS checker and the data path.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 270)
    cdc  = d.add(Box(15,  60, 85,  56, label="Crossing", fill=COLOR_ACCENT_LIGHT))
    ali  = d.add(Box(120, 60, 90,  56, label="Aligner", fill=COLOR_ACCENT))
    rep  = d.add(Box(240, 60, 115, 56, label="Alignment\nreplacer", fill=COLOR_ACCENT))
    dfr  = d.add(Box(375, 60, 95,  56, label="Deframer", fill=COLOR_ACCENT))
    dsc  = d.add(Box(490, 60, 110, 56, label="Descrambler", fill=COLOR_ACCENT))
    out  = d.add(Box(625, 60, 120, 56, label="Skew FIFO", fill=COLOR_ACCENT_LIGHT))
    cgs  = d.add(Box(105, 190, 110, 46, label="CGS\nchecker"))
    ilas = d.add(Box(240, 190, 115, 46, label="ILAS\nchecker"))
    d.add(Arrow((cdc, "r"), (ali, "l"), kind="accent"))
    d.add(Arrow((ali, "r"), (rep, "l"), kind="accent"))
    d.add(Arrow((rep, "r"), (dfr, "l"), kind="accent"))
    d.add(Arrow((dfr, "r"), (dsc, "l"), kind="accent"))
    d.add(Arrow((dsc, "r"), (out, "l"), kind="accent"))
    d.add(Arrow((150, ali.y + ali.h), (150, cgs.y), kind="data"))
    d.add(Arrow((190, ali.y + ali.h), (ilas.cx, ilas.y), via=[(190, 160), (ilas.cx, 160)],
        kind="data"))
    return d
