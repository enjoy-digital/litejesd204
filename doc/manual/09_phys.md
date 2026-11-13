# PHYs: LiteICLink transceivers {#phys}

This chapter describes what the cores expect from their PHYs and how LiteICLink transceivers
meet it. The core has no PHY of its own: each lane is a LiteICLink SerDes wrapper. Read it to
choose and configure the transceivers of a link; the transceivers themselves are documented in
the LiteICLink manual, which this chapter does not repeat.

## The LiteICLink manual {#phys-liteiclink}

The LiteICLink manual (<https://github.com/enjoy-digital/liteiclink/blob/master/doc/manual/>)
covers the transceivers in depth. The chapters that matter for a JESD204 link are:

| Chapter | Topics |
|--------------------------------------|---------------------------------------------------------|
| `03_transceiver_primer.md` | Channels, PLLs, user clocks, reset and reference clocks |
| `05_serdes_architecture.md` | Wrapper interface, PLL solver, clocking, clock aligner, PRBS, loopback, polarity |
| `06_xilinx_7series.md` | GTP, GTX and GTH: PLLs, line rates, limitations |
| `07_xilinx_ultrascale.md` | UltraScale and UltraScale+ GTH and GTY |
| `15_integration.md` | Data width and buffers, constraints, sharing a PLL |
| `18_debugging.md` | PLL lock, initialization, PRBS in loopback, line settings |

The files are in the `doc/manual/` directory of the LiteICLink repository.

## At a glance {#phys-glance}

| Item | JESD204B | JESD204C |
|-------------------------|----------------------------------------|----------------------------------|
| TX endpoint | `sink`: `data` 16 or 32 bits, `ctrl` | `sink`: `data` 64, `header` 2 |
| RX endpoint | `source`: same layout | `source`: same layout |
| RX control | `rx_align` | `rx_slip` |
| Line code | 8b/10b, in the PHY | 64b/66b gearbox, in the PHY |
| Clock domains | `cd_tx`, `cd_rx` of the PHY | Same |
| Flow control | None: one word per user clock | None: one block per link clock |
| LiteICLink wrappers | 8b/10b wrappers, 20 or 40 bits | None on the default branch |

The hardware status of each family is in the [status table](#intro-status) of the introduction.

## The JESD204B contract {#phys-204b}

A JESD204B core uses three things of each PHY:

- **Endpoints.** `sink` and `source` stream endpoints with `data`, 8 bits per octet, and `ctrl`,
  one K flag per octet. The core accepts 16-bit and 32-bit data; octet 0 is the first on the line.
- **Comma alignment.** An `rx_align` input. The RX link layer holds it high during CGS only, so
  that the PHY aligns on commas then, and never again during the ILAS and the data.
- **Clock domains.** A TX and an RX user clock domain, the `cd_tx` and `cd_rx` attributes of
  the PHY ([Clock domains](#phys-domains)).

The LiteICLink 8b/10b wrappers of the Xilinx transceivers have this interface: GTP, GTX and GTH
on 7-Series, GTH and GTY on UltraScale and UltraScale+. They share the names of the attributes
([The LiteICLink manual](#phys-liteiclink), `05_serdes_architecture.md`). LiteICLink has other
8b/10b wrappers, but nothing in this project uses them with the cores.

## Choosing the data width {#phys-width}

The data width of a wrapper counts the line bits of one user clock word: 20 bits carry 2 octets,
40 bits carry 4. It decides the clock domain crossing of the core:

| `data_width` | Endpoint | PHY user clock | Crossing | Latency |
|-----------------|------------|----------------|--------------------------------|-----------|
| 40 | 32 bits | Line rate / 40 | Elastic buffer | Fixed |
| 20 | 16 bits | Line rate / 20 | Asynchronous FIFO, width converter | Not fixed |

With 40 bits, the PHY user clock equals the link clock: 125 MHz at 5 Gbps (computed). With 20
bits, it runs at twice the link clock, and the latency through the crossing is not fixed by
construction ([Deterministic latency](#cores-latency)). The 80-bit width of the GTY is not
accepted by the JESD204B cores.

## Buffers and comma alignment {#phys-buffers}

`rx_align` acts in different ways depending on the RX buffer of the wrapper:

- **RX buffer enabled, `clock_aligner=False`.** `rx_align` enables the comma alignment of the
  transceiver. The published integration example uses this mode, with the TX buffer enabled too.
- **RX buffer bypassed, with the clock aligner.** The clock aligner of LiteICLink restarts the
  receiver until the comma falls on symbol 0; `rx_align` gates those restarts, so they can only
  happen during CGS.

The transceiver buffers have their own latency, which can change from one reset to the next; the
LiteICLink manual describes it for each family (`05_serdes_architecture.md`, Clocking).

## Clock domains {#phys-domains}

The core takes the clocks and the resets of a lane from its PHY. A LiteICLink wrapper has two
clock domain attributes, `cd_tx` and `cd_rx`. For each of them the core creates a domain of its
own, `jesd_phy<n>_tx_core` or `jesd_phy<n>_rx_core`, and drives its clock and its reset from the
PHY (`phy_clock_domain` in `core.py`). The design has no domain to name, with one lane or
several; `n` is the attribute `n` of the PHY, or its position in the list.

The snippet below runs in the `__init__` of a LiteX SoC, a `LiteXModule`, where an attribute
assignment such as `setattr(self, ...)` adds a submodule. In a plain Migen `Module`, use
`self.submodules` instead.

```python
from liteiclink.serdes.gtx_7series import GTXQuadPLL, GTX

pll = GTXQuadPLL(refclk, refclk_freq, linerate)
self.pll = pll  # Adds the QPLL to the design.
phys = []
for n in range(4):
    phy = GTX(pll, platform.request("jesd_tx", n), platform.request("jesd_rx", n), sys_clk_freq,
        data_width       = 40,
        clock_aligner    = False,
        tx_buffer_enable = True,
        rx_buffer_enable = True)
    phy.add_stream_endpoints()
    phy.n = n
    setattr(self, f"jesd_phy{n}", phy) # Registers and signals named jesd_phy{n}.
    phys.append(phy)
```

The pad names are those of the platform. The name of the submodule only sets the names of the
registers and of the signals of the PHY.

A PHY without `cd_tx` and `cd_rx` attributes, such as the stand-in PHYs of the tests, gets no
domain from the core. The design then provides the domains `jesd_phy<n>_tx` and
`jesd_phy<n>_rx`, with their clocks and their resets: the elastic buffers of the crossings use
both.

## Link clock and reference clock {#phys-clocking}

The elastic buffers of the crossings need the `jesd` clock at exactly the frequency of the PHY
user clocks. Both must come from the same reference, as the figure below shows.

A clock chip on the board sends the device clock and SYSREF to the converter and to the FPGA.
In the FPGA, the transceiver PLL and a clocking PLL take the same reference.

![Clocking of a JESD204 link. Look at the reference: the clock chip feeds the converter and the
FPGA; in the FPGA the transceiver PLL gives the PHY user clocks and the clocking PLL gives the
jesd domain, both from the same reference, while SYSREF goes to the core.](phy_clocking.svg)

The published integration example derives `jesd` from the transceiver reference clock through a
7-Series MMCM, and holds `jesd` in reset until all PHYs have completed their initialization
([Integration](#integration)). For deterministic latency, SYSREF must also be sampled reliably by
the `jesd` clock ([SYSREF and SYNC~](#cores-pads)).

## Constraints {#phys-constraints}

The wrappers add no timing constraint. The design declares the periods of the PHY clocks and the
false paths between `sys`, `jesd` and the PHY domains, which only meet through synchronizers and
FIFOs. In the snippet below, `self.crg` is the CRG of the SoC:

```python
for phy in phys:
    platform.add_period_constraint(phy.cd_tx.clk, 1e9/phy.tx_clk_freq)
    platform.add_period_constraint(phy.cd_rx.clk, 1e9/phy.rx_clk_freq)
    platform.add_false_path_constraints(self.crg.cd_sys.clk, self.cd_jesd.clk,
        phy.cd_tx.clk, phy.cd_rx.clk)
```

## The JESD204C contract {#phys-204c}

A JESD204C core expects a PHY that does the 64b/66b gearbox, not the line code of JESD204B:

- **Endpoints.** `sink` and `source` stream endpoints with a 64-bit `data` and a 2-bit `header`,
  one block per link clock, at the line rate divided by 66. The core asserts the 64-bit width.
- **Slip.** An `rx_slip` input, in the PHY RX domain: each pulse moves the receive gearbox by one
  bit. The block lock waits 32 PHY RX clocks after each pulse ([Thresholds](#lc-thresholds)).
- **Clock domains.** The same as in JESD204B; the block lock of each lane runs in the RX domain
  of its PHY.

No LiteICLink wrapper on the default branch provides this interface. The JESD204C cores build and
simulate with stand-in PHYs ([Simulation and tests](#simulation)), but a JESD204C link on hardware
needs a 64b/66b PHY from outside this project.

## Bring-up of the PHYs {#phys-bringup}

Bring up the transceivers before the JESD204 layers. The LiteICLink test features check a lane
without the core: PLL lock, PRBS in loopback and on the line, and the polarity of each pair
(`05_serdes_architecture.md`, Test features; `18_debugging.md`). [Debugging](#debugging) gives
the order of the checks for a whole link.

Where to go next: [Integration](#integration) for a complete SoC with PHYs and cores,
[Debugging](#debugging) for a link that does not come up.
