#
# This file is part of LiteJESD204.
#
# Copyright (c) 2016-2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# JESD204C RX link layer: block lock in the PHY RX domain, sync word receiver, CRC check, data path.

from svgdiag import *


def build():
    d = Diagram(CANVAS_WIDTH, 290)
    d.add(Bus([(205, 45), (205, 280)], dash=DASH_FEEDBACK))
    d.add(Text(95,  25, "jesd_phy<n>_rx", italic=True, size=FONT_SIZE_SM + 2))
    d.add(Text(470, 25, "jesd", italic=True, size=FONT_SIZE_TTL))
    phy = d.add(Box(15,  70, 120, 56, label="PHY", fill=COLOR_HARDWARE))
    cdc = d.add(Box(160, 70, 90,  56, label="Crossing", fill=COLOR_ACCENT_LIGHT))
    dsc = d.add(Box(290, 70, 115, 56, label="Descrambler", fill=COLOR_ACCENT))
    reo = d.add(Box(435, 70, 100, 56, label="Octet\nreorder", fill=COLOR_ACCENT))
    bsy = d.add(Box(15,  205, 120, 56, label="Block lock", fill=COLOR_ACCENT_LIGHT))
    swr = d.add(Box(290, 205, 130, 56, label="Sync word\nreceiver", fill=COLOR_ACCENT_LIGHT))
    crc = d.add(Box(460, 205, 110, 56, label="CRC check"))
    d.add(Arrow((phy, "r"), (cdc, "l"), kind="accent"))
    d.add(Arrow((cdc, "r"), (dsc, "l"), kind="accent"))
    d.add(Arrow((dsc, "r"), (reo, "l"), kind="accent"))
    d.add(Arrow((reo, "r"), (745, reo.cy), kind="accent", label="lane word", label_pos=(640, 86)))
    d.add(Arrow((45, phy.y + phy.h), (45, bsy.y), kind="data", label="header", label_pos=(53, 166),
        label_anchor="start"))
    d.add(Arrow((105, bsy.y), (105, phy.y + phy.h), kind="control", label="rx_slip",
        label_pos=(113, 186), label_anchor="start"))
    d.add(Arrow((230, cdc.y + cdc.h), (swr.x, 222), via=[(230, 222)], kind="data"))
    d.add(Arrow((bsy.x + bsy.w, 248), (swr.x, 248), kind="control", label="sh_lock",
        label_pos=(262, 236)))
    d.add(Arrow((240, cdc.y + cdc.h), (crc.cx, crc.y), via=[(240, 180), (crc.cx, 180)], kind="data",
        label="scrambled", label_pos=(445, 172)))
    d.add(Arrow((swr, "r"), (crc, "l"), kind="control"))
    d.add(Arrow((crc, "r"), (745, crc.cy), kind="control", label="crc_error",
        label_pos=(660, crc.cy - 12)))
    return d
