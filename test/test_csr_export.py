#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litex.build.generic_platform import Pins
from litex.build.sim import SimPlatform
from litex.soc.integration.soc_core import SoCMini
from litex.soc.integration import export
from litex.soc.interconnect import stream

from litejesd204.common import *
from litejesd204.core import LiteJESD204BCoreTX, LiteJESD204BCoreRX, LiteJESD204BCoreControl
from litejesd204.core_204c import LiteJESD204CCoreRX, LiteJESD204CCoreControl

from test import test_core_204c

# SVD export of the core controls (the lmfc register reset was an expression: TypeError).


class FakePHY(Module):
    def __init__(self, n):
        self.n        = n
        self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.rx_align = Signal()


class SoC(SoCMini):
    def __init__(self):
        platform = SimPlatform("sim", [("sys_clk", 0, Pins(1)), ("sys_rst", 0, Pins(1))])
        SoCMini.__init__(self, platform, int(100e6))
        ps = JESD204BPhysicalSettings(l=2, m=2, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
        settings_b = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
        ps = JESD204BPhysicalSettings(l=2, m=4, n=16, np=16)
        ts = JESD204BTransportSettings(f=4, s=1, k=32, cs=0)
        settings_c = JESD204CSettings(ps, ts, did=0x5a, bid=0x5)
        self.submodules.tx  = tx  = LiteJESD204BCoreTX([FakePHY(n) for n in range(2)], settings_b, 32)
        self.submodules.rx  = rx  = LiteJESD204BCoreRX([FakePHY(n) for n in range(2)], settings_b, 32)
        self.submodules.rxc = rxc = LiteJESD204CCoreRX([test_core_204c.FakePHY(n) for n in range(2)], settings_c, 32)
        for core in [tx, rx, rxc]:
            if hasattr(core, "register_jsync"):
                core.register_jsync(Signal())
            core.register_jref(Signal())
        self.submodules.tx_control  = LiteJESD204BCoreControl(tx,  100e6)
        self.submodules.rx_control  = LiteJESD204BCoreControl(rx,  100e6, with_lane_status=True)
        self.submodules.rxc_control = LiteJESD204CCoreControl(rxc, 100e6)


class TestCSRExport(unittest.TestCase):
    def test_csr_svd(self):
        soc = SoC()
        soc.finalize()
        svd = export.get_csr_svd(soc)
        for name in ["TX_CONTROL", "RX_CONTROL", "RXC_CONTROL"]:
            self.assertIn(f"<name>{name}</name>", svd)
        # lmfc reset: the LMFC load value (TX: 1 + 4 link clocks).
        self.assertEqual(soc.tx_control.lmfc.fields.load_on_sysref.reset.value, 5)

if __name__ == "__main__":
    unittest.main()
