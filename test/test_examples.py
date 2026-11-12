#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import os
import tempfile
import unittest
import importlib.util

# Examples: elaborate the designs to Verilog (no vendor tools needed).

examples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")


def load_example(name):
    spec   = importlib.util.spec_from_file_location(name, os.path.join(examples_dir, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestExamples(unittest.TestCase):
    def test_kc705_gtx(self):
        try:
            example = load_example("kc705_gtx")
        except ImportError as e:
            self.skipTest(f"Missing dependency: {e}")
        from litex.soc.integration.builder import Builder
        platform = example.xilinx_kc705.Platform()
        soc      = example.JESD204BSoC(platform)
        with tempfile.TemporaryDirectory() as output_dir:
            csr_csv = os.path.join(output_dir, "csr.csv")
            builder = Builder(soc, output_dir=output_dir, csr_csv=csr_csv, compile_software=False)
            builder.build(run=False)
            verilog = os.path.join(output_dir, "gateware", platform.name + ".v")
            self.assertTrue(os.path.exists(verilog))
            with open(csr_csv) as f:
                csrs = f.read()
            for name in ["jesd_tx_control_control", "jesd_rx_control_status", "jesd_rx_control_stpl_errors"]:
                self.assertIn(name, csrs)

if __name__ == "__main__":
    unittest.main()
