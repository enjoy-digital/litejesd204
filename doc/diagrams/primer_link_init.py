#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204B link start-up on one lane: CGS until the receiver releases SYNC~ on an LMFC boundary,
# ILAS on the next LMFC boundary (4 multiframes), then data.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 215)
    d.add(Text(95, 40, "LMFC", anchor="end"))
    d.add(Text(95, 85, "SYNC~", anchor="end"))
    d.add(Text(95, 140, "lane", anchor="end"))
    for x in range(120, 740, 80):
        d.add(Bus([(x, 28), (x, 52)]))
    d.add(Bus([(110, 95), (200, 95), (200, 72), (740, 72)]))
    d.add(Box(110, 118, 170, 44, label="CGS: /K/", fill=COLOR_ACCENT_LIGHT))
    for i in range(4):
        label = "MF 1\n/Q/ config" if i == 1 else f"MF {i}"
        d.add(Box(280 + 80*i, 118, 80, 44, label=label, radius=0, fill=COLOR_ACCENT, size=13))
    d.add(Box(600, 118, 140, 44, label="data"))
    d.add(Bus([(284, 178), (596, 178)]))
    d.add(Text(440, 192, "ILAS: 4 multiframes, /R/ first, /A/ last", size=FONT_SIZE_SM))
    return d
