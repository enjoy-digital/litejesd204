#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litex.soc.interconnect import stream

from litejesd204.common import *
from litejesd204.core import LiteJESD204BCoreRX, LiteJESD204BCoreControl

# LiteJESD204BCoreRX(ilas_check=False) is kept when a LiteJESD204BCoreControl is added (the control
# defaults its ilas_check_disable field from it).


class FakePHY(Module):
    def __init__(self, n):
        self.n        = n
        self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.rx_align = Signal()


class TestILASCheck(unittest.TestCase):
    def ilas_check(self, core_ilas_check, default_ilas_check_disable):
        ps = JESD204BPhysicalSettings(l=1, m=1, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
        settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
        dut = Module()
        dut.clock_domains.cd_sys  = ClockDomain()
        dut.clock_domains.cd_jesd = ClockDomain()
        dut.clock_domains.cd_jesd_phy0_rx = ClockDomain()
        dut.submodules.phy     = phy  = FakePHY(0)
        dut.submodules.core    = core = LiteJESD204BCoreRX([phy], settings, 32, ilas_check=core_ilas_check)
        dut.submodules.control = LiteJESD204BCoreControl(core, 100e6,
            default_ilas_check_disable=default_ilas_check_disable)
        core.register_jsync(Signal())
        core.register_jref(Signal())
        values = []

        def generator():
            for _ in range(4):
                yield
            values.append((yield core.ilas_check))

        run_simulation(dut, {"sys": generator()}, clocks={"sys": 10, "jesd": 10, "jesd_phy0_rx": 10})
        return values[0]

    def test_ilas_check(self):
        self.assertEqual(self.ilas_check(core_ilas_check=True,  default_ilas_check_disable=0), 1)
        self.assertEqual(self.ilas_check(core_ilas_check=True,  default_ilas_check_disable=1), 0)
        self.assertEqual(self.ilas_check(core_ilas_check=False, default_ilas_check_disable=0), 0)
        self.assertEqual(self.ilas_check(core_ilas_check=False, default_ilas_check_disable=1), 0)

if __name__ == "__main__":
    unittest.main()
