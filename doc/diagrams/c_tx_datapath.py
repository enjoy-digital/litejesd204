#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204C TX link layer: octet reorder, scrambler, registers; CRC-12 and sync word give the header.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 280)
    inp = d.add(Box(15,  70, 90,  56, label="Lane\nword", fill=COLOR_ACCENT_LIGHT))
    reo = d.add(Box(125, 70, 95,  56, label="Octet\nreorder", fill=COLOR_ACCENT))
    scr = d.add(Box(240, 70, 105, 56, label="Scrambler", fill=COLOR_ACCENT))
    reg = d.add(Box(365, 70, 100, 56, label="Two\nregisters", fill=COLOR_ACCENT))
    cdc = d.add(Box(645, 70, 100, 56, label="Crossing", fill=COLOR_ACCENT_LIGHT))
    cnt = d.add(Box(125, 190, 120, 56, label="Block\ncounters"))
    crc = d.add(Box(365, 190, 100, 56, label="CRC-12"))
    swd = d.add(Box(505, 190, 110, 56, label="Sync word"))
    d.add(Arrow((inp, "r"), (reo, "l"), kind="accent"))
    d.add(Arrow((reo, "r"), (scr, "l"), kind="accent"))
    d.add(Arrow((scr, "r"), (reg, "l"), kind="accent"))
    d.add(Arrow((reg, "r"), (cdc, "l"), kind="accent", label="64-bit data", label_pos=(555, 86)))
    d.add(Arrow((reg, "b"), (crc, "t"), kind="data", label="scrambled", label_pos=(423, 168),
        label_anchor="start"))
    d.add(Arrow((cnt, "r"), (crc, "l"), kind="control", label="multiblock start",
        label_pos=(305, 206)))
    d.add(Arrow((crc, "r"), (swd, "l"), kind="control"))
    d.add(Arrow((swd, "r"), (cdc.cx, cdc.y + cdc.h), via=[(cdc.cx, swd.cy)], kind="data",
        label="2-bit header", label_pos=(687, 168), label_anchor="end"))
    d.add(Arrow((15, cnt.cy), (cnt, "l"), kind="control", label="LEMC", label_pos=(60, cnt.cy - 12)))
    return d
