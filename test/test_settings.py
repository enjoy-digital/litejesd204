#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litejesd204.common import *
from litejesd204.link import LiteJESD204BLinkTX

# Frame/multiframe sizing: the frames on a lane are F octets (octets per lane and frame), so the
# LMFC period is F*K/4 link clocks (4 octets per clock), also when M != L.


def jesd204b_settings(l, m, k=32, np=16):
    f  = m*np//(8*l) # S=1.
    ps = JESD204BPhysicalSettings(l=l, m=m, n=np, np=np)
    ts = JESD204BTransportSettings(f=f, s=1, k=k, cs=0)
    return JESD204BSettings(ps, ts, did=0x5a, bid=0x5)


class TestSettings(unittest.TestCase):
    def test_lmfc_cycles(self):
        for l, m in [(1, 1), (2, 2), (4, 4), (2, 4), (4, 8), (8, 4), (4, 2)]:
            for k in [16, 32]:
                with self.subTest(l=l, m=m, k=k):
                    settings = jesd204b_settings(l, m, k)
                    f        = settings.transport.f
                    self.assertEqual(settings.octets_per_lane, f)
                    self.assertEqual(settings.lmfc_cycles, f*k//4)

    def test_jesd204c_emb_alignment(self):
        # Frames must align with the extended multiblock: E*256 octets per lane, F octets per frame.
        def settings(f, e):
            ps = JESD204BPhysicalSettings(l=1, m=1, n=8*f, np=8*f) # F = N'/8 with L=M=S=1.
            ts = JESD204BTransportSettings(f=f, s=1, k=32, cs=0)
            return JESD204CSettings(ps, ts, did=0x5a, bid=0x5, e=e)
        self.assertEqual(settings(f=3, e=3).octets_per_lane, 3)
        self.assertEqual(settings(f=4, e=1).octets_per_lane, 4)
        with self.assertRaises(AssertionError):
            settings(f=3, e=1)

    def link_tx_framing(self, l, m, k=32):
        settings = jesd204b_settings(l, m, k)
        lmfc     = settings.lmfc_cycles
        dut      = LiteJESD204BLinkTX(32, settings)
        dut.ilas = dut.fsm.ongoing("SEND-ILAS")
        stats    = dict(ilas_cycles=0, multiframe_lasts=[], frame_lasts=set())

        def generator(dut):
            yield dut.jsync.eq(1)
            for cycle in range(12*lmfc):
                yield dut.lmfc_zero.eq(int(cycle % lmfc == 0))
                yield
                if (yield dut.ilas):
                    stats["ilas_cycles"] += 1
                if (yield dut.ready):
                    if (yield dut.source.multiframe_last):
                        stats["multiframe_lasts"].append(cycle)
                    stats["frame_lasts"].add((yield dut.source.frame_last))

        run_simulation(dut, generator(dut))
        return settings, stats

    def test_link_tx_framing_m_ne_l(self):
        # L=2 M=4 F=4 K=32: 32 link clocks per multiframe (was 16 with per-converter sizing).
        settings, stats = self.link_tx_framing(l=2, m=4)
        lmfc = settings.lmfc_cycles
        self.assertEqual(lmfc, 32)
        # ILAS: 4 multiframes.
        self.assertEqual(stats["ilas_cycles"], 4*lmfc)
        # Data: one multiframe per LMFC period, one frame per clock (frame_last on octet 3).
        mf = stats["multiframe_lasts"]
        self.assertGreaterEqual(len(mf), 3)
        self.assertEqual({b - a for a, b in zip(mf, mf[1:])}, {lmfc})
        self.assertEqual(stats["frame_lasts"], {0b1000})

    def test_link_tx_framing_m_eq_l(self):
        settings, stats = self.link_tx_framing(l=2, m=2)
        lmfc = settings.lmfc_cycles
        self.assertEqual(stats["ilas_cycles"], 4*lmfc)
        mf = stats["multiframe_lasts"]
        self.assertEqual({b - a for a, b in zip(mf, mf[1:])}, {lmfc})
        self.assertEqual(stats["frame_lasts"], {0b1010})

if __name__ == "__main__":
    unittest.main()
