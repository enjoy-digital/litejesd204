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

# JESD204B core-level TX -> RX loopback through fake PHYs: each PHY loops its TX 32-bit words
# (data + ctrl) back to its RX side, the cores run in the "jesd" domain and the PHYs in their
# "jesd_phy{n}_tx/rx" domains, all at the same period so the elastic buffers of the clock domain
# crossings are exercised. The RX SYNC~ output drives the TX SYNC~ input, SYSREF is common. Small
# multiframes (K=16, LMFC = F*K/4 = 8 or 16 link clocks) keep the simulation short. Scrambling
# enabled (the default; the unscrambled /A/ /F/ character replacement is not covered).


def jesd204b_settings(s=1, scrambling=True):
    # 2 lanes / 2 converters, F = 2*S.
    ps = JESD204BPhysicalSettings(l=2, m=2, n=16, np=16)
    ts = JESD204BTransportSettings(f=2*s, s=s, k=16, cs=0)
    return JESD204BSettings(ps, ts, did=0x5a, bid=0x5, scrambling=scrambling)


class FakePHY(Module):
    def __init__(self, n):
        self.n        = n
        self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.rx_align = Signal()

        # # #

        self.comb += [
            self.sink.ready.eq(1),
            self.source.valid.eq(1),
            self.source.data.eq(self.sink.data),
            self.source.ctrl.eq(self.sink.ctrl),
        ]


class DUT(Module):
    def __init__(self, settings, converter_data_width=32, scrambling=True):
        self.jref  = Signal()
        self.jsync = Signal()

        self.clock_domains.cd_jesd = ClockDomain()
        self.phys = []
        for n in range(settings.phy.l):
            for direction in ["tx", "rx"]:
                self.clock_domains += ClockDomain(f"jesd_phy{n}_{direction}")
            phy = FakePHY(n)
            setattr(self.submodules, f"phy{n}", phy)
            self.phys.append(phy)

        self.submodules.tx = LiteJESD204BCoreTX(self.phys, settings, converter_data_width, scrambling=scrambling)
        self.submodules.rx = LiteJESD204BCoreRX(self.phys, settings, converter_data_width, scrambling=scrambling)
        self.rx.register_jsync(self.jsync)
        self.tx.register_jsync(self.jsync)
        self.tx.register_jref(self.jref)
        self.rx.register_jref(self.jref)

    def get_fragment_and_clocks(self, period=10):
        # Include the local clock domains of the elastic buffers (renamed by Migen when finalized).
        fragment = self.get_fragment()
        clocks   = {cd.name: period for cd in fragment.clock_domains}
        return fragment, clocks


class TestCore(unittest.TestCase):
    def core_loopback(self, s=1, scrambling=True, converter_data_width=32):
        settings    = jesd204b_settings(s, scrambling)
        lmfc        = settings.lmfc_cycles
        nconverters = settings.nconverters
        dut         = DUT(settings, converter_data_width, scrambling)
        stats       = dict(tx_ready_at=None, rx_ready_at=None, stpl_errors=[])
        stats.update(tx_ramp=[], rx_ramp=[])

        def ramp(cycle):
            return [(cycle + (i << 16)) & (2**converter_data_width - 1) for i in range(nconverters)]

        def generator(dut):
            cycle = 0

            def step(n=1):
                nonlocal cycle
                for _ in range(n):
                    yield dut.jref.eq(int(cycle % (4*lmfc) == 0)) # SYSREF at 4 x the LMFC period.
                    yield
                    cycle += 1

            # Reset (cores disabled), then enable in STPL mode.
            yield dut.tx.stpl_enable.eq(1)
            yield dut.rx.stpl_enable.eq(1)
            yield from step(8)
            yield dut.tx.enable.eq(1)
            yield dut.rx.enable.eq(1)

            # Wait for the TX and RX cores to be ready (CGS, then 4 multiframes of ILAS).
            for _ in range(32*lmfc):
                yield from step()
                if stats["tx_ready_at"] is None and (yield dut.tx.ready):
                    stats["tx_ready_at"] = cycle
                if stats["rx_ready_at"] is None and (yield dut.rx.ready):
                    stats["rx_ready_at"] = cycle
                if stats["rx_ready_at"] is not None:
                    break
            if stats["rx_ready_at"] is None:
                return

            # STPL: the checker's error count must not move once the pattern flows through.
            yield from step(2*lmfc)
            for _ in range(2*lmfc):
                stats["stpl_errors"].append((yield dut.rx.stpl.errors))
                yield from step()

            # Ramp on the converters, captured on both sides for the latency check.
            yield dut.tx.stpl_enable.eq(0)
            yield dut.rx.stpl_enable.eq(0)
            for _ in range(4*lmfc):
                for i, value in enumerate(ramp(cycle)):
                    yield getattr(dut.tx.sink, f"converter{i}").eq(value)
                stats["tx_ramp"].append(ramp(cycle))
                yield from step()
                rx_values = []
                for i in range(nconverters):
                    rx_values.append((yield getattr(dut.rx.source, f"converter{i}")))
                stats["rx_ramp"].append(rx_values)

        fragment, clocks = dut.get_fragment_and_clocks()
        run_simulation(fragment, {"jesd": generator(dut)}, clocks=clocks)
        return settings, stats

    def check_loopback(self, settings, stats):
        lmfc = settings.lmfc_cycles
        self.assertIsNotNone(stats["tx_ready_at"])
        self.assertIsNotNone(stats["rx_ready_at"])
        self.assertTrue(stats["tx_ready_at"] <= stats["rx_ready_at"])
        # STPL: no error accumulated while locked.
        self.assertEqual(len(set(stats["stpl_errors"])), 1)
        # Ramp: the RX converters follow the TX converters with a constant latency (the ramp data
        # is unique per cycle: the first match sets the latency, every later cycle must match).
        tx_ramp, rx_ramp = stats["tx_ramp"], stats["rx_ramp"]
        first = [c for c, v in enumerate(rx_ramp) if v in tx_ramp]
        self.assertTrue(len(first) >= 1)
        latency = first[0] - tx_ramp.index(rx_ramp[first[0]])
        self.assertTrue(0 < latency < 2*lmfc)
        for c in range(first[0], len(rx_ramp)):
            self.assertEqual(rx_ramp[c], tx_ramp[c - latency], f"cycle {c}, latency {latency}")
        self.assertTrue(len(rx_ramp) - first[0] >= lmfc)

    def test_core_loopback(self):
        settings, stats = self.core_loopback(s=1) # F=2.
        self.check_loopback(settings, stats)

    def test_core_loopback_f4(self):
        settings, stats = self.core_loopback(s=2) # F=4.
        self.check_loopback(settings, stats)

if __name__ == "__main__":
    unittest.main()
