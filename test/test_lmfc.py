#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from migen import *

from litejesd204.core import LMFC

# LMFC/LEMC counter: zero every lmfc_cycles clocks between SYSREF edges, also when the period is
# not a power of two, and reloaded with load on a SYSREF rising edge.


class TestLMFC(unittest.TestCase):
    def lmfc_zeros(self, lmfc_cycles, load=0, jref_at=None, cycles=None):
        dut   = LMFC(lmfc_cycles, load)
        zeros = []
        cycles = 6*lmfc_cycles if cycles is None else cycles

        def generator(dut):
            for cycle in range(cycles):
                yield dut.jref.eq(int(jref_at is not None and cycle >= jref_at))
                if (yield dut.zero):
                    zeros.append(cycle)
                yield

        run_simulation(dut, generator(dut))
        return zeros

    def test_lmfc_period(self):
        for lmfc_cycles in [8, 10, 16, 24, 32, 48, 96]:
            with self.subTest(lmfc_cycles=lmfc_cycles):
                zeros = self.lmfc_zeros(lmfc_cycles)
                self.assertGreaterEqual(len(zeros), 5)
                self.assertEqual({b - a for a, b in zip(zeros, zeros[1:])}, {lmfc_cycles})

    def test_lmfc_sysref_reload(self):
        for lmfc_cycles in [10, 16, 24]:
            for load in [0, 5]:
                with self.subTest(lmfc_cycles=lmfc_cycles, load=load):
                    jref_at = 3*lmfc_cycles + 1
                    zeros   = self.lmfc_zeros(lmfc_cycles, load, jref_at=jref_at, cycles=8*lmfc_cycles)
                    # Count reloaded 3 cycles after the jref edge (2 synchronization registers).
                    first = jref_at + 3 + (lmfc_cycles - load) % lmfc_cycles
                    after = [z for z in zeros if z > jref_at + 2]
                    self.assertEqual(after[0], first)
                    self.assertEqual({b - a for a, b in zip(after, after[1:])}, {lmfc_cycles})

    def test_lmfc_periodic_sysref(self):
        # Periodic SYSREF (period a multiple of the LMFC period, 1-cycle pulse): the LMFC keeps
        # running with zero every lmfc_cycles, also when lmfc_cycles is not a power of two.
        for lmfc_cycles in [10, 24, 96]:
            for load in [0, 5]:
                with self.subTest(lmfc_cycles=lmfc_cycles, load=load):
                    dut   = LMFC(lmfc_cycles, load)
                    zeros = []

                    def generator(dut):
                        for cycle in range(12*lmfc_cycles):
                            yield dut.jref.eq(int(cycle % (4*lmfc_cycles) == 0))
                            if (yield dut.zero):
                                zeros.append(cycle)
                            yield

                    run_simulation(dut, generator(dut))
                    zeros = [z for z in zeros if z > 3]
                    self.assertGreaterEqual(len(zeros), 10)
                    # No missing zero strobe...
                    self.assertEqual({b - a for a, b in zip(zeros, zeros[1:])}, {lmfc_cycles})
                    # ...and at the SYSREF phase: count reloaded with load 3 cycles after each edge.
                    phase = 3 + (lmfc_cycles - load) % lmfc_cycles
                    self.assertEqual({(z - phase) % lmfc_cycles for z in zeros}, {0})

if __name__ == "__main__":
    unittest.main()
