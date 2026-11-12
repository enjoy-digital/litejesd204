#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Test pattern path: generator in place of the user samples, checker in place of the user side.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 210)
    gen  = d.add(Box(15,  25,  120, 46, label="STPL\ngenerator", fill=COLOR_ACCENT))
    uin  = d.add(Box(15,  135, 120, 46, label="User\nsamples", fill=COLOR_ACCENT_LIGHT))
    ttx  = d.add(Box(190, 75,  110, 56, label="Transport\nTX"))
    lnk  = d.add(Box(340, 75,  120, 56, label="Links and\nlanes", fill=COLOR_HARDWARE))
    trx  = d.add(Box(500, 75,  110, 56, label="Transport\nRX"))
    chk  = d.add(Box(650, 25,  95,  46, label="STPL\nchecker", fill=COLOR_ACCENT))
    uout = d.add(Box(650, 135, 95,  46, label="User\nsamples", fill=COLOR_ACCENT_LIGHT))
    d.add(Arrow((gen, "r"), (ttx.x, 92), via=[(162, gen.cy), (162, 92)], kind="accent"))
    d.add(Arrow((uin, "r"), (ttx.x, 114), via=[(162, uin.cy), (162, 114)], kind="data"))
    d.add(Arrow((ttx, "r"), (lnk, "l"), kind="accent"))
    d.add(Arrow((lnk, "r"), (trx, "l"), kind="accent"))
    d.add(Arrow((trx.x + trx.w, 92), (chk, "l"), via=[(630, 92), (630, chk.cy)], kind="accent"))
    d.add(Arrow((trx.x + trx.w, 114), (uout, "l"), via=[(630, 114), (630, uout.cy)], kind="data"))
    d.add(Text(250, 30, "stpl_enable = 1", size=FONT_SIZE_SM))
    return d
