#
# This file is part of LiteJESD204 project.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Register appendix of the manual: which designs tools/csr_doc.py elaborates and which register banks
# it documents (the engine is generic, part of the manual kit).
#
# The registers are dumped from an elaboration (no FPGA toolchain, no transceiver): a SoCMini on the
# LiteX-Boards KC705 platform with stand-in PHYs that loop TX to RX, carrying the four control
# modules of the project. The csr.csv/csr.json exports are used; the SVD export of these registers
# fails (the reset value of the `lmfc` field is an expression), so the build does not request it.

import json
import os
import sys
import tempfile

# Configurations: name -> parameters of the reference design below (shown in the appendix table).
CONFIGS = {
    "kc705_stand_in" : ["L=4 M=4 F=2 S=1 K=32 N=N'=16", "E=1 (204C)",
                        "with_lane_status=True (204B RX)"],
}

# Banks documented in the appendix (prefix match on the bank name), in order, with their title and
# the Python class that defines them. The longest matching prefix owns a bank.
BANKS = [
    ("jesd204b_tx", "JESD204B TX control", "LiteJESD204BCoreControl", "litejesd204/core.py"),
    ("jesd204b_rx", "JESD204B RX control", "LiteJESD204BCoreControl", "litejesd204/core.py"),
    ("jesd204c_tx", "JESD204C TX control", "LiteJESD204CCoreControl", "litejesd204/core_204c.py"),
    ("jesd204c_rx", "JESD204C RX control", "LiteJESD204CCoreControl", "litejesd204/core_204c.py"),
]

# Descriptions of the fields declared without one in the gateware (CSRField with `values` only).
# Keys: (group, register, field); a group covers the banks of _DESC_GROUPS. A description declared
# in the gateware takes precedence.
DESCRIPTIONS = {
    ("ctrl", "control", "enable")             : "1: links out of reset, the core runs. 0: links held in reset.",
    ("ctrl", "control", "ilas_check_disable") : "1: the RX links accept an ILAS that differs from the expected one. No effect on a TX core.",
    ("ctrl", "status", "ready")               : "1: every link of the core is synchronized and carries data.",
    ("ctrl", "stpl_enable", "enable")         : "1: the STPL generator (TX) or checker (RX) replaces the converter port.",
}

_DESC_GROUPS = {
    "jesd204b_tx" : "ctrl",
    "jesd204b_rx" : "ctrl",
    "jesd204c_tx" : "ctrl",
    "jesd204c_rx" : "ctrl",
}

# Notes printed after the title of a bank family: what the register descriptions do not say.
NOTES = {
    "jesd204b_tx": [
        "One `LiteJESD204BCoreControl` per core; the bank takes the name of the attribute that",
        "holds it. On a TX core, `sync_n` is the SYNC~ level received from the converter, after",
        "the polarity of `register_jsync`: 0 is a synchronization request. `skew_fifo` and",
        "`stpl_errors` are not driven on TX and read 0; `ilas_check_disable` has no effect.",
        "",
        "The flags and levels cross from the link clock to the system clock through `MultiReg`",
        "synchronizers, bit by bit, so a level read while it changes can be inconsistent; the",
        "32-bit `stpl_errors` crosses with a `BusSynchronizer` handshake and always reads a",
        "value the counter had. The reset value of `lmfc` is the LMFC load of the core, 5 on TX",
        "([TX and RX cores](#cores)).",
    ],
    "jesd204b_rx": [
        "Same class as the TX bank. On an RX core, `sync_n` is the SYNC~ level the core drives",
        "towards the converter, before the polarity of `register_jsync`, and `ready` is updated",
        "at each LMFC zero only. `skew_fifo` is the level of the skew FIFO of lane 0. The",
        "reset value of `lmfc` is the RX load, `lmfc_cycles - 5`: 11 here, with 16 link clocks",
        "per multiframe.",
        "",
        "`skew_levels`, `skew_overflows` and `lane_align` exist only with",
        "`with_lane_status=True`. They report lanes 0 to 3, except `skew_overflows`,",
        "which reports lanes 0 to 7. The sticky flags clear when the lane leaves its data",
        "phase. `stpl_errors` counts the link clock cycles in which at least one sample",
        "differs from the pattern, only while `stpl_enable` is set and the core is ready; it",
        "clears when `stpl_enable` goes from 0 to 1.",
    ],
    "jesd204c_tx": [
        "One `LiteJESD204CCoreControl` per core. A TX control creates the same registers as an",
        "RX control; `skew_fifo`, `lane_status`, `crc_errors`, `emb_debug` and `stpl_errors`",
        "are not driven on TX and read 0. The reset value of `lmfc` is the LEMC load, 5 on TX.",
    ],
    "jesd204c_rx": [
        "`lane_status` and `crc_errors` cover lanes 0 to 7, `emb_debug` lanes 0 to 3.",
        "`crc_errors` adds the CRC-12 errors of every lane; software cannot clear it. Both",
        "32-bit counters cross to the system clock with a `BusSynchronizer` handshake. The",
        "reset value of `lmfc` is the RX LEMC load, `lemc_cycles - 5`: 27 here, with E=1.",
        "`stpl_errors` behaves as on a JESD204B RX core.",
    ],
}

