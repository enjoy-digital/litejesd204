```{=latex}
\frontmatter
```

# About this document {.unnumbered}

This manual is the reference of LiteJESD204, the LiteX core that connects an FPGA to high-speed
ADCs and DACs over JESD204B and JESD204C links. It covers the transport layer shared by both
standards, the two link layers, the TX and RX cores with their deterministic latency counters,
the control registers and the integration with the transceiver wrappers of LiteICLink.

No prior knowledge of JESD204 is assumed. Part I explains the standards in plain words and points
at the module that implements each mechanism. Part II describes the core layer by layer.

Part III is the user guide: first simulation, integration in a LiteX SoC, examples, tests and debugging.
The appendices hold the register reference, the build options, the glossary, the performance
figures and the maintenance notes of the manual.

| If you want to | Read |
|------------------------------------------|----------------------------------------------|
| Know what the project does and does not | [Introduction](#introduction) |
| Check what is validated on hardware | [Status](#intro-status) |
| Learn how a JESD204B link works | [JESD204 in a nutshell](#jesd204-primer) |
| Learn what JESD204C changes | [JESD204C and 64b/66b](#jesd204c-primer) |
| See how the core is organised | [Architecture](#architecture) |
| Run a first simulation | [Getting started](#getting-started) |
| Add a core to your design | [Integration](#integration) |
| Understand a link that does not come up | [Debugging](#debugging) |

The manual follows the repository: every name and default is taken from the source code, and
every hardware result from a public commit or document. The register appendix and the figures are
generated from the repository; the chapters are written by hand. When the code and the manual
disagree, the code is right and the manual has a bug.

## Conventions {.unnumbered}

- Numbers: `0x` prefix for hexadecimal, `0b` for binary. Bit fields are written `[msb:lsb]`.
- Rates: line rates in Gbps; clock frequencies in MHz. A value derived by a formula from the code
  or the standard, and not measured, is labelled as computed.
- Link parameters (L, M, F, S, K, N, N', CS, CF, HD, E) are written in capitals as the standard
  writes them; the code uses lower case (`l`, `m`, `np`).
- *Octet* is the 8-bit unit of a lane. *Converter* is one ADC or DAC channel; *converter device*
  is the chip. *Link clock* is the `jesd` clock domain of the cores.
- SYSREF and SYNC~ are written so in prose; the code names them `jref` and `jsync`. The tilde marks
  SYNC~ as active low: a low level is a synchronization request.
- *Register* is a control and status register of the LiteX CSR bus, named as in `csr.csv`.
- `<n>` stands for a lane index in a clock domain name, such as `jesd_phy<n>_rx`.
- Paths are relative to the repository root. Shell commands are given for a Linux host.
- When the text names a source file, it is the file to open to check or extend the fact.
