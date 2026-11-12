```{=latex}
\part{The core}
```

```{=html}
<h1 class="part">Part II. The core</h1>
```

# Architecture {#architecture}

This chapter describes how the core is put together: its layers, the settings that size them,
the clock domains and what the design around the core must provide. Read it before building a
TX core or an RX core by hand. The parameters and the link phases are explained in
[JESD204 in a nutshell](#jesd204-primer) and [JESD204C and 64b/66b](#jesd204c-primer).

## At a glance {#arch-glance}

| Item | JESD204B | JESD204C |
|-----------------|----------------------------------|----------------------------------|
| TX core (to a DAC) | `LiteJESD204BCoreTX` | `LiteJESD204CCoreTX` |
| RX core (from an ADC) | `LiteJESD204BCoreRX` | `LiteJESD204CCoreRX` |
| Registers | `LiteJESD204BCoreControl` | `LiteJESD204CCoreControl` |
| Settings | `JESD204BSettings` | `JESD204CSettings` |
| Transport layer | Shared | Shared |
| Link layer | One per lane | One per lane |
| Lane word | 32 bits: 4 octets | 64 bits: one block |
| PHY word | 16 or 32 bits, K flags | 64 bits, sync header |
| Multiframe counter | LMFC | LEMC, same class |
| Subclass | 1 | 1 |
| Clock domains | `jesd`, PHY domains, `sys` | Same |

The core has no PHY of its own: the transceivers come from LiteICLink
([PHYs: LiteICLink transceivers](#phys)). The hardware status of each standard and family is in
the [status table](#intro-status) of the introduction.

## Layers and data flow {#arch-layers}

A core is a stack of layers between the user logic and the PHYs, as the figure below shows for
the TX core. The transport layer maps the samples of the converters onto lanes. One link layer
per lane adds the link framing of the standard. A clock domain crossing per lane hands the words
to the PHY.

![TX core. Follow the cyan path: converter samples enter the transport layer, which feeds one
link layer per lane; each lane crosses into its PHY clock domain. The test pattern generator can
replace the samples, and the LMFC paces the link layers.](arch_tx.svg)

The RX core is the mirror image, with one more stage. After its link layer, each lane enters a
skew FIFO that holds the lane until every lane is ready, then releases all of them on the same
multiframe boundary. The figure below shows it.

![RX core. Follow the cyan path from the PHYs: each lane crosses into the link clock domain, goes
through its link layer and its skew FIFO, and the transport layer rebuilds the converter samples.
The LMFC releases the skew FIFOs together.](arch_rx.svg)

The transport layer and the test pattern blocks are the same classes for both standards. Only
the link layer, the clock domain crossing and the RX deskew differ. [Transport layer and test
patterns](#transport) describes the shared part, [JESD204B link layer](#link-204b) and
[JESD204C link layer](#link-204c) the two link layers, and [TX and RX cores](#cores) the
counters, the deskew and the registers.

## Settings {#arch-settings}

The settings objects hold the parameters of the link, as the converter datasheet gives them. A
JESD204B link takes two of them: the physical settings (L, M, N, N') and the transport settings
(F, S, K, CS). `JESD204BSettings` combines them with the device and bank identifiers of the
configuration octets.

```python
from litejesd204.common import *

ps       = JESD204BPhysicalSettings(l=4, m=4, n=16, np=16)
ts       = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
```

For JESD204C, `JESD204CSettings` takes the same two objects and E, the number of multiblocks
per extended multiblock (1 by default). It checks that the frames of one converter line up with
the 256 octets of a multiblock. It sets the JESD204C version on a copy of the physical settings
object it receives, so the same object can also serve a `JESD204BSettings`.

The settings class derives the values that size the layers. The table below lists them, with
the values it computes for the example above.

| Attribute | Formula in the code | Example |
|------------------------|------------------------------------------|---------|
| `nibbles_per_word` | N' / 4, rounded down | 4 |
| `octets_per_frame` | S x `nibbles_per_word` / 2 | 2 |
| `octets_per_lane` | `octets_per_frame` x M / L | 2 |
| `lmfc_cycles` | `octets_per_frame` x K / 4 | 16 |
| `lemc_cycles` (204C) | 32 x E | |

`octets_per_lane` is the F of the standard: the octets of one frame on one lane. The core does
not check it against the F given by the user, which only goes into the configuration octets. When
M and L differ, `octets_per_frame` is not F, and the LMFC period and the framer are sized wrong
([Limitations](#cores-limitations)).

The settings also fix the subclass to 1 and leave CF and HD at 0. Control bits are not
supported, so CS must be 0 ([Control bits and tail bits](#tr-tail-bits)).

## Clock domains {#arch-clocks}

A core uses three kinds of clock domains, as the figure below shows. The user provides `jesd`,
the link clock. Each PHY provides its TX and RX user clock domains. The registers run in `sys`.

![Clock domains of a core. Look at the boundaries: the layers and the counters run in jesd; the
crossings, one per lane, straddle the boundary with the PHY user clock domains, and the
synchronizers the boundary with sys.](arch_clocks.svg)

| Domain | Provided by | Content |
|---------------------|-----------|------------------------------------------------|
| `jesd` | The design | Transport, link layers, LMFC or LEMC, skew FIFOs |
| `jesd_phy<n>_tx` | PHY `n` | TX side of the crossing of lane `n` |
| `jesd_phy<n>_rx` | PHY `n` | RX side of the crossing, JESD204C block lock |
| `sys` | The SoC | Registers of the control module |

One link clock carries one lane word: 4 octets in JESD204B, one 64-bit block in JESD204C. The
link clock is therefore the line rate divided by 40 in JESD204B (5 Gbps gives 125 MHz) and by 66
in JESD204C (16.22016 Gbps gives 245.76 MHz). These values are computed, not measured.

The crossing depends on the width of the PHY word:

| PHY word | Crossing | Latency |
|--------------------|--------------------------------------------|---------------------|
| 32 bits (204B) | `ElasticBuffer`, depth 4 | Fixed |
| 16 bits (204B) | `AsyncFIFO` (depth 4), `StrideConverter` | Not fixed by design |
| 64 + 2 bits (204C) | `ElasticBuffer`, depth 4 | Fixed |

The elastic buffer does no rate matching: the `jesd` clock must have exactly the frequency of the
PHY user clocks, from the same reference. The 16-bit path runs the PHY at twice the link clock
and converts the width in the PHY domain. Its asynchronous FIFO lets the latency vary from one
start to the next ([Deterministic latency](#cores-latency)).

## Lanes and PHYs {#arch-lanes}

A core takes a list of PHYs, one per lane, in lane order: the first PHY carries lane 0 of the
transport layer. In JESD204B, the position in the list also sets the lane identifier written in
the ILAS configuration octets of that lane. To connect lanes to transceivers in another order,
reorder the list.

The core finds the clock domains of a PHY by name. It uses `jesd_phy<n>_tx` and `jesd_phy<n>_rx`,
where `n` is the attribute `n` of the PHY when it exists, and its position in the list otherwise.
[PHYs: LiteICLink transceivers](#phys) shows how to name the domains.

## Enable and reset {#arch-enable}

The `enable` input of a core holds every link layer in reset while it is low. A disabled JESD204B
TX core sends /K/ characters, the code group synchronization pattern. A disabled JESD204B RX core
keeps SYNC~ asserted, which requests a synchronization from the converter. A disabled JESD204C
core never becomes ready.

The control module drives `enable` from its `control` register, 0 at reset unless
`default_enable` is set.

The `jesd` domain has its own reset, from the design. The published integration example holds it in reset
until the PHYs have completed their initialization ([Integration](#integration)).

## What the design provides {#arch-provides}

The core leaves the board-level parts to the design:

- **Link clock.** The `jesd` clock domain, frequency-locked to the PHY user clocks, and its reset.
- **PHYs.** One LiteICLink transceiver per lane, initialized, with named clock domains.
- **SYSREF.** A single-ended signal or a differential pad pair, given to `register_jref`.
- **SYNC~.** JESD204B only: an input pad of the TX core and an output pad of the RX core, given to
  `register_jsync`.
- **Converter setup.** The converter and the clock chip are configured over their own control
  interface, outside the core.

A core checks at finalization that SYSREF and, for JESD204B, SYNC~ were registered. The
connections are described in [SYSREF and SYNC~](#cores-pads).

## In the code {#arch-code}

| File | Content |
|----------------------------------|---------------------------------------------------|
| `litejesd204/common.py` | Control characters, configuration fields, settings |
| `litejesd204/transport.py` | Transport layer and test pattern blocks, shared |
| `litejesd204/link.py` | JESD204B link layer |
| `litejesd204/core.py` | JESD204B cores, crossings, LMFC, control module |
| `litejesd204/link_204c.py` | JESD204C link layer |
| `litejesd204/core_204c.py` | JESD204C cores, crossings, control module |

The package `litejesd204b` is a compatibility alias of `litejesd204` ([Introduction](#introduction)).

Where to go next: [Transport layer and test patterns](#transport) for the sample mapping,
[TX and RX cores](#cores) for the constructors and registers, [Integration](#integration) for a
complete design.
