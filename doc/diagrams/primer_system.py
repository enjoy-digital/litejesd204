#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# A JESD204B receive system: the converter device sends L lanes to the FPGA, the FPGA answers on
# SYNC~, and the clock chip sends the device clock and SYSREF to both.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 260)
    clk  = d.add(Box(300, 20, 160, 44, label="Clock chip", fill=COLOR_HARDWARE))
    adc  = d.add(Box(40, 110, 200, 130, label="Converter device\n(ADC)", fill=COLOR_HARDWARE))
    fpga = d.add(Box(520, 110, 200, 130, label="Logic device\n(FPGA)", fill=COLOR_ACCENT))
    for y, l in ((135, "lane 0"), (165, "lane 1"), (195, "lane L-1")):
        d.add(Arrow((240, y), (520, y), kind="accent", label=l, label_pos=(380, y - 10)))
    d.add(Arrow((520, 222), (240, 222), label="SYNC~", label_pos=(380, 232)))
    d.add(Arrow((300, 42), (140, 110), via=[(140, 42)], label="device clock, SYSREF",
        label_pos=(215, 32)))
    d.add(Arrow((460, 42), (620, 110), via=[(620, 42)], label="device clock, SYSREF",
        label_pos=(545, 32)))
    return d
