#
# This file is part of LiteJESD204.
#
# Copyright (c) 2026 Enjoy-Digital <enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Integration: a LiteX SoC with a JESD204B TX and RX core on four GTX lanes. The clock chip of the
# converter card gives the transceiver reference clock, which feeds the quad PLL and, through the
# ODIV2 output of its buffer (refclk/2), the MMCM of the jesd clock, and SYSREF. SYNC~ runs from the
# DAC to the TX core and from the RX core to the ADC; the host reaches the registers through a UART
# bridge.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 355)
    d.add(Container(10, 85, 530, 260, title="FPGA", title_pos="tl"))
    host  = d.add(Box(30, 15, 100, 45, label="Host", fill=COLOR_HARDWARE))
    ctrl  = d.add(Box(30, 175, 100, 60, label="Bridge,\ncontrols"))
    qpll  = d.add(Box(340, 105, 100, 40, label="Quad PLL", fill=COLOR_ACCENT_LIGHT))
    buf   = d.add(Box(460, 105, 60, 40, label="Buffer"))
    cores = d.add(Box(170, 155, 120, 100, label="TX and RX\ncores", fill=COLOR_ACCENT))
    phys  = d.add(Box(340, 165, 100, 70, label="GTX PHYs", stack=2, fill=COLOR_ACCENT_LIGHT))
    mmcm  = d.add(Box(160, 280, 80, 45, label="MMCM"))
    conv  = d.add(Box(600, 155, 140, 100, label="Converter", fill=COLOR_HARDWARE))
    chip  = d.add(Box(600, 280, 140, 45, label="Clock chip", fill=COLOR_HARDWARE))
    # Registers.
    d.add(Arrow((host, "b"), (ctrl, "t"), kind="data", heads="both", label="UART",
        label_side="right"))
    d.add(Arrow((ctrl, "r"), (170, 205), kind="control", heads="both"))
    # Data path.
    d.add(Arrow((290, 185), (340, 185), kind="data", heads="both"))
    d.add(Arrow((452, 185), (600, 185), kind="accent", heads="both", label="lanes",
        label_pos=(565, 177)))
    d.add(Arrow((qpll, "b"), (390, 165), kind="control"))
    # SYNC~: from the DAC to the TX core, from the RX core to the ADC.
    d.add(Arrow((600, 235), (282, 255), via=[(575, 235), (575, 262), (282, 262)],
        label="SYNC~ to TX", label_pos=(380, 257)))
    d.add(Arrow((270, 255), (600, 245), via=[(270, 274), (585, 274), (585, 245)],
        label="SYNC~ from RX", label_pos=(380, 286)))
    # Clocks and SYSREF from the clock chip.
    d.add(Arrow((670, 280), (670, 255), kind="control", label="clocks",
        label_pos=(703, 270)))
    d.add(Arrow((600, 300), (250, 255), via=[(250, 300)], label="SYSREF",
        label_pos=(295, 296)))
    # Reference clock: buffer, quad PLL, and refclk/2 (ODIV2) to the MMCM of the jesd clock.
    d.add(Arrow((buf, "l"), (qpll, "r"), kind="control"))
    d.add(Arrow((490, 145), (240, 315), via=[(490, 315)], kind="control",
        label="refclk/2", label_pos=(420, 328)))
    d.add(Arrow((mmcm, "t"), (200, 255), kind="control", label="jesd",
        label_side="left"))
    d.add(Arrow((740, 302), (520, 125), via=[(752, 302), (752, 125)],
        label="refclk", label_pos=(600, 118)))
    return d
