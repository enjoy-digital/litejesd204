#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Overview: TX and RX cores between the user logic and the PHYs, lanes to a DAC and from an ADC,
# SYNC~ back to each core, device clock and SYSREF from the clock chip.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 330)
    d.add(Container(10, 10, 520, 250, title="FPGA", title_pos="br"))
    user = d.add(Box(25, 50, 95, 150, label="User\nlogic", fill=COLOR_ACCENT_LIGHT))
    tx   = d.add(Box(150, 50, 130, 50, label="TX core", fill=COLOR_ACCENT))
    rx   = d.add(Box(150, 150, 130, 50, label="RX core", fill=COLOR_ACCENT))
    ptx  = d.add(Box(320, 50, 110, 50, label="PHYs", fill=COLOR_ACCENT_LIGHT))
    prx  = d.add(Box(320, 150, 110, 50, label="PHYs", fill=COLOR_ACCENT_LIGHT))
    dac  = d.add(Box(610, 50, 120, 50, label="DAC", fill=COLOR_HARDWARE))
    adc  = d.add(Box(610, 150, 120, 50, label="ADC", fill=COLOR_HARDWARE))
    clk  = d.add(Box(610, 270, 120, 44, label="Clock chip", fill=COLOR_HARDWARE))
    # Samples and lanes.
    d.add(Arrow((user, "r", 1/6), (tx, "l"), kind="data"))
    d.add(Arrow((tx, "r"), (ptx, "l"), kind="data"))
    d.add(Arrow((ptx, "r"), (dac, "l"), kind="accent", label="lanes",
        label_pos=(570, 65)))
    d.add(Arrow((adc, "l"), (prx, "r"), kind="accent", label="lanes",
        label_pos=(570, 165)))
    d.add(Arrow((prx, "l"), (rx, "r"), kind="data"))
    d.add(Arrow((rx, "l"), (user, "r", 5/6), kind="data"))
    # SYNC~ from the DAC to the TX core, from the RX core to the ADC.
    d.add(Arrow((670, 100), (215, 100), via=[(670, 125), (215, 125)], label="SYNC~",
        label_pos=(560, 136)))
    d.add(Arrow((215, 200), (640, 200), via=[(215, 225), (640, 225)], label="SYNC~",
        label_pos=(560, 236)))
    # Device clock and SYSREF.
    d.add(Arrow((700, 270), (700, 200)))
    d.add(Arrow((730, 292), (730, 75), via=[(748, 292), (748, 75)]))
    d.add(Arrow((610, 292), (375, 260), via=[(375, 292)], label="device clock, SYSREF",
        label_pos=(490, 281)))
    return d
