#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# The 14 configuration octets of the ILAS (second multiframe), bit 7 on the left. Parameters
# marked -1 are sent minus one.

from svgdiag import *

ROWS = [
    [(7, 0, "DID")],
    [(7, 4, "ADJCNT"), (3, 0, "BID")],
    [(7, 7, None), (6, 6, "ADJDIR"), (5, 5, "PHADJ"), (4, 0, "LID")],
    [(7, 7, "SCR"), (6, 5, None), (4, 0, "L-1")],
    [(7, 0, "F-1")],
    [(7, 5, None), (4, 0, "K-1")],
    [(7, 0, "M-1")],
    [(7, 6, "CS"), (5, 5, None), (4, 0, "N-1")],
    [(7, 5, "SUBCLASSV"), (4, 0, "N'-1")],
    [(7, 5, "JESDV"), (4, 0, "S-1")],
    [(7, 7, "HD"), (6, 5, None), (4, 0, "CF")],
    [(7, 0, None)],
    [(7, 0, None)],
    [(7, 0, "FCHK")],
]


def build():
    x0, w, y0, h = 150, 70, 40, 22
    d = Diagram(CANVAS_WIDTH, y0 + h*len(ROWS) + 10)
    for b in range(8):
        d.add(Text(x0 + (7 - b)*w + w/2, 22, f"bit {b}", size=FONT_SIZE_SM))
    for i, fields in enumerate(ROWS):
        y = y0 + i*h
        d.add(Text(x0 - 12, y + h/2, f"octet {i}", size=13, anchor="end"))
        for msb, lsb, name in fields:
            x = x0 + (7 - msb)*w
            fill = COLOR_SHADE if name is None else (COLOR_ACCENT if name == "FCHK" else COLOR_FILL)
            d.add(Box(x, y, (msb - lsb + 1)*w, h, label=name or "", radius=0, fill=fill, size=13))
    return d
