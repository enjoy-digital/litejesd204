#
# This file is part of LiteJESD204.
#
# Copyright (c) 2026 Enjoy-Digital <enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Integration: link bring-up from software. The first row configures the converter card and brings
# up the transceivers, the second starts the JESD204B link and checks it.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 210)
    w, h = 155, 55
    xs   = [15, 205, 395, 585]
    row1 = ["Configure\nclock chip", "Configure\nconverter", "Enable PHYs", "Wait PHYs\nready"]
    row2 = ["SYSREF", "Enable cores", "Wait core\nready", "STPL check"]
    fills1 = [COLOR_HARDWARE, COLOR_HARDWARE, COLOR_ACCENT_LIGHT, COLOR_ACCENT_LIGHT]
    fills2 = [COLOR_HARDWARE, COLOR_ACCENT, COLOR_ACCENT, COLOR_ACCENT]
    top = [d.add(Box(x, 20, w, h, label=l, fill=f)) for x, l, f in zip(xs, row1, fills1)]
    bot = [d.add(Box(x, 135, w, h, label=l, fill=f)) for x, l, f in zip(xs, row2, fills2)]
    for a, b in zip(top, top[1:]):
        d.add(Arrow((a, "r"), (b, "l"), kind="data"))
    for a, b in zip(bot, bot[1:]):
        d.add(Arrow((a, "r"), (b, "l"), kind="data"))
    d.add(Arrow((top[-1], "b"), (bot[0], "t"), via=[(662, 105), (92, 105)], kind="data"))
    return d
