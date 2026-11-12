#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import unittest

from litejesd204.common import *

# JESD204CSettings does not modify the physical settings object it is given.


class TestSettings204C(unittest.TestCase):
    def test_shared_physical_settings(self):
        ps = JESD204BPhysicalSettings(l=2, m=2, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
        settings_c = JESD204CSettings(ps, ts, did=0x5a, bid=0x5)
        settings_b = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
        self.assertEqual(ps.jesdv, 0b001)
        self.assertEqual(settings_c.phy.jesdv, 0b010)
        self.assertEqual(settings_b.phy.jesdv, 0b001)
        # JESDV field of the ILAS configuration data (octet 9, bits 7:5).
        self.assertEqual(settings_b.get_configuration_data()[9] >> 5, 0b001)
        self.assertEqual(settings_c.get_configuration_data()[9] >> 5, 0b010)

if __name__ == "__main__":
    unittest.main()
