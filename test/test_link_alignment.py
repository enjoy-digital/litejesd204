#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest
import random

from migen import *

from litejesd204.common import *
from litejesd204.link import LiteJESD204BLinkTXDatapath, LiteJESD204BLinkRXDatapath
from litejesd204.link import LiteJESD204BLinkTX, LiteJESD204BLinkRX

# Link TX -> RX datapaths without scrambling: /A/ and /F/ replace the last octet of a frame equal to
# the last octet of the previous frame (F octets earlier) and are restored on RX, for F=1, 2 and 4,
# also when consecutive frames end with the same value (constant data).


class DUT(Module):
    def __init__(self, octets_per_frame, frames_per_multiframe):
        self.submodules.tx = tx = LiteJESD204BLinkTXDatapath(32, octets_per_frame, frames_per_multiframe)
        self.submodules.rx = rx = LiteJESD204BLinkRXDatapath(32, octets_per_frame, frames_per_multiframe)
        self.comb += [
            tx.scrambler.enable.eq(0),
            rx.descrambler.enable.eq(0),
            rx.sink.eq(tx.source),
        ]


class TestLinkAlignment(unittest.TestCase):
    def loopback(self, octets_per_frame, octets, frames_per_multiframe=16):
        dut     = DUT(octets_per_frame, frames_per_multiframe)
        words   = [int.from_bytes(bytes(octets[4*i:4*(i+1)]), "little") for i in range(len(octets)//4)]
        tx_ctrl = []
        rx_data = []

        def generator():
            for word in words:
                yield dut.tx.sink.data.eq(word)
                yield
                tx_ctrl.append((yield dut.tx.source.ctrl))
                rx_data.append((yield dut.rx.source.data))

        run_simulation(dut, generator())
        return words, tx_ctrl, rx_data

    def check(self, octets_per_frame, octets):
        words, tx_ctrl, rx_data = self.loopback(octets_per_frame, octets)
        # Alignment characters were inserted.
        self.assertTrue(any(tx_ctrl))
        # RX data follows TX data with a constant latency (skip the first words: reset/pipeline).
        for latency in range(8):
            if rx_data[16 + latency:] == words[16:len(words) - latency]:
                break
        else:
            self.fail("RX data does not match TX data")

    def test_constant_data(self):
        for octets_per_frame in [1, 2, 4]:
            with self.subTest(octets_per_frame=octets_per_frame):
                self.check(octets_per_frame, [0x55]*4*256)

    def test_repeated_frames(self):
        prng = random.Random(42)
        for octets_per_frame in [1, 2, 4]:
            with self.subTest(octets_per_frame=octets_per_frame):
                octets = []
                while len(octets) < 4*256:
                    frame = [prng.randrange(256) for _ in range(octets_per_frame)]
                    for _ in range(prng.randrange(1, 4)): # Frames repeated 1 to 3 times.
                        octets += frame
                octets = octets[:4*256]
                self.check(octets_per_frame, octets)

    def test_frame_end_rule(self):
        # F=2: only frame ends equal to the previous frame end (2 octets earlier) are replaced.
        octets = [0x11, 0x22, 0x33, 0x22]*256 # Frame ends 0x22, 0x22: replaced.
        _, tx_ctrl, _ = self.loopback(2, octets)
        self.assertTrue(set(tx_ctrl[16:]) <= {0b1010, 0b1000, 0b0010})
        self.assertTrue(any(tx_ctrl))
        octets = [0x11, 0x22, 0x22, 0x33]*256 # Equal consecutive octets in a frame: not replaced.
        _, tx_ctrl, _ = self.loopback(2, octets)
        self.assertEqual(set(tx_ctrl[16:]), {0})

    def test_link_constant_data(self):
        # Full links (CGS, ILAS, data) without scrambling, constant data: the first data frame
        # follows the ILAS on the lane, the data must be received unchanged.
        for np, s in [(8, 1), (16, 1), (16, 2)]: # F = 1, 2, 4.
            with self.subTest(f=np*s//8):
                ps = JESD204BPhysicalSettings(l=1, m=1, n=np, np=np)
                ts = JESD204BTransportSettings(f=np*s//8, s=s, k=16, cs=0)
                settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5, scrambling=False)
                lmfc = settings.lmfc_cycles
                dut  = Module()
                dut.submodules.tx = tx = LiteJESD204BLinkTX(32, settings)
                dut.submodules.rx = rx = LiteJESD204BLinkRX(32, settings)
                dut.comb += [
                    tx.datapath.scrambler.enable.eq(0),
                    rx.datapath.descrambler.enable.eq(0),
                    rx.sink.eq(tx.source),
                    tx.jsync.eq(rx.jsync),
                    tx.sink.data.eq(0x55555555),
                ]
                received = []

                def generator():
                    for cycle in range(24*lmfc):
                        yield tx.lmfc_zero.eq(int(cycle % lmfc == 0))
                        yield rx.lmfc_zero.eq(int(cycle % lmfc == 0))
                        yield
                        if (yield rx.ready):
                            received.append((yield rx.source.data))

                run_simulation(dut, generator())
                self.assertGreater(len(received), 4*lmfc)
                self.assertEqual(set(received[2:]), {0x55555555})

if __name__ == "__main__":
    unittest.main()
