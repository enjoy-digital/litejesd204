#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# LMFC in a JESD204B link: SYSREF reloads the counter, boundaries pace the TX ILAS start.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 270)
    xs, xe, period = 120, 745, 70
    ys, yl, yy, yt = 50, 115, 170, 215
    for y, name in ((ys, "SYSREF"), (yl, "LMFC"), (yy - 7, "SYNC~"), (yt + 15, "TX lane")):
        d.add(Text(15, y, name, anchor="start"))
    d.add(Bus([(xs, ys), (160, ys), (160, ys - 16), (176, ys - 16), (176, ys), (xe, ys)]))
    d.add(Bus([(xs, yl), (xe, yl)]))
    bounds = list(range(200, xe, period))
    for x in bounds:
        d.add(Bus([(x, yl), (x, yl - 16)], kind="data"))
    d.add(Arrow((176, ys + 6), (176, yl - 4), kind="control", label="reload", label_pos=(184, 82),
        label_anchor="start"))
    d.add(Text(305, yl - 28, "boundaries", size=FONT_SIZE_SM))
    d.add(Bus([(xs, yy), (300, yy), (300, yy - 14), (xe, yy - 14)]))
    d.add(Text(294, yy - 26, "released", size=FONT_SIZE_SM, anchor="end"))
    ilas0, ilas1 = 340, 340 + 4*period
    d.add(Box(xs, yt, ilas0 - xs, 30, label="CGS", radius=0))
    d.add(Box(ilas0, yt, ilas1 - ilas0, 30, label="ILAS: 4 multiframes", radius=0, fill=COLOR_ACCENT))
    d.add(Box(ilas1, yt, xe - ilas1, 30, label="data", radius=0, fill=COLOR_ACCENT_LIGHT))
    for x in (ilas0, ilas1):
        d.add(Bus([(x, yl + 4), (x, yy - 18)], dash="2,3"))
        d.add(Bus([(x, yy + 4), (x, yt)], dash="2,3"))
    return d
