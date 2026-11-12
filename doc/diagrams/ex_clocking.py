#
# This file is part of LiteJESD204.
#
# Copyright (c) 2026 Enjoy-Digital <enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Examples: clocking of the 7-Series example. One reference clock from the clock chip feeds the
# quad PLL of the transceivers and, divided by two in the input buffer, the MMCM of the jesd clock.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 250)
    d.add(Container(170, 10, 580, 230, title="FPGA", title_pos="br"))
    chip  = d.add(Box(15, 95, 115, 60, label="Clock chip", fill=COLOR_HARDWARE))
    buf   = d.add(Box(200, 95, 120, 60, label="IBUFDS_GTE2", fill=COLOR_ACCENT_LIGHT))
    qpll  = d.add(Box(380, 30, 110, 50, label="Quad PLL", fill=COLOR_ACCENT_LIGHT))
    mmcm  = d.add(Box(380, 170, 110, 50, label="MMCM", fill=COLOR_ACCENT_LIGHT))
    phys  = d.add(Box(560, 30, 120, 50, label="GTX PHYs", stack=2, fill=COLOR_ACCENT_LIGHT))
    cores = d.add(Box(560, 145, 120, 75, label="Cores", fill=COLOR_ACCENT))
    d.add(Arrow((chip, "r"), (buf, "l"), label="refclk", label_pos=(150, 117)))
    d.add(Arrow((260, 95), (qpll, "l"), via=[(260, 55)], label="O", label_pos=(320, 47)))
    d.add(Arrow((260, 155), (mmcm, "l"), via=[(260, 195)], label="ODIV2",
        label_pos=(320, 187)))
    d.add(Arrow((qpll, "r"), (phys, "l"), label="line rate", label_pos=(525, 47)))
    d.add(Arrow((mmcm, "r"), (560, 195), kind="accent", label="jesd", label_pos=(525, 187)))
    d.add(Arrow((620, 80), (620, 145), kind="accent", label="user clocks",
        label_side="right"))
    return d