# Opening paragraph of the appendix and the sentence that ends the access paragraph.
INTRO = ["This appendix lists the registers of the control modules of LiteJESD204, one bank per",
         "TX or RX core, JESD204B and JESD204C. It is generated from the register definitions of",
         "the gateware, elaborated on a reference design for the KC705 platform with stand-in",
         "PHYs, without running an FPGA toolchain: the design is elaborated only, never built or",
         "run on hardware. Offsets are in bytes from the base of the bank; the base addresses",
         "depend on the SoC and are in the `csr.csv` of a build. A LiteX SoC names the banks",
         "after the attributes that hold the control modules, `jesd204b_tx`, `jesd204b_rx`,",
         "`jesd204c_tx` and `jesd204c_rx` in this design."]
USAGE = ["Software uses these names through the `csr.csv` or `csr.h` of the build, so it rarely",
         "needs the offsets. The reset value of `lmfc` is given in the notes of each bank."]
MAIN_BANK = "Registers of the top-level `main` bank of the SoC."


def _describe(soc):
    """Attach the descriptions of DESCRIPTIONS to the fields that have none in the gateware."""
    for bank, region in soc.csr.regions.items():
        if not isinstance(region.obj, list):
            continue
        group = _DESC_GROUPS.get(bank)
        if group is None:
            continue
        for csr in region.obj:
            for f in getattr(csr, "fields", None) and csr.fields.fields or []:
                desc = DESCRIPTIONS.get((group, csr.name, f.name))
                if desc and not (f.description or "").strip():
                    f.description = desc


