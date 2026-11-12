#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Character replacement on one lane, F = 4, K = 4: the last octet of a frame may become /F/, the
# last octet of the multiframe may become /A/.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 150)
    x0, w = 60, 40
    cells = []
    for f in range(4):
        for o in range(4):
            last = o == 3
            if last and f == 3:
                label, fill = "/A/", COLOR_ACCENT
            elif last and f in (0, 2):
                label, fill = "/F/", COLOR_ACCENT_LIGHT
            else:
                label, fill = "D", COLOR_FILL
            cells.append(d.add(Box(x0 + (4*f + o)*w, 30, w, 30, label=label, radius=0, fill=fill, size=13)))
    for f in range(4):
        xa, xb = x0 + 4*f*w + 4, x0 + 4*(f + 1)*w - 4
        d.add(Bus([(xa, 72), (xb, 72)]))
        d.add(Text((xa + xb)/2, 86, f"frame {f}", size=FONT_SIZE_SM))
    d.add(Bus([(x0 + 4, 108), (x0 + 16*w - 4, 108)]))
    d.add(Text(x0 + 8*w, 122, "multiframe: K = 4 frames", size=FONT_SIZE_SM))
    d.add(Arrow((x0 + 16*w + 8, 45), (x0 + 16*w + 52, 45), kind="data", label="time", label_side="above"))
    return d
