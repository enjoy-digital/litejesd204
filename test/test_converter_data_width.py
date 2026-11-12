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

from test import test_core_204c

# converter_data_width: invalid values are rejected with a readable message (instead of a Migen
# width error or cores built silently with wrong lane widths).


class FakePHY(Module):
    def __init__(self, n):
        self.n        = n
        self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.rx_align = Signal()


def settings(cls, l, m):
    ps = JESD204BPhysicalSettings(l=l, m=m, n=16, np=16)
    ts = JESD204BTransportSettings(f=2*m//l, s=1, k=32, cs=0)
    return cls(ps, ts, did=0x5a, bid=0x5)


class TestConverterDataWidth(unittest.TestCase):
    def test_204b(self):
        for core_cls in [LiteJESD204BCoreTX, LiteJESD204BCoreRX]:
            # L=2, M=2: 32-bit lanes with converter_data_width=32.
            core_cls([FakePHY(n) for n in range(2)], settings(JESD204BSettings, 2, 2), 32)
            for cdw in [8, 16, 24, 48, 64]:
                with self.subTest(core=core_cls.__name__, cdw=cdw):
                    with self.assertRaises(AssertionError) as cm:
                        core_cls([FakePHY(n) for n in range(2)], settings(JESD204BSettings, 2, 2), cdw)
                    self.assertIn("converter_data_width", str(cm.exception))
            # L=1, M=4, N=16: converter_data_width < N.
            with self.assertRaises(AssertionError) as cm:
                core_cls([FakePHY(0)], settings(JESD204BSettings, 1, 4), 8)
            self.assertIn("multiple of N", str(cm.exception))

    def test_204c(self):
        for core_cls in [LiteJESD204CCoreTX, LiteJESD204CCoreRX]:
            phys = lambda: [test_core_204c.FakePHY(n) for n in range(2)]
            core_cls(phys(), settings(JESD204CSettings, 2, 4), 32)
            for cdw in [16, 64]:
                with self.subTest(core=core_cls.__name__, cdw=cdw):
                    with self.assertRaises(AssertionError) as cm:
                        core_cls(phys(), settings(JESD204CSettings, 2, 4), cdw)
                    self.assertIn("converter_data_width = 32", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
