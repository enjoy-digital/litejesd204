#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# The 32-bit sync word of a multiblock in CRC-12 mode, as the core builds it: one bit per block,
# bit 31 first. C: CRC-12 bit, 1: pilot bit, c: command bit, E: EoEMB, then the EoMB sequence.

from svgdiag import *


def cell(bit):
    if bit >= 17:
        return "1" if bit in (28, 24, 20) else "C"
    if bit in (16, 12, 10, 8):
        return "1"
    if bit == 9:
        return "E"
    if bit <= 4:
        return "1" if bit == 0 else "0"
    return "c"


def build():
    d = Diagram(CANVAS_WIDTH, 140)
    x0, w = 44, 21
    for i, bit in enumerate(range(31, -1, -1)):
        c = cell(bit)
        if bit <= 4:
            fill = COLOR_ACCENT
        elif c == "E":
            fill = COLOR_ACCENT
        elif c == "1":
            fill = COLOR_SHADE
        else:
            fill = COLOR_ACCENT_LIGHT if c == "C" else COLOR_FILL
        d.add(Box(x0 + i*w, 40, w, 30, label=c, radius=0, fill=fill, size=13))
    for bit in (31, 17, 9, 4, 0):
        d.add(Text(x0 + (31 - bit)*w + w/2, 25, str(bit), size=FONT_SIZE_SM))
    def bracket(msb, lsb, text):
        xa, xb = x0 + (31 - msb)*w + 3, x0 + (32 - lsb)*w - 3
        d.add(Bus([(xa, 84), (xb, 84)]))
        d.add(Text((xa + xb)/2, 98, text, size=FONT_SIZE_SM))
    bracket(31, 17, "CRC-12 of the previous multiblock")
    bracket(16, 5, "command bits, EoEMB")
    bracket(4, 0, "EoMB")
    d.add(Arrow((x0 + 260, 128), (x0 + 420, 128), kind="data", label="time", label_side="above"))
    return d
