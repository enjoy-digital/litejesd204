# JESD204C and 64b/66b {#jesd204c-primer}

This chapter explains what JESD204C changes in a link, for a reader who knows the JESD204B
mechanisms of [JESD204 in a nutshell](#jesd204-primer). The transport layer and the role of SYSREF
stay; the line code, the framing and the link start-up are new. The chapter ends with what the
core does not implement.

## Why JESD204C {#c-why}

8b/10b sends 10 line bits for 8 data bits: 20 % of every lane carries coding, not samples. At the
rates of recent converters this costs lanes, and lanes cost transceivers and board area. JESD204C
raises the lane rate and adopts 64b/66b, which sends 66 line bits for 64 data bits.

At the 16.22016 Gbps of the record in the [status table](#intro-status), a 64b/66b lane carries
16.22016 x 64/66 = 15.72864 Gbps of payload, against 12.976128 Gbps with 8b/10b at the same rate
(both computed). For the same samples, a link needs about 18 % fewer lanes or a lower lane rate.

The cost is in the receiver. 64b/66b has no comma to find word boundaries and no K characters to
mark frames, so JESD204C replaces them with a sync header per block, a sync word spread over many
blocks, and a CRC. The next sections take them in order.

## Blocks and sync headers {#c-blocks}

A lane is a sequence of 66-bit *blocks*: a 2-bit *sync header* followed by 8 octets of payload,
as the figure below shows. The payload carries the transport layer octets, scrambled.

![A 64b/66b block: a 2-bit sync header (H) and 64 bits of scrambled payload, sent from left to
right.](c_block.svg)

A valid sync header is `01` or `10`: it always has a transition. The receiver slides its block
boundary one bit at a time until every header it sees is valid; random payload bits cannot keep
that property for long, so the boundary is found. In JESD204C the value of the header is not
wasted: each header carries one bit of the *sync word* described below.

In LiteJESD204, the JESD204C link layer handles one block per link clock and per lane: a 64-bit
`data` word and a 2-bit `header`, which the PHY serializes. The link clock is therefore the line
rate divided by 66: 245.76 MHz at 16.22016 Gbps (computed).

## Multiblocks and extended multiblocks {#c-multiblocks}

32 blocks form a *multiblock*: 256 octets per lane. E multiblocks form an *extended multiblock*
(EMB), the JESD204C counterpart of the multiframe. An extended multiblock holds a whole number of
frames, so E > 1 is needed when F does not divide 256, as with F = 3 or F = 6.

Each device counts extended multiblocks with its *local extended multiblock clock* (LEMC), the
counterpart of the LMFC. SYSREF sets the phase of the LEMC in both devices, exactly as it sets the
LMFC in JESD204B (see [Device clock and SYSREF](#primer-sysref)).

In LiteJESD204, `JESD204CSettings` adds E (`e`, default 1) to the JESD204B settings and derives
the LEMC period, 32 x E link clocks (`lemc_cycles`). The cores reuse the LMFC counter of the
JESD204B cores at this period.

That counter wraps at the LEMC period for any E, such as 96 link clocks with E = 3. The settings
require the octets of one converter in a frame to divide 256, whatever E is, so E > 1 does not
enable F = 3 or F = 6 in the core ([Known issues](#debug-known-issues)).

## The sync word {#c-syncword}

The 32 sync header bits of a multiblock form a 32-bit *sync word*, sent one bit per block. The
standard defines several sync word formats; the figure below shows the CRC-12 format, the one the
core uses, as the core builds it.

![The sync word in CRC-12 mode, bit 31 sent first. C: CRC-12 bits; 1: pilot bits; c: command
channel bits; E: EoEMB; the last five bits are the EoMB sequence `00001`.](c_syncword.svg)

The fields are:

- **EoMB**: the end-of-multiblock sequence `00001` in the last five bits. The pilot bits, always
  1, come every fourth bit, so `00001` appears nowhere else in the sync word and marks the
  multiblock boundary.
- **EoEMB**: 1 in the last multiblock of an extended multiblock, which marks the extended
  multiblock boundary.
- **CRC-12**: the CRC of the scrambled payload of the previous multiblock. The receiver computes
  its own and compares, which detects bit errors on the lane.
- **Command channel**: 7 bits per multiblock for a slow side channel between the devices.

In LiteJESD204, the sync word generator (`SyncWordTX`) and receiver (`SyncWordRX`) implement the
CRC-12 format, and `CRC12` computes the CRC over the scrambled payload. A sync bit of 1 gives the
header value `0b01` and a 0 gives `0b10`. The command channel bits are sent as 0 and ignored on
receive.

## Scrambling {#c-scrambling}

The 64b/66b payload is always scrambled in JESD204C, with the self-synchronous polynomial
1 + x^39 + x^58. Scrambling is what bounds the run length on the line, since 64b/66b alone does
not; the sync header is not scrambled.

As in JESD204B, the descrambler takes its state from the received bits, so it is in step after 58
bits without any seed exchange.

In LiteJESD204, `Scrambler64b66b` processes one 64-bit block per link clock, the first octet of the
block in the most significant position. The settings and the cores have a `scrambling` argument
for debugging: the link layer scrambles when both are true, so either one turns scrambling off.

## Link start-up and lock {#c-lock}

JESD204C has no SYNC~, no CGS and no ILAS. The transmitter sends blocks as soon as its LEMC is
aligned, and each receiver lane locks on its own in two steps, as the figure below shows.

![JESD204C receiver lock. On each lane, sync header lock slips the block boundary until the
headers are valid; extended multiblock lock then finds the EoEMB markers at their expected
spacing. The numbers are those of the core.](c_lock.svg)

1. **Sync header lock**: the lane checks each header. An invalid one makes it slip the boundary by
   one bit, and wait for the slip to take effect. After enough consecutive valid headers the lane
   is locked; too many invalid headers drop the lock.
2. **Extended multiblock lock**: on the sync words, the lane looks for EoEMB, then checks that the
   next ones come exactly one extended multiblock later. A few in a row give the lock; repeated
   missing EoMB or EoEMB markers at their expected positions drop it.

Lane alignment then works as in JESD204B. Each lane writes its data into a FIFO from an extended
multiblock boundary, and the receiver releases all FIFOs together on an LEMC boundary, which gives
deterministic latency.

Without an ILAS, the link parameters are never sent on the lanes. Both devices must be configured
with the same values by software, and a mismatch shows up only as wrong samples.

In LiteJESD204, `BlockSync` runs sync header lock in the PHY receive clock domain and drives the
PHY slip input (`rx_slip`). It locks after 64 consecutive valid headers, unlocks after 16
consecutive invalid ones, and ignores the headers for 32 PHY RX clocks after each slip.
`SyncWordRX` locks after an EoEMB and three more at the right spacing, and unlocks after 8 missing
markers without a valid EoEMB in between. [JESD204C link layer](#link-204c) describes both.

## What the core does not implement {#c-limits}

JESD204C has more options than the core uses. The core does not implement:

- the command channel: its bits are sent as 0;
- forward error correction and the other sync word formats: only CRC-12 is implemented;
- the 64b/80b code;
- the 8b/10b mode of JESD204C: 8b/10b links use the JESD204B layers of the core, which advertise
  JESD204B in their configuration octets.

The JESD204C cores also need a PHY that passes 66-bit blocks and accepts a slip request, and
LiteICLink has none on its default branch: the [status table](#intro-status) gives the
consequence.

## Where to go next {#c-next}

[Architecture](#architecture) shows how the JESD204B and JESD204C layers fit in the core;
[JESD204C link layer](#link-204c) gives the implementation of this chapter.
