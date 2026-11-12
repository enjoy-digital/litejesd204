#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204B and JESD204C share the transport layer: each has its own link layer, its own
# deterministic latency counter (LMFC or LEMC) and its own PHY line code.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 300)
    tr = d.add(Box(40, 20, 680, 44, label="Transport layer and test pattern (shared)", fill=COLOR_ACCENT))
    d.add(Container(40, 85, 330, 130, title="JESD204B", title_pos="br"))
    d.add(Container(390, 85, 330, 130, title="JESD204C", title_pos="br"))
    lb = d.add(Box(60, 105, 170, 50, label="8b/10b link layer", fill=COLOR_ACCENT_LIGHT))
    tb = d.add(Box(250, 105, 100, 50, label="LMFC"))
    lc = d.add(Box(410, 105, 170, 50, label="64b/66b link layer", fill=COLOR_ACCENT_LIGHT))
    tc = d.add(Box(600, 105, 100, 50, label="LEMC"))
    pb = d.add(Box(60, 240, 290, 44, label="8b/10b PHYs (LiteICLink)", fill=COLOR_HARDWARE))
    pc = d.add(Box(410, 240, 290, 44, label="64b/66b PHYs", fill=COLOR_HARDWARE))
    d.add(Arrow((145, 64), (lb, "t"), kind="data", heads="both"))
    d.add(Arrow((495, 64), (lc, "t"), kind="data", heads="both"))
    d.add(Arrow((lb, "b"), (145, 240), kind="data", heads="both"))
    d.add(Arrow((lc, "b"), (495, 240), kind="data", heads="both"))
    d.add(Arrow((tb, "l"), (lb, "r")))
    d.add(Arrow((tc, "l"), (lc, "r")))
    return d
