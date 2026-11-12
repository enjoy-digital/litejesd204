# Performance and resources {#performance}

This appendix gathers the figures of the project: the link clock and the payload of a lane for a
given line rate, the sample rates they allow, the latency stages of the cores and resource
estimates.

Computed values are labelled as such. The repository records one hardware figure, a line rate
quoted below as recorded; it records no throughput, error rate, latency or resource figure
measured on a board.

## Line rate and link clock {#perf-clocks}

A core processes one word per lane and link clock: 32 bits, four octets, for JESD204B, and one
64-bit block for JESD204C. The link clock is therefore fixed by the line rate. With 8b/10b, four
octets take 40 line bits; with 64b/66b, a block takes 66.

| Standard | Line bits per link clock | Payload bits | Link clock | Payload efficiency |
|----------------|---------------------------|----------------|------------------------|-----------------------|
| JESD204B | 40 | 32 | line rate / 40 | 80 % |
| JESD204C | 66 | 64 | line rate / 66 | 96.97 % (computed) |

The table below applies these ratios to common line rates. All values are computed.

| Standard | Line rate | Link clock | Payload per lane |
|----------------|----------------|----------------|--------------------|
| JESD204B | 2.4576 Gbps | 61.44 MHz | 1.96608 Gbps |
| JESD204B | 4.9152 Gbps | 122.88 MHz | 3.93216 Gbps |
| JESD204B | 5 Gbps | 125 MHz | 4 Gbps |
| JESD204B | 6.144 Gbps | 153.6 MHz | 4.9152 Gbps |
| JESD204B | 10 Gbps | 250 MHz | 8 Gbps |
| JESD204B | 12.5 Gbps | 312.5 MHz | 10 Gbps |
| JESD204C | 16.22016 Gbps | 245.76 MHz | 15.72864 Gbps |
| JESD204C | 24.33024 Gbps | 368.64 MHz | 23.59296 Gbps |

The `jesd` domain runs at the link clock and the FPGA must close timing at that frequency. The
link clock is also a multiple of the LMFC (or LEMC) rate: one multiframe lasts F*K/4 link clocks,
one extended multiblock 32*E ([JESD204 in a nutshell](#jesd204-primer)).

## Sample rate {#perf-samples}

The payload of the L lanes carries M converters of N'-bit words, so each converter receives L
times the payload of a lane divided by M*N'. The table computes it for a few JESD204B modes, with
N' = 16.

| L | M | Line rate | Link clock | Samples per converter (computed) |
|------|------|----------------|----------------|------------------------------------|
| 4 | 4 | 2.4576 Gbps | 61.44 MHz | 122.88 MSPS |
| 2 | 4 | 4.9152 Gbps | 122.88 MHz | 122.88 MSPS |
| 4 | 4 | 5 Gbps | 125 MHz | 250 MSPS |
| 8 | 8 | 10 Gbps | 250 MHz | 500 MSPS |

The converter port of a core carries `converter_data_width // N` samples per link clock; for
32-bit JESD204B lanes, `converter_data_width` is N times 32*L/(M*N') ([Build options](#opt-cores)).
The second mode, with M different from L, falls under the LMFC sizing limitation of
[Known issues](#debug-known-issues).

## Recorded hardware figures {#perf-recorded}

The README of the repository records this use of the core, without a commit or a test that gives
more detail:

> Commercial SDR designs (JESD204C on UltraScale+, 4 lanes at 16.22016Gbps).

At that line rate, the computed link clock is 245.76 MHz and the computed payload is 15.72864
Gbps per lane, 62.91456 Gbps for the four lanes. The README does not give the converter mode, so
no sample rate follows from it. Its status, and that of the JESD204C cores on the default branch,
is in [Status](#intro-status).

## Latency stages {#perf-latency}

The latency of a link is set, by design, by the LMFC: an RX core releases its lanes at an LMFC
boundary, so the latency of the data path rounds up to the multiframe structure. The stages below
are those of the code, in link clocks; they are what the default LMFC loads compensate. No total
latency is recorded.

| Stage | Latency | Code |
|------------------------------|---------------------------|-----------------------------------------------|
| 204B TX link datapath | 1 (scrambler) | `LiteJESD204BLinkTXDatapath` |
| 204B RX aligner and datapath | 1 + 1 (aligner, descrambler) | `Aligner`, `LiteJESD204BLinkRXDatapath` |
| 204C TX link | 2 register stages after the scrambler | `LiteJESD204CLinkTX` |
| 204C RX link | 1 register stage after the descrambler | `LiteJESD204CLinkRX` |
| CDC, 32-bit PHY words or 204C blocks | Elastic buffer of 4 words | `LiteJESD204BTXCDC`, `LiteJESD204CTXCDC` and RX |
| CDC, 16-bit PHY words (204B) | Asynchronous FIFO of 4 words, not fixed | `LiteJESD204BTXCDC`, `LiteJESD204BRXCDC` |
| SYSREF to LMFC reload | 3 register stages, edge detection included | Cores, `LMFC` |
| RX skew FIFO | Up to 4 multiframes or extended multiblocks | `LiteJESD204BCoreRX`, `LiteJESD204CCoreRX` |

The default LMFC loads, +5 on TX and -5 on RX, are commented in the code as the SYSREF and
elastic buffer latency. [Debugging](#debug-lmfc) explains how to tune them.

## Resources {#perf-resources}

The figures below are Yosys estimates, not vendor results: Yosys 0.70 with `synth_xilinx -family
xc7`, no placement. Each design is one core with its control module and a register bus, for L=4,
M=4, F=2, S=1, K=32, N=N'=16 (E=1 for JESD204C), with 32-bit converter ports for JESD204B and
64-bit ones for JESD204C.

The PHY and converter ports and the register bus are top-level ports, so nothing is optimized
away. The Verilog comes from the LiteX KC705 platform, with the control of the RX cores at its
defaults (no lane status).

| Design (computed by Yosys) | LUTs | Flip-flops | LUTRAM cells | CARRY4 |
|----------------------------------|----------|--------------|--------------------------|----------|
| `LiteJESD204BCoreTX` | 474 | 496 | 24 RAM32M | 21 |
| `LiteJESD204BCoreRX` | 923 | 785 | 24 RAM32M, 44 RAM64M | 41 |
| `LiteJESD204CCoreTX` | 1311 | 1203 | 44 RAM32M | 10 |
| `LiteJESD204CCoreRX` | 2101 | 1540 | 44 RAM32M, 176 RAM64M | 78 |

The LUTRAM cells hold the elastic buffers and the skew FIFOs of the RX cores; the skew FIFOs grow
with the multiframe length. Vivado packs logic
differently: take these figures as an order of magnitude, and use a vendor build for a resource
budget.

```sh
# b_rx.v: Verilog of one core with its control module and a CSR bus as top-level
# ports, generated outside the repository
yosys -q -p "read_verilog b_rx.v; synth_xilinx -family xc7 -top top; stat"
```
