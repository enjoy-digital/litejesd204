#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *
from migen.genlib.cdc import BusSynchronizer

from litex.soc.interconnect import stream

from litejesd204.common import *
from litejesd204.core import LiteJESD204BCoreTX, LiteJESD204BCoreControl
from litejesd204.core_204c import LiteJESD204CCoreRX, LiteJESD204CCoreControl

from test import test_core_204c

# Core controls: the 32-bit error counters (jesd domain) are crossed to sys as whole words.


class FakePHY(Module):
    def __init__(self, n):
        self.n        = n
        self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.rx_align = Signal()


class DUT(Module):
    def __init__(self):
        self.clock_domains.cd_sys        = ClockDomain()
        self.clock_domains.cd_jesd       = ClockDomain()
        self.clock_domains.cd_jesd_phy0_tx = ClockDomain()
        ps = JESD204BPhysicalSettings(l=1, m=1, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
        settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
        self.submodules.core    = core    = LiteJESD204BCoreTX([FakePHY(0)], settings, 32)
        self.submodules.control = control = LiteJESD204BCoreControl(core, 100e6)
        core.register_jsync(Signal())
        core.register_jref(Signal())
        # The TX STPL generator does not drive its errors counter: use it as a test counter.
        self.counter = core.stpl.errors
        self.status  = control.stpl_errors.status


class TestControlCDC(unittest.TestCase):
    def test_error_counters_synchronizers(self):
        ps = JESD204BPhysicalSettings(l=2, m=4, n=16, np=16)
        ts = JESD204BTransportSettings(f=4, s=1, k=32, cs=0)
        settings = JESD204CSettings(ps, ts, did=0x5a, bid=0x5)
        phys     = [test_core_204c.FakePHY(n) for n in range(2)]
        control  = LiteJESD204CCoreControl(LiteJESD204CCoreRX(phys, settings, 32), 100e6)
        self.assertIsInstance(getattr(control, "stpl_errors_cdc", None), BusSynchronizer)
        self.assertIsInstance(getattr(control, "crc_errors_cdc",  None), BusSynchronizer)

    def test_stpl_errors_cdc(self):
        dut     = DUT()
        samples = []
        written = []

        def jesd_generator(dut):
            value = 0
            for i in range(200):
                value = (value + 0x01010101) & 0xffffffff # Carries across the 4 bytes.
                written.append(value)
                yield dut.counter.eq(value)
                yield
            for i in range(200):
                yield

        def sys_generator(dut):
            for i in range(500):
                samples.append((yield dut.status))
                yield

        run_simulation(dut, {"jesd": jesd_generator(dut), "sys": sys_generator(dut)},
            clocks={"sys": 10, "jesd": 7, "jesd_phy0_tx": 7})
        # Every value seen in sys was a counter value, in order, and the last one gets through.
        seen = [s for s in samples if s != 0]
        self.assertTrue(len(seen) > 10)
        self.assertTrue(set(seen) <= set(written))
        self.assertEqual(seen, sorted(seen))
        self.assertEqual(samples[-1], written[-1])

if __name__ == "__main__":
    unittest.main()
