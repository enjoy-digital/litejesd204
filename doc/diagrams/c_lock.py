#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204C receiver lock: per lane, sync header lock (hunt, slip, lock); then extended multiblock
# lock on the sync words (init, hunt, lock).

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 235)
    d.add(Container(10, 20, 360, 200, title="Sync header lock", title_pos="br"))
    d.add(Container(390, 20, 360, 200, title="Extended multiblock lock", title_pos="br"))
    hunt = d.add(Box(30, 60, 100, 40, label="HUNT", fill=COLOR_ACCENT_LIGHT))
    lock = d.add(Box(240, 60, 100, 40, label="LOCK", fill=COLOR_ACCENT))
    slip = d.add(Box(30, 160, 100, 40, label="SLIP"))
    d.add(Arrow((hunt, "r", 0.25), (lock, "l", 0.25), label="64 valid"))
    d.add(Arrow((lock, "l", 0.75), (hunt, "r", 0.75), label="16 invalid", label_side="below"))
    d.add(Arrow((hunt, "b", 0.3), (slip, "t", 0.3), label="invalid", label_side="left"))
    d.add(Arrow((slip, "t", 0.7), (hunt, "b", 0.7), label="wait", label_side="right"))
    init  = d.add(Box(405, 60, 80, 40, label="INIT", fill=COLOR_ACCENT_LIGHT))
    ehunt = d.add(Box(535, 60, 80, 40, label="HUNT", fill=COLOR_ACCENT_LIGHT))
    elock = d.add(Box(662, 60, 80, 40, label="LOCK", fill=COLOR_ACCENT))
    d.add(Arrow((init, "r"), (ehunt, "l"), label="EoEMB"))
    d.add(Arrow((ehunt, "r"), (elock, "l"), label="3 more"))
    d.add(Arrow((575, 100), (458, 100), via=[(575, 125), (458, 125)]))
    d.add(Text(516, 138, "missing", size=FONT_SIZE_SM))
    d.add(Arrow((702, 100), (431, 100), via=[(702, 152), (431, 152)]))
    d.add(Text(640, 165, "8 missing", size=FONT_SIZE_SM))
    d.add(Arrow((lock, "r"), (init, "l")))
    return d
