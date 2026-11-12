#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litejesd204.common import *
from litejesd204.transport import LiteJESD204BSTPLChecker, seed_to_data

from litex.soc.interconnect import stream

from test import test_core_204c

# STPL checker: counts the link clocks with mismatching samples while enabled, clear; RX cores count only while STPL is
# enabled and the core is ready.


class FakePHY204B(Module):
    def __init__(self, n):
        self.n        = n
        self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.rx_align = Signal()


def stpl_settings():
    ps = JESD204BPhysicalSettings(l=1, m=2, n=16, np=16)
    ts = JESD204BTransportSettings(f=4, s=1, k=32, cs=0)
    return JESD204BSettings(ps, ts, did=0x5a, bid=0x5)


class TestSTPL(unittest.TestCase):
    def test_stpl_checker(self):
        settings = stpl_settings()
        dut      = LiteJESD204BSTPLChecker(settings, 32) # 2 converters, 2 samples per clock.
        errors   = []

        def pattern(i):
            return seed_to_data((i << 8) | 0) | (seed_to_data((i << 8) | 0) << 16) # S=1.

        def generator(dut):
            # Good pattern: no error.
            yield dut.sink.converter0.eq(pattern(0))
            yield dut.sink.converter1.eq(pattern(1))
            yield dut.clear.eq(1)
            yield
            yield dut.clear.eq(0)
            for _ in range(4):
                yield
            errors.append((yield dut.errors))
            # 3 bad samples per clock during 4 clocks: 4 errors (link clocks with mismatches).
            yield dut.sink.converter0.eq(pattern(0) ^ 0x00010001)
            yield dut.sink.converter1.eq(pattern(1) ^ 0x00010000)
            for _ in range(4):
                yield
            yield dut.sink.converter0.eq(pattern(0))
            yield dut.sink.converter1.eq(pattern(1))
            yield
            errors.append((yield dut.errors))
            # Disabled: not counted.
            yield dut.enable.eq(0)
            yield dut.sink.converter0.eq(0)
            for _ in range(4):
                yield
            errors.append((yield dut.errors))
            # Clear.
            yield dut.clear.eq(1)
            yield
            yield dut.clear.eq(0)
            yield
            errors.append((yield dut.errors))

        run_simulation(dut, generator(dut))
        self.assertEqual(errors, [0, 4, 4, 0])

    def check_core_rx_not_ready(self, core_cls, settings_cls, phy_cls):
        # RX core not ready (nothing received): no STPL error counted, STPL enabled or not.
        ps   = JESD204BPhysicalSettings(l=2, m=4, n=16, np=16)
        ts   = JESD204BTransportSettings(f=4, s=1, k=32, cs=0)
        phys = [phy_cls(n) for n in range(2)]
        dut  = Module()
        dut.clock_domains.cd_jesd = ClockDomain()
        for n in range(2):
            setattr(dut.submodules, f"phy{n}", phys[n])
            dut.clock_domains += ClockDomain(f"jesd_phy{n}_rx")
        dut.submodules.rx = rx = core_cls(phys, settings_cls(ps, ts, did=0x5a, bid=0x5), 32)
        if hasattr(rx, "register_jsync"):
            rx.register_jsync(Signal())
        rx.register_jref(Signal())
        errors = []

        def generator():
            yield rx.enable.eq(1)
            for stpl_enable in [0, 1]:
                yield rx.stpl_enable.eq(stpl_enable)
                for _ in range(64):
                    yield
                errors.append((yield rx.stpl.errors))
                self.assertEqual((yield rx.ready), 0)

        fragment = dut.get_fragment()
        clocks   = {cd.name: 10 for cd in fragment.clock_domains}
        run_simulation(fragment, {"jesd": generator()}, clocks=clocks)
        self.assertEqual(errors, [0, 0])

    def test_core_rx_not_ready(self):
        from litejesd204.core      import LiteJESD204BCoreRX
        from litejesd204.core_204c import LiteJESD204CCoreRX
        self.check_core_rx_not_ready(LiteJESD204BCoreRX, JESD204BSettings, FakePHY204B)
        self.check_core_rx_not_ready(LiteJESD204CCoreRX, JESD204CSettings, test_core_204c.FakePHY)

if __name__ == "__main__":
    unittest.main()
