# Integration {#integration}

This chapter builds a LiteX SoC around a JESD204B TX core and RX core with LiteICLink
transceivers, step by step, then brings the link up from software. Read it when you put the core
on a board. [Architecture](#architecture) and [TX and RX cores](#cores) describe the parts used
here.

## At a glance {#integ-glance}

The table below lists the parts a design adds around the cores, in the order of this chapter.

| Step | What the design adds | Classes and methods |
|----------------|----------------------------------|----------------------------------|
| 1. Settings | Link parameters of the converter | `JESD204BSettings` |
| 2. Clocks | Reference clock and `jesd` clock | `S7MMCM` |
| 3. PHYs | One transceiver per lane | `GTXQuadPLL`, `GTX` |
| 4. Reset | `jesd` reset until the PHYs are ready | `AsyncResetSynchronizer` |
| 5. Cores | Cores, SYSREF and SYNC~ pads | `register_jref` |
| 6. Registers | Control modules, a bridge to the host | `LiteJESD204BCoreControl` |
| 7. Build | Verilog, constraints, bitstream | `Builder` |

## The example design {#integ-design}

The example of this chapter is a KC705 board with a converter card on its HPC FMC connector, as
the figure below shows. Four GTX transceivers carry four lanes at 5 Gbps from a 125 MHz reference
clock. The clock chip of the card also gives SYSREF; the `jesd` clock is made from the reference
clock.

![The example design. Follow the cyan lanes between the GTX PHYs and the converter. The clock
chip of the converter card gives the reference clock, which feeds the quad PLL of the transceivers
and, divided by two, the MMCM of the jesd clock, and SYSREF. SYNC~ runs from the DAC to the TX core
and from the RX core to the ADC; the host reaches the registers through a UART
bridge.](integ_soc.svg)

The design below was elaborated to Verilog with LiteX, LiteICLink and LiteX-Boards from their
default branches, without Vivado ([Build](#integ-build)). It has not been built into a bitstream
or run on a board for this manual. The pins of the converter card are placeholders: take them
from the schematic of your card. For a design that builds as is, without a converter card,
`examples/kc705_gtx.py` loops one GTX lane on the SFP cage from TX to RX
([Examples and boards](#examples)).

```python
_jesd_io = [
    ("jesd_refclk", 0,
        Subsignal("p", Pins("HPC:GBTCLK0_M2C_P")),
        Subsignal("n", Pins("HPC:GBTCLK0_M2C_N")),
    ),
    ("jesd_sysref", 0,
        Subsignal("p", Pins("HPC:LA00_CC_P")),
        Subsignal("n", Pins("HPC:LA00_CC_N")),
        IOStandard("LVDS_25"),
    ),
    ("jesd_sync_tx", 0,
        Subsignal("p", Pins("HPC:LA01_CC_P")),
        Subsignal("n", Pins("HPC:LA01_CC_N")),
        IOStandard("LVDS_25"),
    ),
    ("jesd_sync_rx", 0,
        Subsignal("p", Pins("HPC:LA02_P")),
        Subsignal("n", Pins("HPC:LA02_N")),
        IOStandard("LVDS_25"),
    ),
]
for i in range(4):
    _jesd_io += [
        ("jesd_tx", i,
            Subsignal("p", Pins(f"HPC:DP{i}_C2M_P")),
            Subsignal("n", Pins(f"HPC:DP{i}_C2M_N")),
        ),
        ("jesd_rx", i,
            Subsignal("p", Pins(f"HPC:DP{i}_M2C_P")),
            Subsignal("n", Pins(f"HPC:DP{i}_M2C_N")),
        ),
    ]
```

The SoC itself is a `SoCMini` with no CPU and a UART bridge to the host. It imports the
following modules:

```python
from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *
from litex.build.generic_platform import Subsignal, Pins, IOStandard
from litex.build.io import DifferentialInput
from litex.soc.cores.clock import S7PLL, S7MMCM
from litex.soc.integration.soc_core import SoCMini
from litex.soc.integration.builder import Builder

from litex_boards.platforms import xilinx_kc705

from liteiclink.serdes.gtx_7series import GTXQuadPLL, GTX

from litejesd204.common import *
from litejesd204.core import LiteJESD204BCoreTX, LiteJESD204BCoreRX, LiteJESD204BCoreControl
```

The system clock comes from a PLL on the 200 MHz oscillator of the board. The steps below fill
the constructor of the SoC.

```python
class CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq):
        self.cd_sys = ClockDomain()
        self.pll = pll = S7PLL(speedgrade=-2)
        pll.register_clkin(platform.request("clk200"), 200e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)

class JESDSoC(SoCMini):
    def __init__(self, nlanes=4, data_width=40, linerate=5e9, refclk_freq=125e6):
        platform     = xilinx_kc705.Platform()
        platform.add_extension(_jesd_io)
        sys_clk_freq = 125e6
        self.crg     = CRG(platform, sys_clk_freq)
        SoCMini.__init__(self, platform, sys_clk_freq, ident="LiteJESD204 KC705 example")
        self.add_uartbone() # Register access from the host (litex_server --uart).
```

## Step 1: settings {#integ-settings}

The link parameters come from the datasheet of the converter, for the mode it is configured in.
The example uses four converters of 16 bits on four lanes, one sample per converter per frame:
L = 4, M = 4, N = N' = 16, S = 1, which gives F = 2. K = 32 frames per multiframe.

```python
ps       = JESD204BPhysicalSettings(l=nlanes, m=4, n=16, np=16)
ts       = JESD204BTransportSettings(f=8//nlanes, s=1, k=32, cs=0)
settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
```

The example is written for four lanes. The `nlanes` argument only serves the variant of
[Examples and boards](#ex-ad937x-elab), which keeps four lanes: other values give M different from
L or lanes that are not 32 bits wide ([Known issues](#debug-known-issues)).

`did` and `bid` are the device and bank identifiers sent in the configuration data; set them to
the values the converter expects. With these settings, the LMFC period is 16 link clock cycles.
The line rate fixes the link clock: 5 Gbps divided by 40 gives 125 MHz (computed). The settings
and the values they derive are described in [Architecture](#architecture).

When M and L differ, the core sizes the LMFC and the framer from the octets of one converter, not
from F. Such modes are a known issue of the core ([Known issues](#debug-known-issues)); the
example keeps M = L.

## Step 2: clocks {#integ-clocks}

The design needs two clocks: the reference clock of the transceivers and the `jesd` clock. Both
must come from the same clock chip, so that they are frequency-locked, as the elastic buffers of
the cores require. The example takes the reference clock through `IBUFDS_GTE2` and feeds its
divided output, `ODIV2`, to an MMCM.

```python
refclk_pads = platform.request("jesd_refclk")
refclk      = Signal()
refclk_div2 = Signal()
self.specials += Instance("IBUFDS_GTE2",
    i_CEB   = 0,
    i_I     = refclk_pads.p,
    i_IB    = refclk_pads.n,
    o_O     = refclk,
    o_ODIV2 = refclk_div2,
)
platform.add_period_constraint(refclk_div2, 1e9/(refclk_freq/2))
self.cd_jesd = ClockDomain()
self.jesd_mmcm = mmcm = S7MMCM(speedgrade=-2)
mmcm.register_clkin(refclk_div2, refclk_freq/2)
mmcm.create_clkout(self.cd_jesd, linerate/40, with_reset=False)
```

The MMCM makes the `jesd` clock at the line rate divided by 40, 125 MHz here. Its reset is left
to the next steps. A board whose clock chip outputs the device clock on a separate pin can drive
`jesd` from that pin instead, through a global clock buffer.

## Step 3: PHYs {#integ-phys}

Each lane gets one GTX transceiver, all driven by one quad PLL. The loop below builds them and
names them `jesd_phy0` to `jesd_phy3`, which sets the names of their registers.

```python
self.jesd_pll = pll = GTXQuadPLL(refclk, refclk_freq, linerate)
print(pll)
phys = []
for i in range(nlanes):
    phy = GTX(pll,
        tx_pads          = platform.request("jesd_tx", i),
        rx_pads          = platform.request("jesd_rx", i),
        sys_clk_freq     = sys_clk_freq,
        data_width       = data_width,
        clock_aligner    = False,
        tx_buffer_enable = True,
        rx_buffer_enable = True)
    phy.add_stream_endpoints()
    phy.add_controls(auto_enable=False)
    phy.n = i
    setattr(self, f"jesd_phy{i}", phy)
    platform.add_period_constraint(phy.cd_tx.clk, 1e9/phy.tx_clk_freq)
    platform.add_period_constraint(phy.cd_rx.clk, 1e9/phy.rx_clk_freq)
    platform.add_false_path_constraints(
        self.crg.cd_sys.clk, self.cd_jesd.clk, phy.cd_tx.clk, phy.cd_rx.clk)
    phys.append(phy)
```

The parameters of the PHYs matter for the core, as the table below shows.

| Parameter | Value | Why |
|--------------------------|------------|--------------------------------------------|
| `data_width` | 40 | 32-bit words: fixed-latency elastic buffer |
| `clock_aligner` | `False` | The RX core drives the comma alignment itself |
| `tx_buffer_enable` | `True` | Transceiver buffers, as in the public examples |
| `rx_buffer_enable` | `True` | The RX comma alignment needs the buffer |
| `n` | Lane index | Tells the cores the names of its domains |

The two calls after the constructor complete each PHY. `add_stream_endpoints()` creates the
`sink` and `source` streams the cores connect to. `add_controls()` adds the PHY registers;
with `auto_enable=False`, the transceivers stay disabled until software enables them.

With `data_width=40`, the PHY user clock equals the `jesd` clock, 125 MHz here. With 20, it runs
at twice the `jesd` clock and the cores cross through an asynchronous FIFO, whose latency is not
fixed by design ([Architecture](#architecture)). The choice of transceiver, PLL and buffers is
covered in [PHYs: LiteICLink transceivers](#phys).

`print(pll)` shows the configuration the quad PLL takes. For this example, the elaboration
printed, after a drawing of the PLL:

```console
  config:
  -------
    CLKIN    = 125.0MHz
    CLKOUT   = CLKIN x N / (2 x M) = 125.0MHz x 80 / (2 x 1)
             = 5.0GHz
    VCO      = 10.0GHz (upper)
    LINERATE = CLKOUT x 2 / D = 5.0GHz x 2 / 2
             = 5.0GHz
```

### The PHY clock domains {#integ-domains}

Each GTX creates two clock domains, its `cd_tx` and `cd_rx` attributes. The cores drive their
side of each lane crossing from them, clock and reset, so the design names no clock domain for
the PHYs: the loop above is enough with one lane as with several
([Clock domains](#phys-domains)).

## Step 4: reset {#integ-reset}

The `jesd` domain stays in reset until the MMCM is locked and every transceiver has completed
its initialization. The cores then start from a known state each time the PHYs come up.

```python
tx_init_done = Reduce("AND", [phy.tx_init.done for phy in phys])
rx_init_done = Reduce("AND", [phy.rx_init.done for phy in phys])
self.specials += AsyncResetSynchronizer(self.cd_jesd,
    ~(tx_init_done & rx_init_done) | ~mmcm.locked)
```

The links have a second reset: the `enable` of each core, driven by its `control` register
([Bring-up from software](#integ-software)).

## Step 5: cores, SYSREF and SYNC~ {#integ-cores}

The cores take the list of PHYs in lane order, the settings and the width of each converter word
on the user side. SYSREF enters through a differential input buffer and goes to both cores. Each
core gets its SYNC~ pads.

```python
sysref      = Signal()
sysref_pads = platform.request("jesd_sysref")
self.specials += DifferentialInput(sysref_pads.p, sysref_pads.n, sysref)

cdw = 32*nlanes//4 # converter_data_width: 32 lane bits x L / M.
self.jesd_tx = LiteJESD204BCoreTX(phys, settings, converter_data_width=cdw)
self.jesd_tx.register_jsync(platform.request("jesd_sync_tx"))
self.jesd_tx.register_jref(sysref)

self.jesd_rx = LiteJESD204BCoreRX(phys, settings, converter_data_width=cdw)
self.jesd_rx.register_jsync(platform.request("jesd_sync_rx"))
self.jesd_rx.register_jref(sysref)
```

Each lane carries 32 bits per link clock, so the M converters share 32 x L bits per cycle. The
example gives 32 bits to each converter, two 16-bit samples per cycle.

`converter_data_width` must be exactly 32 x L / M x N / N', 32 here. Any other value fails at
construction: the transport layer asserts a non-zero multiple of N, and the core asserts 32-bit
lanes with a message that gives the value that fits.

The user logic reads the samples on `self.jesd_rx.source` and writes them on
`self.jesd_tx.sink`, in the `jesd` domain. Both are records with one field per converter,
`converter0` to `converter3`.

`register_jsync` and `register_jref` accept a `Signal` or a differential pad record. The TX core
reads SYNC~ from the DAC; the RX core drives it to the ADC. A board that inverts SYNC~ passes
`polarity=1`. A core that misses one of the two calls fails at finalization.

## Step 6: registers {#integ-registers}

A control module per core gives software its enable, its status and its test pattern registers.
The RX module of the example also exposes the per-lane status.

```python
self.jesd_tx_control = LiteJESD204BCoreControl(self.jesd_tx)
self.jesd_rx_control = LiteJESD204BCoreControl(self.jesd_rx, with_lane_status=True)
```

The register names start with the name of the module: `jesd_tx_control_control`,
`jesd_rx_control_status`. The PHY registers start with `jesd_phy0` to `jesd_phy3`. The control
module also accepts a `sys_clk_freq` argument, optional and unused, for older designs.
[Register reference](#registers) lists every field.

## Step 7: build {#integ-build}

A LiteX `Builder` writes the Verilog, the constraints and the register map, then runs the vendor
tool. With `build(run=False)`, it stops before Vivado, which is how this example was checked:

```python
soc = JESDSoC()
Builder(soc, output_dir="build/kc705_jesd", csr_csv="build/kc705_jesd/csr.csv",
    compile_software=False).build(run=False)
```

The elaboration of this manual wrote `xilinx_kc705.v`, `xilinx_kc705.xdc` and the Vivado script
in the `gateware` directory, and the register map in `csr.csv`. It printed one warning, on the
scrambler of the first JESD204B TX link layer (cut here):

```console
RuntimeWarning: Combinatorial cycle detected: [...]_scrambler_feedback ->
[...]_scrambler_full -> [...]_scrambler_feedback.
```

The loop is between bits of the same signals in the scrambler, not a real combinational loop:
each bit depends on other bits of the same vector. LiteX reports the first such loop of a design
only; a JESD204C design reports the same kind of warning on the CRC-12 of a link.

`build()` without `run=False` runs Vivado and produces the bitstream.

## Bring-up from software {#integ-software}

Once the board is loaded, software brings the link up in the order of the figure below. The
converter card is configured first, then the transceivers, then the link.

![Bring-up order. The grey steps act on the converter card, outside the core; the cyan steps
write and read the registers of the PHYs and of the cores.](integ_bringup.svg)

The steps are:

1. **Clock chip and converter.** Configure them through their own control interface, with the
   mode of [Step 1](#integ-settings): the core does not do it.
2. **PHYs.** Write 1 to `tx_enable` and `rx_enable` of each PHY, then wait for `tx_ready` and
   `rx_ready`. The `jesd` domain leaves reset when all of them are ready.
3. **SYSREF.** Send SYSREF before enabling the cores, so that the LMFC of each core starts in
   phase with the one of the converter. A periodic SYSREF keeps them in phase.
4. **Cores.** Write 1 to the `enable` field of `control` in both modules. The RX core asks the
   ADC for synchronization; the TX core waits for the SYNC~ of the DAC.
5. **Link.** Wait for `ready` in `status`. In JESD204B, `sync_n` reads 1 once code group
   synchronization is complete.
6. **Test pattern.** Set `stpl_enable` on both sides of a link, put the converter in its matching
   test mode, and read `stpl_errors`: it clears when `stpl_enable` is set and stays 0 on a link
   without error.

The script below runs these register steps from a host, through `litex_server --uart`. It was
written against the register map of the example and has not been run on a board for this
manual; the converter steps are left as comments.

```python
import time
from litex import RemoteClient

bus = RemoteClient(csr_csv="build/kc705_jesd/csr.csv")
bus.open()
phys = [f"jesd_phy{i}" for i in range(4)]

# Clock chip and converter: through their own interface (not shown).

# PHYs: enable, then wait for the initialization.
for phy in phys:
    getattr(bus.regs, f"{phy}_tx_enable").write(1)
    getattr(bus.regs, f"{phy}_rx_enable").write(1)
for phy in phys:
    for reg in ["tx_ready", "rx_ready"]:
        while getattr(bus.regs, f"{phy}_{reg}").read() == 0:
            time.sleep(0.01)

# SYSREF: from the clock chip (not shown).

# Cores: enable (bit 0 of control), then wait for ready (bit 0 of status).
bus.regs.jesd_tx_control_control.write(1)
bus.regs.jesd_rx_control_control.write(1)
for core in ["jesd_tx_control", "jesd_rx_control"]:
    status = getattr(bus.regs, f"{core}_status")
    while (status.read() & 0b1) == 0:
        time.sleep(0.01)
    print(core, "status:", hex(status.read()))

bus.close()
```

The fields of the registers used above are listed below; [Register reference](#registers) has
all of them.

| Register | Field | Bits | Use |
|------------------|-----------------------------|-------|---------------------------------|
| `control` | `enable` | 0 | Releases the links of the core |
| `control` | `ilas_check_disable` | 8 | RX: data phase despite an ILAS mismatch |
| `status` | `ready` | 0 | All the links of the core are up |
| `status` | `sync_n` | 1 | Level of SYNC~ in the core |
| `status` | `skew_fifo` | 8-15 | RX: fill level of the lane 0 skew FIFO |
| `stpl_enable` | `enable` | 0 | Test pattern instead of samples |
| `stpl_errors` | | 0-31 | RX: link clocks with a wrong sample, cleared when STPL is enabled |
| `lmfc` | `load_on_sysref` | 0-3 | LMFC value loaded on a SYSREF edge |

When `ready` does not come, [Debugging](#debugging) gives the checks in order, starting with
the PHYs.

### The LMFC load value {#integ-lmfc}

Each core reloads its LMFC counter on the rising edge of SYSREF, with the value of the `lmfc`
register. The reset value compensates the delays of the SYSREF synchronizer and of the elastic
buffer: 5 for a TX core, the LMFC period minus 5 for an RX core (11 here).

Changing the value moves the multiframe boundaries of the core by whole link clock cycles, which
tunes the latency of the link at bring-up. [TX and RX cores](#cores) describes the counter.

## Lanes and several converters {#integ-lanes}

The list of PHYs given to a core is the lane order: the first PHY carries lane 0. When the lanes
of the converter reach the transceivers in another order, reorder the list, and reorder it
separately for TX and RX when the two directions differ. The PHY keeps its `n`, so its clock
domains keep their name.

A board with two converter devices can use one TX core and one RX core per device. Each core has its
own settings and SYNC~ pads, and all of them share the SYSREF of the clock chip. The PHYs of all
the cores need distinct names and `n` values, `jesd_phy0` to `jesd_phy7` for two devices of four
lanes.

## JESD204C {#integ-204c}

A JESD204C design follows the same steps with the JESD204C settings, cores and control modules.
There is no SYNC~: the cores only take `register_jref`.

The PHY must provide 64-bit blocks with a 2-bit sync header, and a gearbox slip input, `rx_slip`.
No LiteICLink transceiver on its default branch provides this interface, so a JESD204C design
needs its own PHY wrapper ([status](#intro-status), [PHYs: LiteICLink transceivers](#phys)).

## Standalone use {#integ-standalone}

The repository has no generator script. To use a core outside a LiteX SoC, elaborate a
`SoCMini` that contains the cores, the PHYs and the control modules, as above, and build it with
`run=False`. The Verilog of the `gateware` directory then serves as a module of the larger design.

`csr.csv` gives the register addresses on the CSR bus; the `Builder` can also export them as JSON
or a C header, or as SVD.

## Migration from LiteJESD204B {#integ-migration}

The package was named `litejesd204b`. The old name is an alias of `litejesd204` that returns the
same classes, and raises a warning that gives the release that removes it (cut here):

```console
$ python3 -W always -c "from litejesd204b.core import LiteJESD204BCoreTX"
<string>:1: DeprecationWarning: The litejesd204b package has been renamed litejesd204;
[...] The litejesd204b compatibility package will be removed in LiteX 2027.04.
```

To migrate a design:

- **Imports.** Replace `litejesd204b` with `litejesd204` in every import; the class names are the
  same.
- **Installation.** Uninstall the old package (`pip uninstall litejesd204b`) before installing
  the new one: an editable installation of the old clone hides the alias.
- **Clone.** Rename a `litex_setup.py` clone from `litejesd204b` to `litejesd204`, or run
  the initialization of `litex_setup.py` again.
- **LiteICLink.** Old designs import the transceivers from `liteiclink.transceiver`, a deprecated
  alias of `liteiclink.serdes`; import from `liteiclink.serdes`, as in this chapter.

## In the code {#integ-code}

The classes used in this chapter come from `litejesd204.common` (settings), `litejesd204.core`
(JESD204B cores and control module), `litejesd204.core_204c` (JESD204C) and
`liteiclink.serdes.gtx_7series` (GTX and its quad PLL).

Where to go next: [Examples and boards](#examples) for other starting points,
[Debugging](#debugging) for the bring-up checklist.
