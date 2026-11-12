```{=latex}
\mainmatter
\part{Understand}
```

```{=html}
<h1 class="part">Part I. Understand</h1>
```

# Introduction {#introduction}

This chapter says what LiteJESD204 is, why it exists, what it does and what it does not do. It
gives the hardware status of each part, the old name and its compatibility package, the layout of
the repository and a map of the manual. Every reader should start here.

## What the project is {#intro-what}

LiteJESD204 is a JESD204B and JESD204C core for LiteX, written in Python with Migen and LiteX. It
moves samples between the logic of an FPGA and high-speed data converters: DACs on the transmit
side, ADCs on the receive side. The samples travel on serial lanes driven by the transceivers of
the FPGA.

A *TX core* takes samples from the user logic, maps them onto octets, adds the link framing and
hands one word per lane and per link clock to a PHY, through a clock domain crossing: 32 bits for
JESD204B, a 66-bit block for JESD204C.

An *RX core* does the reverse, and also aligns the lanes so that samples taken at the same instant
leave the core together. The figure below shows both cores in a system.

![LiteJESD204 in a system. The TX core feeds a DAC and the RX core reads an ADC, each through one
PHY per lane. The converter devices answer on SYNC~, and the clock chip sends the device clock and
SYSREF to the converters and to the FPGA.](intro_overview.svg)

