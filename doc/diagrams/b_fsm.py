#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204B link state machines: TX (CGS, ILAS, data) and RX (CGS, sync, ILAS, data).

from svgdiag import *


def state(d, x, y, label, w, fill=COLOR_FILL):
    return d.add(Box(x, y, w, 46, label=label, fill=fill))


def build():
    d = Diagram(CANVAS_WIDTH, 330)
    d.add(Text(135, 20, "TX link layer", italic=True, size=FONT_SIZE_TTL))
    d.add(Text(560, 20, "RX link layer", italic=True, size=FONT_SIZE_TTL))
    tw, rw = 150, 160
    tcgs  = state(d, 60, 60,  "SEND-CGS",  tw)
    tilas = state(d, 60, 150, "SEND-ILAS", tw)
    tdata = state(d, 60, 240, "SEND-DATA", tw, fill=COLOR_ACCENT)
    d.add(Arrow((135, tcgs.y + 46), (135, tilas.y), label="SYNC~ released,\nLMFC", label_pos=(143, 122),
        label_anchor="start"))
    d.add(Arrow((135, tilas.y + 46), (135, tdata.y), label="last word", label_pos=(143, 218),
        label_anchor="start"))
    d.add(Arrow((tdata, "r"), (tcgs, "r"), via=[(250, tdata.cy), (250, tcgs.cy)],
        label="SYNC~ low,\n4 clocks", label_pos=(258, 173), label_anchor="start"))
    rcgs  = state(d, 480, 45,  "RECEIVE-CGS",  rw)
    rsync = state(d, 480, 120, "ASSERT-SYNC",  rw)
    rilas = state(d, 480, 195, "RECEIVE-ILAS", rw)
    rdata = state(d, 480, 270, "RECEIVE-DATA", rw, fill=COLOR_ACCENT)
    for a, b, label, ly in ((rcgs, rsync, "valid CGS, LMFC", 106), (rsync, rilas, "/R/ in octet 0", 181),
                           (rilas, rdata, "ILAS done", 256)):
        d.add(Arrow((560, a.y + 46), (560, b.y), label=label, label_pos=(568, ly),
            label_anchor="start"))
    d.add(Arrow((rilas, "r"), (640, 60), via=[(675, rilas.cy), (675, 60)],
        label="ILAS\nmismatch", label_pos=(683, 135), label_anchor="start"))
    d.add(Arrow((rdata, "l"), (480, 60), via=[(440, rdata.cy), (440, 60)],
        label="/K/ again", label_pos=(432, 220), label_anchor="end"))
    return d
