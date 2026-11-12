#!/usr/bin/env python3

#
# This file is part of LiteJESD204
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

# JESD204B example on KC705: LiteICLink GTX transceiver on the SFP cage (125 MHz SGMII reference
# clock), LiteJESD204BCoreTX looped back to LiteJESD204BCoreRX through the SFP (loopback module or
# fiber), with the core controls and the GTX controls (PRBS, polarity, near-end loopback) reachable
# over a UART bridge (litex_server --uart).
#
# Without a converter, the example generates what a converter design gets from its clock chip and
# from the converter: the device clock ("jesd" domain) is the GTX TX user clock (line rate/40),
# SYSREF is a periodic pulse generated in the "jesd" domain and the RX SYNC~ drives the TX SYNC~.
# In a converter design, the "jesd" clock comes from the clock chip (frequency-locked to the
# transceiver reference clock), SYSREF and SYNC~ from/to pads (register_jref/register_jsync).
#
# Generate the gateware without vendor tools (Verilog, constraints, csr.csv):
#   ./kc705_gtx.py
# Build/load the bitstream (Vivado):
#   ./kc705_gtx.py --build --load
# Then, with litex_server --uart --uart-port=/dev/ttyUSBX running, enable the cores in STPL mode:
#   litex_cli --write jesd_tx_control_stpl_enable 1
#   litex_cli --write jesd_rx_control_stpl_enable 1
#   litex_cli --write jesd_tx_control_control 1
#   litex_cli --write jesd_rx_control_control 1
#   litex_cli --regs   # jesd_rx_control_status ready bit, jesd_rx_control_stpl_errors.
#
# Elaboration only: not run on hardware.

import os
import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *

from litex_boards.platforms import xilinx_kc705

from litex.soc.cores.clock import S7PLL
from litex.soc.integration.soc_core import SoCMini
from litex.soc.integration.builder import Builder

from liteiclink.serdes.gtx_7series import GTXQuadPLL, GTX

from litejesd204.common import *
from litejesd204.core import LiteJESD204BCoreTX, LiteJESD204BCoreRX, LiteJESD204BCoreControl

# CRG ----------------------------------------------------------------------------------------------

class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq):
        self.rst    = Signal()
        self.cd_sys = ClockDomain()

        # # #

        self.pll = pll = S7PLL(speedgrade=-2)
        self.comb += pll.reset.eq(platform.request("cpu_reset") | self.rst)
        pll.register_clkin(platform.request("clk200"), 200e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin)

# JESD204B SoC -------------------------------------------------------------------------------------

