#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Clock domains of a core: sys (registers), jesd (layers and counters), PHY user clock domains.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 220)
    d.add(Text(90,  30, "sys", italic=True, size=FONT_SIZE_TTL))
    d.add(Text(362, 30, "jesd (link clock)", italic=True, size=FONT_SIZE_TTL))
    d.add(Text(652, 30, "PHY TX and RX", italic=True, size=FONT_SIZE_SM + 2))
    regs = d.add(Box(15,  100, 100, 56, label="Registers"))
    sync = d.add(Box(130, 100, 100, 56, label="Synchro-\nnizers", fill=COLOR_ACCENT_LIGHT))
    core = d.add(Box(285, 90,  150, 76, label="Layers,\nLMFC or LEMC,\nskew FIFOs", fill=COLOR_ACCENT))
    cdc  = d.add(Box(490, 100, 110, 56, label="Crossings", fill=COLOR_ACCENT_LIGHT, stack=2))
    phy  = d.add(Box(645, 100, 100, 56, label="PHYs", fill=COLOR_HARDWARE, stack=2))
    # Boundaries drawn over the two blocks that straddle them (synchronizers, crossings).
    for x in (180, 545):
        d.add(Bus([(x, 50), (x, 92)], dash=DASH_FEEDBACK))
        d.add(Bus([(x, 164), (x, 205)], dash=DASH_FEEDBACK))
    d.add(Arrow((regs, "r"), (sync, "l"), kind="control", heads="both"))
    d.add(Arrow((sync, "r"), (core.x, sync.cy), kind="control", heads="both"))
    d.add(Arrow((core.x + core.w, cdc.cy), (cdc, "l"), kind="accent", heads="both"))
    d.add(Arrow((cdc.x + cdc.w + 10, cdc.cy), (phy, "l"), kind="accent", heads="both"))
    return d
