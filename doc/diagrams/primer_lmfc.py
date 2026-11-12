#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Subclass 1 deskew: SYSREF resets the LMFC phase; each lane ends its ILAS at its own time; the
# receiver buffers the early lanes and releases all of them on the same LMFC boundary.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 240)
    d.add(Text(95, 35, "SYSREF", anchor="end"))
    d.add(Text(95, 82, "LMFC", anchor="end"))
    d.add(Text(95, 137, "lane 0", anchor="end"))
    d.add(Text(95, 187, "lane 1", anchor="end"))
    d.add(Bus([(110, 45), (140, 45), (140, 25), (160, 25), (160, 45), (740, 45)]))
    for x in (160, 235, 310, 385, 460, 535, 610, 685):
        d.add(Bus([(x, 70), (x, 94)]))
    d.add(Box(110, 120, 50, 34, label="CGS", radius=0))
    d.add(Box(160, 120, 300, 34, label="ILAS, 4 multiframes", radius=0, fill=COLOR_ACCENT_LIGHT))
    d.add(Box(460, 120, 75, 34, label="buffered", radius=0, fill=COLOR_SHADE))
    d.add(Box(535, 120, 205, 34, label="data", radius=0, fill=COLOR_ACCENT))
    d.add(Box(110, 170, 90, 34, label="CGS", radius=0))
    d.add(Box(200, 170, 300, 34, label="ILAS, 4 multiframes", radius=0, fill=COLOR_ACCENT_LIGHT))
    d.add(Box(500, 170, 35, 34, radius=0, fill=COLOR_SHADE))
    d.add(Box(535, 170, 205, 34, label="data", radius=0, fill=COLOR_ACCENT))
    d.add(Bus([(535, 100), (535, 212)], dash="4,3"))
    d.add(Text(535, 225, "release", size=FONT_SIZE_SM))
    return d
