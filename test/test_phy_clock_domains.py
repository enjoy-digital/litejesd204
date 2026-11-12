#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litex.soc.interconnect import stream

from litejesd204.common import *
from litejesd204.core import LiteJESD204BCoreTX, LiteJESD204BCoreRX
from litejesd204.core_204c import LiteJESD204CCoreTX, LiteJESD204CCoreRX
from litejesd204.link_204c import link_204c_layout

# PHYs with their own tx/rx clock domains (as LiteICLink PHYs): the cores use them directly, with
# one lane (no Migen renaming of the PHY domains) as with several.


class FakePHY(Module):
    def __init__(self, layout, with_slip=False):
        self.clock_domains.cd_tx = ClockDomain()
        self.clock_domains.cd_rx = ClockDomain()
        self.sink     = stream.Endpoint(layout)
        self.source   = stream.Endpoint(layout)
        self.rx_align = Signal()
        if with_slip:
            self.rx_slip = Signal()

        # # #

        tx_data = Signal(len(self.sink.data))
        self.sync.tx += tx_data.eq(self.sink.data)
        self.sync.rx += self.source.data.eq(tx_data)


class DUT(Module):
    def __init__(self, nlanes, jesd204c=False):
        self.clock_domains.cd_jesd = ClockDomain()
        ps = JESD204BPhysicalSettings(l=nlanes, m=nlanes, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
        if jesd204c:
            layout   = link_204c_layout()
            settings = JESD204CSettings(ps, ts, did=0x5a, bid=0x5)
            cores    = (LiteJESD204CCoreTX, LiteJESD204CCoreRX)
            cdw      = 64
        else:
            layout   = [("data", 32), ("ctrl", 4)]
            settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
            cores    = (LiteJESD204BCoreTX, LiteJESD204BCoreRX)
            cdw      = 32
        phys = []
        for n in range(nlanes):
            phy = FakePHY(layout, with_slip=jesd204c)
            setattr(self.submodules, f"jesd_phy{n}", phy)
            phys.append(phy)
        self.submodules.tx = tx = cores[0](phys, settings, cdw)
        self.submodules.rx = rx = cores[1](phys, settings, cdw)
        for core in [tx, rx]:
            if hasattr(core, "register_jsync"):
                core.register_jsync(Signal())
            core.register_jref(Signal())


class TestPHYClockDomains(unittest.TestCase):
    def test_elaborate(self):
        for jesd204c in [False, True]:
            for nlanes in [1, 2]:
                with self.subTest(jesd204c=jesd204c, nlanes=nlanes):
                    dut      = DUT(nlanes, jesd204c)
                    fragment = dut.get_fragment()
                    clocks   = {cd.name: 10 for cd in fragment.clock_domains}
                    # Elaborate and simulate a few cycles (all the used clock domains must exist).
                    def generator():
                        for _ in range(8):
                            yield
                    run_simulation(fragment, {"jesd": generator()}, clocks=clocks)

if __name__ == "__main__":
    unittest.main()
