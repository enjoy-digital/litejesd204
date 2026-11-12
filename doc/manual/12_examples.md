# Examples and boards {#examples}

This chapter lists the designs to start from: the simulations of the repository, the integration
designs of this manual, the example design of the repository and the earlier public examples. It
ends with the boards of LiteX-Boards that have converter pins.

## At a glance {#ex-glance}

| Example | Where | Standard | Hardware |
|-------------------------|---------------------------------------|----------|--------------------|
| Core loopback | `test/test_core.py` | 204B | None, simulation |
| Core loopback | `test/test_core_204c.py` | 204C | None, simulation |
| Link datapath loopback | `test/test_link.py` | 204B | None, simulation |
| KC705 GTX loopback | `examples/kc705_gtx.py` ([below](#ex-kc705-gtx)) | 204B | KC705, GTX on SFP |
| KC705 converter card design | [Integration](#integration) | 204B | KC705, GTX |
| AD937x design on 7-Series | [This chapter](#ex-ad937x) | 204B | 7-Series GTX or GTP |
| AD9154 settings | `MEMO` | 204B | KC705 or KCU105, AD9154 card |

The simulations run with the test suite ([Getting started](#getting-started)), which also
elaborates `examples/kc705_gtx.py`. The LiteX designs were elaborated to Verilog for this manual
but not built into a bitstream. The hardware status of each standard and family is in the
[status table](#intro-status).

## Simulations {#ex-sim}

The core loopbacks are the most complete simulations of the repository. Each builds a TX core and
an RX core with two lanes, loops them through stand-in PHYs, and checks the test pattern and the
latency of a ramp. The JESD204C one has four converters, E = 1 and E = 2; the JESD204B one has two
converters, F = 2 and F = 4, with SYNC~ from the RX core to the TX core, CGS and ILAS.
[Run a core loopback](#gs-loopback) prints what the JESD204C one records.

`test_link_loopback` connects a TX link datapath to an RX link datapath, four octets per clock,
and `test_transport_loopback` the TX and RX transport layers; the tests are listed in
[Simulation and tests](#simulation).

## KC705 GTX loopback {#ex-kc705-gtx}

`examples/kc705_gtx.py` is a complete JESD204B design without a converter: a TX core and an RX
core on one GTX transceiver of the KC705 SFP cage, TX looped back to RX through an SFP loopback
module or a fiber. The core controls and the GTX controls (PRBS, polarity, near-end loopback) are
reached over a UART bridge.

| Item | Value |
|-----------------------|------------------------------------------------------------|
| Mode | L = 1, M = 1, N = N' = 16, F = 2, S = 1, K = 32 |
| Line rate | 5 Gbps by default (`--linerate`), 125 MHz SGMII reference clock |
| PHY | LiteICLink `GTX`, 40-bit interface, TX and RX buffers on |
| `jesd` clock | The GTX TX user clock, line rate / 40 |
| SYSREF | Periodic pulse made in the `jesd` domain, every 8 multiframes |
| SYNC~ | The RX core drives the TX core |
| Samples | Ramp on converter 0 when the STPL is off |
| LEDs | TX `ready`, RX `ready`, SYNC~ |

Without arguments, the script writes the Verilog, the constraints and `csr.csv` to
`build/xilinx_kc705`, without vendor tools; `--build` runs Vivado and `--load` loads the
bitstream. Its header gives the `litex_cli` writes that enable both cores in STPL mode. The design
is elaborated by the test suite (`test/test_examples.py`) and has not been run on hardware.

In a converter design, the `jesd` clock comes from the clock chip, SYSREF and SYNC~ from and to
pads, as in [Integration](#integration).

## AD937x design on 7-Series {#ex-ad937x}

A public integration example of the core, a gist linked from the issues of the repository
(<https://gist.github.com/enjoy-digital/cd9ea52fafaebe016e739a90983eb237>), targets an AD937x
converter device (an RF transceiver) on a 7-Series FPGA, with GTX or GTP transceivers.

It supports two modes of the converter, both with four converters of 16 bits (the I and Q of two
channels) and a 122.88 MHz reference clock:

| Mode | L | M | F | K | Line rate | Link clock |
|--------------|----|----|----|----|-------------|--------------|
| Four lanes | 4 | 4 | 2 | 32 | 2.4576 Gbps | 61.44 MHz |
| Two lanes | 2 | 4 | 4 | 32 | 4.9152 Gbps | 122.88 MHz |

The link clocks are the line rates divided by 40 (computed). The two-lane mode has M different
from L, a mode in which the core sizes the LMFC wrong ([Known issues](#debug-known-issues)): use
the four-lane mode.

The example uses old import paths. The table below gives their replacements; the classes and
their arguments are unchanged.

| In the example | Replacement |
|----------------------------------|----------------------------------|
| `liteiclink.transceiver` | `liteiclink.serdes` |
| `litejesd204b` | `litejesd204` |
| `reduce(and_, ...)` | `Reduce("AND", ...)` |

The module names below these packages, such as `gtx_7series` or `core`, are unchanged.

### Clocking {#ex-ad937x-clocking}

The design takes both of its clocks from the reference clock of the converter, as the figure
below shows. The transceiver input buffer passes the reference clock to the quad PLL and, divided
by two, to an MMCM. The MMCM makes the `jesd` clock.

![Clocking of the 7-Series example. One reference clock feeds the quad PLL of the transceivers
and, through the ODIV2 output of IBUFDS_GTE2, the MMCM of the jesd clock. Follow the cyan clocks
into the cores: the PHY user clocks and jesd are frequency-locked.](ex_clocking.svg)

The example runs the transceivers with `data_width=20`. Their user clock is then twice the
`jesd` clock, and the cores cross through an asynchronous FIFO whose latency is not fixed by
design ([Architecture](#architecture)). The original design makes two
link clocks with one MMCM and selects one at run time with a `BUFGMUX` driven by a register.

### Elaborating the four-lane mode {#ex-ad937x-elab}

The four-lane mode is the design of [Integration](#integration) with other arguments: 20-bit
PHYs, 2.4576 Gbps lanes and a 122.88 MHz reference clock. Only the pins differ on an AD937x
card.

```python
soc = JESDSoC(nlanes=4, data_width=20, linerate=2.4576e9, refclk_freq=122.88e6)
```

For this manual, the elaboration of this variant on the KC705 platform printed the following
configuration of the quad PLL and of the MMCM (extracts):

```console
INFO:S7MMCM:Registering Single Ended ClkIn of 61.44MHz.
INFO:S7MMCM:Creating ClkOut0 jesd of 61.44MHz (+-10000.00ppm).
[...]
    CLKIN    = 122.88MHz
    CLKOUT   = CLKIN x N / (2 x M) = 122.88MHz x 80 / (2 x 1)
             = 4.9152GHz
    VCO      = 9.8304GHz (upper)
    LINERATE = CLKOUT x 2 / D = 4.9152GHz x 2 / 4
             = 2.4576GHz
```

For the two-lane mode, `GTXQuadPLL.compute_config()` returns the same VCO frequency with D = 2
instead of 4: only the output divider of the quad PLL changes between the modes.
The MMCM takes half the reference clock, 61.44 MHz, and outputs the `jesd` clock at the same
frequency for the four-lane mode.

### Other parts of the example {#ex-ad937x-other}

The example has three more features worth reusing:

- **Lane order.** Two lists, one for TX and one for RX, give the order of the PHYs for each core,
  as in [Lanes and several converters](#integ-lanes).
- **PHY selection.** A dictionary picks `GTXQuadPLL` and `GTX` or `GTPQuadPLL` and `GTP`; both
  have the same constructor arguments.
- **Link status.** A signal combines `enable` and `jsync` of both cores, for a LED or a status
  register.

## AD9154 settings {#ex-ad9154}

An early design of the core drove an AD9154 DAC card from a KC705. The repository history of 2016
holds its KC705 platform, with transceivers that were then part of the core, before LiteICLink;
that code is not on the default branch.

The `MEMO` file of the repository keeps the AD9154 settings of that work, listed below.

| Parameter | AD9154 setting |
|----------------|-------------------------------------------------|
| M | 4 |
| L | 4 on the KC705, 8 on the KCU105 |
| S | 1 |
| F | 2 |
| K | 16 or 32 |
| CF | Always 0 on these devices |
| Control bits | Not supported |
| HD | Must be 1 when F = 1 |

F = 2 holds for L = 4. With L = 8, F = M x S x N' / (8 x L) is 1 and HD must be 1, which
LiteJESD204 does not send: HD is always 0.

## Boards {#ex-boards}

No LiteX-Boards target instantiates the core; `examples/kc705_gtx.py` is the board design of the
repository. The boards in the examples above, the KC705 and
the KCU105, have transceivers on their FMC connectors; the converter card brings the converter,
its clock chip and the pins of SYSREF and SYNC~.

One LiteX-Boards platform defines JESD204 pads for its converters: `adi_adrv2crr_fmc`, a carrier
with a Zynq UltraScale+ device and two RF transceivers (the `talise_` pads). Its LiteX-Boards
target builds a SoC with DDR4 and PCIe but does not use the converter pads. The pads, listed
below, follow the names a design passes to `platform.request()`.

| Pad | Indices | Content |
|----------------------|----------------|--------------------------------------------------|
| `talise_refclk` | 0, 1 | Reference clock of each transceiver |
| `talise_sysref` | 0, 1 | SYSREF of each transceiver, LVDS |
| `talise_sync_tx` | 0, 1 and 2, 3 | Two SYNC~ per transceiver, terminated in the FPGA |
| `talise_sync_rx` | 0, 1 and 2, 3 | Two SYNC~ per transceiver, from the FPGA |
| `talise_jesd_tx` | 0-3 and 4-7 | Four lanes to each transceiver |
| `talise_jesd_rx` | 0-3 and 4-7 | Four lanes from each transceiver |

A design for this platform follows [Integration](#integration) with UltraScale+ transceivers from
LiteICLink ([PHYs: LiteICLink transceivers](#phys)), one TX core and one RX core per RF
transceiver.

Where to go next: [Integration](#integration) for the steps of a design, [Debugging](#debugging)
for the bring-up on a board.
