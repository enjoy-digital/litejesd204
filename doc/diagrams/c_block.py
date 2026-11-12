#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# A JESD204C 64b/66b block: a 2-bit sync header, then 8 octets of scrambled payload.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 135)
    x0 = 40
    d.add(Box(x0, 30, 40, 34, label="H", radius=0, fill=COLOR_ACCENT, size=13))
    d.add(Box(x0 + 40, 30, 40, 34, label="H", radius=0, fill=COLOR_ACCENT, size=13))
    for i in range(8):
        d.add(Box(x0 + 80 + i*75, 30, 75, 34, label=f"octet {i}", radius=0, fill=COLOR_ACCENT_LIGHT, size=13))
    d.add(Bus([(x0 + 4, 78), (x0 + 76, 78)]))
    d.add(Text(x0 + 40, 92, "sync header", size=FONT_SIZE_SM))
    d.add(Bus([(x0 + 84, 78), (x0 + 676, 78)]))
    d.add(Text(x0 + 380, 92, "64-bit payload, scrambled", size=FONT_SIZE_SM))
    d.add(Arrow((x0 + 300, 122), (x0 + 460, 122), kind="data", label="time", label_side="above"))
    return d
