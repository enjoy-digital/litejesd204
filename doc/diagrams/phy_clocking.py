#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Clocking of a JESD204 link: one clock chip feeds the converter and the FPGA; transceiver PLL and
# clocking PLL share the reference; SYSREF goes to the core.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 260)
    d.add(Container(190, 5, 555, 245, title="FPGA", title_pos="br"))
    conv = d.add(Box(15,  20,  110, 50,  label="Converter", fill=COLOR_HARDWARE))
    chip = d.add(Box(15,  150, 110, 70,  label="Clock chip", fill=COLOR_HARDWARE))
    xpll = d.add(Box(215, 75,  115, 50,  label="Transceiver\nPLL"))
    phys = d.add(Box(380, 75,  110, 50,  label="PHYs", fill=COLOR_ACCENT_LIGHT, stack=2))
    cpll = d.add(Box(215, 150, 115, 50,  label="Clocking\nPLL"))
    core = d.add(Box(570, 95,  150, 100, label="Core\n(jesd domain)", fill=COLOR_ACCENT))
    d.add(Arrow((chip, "t"), (conv, "b"), kind="control", label="device clock\nSYSREF",
        label_pos=(78, 110), label_anchor="start"))
    d.add(Arrow((125, cpll.cy), (xpll, "l"), via=[(170, cpll.cy), (170, xpll.cy)], kind="control",
        label="reference", label_pos=(130, 189), label_anchor="start"))
    d.add(Arrow((170, cpll.cy), (cpll, "l"), kind="control"))
    d.add(Arrow((xpll, "r"), (phys, "l"), kind="control"))
    d.add(Arrow((phys, "r"), (core.x, 115), via=[(530, phys.cy), (530, 115)], kind="control",
        label="user clocks", label_pos=(500, 72), label_anchor="start"))
    d.add(Arrow((cpll, "r"), (core.x, cpll.cy), kind="accent", label="jesd",
        label_pos=(450, cpll.cy - 12)))
    d.add(Arrow((125, 210), (core.cx, core.y + core.h), via=[(core.cx, 210)], kind="control",
        label="SYSREF", label_pos=(450, 222)))
    d.add(Arrow((conv, "r"), (435, phys.y - 10), via=[(435, conv.cy)], kind="data", heads="both",
        label="lanes", label_pos=(300, conv.cy - 12)))
    return d
