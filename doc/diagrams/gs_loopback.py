#
# This file is part of LiteJESD204.
#
# Copyright (c) 2026 Enjoy-Digital <enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Getting started: the JESD204C core loopback of test/test_core_204c.py. The TX core feeds two stand-in
# PHYs that loop each block back to the RX core; the test drives SYSREF and checks STPL and a ramp.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 285)
    d.add(Container(150, 10, 460, 215, title="Simulated design", title_pos="tl"))
    gen  = d.add(Box(15, 95, 110, 90, label="Test\ngenerator", fill=COLOR_ACCENT_LIGHT))
    tx   = d.add(Box(175, 55, 120, 150, label="TX core", fill=COLOR_ACCENT))
    phy0 = d.add(Box(325, 60, 110, 50, label="Stand-in PHY 0", fill=COLOR_HARDWARE))
    phy1 = d.add(Box(325, 150, 110, 50, label="Stand-in PHY 1", fill=COLOR_HARDWARE))
    rx   = d.add(Box(465, 55, 120, 150, label="RX core", fill=COLOR_ACCENT))
    chk  = d.add(Box(635, 95, 110, 90, label="Checks", fill=COLOR_ACCENT_LIGHT))
    # Samples in, lanes through the stand-in PHYs, samples out.
    d.add(Arrow((gen, "r"), (175, 140), kind="data"))
    d.add(Arrow((295, 85), (phy0, "l"), kind="accent"))
    d.add(Arrow((295, 175), (phy1, "l"), kind="accent"))
    d.add(Arrow((phy0, "r"), (465, 85), kind="accent"))
    d.add(Arrow((phy1, "r"), (465, 175), kind="accent"))
    d.add(Arrow((585, 140), (chk, "l"), kind="data"))
    # SYSREF from the test generator to both cores.
    d.add(Arrow((70, 185), (235, 205), via=[(70, 255), (235, 255)], label="SYSREF",
        label_pos=(110, 247)))
    d.add(Arrow((235, 255), (525, 205), via=[(525, 255)]))
    return d