def _reference_soc():
    """Reference design: SoCMini on the KC705 platform, four stand-in lanes per standard, the TX and
    RX cores of JESD204B and JESD204C and their control modules."""
    from migen import Module, Signal, ClockDomain, ClockSignal
    from migen.genlib.io import CRG
    from litex.soc.integration.soc_core import SoCMini
    from litex.soc.interconnect import stream
    from litex_boards.platforms import xilinx_kc705
    from litejesd204.common import JESD204BPhysicalSettings, JESD204BTransportSettings
    from litejesd204.common import JESD204BSettings, JESD204CSettings
    from litejesd204.core import LiteJESD204BCoreTX, LiteJESD204BCoreRX, LiteJESD204BCoreControl
    from litejesd204.core_204c import LiteJESD204CCoreTX, LiteJESD204CCoreRX
    from litejesd204.core_204c import LiteJESD204CCoreControl
    from litejesd204.link_204c import link_204c_layout

    # Stand-in PHYs: the stream contract of the cores, TX looped to RX, no transceiver.
    class StandIn8b10bPHY(Module):
        def __init__(self, n):
            self.n        = n
            self.sink     = stream.Endpoint([("data", 32), ("ctrl", 4)])
            self.source   = stream.Endpoint([("data", 32), ("ctrl", 4)])
            self.rx_align = Signal()
            self.comb += [
                self.sink.ready.eq(1),
                self.source.valid.eq(1),
                self.source.data.eq(self.sink.data),
                self.source.ctrl.eq(self.sink.ctrl),
            ]

    class StandIn64b66bPHY(Module):
        def __init__(self, n):
            self.n       = n
            self.sink    = stream.Endpoint(link_204c_layout())
            self.source  = stream.Endpoint(link_204c_layout())
            self.rx_slip = Signal()
            self.comb += [
                self.sink.ready.eq(1),
                self.source.valid.eq(1),
                self.source.data.eq(self.sink.data),
                self.source.header.eq(self.sink.header),
            ]

    class ReferenceSoC(SoCMini):
        def __init__(self):
            platform     = xilinx_kc705.Platform()
            sys_clk_freq = 125e6
            # Elaboration only: one leg of the differential 200 MHz clock, never built.
            self.crg = CRG(platform.request("clk200").p)
            SoCMini.__init__(self, platform, sys_clk_freq, ident="LiteJESD204 registers")

            # Link clock and PHY clocks: all on the system clock (elaboration only).
            nlanes = 4
            self.cd_jesd = ClockDomain()
            self.comb += self.cd_jesd.clk.eq(ClockSignal())
            for n in range(2*nlanes):
                for d in ["tx", "rx"]:
                    cd = ClockDomain(f"jesd_phy{n}_{d}")
                    setattr(self, f"cd_jesd_phy{n}_{d}", cd)
                    self.comb += cd.clk.eq(ClockSignal())

            transport = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)

            # JESD204B on PHYs 0-3.
            settings_b = JESD204BSettings(JESD204BPhysicalSettings(l=nlanes, m=4, n=16, np=16),
                transport, did=0x5a, bid=0x5)
            phys_b = [StandIn8b10bPHY(n) for n in range(nlanes)]
            for n, p in enumerate(phys_b):
                setattr(self, f"phy_b{n}", p)
            self.jesd204b_tx_core = LiteJESD204BCoreTX(phys_b, settings_b, converter_data_width=32)
            self.jesd204b_rx_core = LiteJESD204BCoreRX(phys_b, settings_b, converter_data_width=32)
            for core in [self.jesd204b_tx_core, self.jesd204b_rx_core]:
                core.register_jsync(Signal())
                core.register_jref(Signal())
            self.jesd204b_tx = LiteJESD204BCoreControl(self.jesd204b_tx_core, sys_clk_freq)
            self.jesd204b_rx = LiteJESD204BCoreControl(self.jesd204b_rx_core, sys_clk_freq,
                with_lane_status=True)

            # JESD204C on PHYs 4-7. Its own physical settings object: JESD204CSettings sets the
            # JESD204 version of the object it receives.
            settings_c = JESD204CSettings(JESD204BPhysicalSettings(l=nlanes, m=4, n=16, np=16),
                transport, did=0x5a, bid=0x5, e=1)
            phys_c = [StandIn64b66bPHY(nlanes + n) for n in range(nlanes)]
            for n, p in enumerate(phys_c):
                setattr(self, f"phy_c{n}", p)
            self.jesd204c_tx_core = LiteJESD204CCoreTX(phys_c, settings_c, converter_data_width=64)
            self.jesd204c_rx_core = LiteJESD204CCoreRX(phys_c, settings_c, converter_data_width=64)
            for core in [self.jesd204c_tx_core, self.jesd204c_rx_core]:
                core.register_jref(Signal())
            self.jesd204c_tx = LiteJESD204CCoreControl(self.jesd204c_tx_core, sys_clk_freq)
            self.jesd204c_rx = LiteJESD204CCoreControl(self.jesd204c_rx_core, sys_clk_freq)

    return ReferenceSoC()


def elaborate(name, repo_root):
    """Elaborate the reference design with a Builder that runs no toolchain; return
    (soc, csr_json, module, argv)."""
    # The LiteJESD204 of this repository, not an installed one.
    sys.path.insert(0, repo_root)
    from litex.soc.integration.builder import Builder
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            soc     = _reference_soc()
            builder = Builder(soc, output_dir=tmp, csr_csv=os.path.join(tmp, "csr.csv"),
                csr_json=os.path.join(tmp, "csr.json"), compile_software=False,
                compile_gateware=False)
            builder.build(run=False)
            csr_json = json.load(open(os.path.join(tmp, "csr.json")))
        finally:
            os.chdir(old_cwd)
    # Memories mapped on the CSR bus have no register definitions: keep the register banks only.
    for bank, region in list(soc.csr.regions.items()):
        if not isinstance(region.obj, list):
            del soc.csr.regions[bank]
    _describe(soc)
    return soc, csr_json, "xilinx_kc705", CONFIGS[name]