class JESD204BSoC(SoCMini):
    def __init__(self, platform, sys_clk_freq=125e6, linerate=5e9, with_uartbone=True):
        refclk_freq = 125e6

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, sys_clk_freq, ident="LiteJESD204 example on KC705")

        # CRG --------------------------------------------------------------------------------------
        self.crg = _CRG(platform, sys_clk_freq)

        # UARTBone ---------------------------------------------------------------------------------
        if with_uartbone:
            self.add_uartbone()

        # JESD Settings ----------------------------------------------------------------------------
        # 1 lane / 1 converter / 16-bit samples: F=2, K=32 (LMFC = F*K/4 = 16 link clocks).
        ps = JESD204BPhysicalSettings(l=1, m=1, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
        jesd_settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)

        # JESD PHY (GTX on SFP) --------------------------------------------------------------------
        refclk      = Signal()
        refclk_pads = platform.request("sgmii_clock")
        self.specials += Instance("IBUFDS_GTE2",
            i_CEB = 0,
            i_I   = refclk_pads.p,
            i_IB  = refclk_pads.n,
            o_O   = refclk,
        )
        self.jesd_pll = jesd_pll = GTXQuadPLL(refclk, refclk_freq, linerate)

        # 40-bit GTX interface: 32-bit data + 4-bit ctrl per link clock (line rate/40), elastic
        # buffer (fixed latency) clock domain crossings in the cores.
        self.jesd_phy0 = jesd_phy = GTX(jesd_pll,
            tx_pads          = platform.request("sfp_tx"),
            rx_pads          = platform.request("sfp_rx"),
            sys_clk_freq     = sys_clk_freq,
            data_width       = 40,
            clock_aligner    = False, # Comma alignment driven by the JESD RX core (rx_align).
            tx_buffer_enable = True,
            rx_buffer_enable = True,
        )
        jesd_phy.add_stream_endpoints()
        jesd_phy.add_controls()
        jesd_phy.n = 0
        self.comb += platform.request("sfp_tx_disable_n").eq(1)

        # PHY clock domains expected by the cores: jesd_phy{n}_tx/rx.
        self.cd_jesd_phy0_tx = ClockDomain()
        self.cd_jesd_phy0_rx = ClockDomain()
        self.comb += [
            self.cd_jesd_phy0_tx.clk.eq(jesd_phy.cd_tx.clk),
            self.cd_jesd_phy0_tx.rst.eq(jesd_phy.cd_tx.rst),
            self.cd_jesd_phy0_rx.clk.eq(jesd_phy.cd_rx.clk),
            self.cd_jesd_phy0_rx.rst.eq(jesd_phy.cd_rx.rst),
        ]
        platform.add_period_constraint(jesd_phy.cd_tx.clk, 1e9/jesd_phy.tx_clk_freq)
        platform.add_period_constraint(jesd_phy.cd_rx.clk, 1e9/jesd_phy.rx_clk_freq)

        # JESD Device Clock ------------------------------------------------------------------------
        # GTX TX user clock (line rate/40) as device clock stand-in, reset until the PHY is ready.
        self.cd_jesd = ClockDomain()
        self.comb += self.cd_jesd.clk.eq(jesd_phy.cd_tx.clk)
        self.specials += AsyncResetSynchronizer(self.cd_jesd, ~(jesd_phy.tx_init.done & jesd_phy.rx_init.done))
        platform.add_false_path_constraints(self.crg.cd_sys.clk, jesd_phy.cd_tx.clk, jesd_phy.cd_rx.clk)

        # JESD SYSREF ------------------------------------------------------------------------------
        # Periodic SYSREF, period a multiple of the LMFC period (here 8 LMFC periods).
        sysref_period = 8*jesd_settings.lmfc_cycles
        sysref        = Signal()
        sysref_count  = Signal(max=sysref_period)
        self.sync.jesd += [
            sysref_count.eq(sysref_count + 1),
            If(sysref_count == (sysref_period - 1),
                sysref_count.eq(0),
            ),
            sysref.eq(sysref_count < 4),
        ]

        # JESD TX/RX Cores -------------------------------------------------------------------------
        # Converter data width: 2 samples (16-bit) per link clock and converter.
        converter_data_width = 32
        jsync = Signal()

        self.jesd_tx = LiteJESD204BCoreTX([jesd_phy], jesd_settings, converter_data_width)
        self.jesd_tx.register_jsync(jsync)
        self.jesd_tx.register_jref(sysref)
        self.jesd_tx_control = LiteJESD204BCoreControl(self.jesd_tx, sys_clk_freq)

        self.jesd_rx = LiteJESD204BCoreRX([jesd_phy], jesd_settings, converter_data_width)
        self.jesd_rx.register_jsync(jsync)
        self.jesd_rx.register_jref(sysref)
        self.jesd_rx_control = LiteJESD204BCoreControl(self.jesd_rx, sys_clk_freq, with_lane_status=True)

        # TX data: ramp on converter 0 (when STPL is disabled), 2 samples per link clock.
        ramp0 = Signal(16)
        ramp1 = Signal(16)
        self.sync.jesd += ramp0.eq(ramp0 + 2)
        self.comb += [
            ramp1.eq(ramp0 + 1),
            self.jesd_tx.sink.converter0.eq(Cat(ramp0, ramp1)),
        ]

        # Leds: TX ready, RX ready, SYNC~.
        self.comb += [
            platform.request("user_led", 0).eq(self.jesd_tx.ready),
            platform.request("user_led", 1).eq(self.jesd_rx.ready),
            platform.request("user_led", 2).eq(jsync),
        ]

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteJESD204 JESD204B example on KC705 (GTX on SFP).")
    parser.add_argument("--build",      action="store_true", help="Build bitstream (Vivado).")
    parser.add_argument("--load",       action="store_true", help="Load bitstream (to SRAM).")
    parser.add_argument("--linerate",   default="5e9",       help="Line rate (default: 5e9).")
    parser.add_argument("--output-dir", default=None,        help="Build directory.")
    args = parser.parse_args()

    platform   = xilinx_kc705.Platform()
    soc        = JESD204BSoC(platform, linerate=float(args.linerate))
    output_dir = args.output_dir or os.path.join("build", platform.name)
    builder    = Builder(soc, output_dir=output_dir, csr_csv=os.path.join(output_dir, "csr.csv"))
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))

if __name__ == "__main__":
    main()
