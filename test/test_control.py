#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litex.soc.interconnect import stream

from litejesd204.common import *
from litejesd204.core import LiteJESD204BCoreTX, LiteJESD204BCoreRX, LiteJESD204BCoreControl
from litejesd204.core_204c import LiteJESD204CCoreTX, LiteJESD204CCoreRX, LiteJESD204CCoreControl

from test.test_core_204c import FakePHY as FakePHY204C

# Core controls: sys_clk_freq is optional (unused), positional and keyword forms still accepted.


class FakePHY204B(Module):
    def __init__(self, n):
        self.n        = n
        self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.rx_align = Signal()


def settings(cls):
    ps = JESD204BPhysicalSettings(l=2, m=4, n=16, np=16)
    ts = JESD204BTransportSettings(f=4, s=1, k=32, cs=0)
    return cls(ps, ts, did=0x5a, bid=0x5)


class TestControl(unittest.TestCase):
    def check_controls(self, core_cls, control_cls, phy_cls, settings, cdw, with_jsync):
        for kwargs in [{}, dict(sys_clk_freq=100e6)]:
            phys = [phy_cls(n) for n in range(settings.nlanes)]
            core = core_cls(phys, settings, cdw)
            if with_jsync:
                core.register_jsync(Signal())
            core.register_jref(Signal())
            control = control_cls(core, **kwargs)
            self.assertIn("control", [csr.name for csr in control.get_csrs()])
            control.get_fragment()
        # Positional sys_clk_freq.
        phys = [phy_cls(n) for n in range(settings.nlanes)]
        control_cls(core_cls(phys, settings, cdw), 100e6, 1)

    def test_204b_controls(self):
        for core_cls in [LiteJESD204BCoreTX, LiteJESD204BCoreRX]:
            self.check_controls(core_cls, LiteJESD204BCoreControl, FakePHY204B,
                settings(JESD204BSettings), cdw=16, with_jsync=True)

    def test_204c_controls(self):
        for core_cls in [LiteJESD204CCoreTX, LiteJESD204CCoreRX]:
            self.check_controls(core_cls, LiteJESD204CCoreControl, FakePHY204C,
                settings(JESD204CSettings), cdw=32, with_jsync=False)

    def test_skew_fifo_level_width(self):
        # status.skew_fifo holds the full level of the lane 0 skew FIFO (4 multiframes or extended
        # multiblocks: 256 words and more with F*K/4 >= 64 or E >= 2) and the status register
        # stays within one 32-bit CSR word (no register moves).
        def settings_204b(k):
            ps = JESD204BPhysicalSettings(l=2, m=2, n=16, np=16)
            ts = JESD204BTransportSettings(f=2, s=1, k=k, cs=0)
            return JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
        def settings_204c(e):
            ps = JESD204BPhysicalSettings(l=2, m=4, n=16, np=16)
            ts = JESD204BTransportSettings(f=4, s=1, k=32, cs=0)
            return JESD204CSettings(ps, ts, did=0x5a, bid=0x5, e=e)
        configs  = [(LiteJESD204BCoreRX, LiteJESD204BCoreControl, FakePHY204B, settings_204b(k), 32, True)
            for k in [32, 128, 256]]
        configs += [(LiteJESD204CCoreRX, LiteJESD204CCoreControl, FakePHY204C, settings_204c(e), 32, False)
            for e in [1, 2, 8]]
        for core_cls, control_cls, phy_cls, settings, cdw, with_jsync in configs:
            with self.subTest(core=core_cls.__name__, k=settings.transport.k, e=getattr(settings, "e", None)):
                phys = [phy_cls(n) for n in range(settings.nlanes)]
                core = core_cls(phys, settings, cdw)
                if with_jsync:
                    core.register_jsync(Signal())
                core.register_jref(Signal())
                control = control_cls(core)
                level   = core.skew_fifos[0].level
                field   = control.status.fields.skew_fifo
                self.assertGreaterEqual(len(field), len(level))
                self.assertLessEqual(len(control.status.status), 32)

if __name__ == "__main__":
    unittest.main()
