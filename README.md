```
                               __   _ __         _____________  ___  ___  ____
                              / /  (_) /____ __ / / __/ __/ _ \|_  |/ _ \/ / /
                             / /__/ / __/ -_) // / _/_\ \/ // / __// // /_  _/
                            /____/_/\__/\__/\___/___/___/____/____/\___/ /_/

                                     Copyright 2016-2026 / EnjoyDigital
                                     Copyright 2016-2018 / M-Labs Ltd

                       A small footprint and configurable JESD204B/JESD204C core
                                        powered by Migen & LiteX
```

[![](https://github.com/enjoy-digital/litejesd204/workflows/ci/badge.svg)](https://github.com/enjoy-digital/litejesd204/actions) ![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/enjoy-digital/litejesd204)


[> Intro
--------
LiteJESD204 provides a small footprint and configurable JESD204B (8b10b) and JESD204C (64b66b) core:
the two link layers share the same transport layer, deterministic latency counter (LMFC/LEMC),
TX/RX cores and control interface, and use the transceiver PHYs of
[LiteICLink](https://github.com/enjoy-digital/liteiclink).

LiteJESD204 is part of LiteX libraries whose aims are to lower entry level of
complex FPGA cores by providing simple, elegant and efficient implementations
of components used in today's SoC such as Ethernet, SATA, PCIe, SDRAM Controller...

Using Migen to describe the HDL allows the core to be highly and easily configurable.

LiteJESD204 is used as a LiteX library: designs instantiate its cores in a LiteX SoC or in a
Migen module (there is no standalone Verilog generator).

LiteJESD204 was previously named LiteJESD204B, see the migration section below.

[> Features
-----------
Link layer JESD204B (`litejesd204.link`):
 - 8b10b encoding, scrambling (x^15 + x^14 + 1) to reduce EMI.
 - Special characters insertion/replacement (/F/, /A/, /K/, /R/).
 - Code Group Synchronization (CGS) and Initial Lane Alignment Sequence (ILAS).
 - Byte alignment, lane deskew (skew FIFOs) and optional per-lane status.

Link layer JESD204C (`litejesd204.link_204c`):
 - 64b66b blocks, x^58 + x^39 + 1 self-synchronous scrambling.
 - CRC-12 mode sync words, end-of-multiblock/extended-multiblock detection.
 - Sync header lock (with PHY gearbox slip control) and extended multiblock lock.
 - Lane deskew on extended multiblock boundaries (LEMC), CRC error and lock diagnostics.

Transport layer (`litejesd204.transport`, shared):
 - Converters <--> lanes mapping.
 - Simple Transport Layer Pattern (STPL) generator/checker.

Cores (`litejesd204.core` for JESD204B, `litejesd204.core_204c` for JESD204C):
 - TX/RX cores with LMFC/LEMC counter (SYSREF/JREF), clock domain crossings to the PHYs.
 - Control/Status CSRs for LiteX SoCs.

PHY:
 - JESD204B: 7-Series GTP/GTX and UltraScale(+) GTH/GTY 8b10b wrappers of LiteICLink.
 - JESD204C: the cores expect a 64b66b PHY (64-bit data + 2-bit sync header per block, RX gearbox
   slip); no LiteICLink 64b66b wrapper is merged yet (UltraScale+ GTH one in development).

[> FPGA Proven
---------------
LiteJESD204 is already used in commercial and open-source designs:
- ARTIQ (JESD204B): http://m-labs.hk/artiq/index.html
- Commercial SDR designs (JESD204C on UltraScale+, 4 lanes at 16.22016Gbps).
- and others commercial designs...

[> Possible improvements
------------------------
- add support for JESD204C command channel and FEC.
- add support for Altera PHYs
- add support for Lattice PHYs
- ... See below Support and consulting :)

If you want to support these features, please contact us at florent [AT]
enjoy-digital.fr.

[> Documentation
----------------
The **JESD204B & JESD204C Converter Links manual** is the reference of LiteJESD204: a nightly
[PDF](https://github.com/enjoy-digital/litejesd204/releases/download/manual-nightly/litejesd204_manual.pdf)
and [HTML page](https://github.com/enjoy-digital/litejesd204/releases/download/manual-nightly/litejesd204_manual.html)
are published on the [manual-nightly](https://github.com/enjoy-digital/litejesd204/releases/tag/manual-nightly)
release. Sources in [doc/manual](doc/manual/README.md) (build: `python3 doc/manual/build.py`, outputs in
`build/doc/`; pandoc, XeLaTeX and the fonts listed in the README of `doc/manual`):

- **Understand**: [introduction](doc/manual/01_introduction.md), [JESD204 in a nutshell](doc/manual/02_jesd204_primer.md),
  [JESD204C and 64b/66b](doc/manual/03_jesd204c_primer.md).
- **The core**: [architecture](doc/manual/04_architecture.md), [transport layer](doc/manual/05_transport.md),
  [JESD204B link layer](doc/manual/06_link_204b.md), [JESD204C link layer](doc/manual/07_link_204c.md),
  [TX and RX cores](doc/manual/08_cores.md), [PHYs](doc/manual/09_phys.md).
- **Use it**: [getting started](doc/manual/10_getting_started.md), [integration](doc/manual/11_integration.md),
  [examples](doc/manual/12_examples.md), [simulation](doc/manual/13_simulation.md),
  [debugging](doc/manual/14_debugging.md).
- **Appendices**: [registers](doc/manual/A_registers.md), [build options](doc/manual/B_build_options.md),
  [glossary](doc/manual/C_glossary.md), [performance and resources](doc/manual/D_performance.md),
  [maintaining this manual](doc/manual/E_maintenance.md).

[> Getting started
------------------
1. Install Python 3.7+ and FPGA vendor's development tools.
2. Install LiteX and the cores by following the LiteX's wiki [installation guide](https://github.com/enjoy-digital/litex/wiki/Installation).
3. Instantiate `LiteJESD204BCoreTX/RX` (JESD204B) or `LiteJESD204CCoreTX/RX` (JESD204C) with the PHYs
   from LiteICLink in your LiteX SoC, and add the matching `Core Control` module for the CSRs.
   `examples/kc705_gtx.py` is a complete JESD204B design (KC705, GTX on SFP, TX looped back to RX)
   that generates its Verilog without vendor tools (`./kc705_gtx.py`, `--build` with Vivado).

[> Migration from LiteJESD204B
------------------------------
The project, the Python package and the pip distribution have been renamed from `litejesd204b` to
`litejesd204`. The `litejesd204b` package is kept as a compatibility shim for two LiteX release
cycles (removal planned for LiteX 2027.04): the old imports keep working, return the same objects
and raise a `DeprecationWarning`.

- Update your imports: `from litejesd204b.core import ...` -> `from litejesd204.core import ...`.
- Editable/develop installs of the old checkout shadow the shim: run `pip uninstall litejesd204b`
  before installing `litejesd204`.
- `litex_setup.py` checkouts: `mv litejesd204b litejesd204` (or re-run `litex_setup.py init`),
  the GitHub repository redirects to its new name.

[> Tests
--------
Unit tests are available in ./test/.
To run all the unit tests:
```sh
$ python3 -m pytest
```

Tests can also be run individually:
```sh
$ python3 -m unittest test.test_name
```

[> License
----------
LiteJESD204 is released under the very permissive two-clause BSD license. Under
the terms of this license, you are authorized to use LiteJESD204 for closed-source
proprietary designs.
Even though we do not require you to do so, those things are awesome, so please
do them if possible:
 - tell us that you are using LiteJESD204
 - cite LiteJESD204 in publications related to research it has helped
 - send us feedback and suggestions for improvements
 - send us bug reports when something goes wrong
 - send us the modifications and improvements you have done to LiteJESD204.

[> Support and consulting
-------------------------
We love open-source hardware and like sharing our designs with others.

LiteJESD204 is developed and maintained by EnjoyDigital.

If you would like to know more about LiteJESD204 or if you are already a happy user
and would like to extend it for your needs, EnjoyDigital can provide standard
commercial support as well as consulting services.

So feel free to contact us, we'd love to work with you! (and eventually shorten
the list of the possible improvements :)

[> Contact
----------
E-mail: florent [AT] enjoy-digital.fr
