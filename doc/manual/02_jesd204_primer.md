# JESD204 in a nutshell {#jesd204-primer}

This chapter explains JESD204B to an FPGA engineer who has never connected a converter over
serial lanes. It starts from the system and the link parameters, follows the samples onto the
lanes, then gives the link start-up, the lane alignment and the deterministic latency that SYSREF
provides. JESD204C reuses most of it; [JESD204C and 64b/66b](#jesd204c-primer) gives the changes.

Each section starts with the idea, then gives the mechanism, and ends with the part of
LiteJESD204 that implements it. The transceiver itself (serializer, 8b/10b, comma alignment) is
explained in the LiteICLink manual and only summarised here.

## Why serial converter interfaces {#primer-why}

A fast ADC or DAC produces or consumes hundreds of millions of samples per second, each of 12 to
16 bits, on several channels. A parallel interface needs one pair of pins per bit and per channel,
with a careful layout to keep the skew between them small. At these rates it costs hundreds of
pins on both chips.

JESD204 replaces the parallel bus with a few serial lanes, each running at several Gbps with
8b/10b coding. The pin count drops to a few pairs, and the receiver aligns the lanes itself, so
the board only needs matched pairs within each lane.

The standard went through four versions. JESD204 had one lane; JESD204A added several lanes;
JESD204B raised the lane rate up to 12.5 Gbps and added deterministic latency with a device clock
and SYSREF; JESD204C moved to 64b/66b and rates up to 32 Gbps. LiteJESD204 implements JESD204B and
JESD204C.

## Converter devices and logic devices {#primer-devices}

A JESD204 *link* connects one converter device to one logic device, here the FPGA. The figure
below shows the signals of a receive link, from an ADC to the FPGA.

![A JESD204B receive link. The converter device sends its samples on L lanes, the FPGA answers on
SYNC~, and a clock chip sends the device clock and SYSREF to both
devices.](primer_system.svg)

The lanes carry the data, in one direction. SYNC~ goes the other way, from the receiver to the
transmitter: it is a single active-low signal, usually LVDS, that requests synchronization. For a
DAC the roles swap: the FPGA transmits, and the DAC drives SYNC~.

The *device clock* is the reference of everything: the converter derives its sample clock from
it, and the FPGA derives its link clock from it. *SYSREF* is a timing pulse, sent with the device
clock, that marks the same instant in both devices; [Device clock and SYSREF](#primer-sysref)
explains it.

In LiteJESD204, a TX core drives the lanes of a DAC and an RX core receives those of an ADC.
SYNC~ is an input of the TX core and an output of the RX core (`register_jsync`), and SYSREF an
input of both (`register_jref`).

## Link parameters {#primer-parameters}

A link is described by a set of parameters. Both devices must use the same values: the
transmitter announces them at start-up, and the converter datasheet lists the modes it supports.
The table below gives the parameters and the ranges that their configuration fields allow.

| Parameter | Meaning | Range |
|-----------|------------------------------------------------------|----------------------|
| L | Lanes per converter device | 1 to 32 |
| M | Converters per device | 1 to 256 |
| F | Octets per frame, per lane | 1 to 256 |
| S | Samples per converter per frame | 1 to 32 |
| N | Conversion bits per sample (converter resolution) | 1 to 32 |
| N' | Transmitted bits per sample (N plus control and tail bits) | 1 to 32 |
| K | Frames per multiframe | 32 at most, F x K of 17 or more |
| CS | Control bits per sample | 0 to 3 |
| CF | Control words per frame clock period per link | 0 to 32 |
| HD | High density format (samples may span lanes) | 0 or 1 |

The core supports a subset of these modes, listed in [Transport layer and test
patterns](#transport).

A *frame* is the set of octets that carries S samples of each of the M converters. It is spread
over the L lanes, F octets on each lane, so F follows from the other parameters:

- F = M x S x N' / (8 x L)
- frame clock = sample clock / S
- multiframe clock (LMFC) = frame clock / K
- line rate = M x S x N' x 10/8 x frame clock / L, the factor 10/8 being the 8b/10b overhead.

As an example, take a public LiteJESD204 integration with an AD937x converter device (an RF
transceiver): L = 4, M = 4,
S = 1, N' = 16 and a 2.4576 Gbps line rate. Then F = 4 x 1 x 16 / 32 = 2, and the sample clock is
2.4576 Gbps x 4 / (4 x 16 x 10/8) = 122.88 MHz (computed).

With L = 2 at 4.9152 Gbps, F becomes 4 and the sample clock is the same. This mode has M
different from L, which the core does not size correctly ([Known issues](#debug-known-issues)).

In LiteJESD204, the parameters are grouped in two objects, `JESD204BPhysicalSettings` (L, M, N,
N') and `JESD204BTransportSettings` (F, S, K, CS), combined in `JESD204BSettings` with the device
and bank identifiers. The settings derive the widths and lengths used by the core;
[Architecture](#architecture) lists them.

## Transport layer: samples to octets {#primer-mapping}

The *transport layer* turns the samples of one frame into octets and distributes them over the
lanes. Each sample occupies N' bits: the N conversion bits first, most significant bit first,
then CS control bits, then tail bits that fill the word. The words of all the samples of a frame
are concatenated, cut into octets, and the first F octets go to lane 0, the next F to lane 1, and
so on.

The figure below shows a mode with four 14-bit converters on two lanes, each sample sent as 16
bits.

![Transport mapping with M = 4, L = 2, S = 1, N = 14 and N' = 16, so F = 4. Each sample becomes a
16-bit word with two tail bits (T), cut into two octets, most significant first; lane 0 carries
converters 0 and 1, lane 1 converters 2 and 3.](primer_mapping.svg)

This mode, like the AD937x one with two lanes, has M different from L: it illustrates the standard,
not a mode that the core sizes correctly ([Known issues](#debug-known-issues)).

The receiver does the opposite: it collects the F octets of each lane, rebuilds the words and
drops the control and tail bits. With HD = 1, a sample may straddle two lanes; with CF > 0,
control bits are grouped in control words at the end of the frame.

In LiteJESD204, the transport layer (`LiteJESD204BTransportTX`, `LiteJESD204BTransportRX`) handles
several frames per link clock and is shared by JESD204B and JESD204C. It has no control bits and
no HD or CF format. It places the N conversion bits in the low bits of the N'-bit word, not at the
top, so a converter with N smaller than N' receives its samples shifted ([Known
issues](#debug-known-issues)).

## 8b/10b and control characters {#primer-characters}

Each lane is coded in 8b/10b: every octet becomes a 10-bit symbol, and a few control symbols, the
K characters, cannot appear in data. JESD204B gives five of them a role, listed in the table
below.

| Character | Symbol | Role |
|-----------|--------|------------------------------------------------------------------|
| /K/ | K28.5 | Code group synchronization: sent continuously while SYNC~ is low |
| /R/ | K28.0 | Start of a multiframe in the ILAS |
| /A/ | K28.3 | Lane alignment: end of a multiframe |
| /Q/ | K28.4 | Start of the configuration octets in the ILAS |
| /F/ | K28.7 | Frame alignment: end of a frame |

The receiver uses K28.5 to find the symbol boundaries in the bit stream, as any 8b/10b link does.
The coding and the comma alignment are explained in the LiteICLink manual, chapter "Serial links
in a nutshell".

In LiteJESD204, the characters are defined in `common.py` (`control_characters`). The link layer
works on octets with a K flag per octet (`data` and `ctrl`); the 8b/10b coding itself is done by
the LiteICLink PHY.

## Scrambling {#primer-scrambling}

Converter data can be very regular: a constant or a slow sine wave gives the same octets again and
again, which concentrates the emitted energy on a few frequencies. JESD204B can scramble the data
octets with the polynomial 1 + x^14 + x^15 to spread it.

The scrambler is *self-synchronous*: the descrambler computes its state from the received bits
only, so it locks after 15 bits without any seed exchange. Scrambling applies to the data octets
after the ILAS; the CGS and the ILAS are sent unscrambled. It is optional, and the SCR bit of the
configuration octets tells the receiver whether it is on.

In LiteJESD204, the scrambler and descrambler of `link.py` process 4 octets per link clock. They
are enabled by the `scrambling` argument of the cores, and the SCR bit of the ILAS comes from the
`scrambling` argument of the settings: both must agree.

## Frames, multiframes and alignment characters {#primer-frames}

A *multiframe* is K consecutive frames, so F x K octets per lane. JESD204B marks frame and
multiframe ends on the lanes without adding octets: it replaces the last octet of a frame by a
control character when the receiver can recover its value. The figure below shows the result on
one lane.

![Character replacement on one lane with F = 4 and K = 4. The last octet of a frame may be sent
as /F/, the last octet of the multiframe as /A/; in this example frame 1 kept its last octet,
because the replacement condition was not met.](primer_frames.svg)

The condition depends on scrambling:

- Without scrambling, the last octet of a frame is replaced when it equals the last octet of the
  previous frame: by /A/ at the end of a multiframe, by /F/ otherwise. The receiver puts the
  previous value back.
- With scrambling, the last octet of a frame is replaced when its value is that of the character
  itself, `0x7C` for /A/ at the end of a multiframe and `0xFC` for /F/. The receiver only clears
  the K flag, since the value is already right.

The /A/ characters arrive at known positions, one per multiframe. A receiver can watch them to
check that the lanes stay aligned, and realign when they move.

In LiteJESD204, the TX link inserts the characters (`AlignInserter`) and the RX link replaces them
(`AlignReplacer`). The RX link does not monitor the position of /A/ characters; [JESD204B link
layer](#link-204b) gives the details.

## Link start-up: CGS, ILAS and data {#primer-link-init}

A JESD204B link starts in three phases, driven by SYNC~ and timed by the multiframe clock. The
figure below shows them on one lane.

![JESD204B start-up on one lane. The transmitter sends /K/ while SYNC~ is low; the receiver
releases SYNC~ on an LMFC boundary; the transmitter starts the ILAS on the next LMFC boundary, four
multiframes long, then sends data.](primer_link_init.svg)

1. **CGS** (code group synchronization): the receiver holds SYNC~ low; the transmitter sends
   /K/ on every lane. Each receiver lane locks its symbol boundaries on the K28.5 commas. When all
   lanes have received at least four correct /K/ in a row, the receiver releases SYNC~ (high).
2. **ILAS** (initial lane alignment sequence): at the next LMFC boundary, the transmitter sends
   four multiframes. Each starts with /R/ and ends with /A/; the second carries /Q/ and the
   configuration octets.
3. **Data**: the transmitter sends the frames, scrambled when SCR is set, with the /F/ and /A/
   replacement above.

The receiver uses the ILAS to align the lanes: the /R/ of the first multiframe arrives on each
lane with its own delay, and the receiver buffers the early lanes until all have arrived (see
[Lane alignment and deskew](#primer-deskew)).

SYNC~ also reports problems. A short low pulse reports an error, such as a code error, without
restarting the link; a longer low level requests a new synchronization, and the transmitter
returns to CGS. The standard sets the minimum durations of both.

In LiteJESD204, the TX and RX link layers each run a state machine through these phases: CGS,
ILAS, data, plus a SYNC~ release state on the receive side. The RX link releases SYNC~ on the
first LMFC boundary where a lane word holds four /K/, and checks every ILAS octet against the
expected sequence (`ilas_check`).

The TX link ignores SYNC~ low pulses shorter than a 4-cycle timer and returns to CGS on longer
ones. [JESD204B link layer](#link-204b) describes both state machines.

## Configuration octets {#primer-ilas}

The second multiframe of the ILAS carries 14 *configuration octets* after /Q/: the link
parameters as the transmitter sees them. The receiver compares them with its own settings, which
catches a mismatched mode before any sample is used. The figure below gives their layout.

![The 14 configuration octets, bit 7 on the left. Most parameters are sent minus one (L-1, F-1,
K-1); grey bits are reserved; FCHK is the checksum.](primer_ilas.svg)

DID and BID identify the device and its bank, and LID the lane, so each lane carries a different
LID. SCR is the scrambling bit, SUBCLASSV the subclass and JESDV the version (1 for JESD204B).
ADJCNT, ADJDIR and PHADJ serve subclass 2 only. The checksum FCHK is the sum of the field values,
not of the octets, modulo 256.

In LiteJESD204, `JESD204BSettings.get_configuration_data` builds the 14 octets for a lane; with
`debug=True` it also prints the fields. The lane index of the core is the LID. ADJCNT, ADJDIR,
PHADJ, CF and HD are always 0, and SUBCLASSV is always 1.

CS is copied from the `cs` setting, but the transport layer never inserts control bits: keep
`cs=0` ([Known issues](#debug-known-issues)). The field table of `common.py`
(`configuration_data_fields`) gives the octet, bit offset and width of every field as in the
figure, HD at bit 7 of octet 10.

## Lane alignment and deskew {#primer-deskew}

The lanes of a link have different lengths on the board and different delays in the
transceivers. A frame sent on all lanes at once arrives at the receiver lane by lane, a few
octets apart. The receiver must remove this *skew* before it rebuilds the samples.

Each receiver lane writes its data into a FIFO from the /R/ that starts the ILAS. When the last
lane has started, the receiver reads all FIFOs together: from then on, octet n of every lane is
read in the same cycle. The /A/ characters of the following multiframes let it check that this
stays true.

The standard lets the receiver release the FIFOs at a fixed point after an LMFC boundary, set by
the *release buffer delay*. Releasing on the LMFC, rather than as soon as the last lane is in, is
what makes the latency the same at each start-up, as the next sections show.

In LiteJESD204, the RX core has one skew FIFO per lane, sized for four multiframes, and releases
all of them on an LMFC boundary once every lane is in the data phase. [TX and RX cores, LMFC/LEMC
and deskew](#cores) describes them and their status registers.

## Deterministic latency {#primer-latency}

The *latency* of a link is the time from a sample entering the transmitter to the same sample
leaving the receiver. It includes the transceivers, the FIFOs and the lane skew, and without care
it changes each time the link starts: a FIFO fills to a different level, a clock divider starts on
another phase.

Many systems need it to be the same at every start-up, the *deterministic latency* of the
standard. A phased-array radar or a multi-channel receiver combines samples of several converter
devices, and those samples must come from the same instant. A control loop needs a fixed delay to
stay stable.

JESD204B obtains it with the LMFC. If both devices count multiframes in phase, and the receiver
releases its FIFOs on an LMFC boundary, the total latency is a fixed number of multiframes. The
FIFOs absorb the variable parts, and the release point does not move. The LMFCs of the two
devices must also agree, which is the job of SYSREF.

## Device clock and SYSREF {#primer-sysref}

Each device runs a *local multiframe clock* (LMFC), a counter that wraps every multiframe. Two
counters fed by the same device clock run at the same rate, but they start at different times, so
their phases differ. SYSREF fixes the phase: on a SYSREF edge, every device resets its LMFC.

The figure below shows SYSREF, the LMFC and the release of two lanes in a receiver.

![SYSREF resets the LMFC phase. Lane 0 finishes its ILAS earlier than lane 1 and waits in its skew
FIFO; both lanes are released on the same LMFC boundary, so the latency is the same at each
start-up.](primer_lmfc.svg)

SYSREF must be sampled by the device clock with good timing margins in every device, so the clock
chip sends both with a controlled phase. It comes in three forms:

- **One-shot**: a single pulse after power-up.
- **Periodic**: a continuous clock whose period is a multiple of the LMFC period, so each edge
  falls on a boundary that already exists.
- **Gapped periodic**: a few periodic pulses, then silence, which avoids coupling a SYSREF tone
  into the converter during operation.

In LiteJESD204, each core has an LMFC counter (`LMFC` in `core.py`) clocked by the link clock. On
each rising edge of SYSREF it reloads with a value that compensates the input synchronizer and the
clock domain crossing, adjustable at run time through the `lmfc` register. The counter wraps at
the next power of two of the multiframe length, which equals F x K / 4 link clocks only when M
equals L; with a periodic SYSREF, a period that is not a power of two gives missing or misplaced
boundaries ([Known issues](#debug-known-issues)).

## Subclasses {#primer-subclasses}

JESD204B defines three *subclasses*, which differ in how the LMFC phase is set. The table below
compares them.

| Subclass | LMFC phase set by | Deterministic latency |
|----------|------------------------------------------|----------------------------------------------|
| 0 | Nothing (each device starts its own LMFC) | No |
| 1 | SYSREF, sampled by the device clock | Yes |
| 2 | SYNC~, sampled by the device clock | Yes, as long as SYNC~ timing can be met |

Subclass 2 reuses SYNC~ as the timing reference, which removes the SYSREF signal but limits the
device clock rate, since SYNC~ comes from the other device and must meet setup and hold times.
Subclass 1 is the usual choice at high rates.

In LiteJESD204, the cores implement subclass 1: SUBCLASSV is always 1 in the configuration
octets, and the TX and RX cores require a SYSREF input. Subclass 0 and subclass 2 are not
supported.

## Test patterns {#primer-test}

When a link is up but the samples look wrong, the fault can be in the lanes, in the mapping or in
the converter. JESD204B defines test patterns at several levels to separate them.

- **Transport layer patterns**: each converter sends a known sample value at each position of the
  frame. If the receiver gets them right, the lanes, the mapping and the parameters agree.
- **PRBS patterns** on each lane: they check the physical lane alone, before any JESD204 framing,
  and give a bit error count.
- Converters also have their own patterns, such as ramps, set through their configuration
  registers.

In LiteJESD204, the TX core has an STPL generator and the RX core an STPL checker with an error
counter (`stpl_enable`, `stpl_errors`): see [Transport layer and test patterns](#transport). PRBS
generators and checkers are part of the LiteICLink PHYs.

The STPL values are the core's own, not those of the short and long transport layer test patterns
of the standard. The checker validates a LiteJESD204 transmitter, not the built-in pattern of a
converter.

## Where to go next {#primer-next}

[JESD204C and 64b/66b](#jesd204c-primer) explains what JESD204C changes; [Architecture](#architecture)
shows how the core implements these mechanisms.