The PHYs are not part of the project: they are the SerDes wrappers of LiteICLink, the transceiver
library of LiteX. The cores only need a stream of words per lane and a few control signals, as
described in [PHYs: LiteICLink transceivers](#phys).

LiteJESD204 is a library: designs instantiate its classes in a LiteX SoC or in a Migen module.
There is no standalone Verilog generator.

## JESD204B and JESD204C {#intro-bc}

The two standards carry samples the same way but code the lanes differently. JESD204B uses 8b/10b
and a handshake on SYNC~ to start the link; JESD204C uses 64b/66b blocks and starts each lane on
its own. The core shares everything that does not depend on the line code, as the figure below
shows.

![The shared transport layer above two link layers. Each standard has its own link layer, its own
local timing counter (LMFC for JESD204B, LEMC for JESD204C) and its own PHY line
code.](intro_bc.svg)

| Item | JESD204B | JESD204C |
|---------------------------|---------------------------------|---------------------------------|
| Line code | 8b/10b | 64b/66b |
| Lane word per link clock | 32 bits (4 octets) | 64 bits and a 2-bit sync header |
| Scrambler | 1 + x^14 + x^15 | 1 + x^39 + x^58 |
| Link start | SYNC~, CGS, ILAS | Sync header, extended multiblock lock |
| Local timing counter | LMFC | LEMC |
| Error detection in the core | None | CRC-12 per multiblock |
| Python modules | `link.py`, `core.py` | `link_204c.py`, `core_204c.py` |
| LiteICLink PHY available | Yes (GTP, GTX, GTH, GTY) | No |

[JESD204 in a nutshell](#jesd204-primer) explains the JESD204B mechanisms, and [JESD204C and
64b/66b](#jesd204c-primer) what JESD204C changes.

## Why LiteJESD204 {#intro-why}

FPGA vendors provide JESD204 cores as licensed IP, configured with a wizard and delivered as
encrypted or generated netlists. They are tied to one vendor and hard to inspect when a link does
not come up. LiteJESD204 is an open alternative with three goals.

- **Small and readable**: the transport, link layers and cores of both standards fit in about
  2 400 lines of Python, which a user can read to understand what happens on each lane.
- **Configured from Python**: the link parameters are Python objects; the core derives its widths,
  multiframe lengths and the configuration octets from them at build time.
- **Portable transceivers**: the PHYs come from LiteICLink, so the same core runs on the Xilinx
  transceivers that LiteICLink wraps for 8b/10b (GTP, GTX, GTH, GTY).

## Features at a glance {#intro-features}

| Area | Features |
|-----------------------|---------------------------------------------------------------------|
| Transport layer | Converter to lane mapping and back, shared by both standards; the supported modes are in [Transport layer](#transport) |
| Test pattern | STPL: one fixed value per converter and sample position, generated in the TX core, checked with an error counter in the RX core |
| JESD204B link | Scrambling, /F/ and /A/ character insertion and replacement, CGS, ILAS generation and checking, byte alignment on /R/ |
| JESD204C link | 64b/66b blocks, scrambling, CRC-12 sync words, sync header lock with PHY slip, extended multiblock lock, CRC error pulses |
| Cores | TX and RX cores per standard, LMFC or LEMC counter reset by SYSREF, clock domain crossing to the PHYs, lane deskew FIFOs |
| Control | Register block per core: enable, status, test pattern, LMFC or LEMC load value, optional per-lane status |
| Verification | Unit tests of each layer against Python models; JESD204C core loopback tests |

## Status {#intro-status}

This is the one status table of the manual: other chapters link here. The status words are
defined below the table. The third column names the boards and rates that a public commit or
document records, and the last one the record.

| Block | Status | Recorded on hardware | Record |
|----------------------------------|-----------------------|----------------------------------------|--------------------|
| JESD204B cores, 7-Series GTX | Validated on hardware | KC705 with an AD9154 FMC board (DAC), in the 2016 example design and its own GTX PHY set for 5 Gbps; no result recorded | `f6dc2a1`, `70d2b0a` |
| JESD204B cores, 7-Series GTP | Validated on hardware | Not recorded publicly | None |
| JESD204B cores, UltraScale and UltraScale+ GTH and GTY | Validated on hardware | KCU105 with an AD9154 board, L = 8, in the notes of `MEMO`; no result recorded | `MEMO`, `5afa985` |
| JESD204C cores | In development | "JESD204C on UltraScale+, 4 lanes at 16.22016Gbps" | `README.md` |
| STPL, ILAS check, lane status | Status of their core | As their core | As their core |

The status words mean:

- **Validated on hardware**: the maintainer states that the block works on hardware, in subclass
  1. Numbers are given only where a public commit or document records them.
- **In development**: the code is on the default branch and tested in simulation, without a
  recorded use on hardware. The JESD204C cores also need a 64b/66b PHY, which LiteICLink lacks on
  its default branch.

"Not recorded publicly" means that no public commit or document names a board or a rate for that
block; it does not lower its status. Beyond the table, a public issue of the repository (issue #2)
reports a JESD204B link up on an AD9174 DAC after a fix of the ILAS counter octets, without naming
the FPGA.

The `README.md` line of the JESD204C row is quoted as written. The same file names a
`gth4_ultrascale_64b66b` wrapper of LiteICLink, which is not on the LiteICLink default branch.
[JESD204C link layer](#link-204c) gives the PHY contract that such a wrapper must meet.

## What it is not {#intro-limits}

LiteJESD204 implements the transport and link layers and stops there. It does not implement:

- subclass 0 or subclass 2: the configuration octets always advertise subclass 1 (see
  [Subclasses](#primer-subclasses));
- control bits and control words: CF and HD are always 0, and samples fill their N' bits without
  control bits. CS is advertised from the `cs` setting but never inserted, so keep `cs=0`;
- modes outside a subset of the standard: on JESD204B, frames of 1, 2 or 4 octets only, and the
  other limits of [Known issues](#debug-known-issues);
- SYNC~ error reporting: the RX core never sends an error report, and the TX core restarts the
  link only when SYNC~ stays low for a few link clocks (a 4-cycle timer);
- the JESD204C command channel, forward error correction and the 64b/80b code;
- a PHY: the transceivers come from LiteICLink, which has no 64b/66b wrapper on its default
  branch;
- the configuration of the converter or clock chip: their SPI registers are set by software, from
  the vendor datasheets;
- a standalone generator: there is no command that writes a Verilog core.

## The name and the compatibility package {#intro-rename}

The project was called LiteJESD204B until JESD204C was added. The Python package is now
`litejesd204`, and the pip distribution has the same name.

The old package `litejesd204b` remains as a compatibility layer. It maps each old module name to
the new module, so `from litejesd204b.core import LiteJESD204BCoreTX` returns the same class as the
new import.

It raises a `DeprecationWarning` that announces its removal in LiteX 2027.04. The class
names are unchanged: the JESD204B classes keep their `LiteJESD204B` prefix, and the JESD204C ones
use `LiteJESD204C`. [Integration](#integration) gives the migration steps.

## Repository layout {#intro-layout}

| Path | Content |
|--------------------------------------|---------------------------------------------------------|
| `litejesd204/common.py` | Control characters, configuration octets, settings classes |
| `litejesd204/transport.py` | Transport layer and STPL generator and checker (both standards) |
| `litejesd204/link.py` | JESD204B link layer |
| `litejesd204/core.py` | JESD204B cores, LMFC counter, control module |
| `litejesd204/link_204c.py` | JESD204C link layer |
| `litejesd204/core_204c.py` | JESD204C cores and control module |
| `litejesd204b/` | Compatibility package for the old name |
| `test/` | Unit and loopback tests (pytest), Python models in `test/model/` |
| `MEMO` | Notes on the JESD204B parameters and character insertion |
| `doc/` | This manual (`doc/manual/`), its figures (`doc/diagrams/`), logos |

## License and credits {#intro-license}

LiteJESD204 is released under the BSD 2-Clause license by Enjoy-Digital. It can be used in
closed-source designs.

The repository history starts in 2016 with the JESD204B transport and link layers, their own
transceiver PHYs and a KC705 example design with an AD9154 DAC board. The example design left the
repository in 2016, and the PHYs were replaced by the LiteICLink wrappers in 2019.

The JESD204C link layer and cores, and the new name, came in 2026. The contributors are listed in
`CONTRIBUTORS` and in the history of the repository.

## How to read this manual {#intro-reading}

If JESD204 is new to you, read [JESD204 in a nutshell](#jesd204-primer) next, then [JESD204C and
64b/66b](#jesd204c-primer) if you need JESD204C. Otherwise, the table below sends each question to
its chapter.

| Question | Chapter |
|-----------------------------------------------|----------------------------------------|
| How does a JESD204B link work? | [JESD204 in a nutshell](#jesd204-primer) |
| What does JESD204C change? | [JESD204C and 64b/66b](#jesd204c-primer) |
| How is the core organised? | [Architecture](#architecture) |
| How are samples mapped onto lanes? | [Transport layer and test patterns](#transport) |
| What does the JESD204B link layer do? | [JESD204B link layer](#link-204b) |
| What does the JESD204C link layer do? | [JESD204C link layer](#link-204c) |
| How do the cores align lanes and keep latency fixed? | [TX and RX cores](#cores) |
| Which transceiver wrapper do I use? | [PHYs: LiteICLink transceivers](#phys) |
| How do I run a first simulation? | [Getting started](#getting-started) |
| How do I add a core to my design? | [Integration](#integration) |
| Is there a complete example? | [Examples and boards](#examples) |
| How do I simulate and test? | [Simulation and tests](#simulation) |
| The link does not come up: what now? | [Debugging](#debugging) |
| What does this acronym mean? | [Glossary](#glossary) |
