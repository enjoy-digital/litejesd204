#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# RX lane deskew: per-lane skew FIFOs filled by different amounts, released on the same boundary.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 230)
    cw, fx = 30, 175
    tr  = d.add(Box(520, 30, 110, 150, label="Transport\nRX", fill=COLOR_ACCENT_LIGHT))
    out = d.add(Box(660, 80, 85,  50,  label="Converter\nsamples"))
    for lane, (y, filled) in enumerate(((40, 4), (130, 2))):
        link = d.add(Box(15, y, 110, 46, label=f"Link RX {lane}", fill=COLOR_ACCENT_LIGHT))
        for i in range(6):
            fill = COLOR_ACCENT if i >= 6 - filled else COLOR_FILL
            d.add(Box(fx + i*cw, y + 8, cw, 30, radius=0, fill=fill))
        d.add(Text(fx + 3*cw, y - 10, f"skew FIFO {lane}", size=FONT_SIZE_SM))
        d.add(Arrow((link, "r"), (fx, link.cy), kind="data"))
        d.add(Arrow((fx + 6*cw, link.cy), (tr.x, link.cy), kind="accent"))
    d.add(Arrow((tr, "r"), (out, "l"), kind="accent"))
    d.add(Bus([(420, 25), (420, 185)], dash="2,3"))
    d.add(Text(420, 205, "LMFC boundary: release", size=FONT_SIZE_SM))
    return d
