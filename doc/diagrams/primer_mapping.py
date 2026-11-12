#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Transport mapping, M = 4, L = 2, S = 1, N = 14, N' = 16, F = 4: each sample becomes two octets,
# most significant first, and each lane carries the F octets of its share of the frame.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 215)
    d.add(Text(115, 45, "samples", anchor="end"))
    d.add(Text(115, 115, "octets", anchor="end"))
    d.add(Text(115, 180, "lanes", anchor="end"))
    x0, w = 130, 75
    for c in range(4):
        x = x0 + c*2*w
        d.add(Box(x, 30, 2*w - 22, 30, label=f"converter {c}", radius=0, fill=COLOR_ACCENT_LIGHT, size=13))
        d.add(Box(x + 2*w - 22, 30, 22, 30, label="T", radius=0, fill=COLOR_SHADE, size=13))
        for h, name in enumerate(("[15:8]", "[7:0]")):
            d.add(Box(x + h*w, 100, w, 30, label=f"C{c} {name}", radius=0, size=13))
    for c in range(4):
        x = x0 + c*2*w + w
        d.add(Arrow((x, 60), (x, 100), kind="data"))
    for i in range(2):
        d.add(Box(x0 + i*4*w + 10, 165, 4*w - 20, 30, label=f"lane {i}: F = 4 octets", fill=COLOR_ACCENT))
        d.add(Arrow((x0 + i*4*w + 2*w, 130), (x0 + i*4*w + 2*w, 165), kind="data"))
    return d
