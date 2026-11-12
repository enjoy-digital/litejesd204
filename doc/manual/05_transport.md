# Transport layer and test patterns {#transport}

This chapter describes the transport layer, the part of the core that maps converter samples
onto lane octets and back, and the test pattern blocks attached to it. Read it to size the
converter interface of a core and to check a link with a test pattern. The mapping rules of the
standard are explained in [JESD204 in a nutshell](#jesd204-primer).

## At a glance {#tr-glance}

| Item | Value |
|-----------------------|----------------------------------------------------------------|
| Classes | `LiteJESD204BTransportTX`, `LiteJESD204BTransportRX` |
| Test pattern classes | `LiteJESD204BSTPLGenerator`, `LiteJESD204BSTPLChecker` |
| Standards | JESD204B and JESD204C: the same classes |
| User side | One field per converter, `converter0` to `converter<M-1>` |
| Lane side | One field per lane, `lane0` to `lane<L-1>` |
| Lane width | 32 bits (JESD204B), 64 bits (JESD204C) |
| Logic | Combinational: wiring only, no latency |
| Clock domain | `jesd` |
| Not supported | Control bits (CS), CF, HD, tail bits at their standard place |

## Converter and lane records {#tr-records}

The user side of a core is a record with one field per converter. Each field carries the samples
of that converter for one link clock, packed side by side: sample 0 in the low N bits, the next
sample above it.

The width of a field is `converter_data_width`, a parameter of the core; the number of samples
per link clock is that width divided by N.

The lane side has one field per lane, whose width follows from the converter side: samples per
clock x N' x M / L. The link layer takes 32-bit lanes in JESD204B and 64-bit lanes in JESD204C,
so `converter_data_width` must give exactly that width.

| Link | Lane width | `converter_data_width` |
|----------|------------|--------------------------------|
| JESD204B | 32 bits | 32 x L x N / (M x N') |
| JESD204C | 64 bits | 64 x L x N / (M x N') |

The JESD204C cores assert the lane width. The JESD204B cores do not: a wrong
`converter_data_width` usually builds without a clear error. The lane is then padded or cut where
it meets the 32-bit link layer, or, for a value below N, Migen rejects a zero width
([Known issues](#debug-known-issues)).

## Mapping {#tr-mapping}

The transport layer builds each frame in the order of the standard. It takes the S samples of
converter 0, then those of converter 1, up to converter M-1. Each sample is cut into nibbles,
most significant first, and pairs of nibbles make octets.

Lane 0 receives the first F octets of the frame, lane 1 the next F, and so on up to lane L-1.
The figure below shows one link clock of a link with L = 2, M = 4, N = N' = 16 and S = 1, so
F = 4. Each converter gives one 16-bit sample per clock (`converter_data_width` = 16) and each
lane carries one frame of 4 octets.

![Transport mapping for L = 2, M = 4, N' = 16, S = 1. Follow converter 0: its sample splits into
a high and a low octet, which fill the first two octets of lane 0; converter 1 fills the next
two, and converters 2 and 3 fill lane 1.](tr_mapping.svg)

The transport layer handles this mode with M different from L, but the link layer sizing does not
on this version ([Known issues](#debug-known-issues)): use the figure to read the mapping, not as a
mode to build.

Octet 0 of a lane word, in bits 7 to 0, is the first octet on the line. The sample of converter
0 therefore goes out high octet first, as the standard requires.

When the lane word holds several frames, the transport layer repeats the mapping for each frame,
the first frame in the low octets. With L = 4, M = 4, N' = 16, S = 1 and F = 2, each converter
gives two samples per clock (`converter_data_width` = 32): lane 0 carries sample 0 of converter 0
in octets 0 and 1, then sample 1 in octets 2 and 3.

The RX transport layer applies the same mapping in reverse. Both directions are combinational
and add no latency.

## Control bits and tail bits {#tr-tail-bits}

The transport layer carries samples only. It inserts no control bits, so CS must be 0, and the
CF and HD modes of the standard are not implemented.

When N is smaller than N', the standard places the N bits of the sample at the top of the N'-bit
word and fills the bits below with tail bits. The transport layer places the sample in the low N
bits instead, with zeros above it. The RX side keeps the low N bits of each word, so a TX core
and an RX core of this project agree with each other, but not with a converter.

With N = 14 and N' = 16, for example, an ADC sends its sample in bits 15 to 2. The RX core
returns bits 13 to 0: the two tail bits at the bottom and the two top bits of the sample lost.

Use configurations with N = N' ([Known issues](#debug-known-issues)). Another way is to declare
N = N' and take the top N bits in the user logic; the configuration octets then advertise N = N',
which the converter or the ILAS check may reject.

## Test patterns {#tr-stpl}

The test pattern blocks check the transport mapping and the lanes end to end, without real
samples. The generator produces the transport layer test pattern of the core (STPL, "Simple
Transport Layer Pattern" in the code).

The pattern is a fixed value for each sample position of a frame, the same in every frame. The
checker compares what it receives with the same values.

The figure below shows where the blocks sit. In the TX core, `stpl_enable` replaces the user
samples with the generator output. In the RX core, it sends the transport output to the checker
instead of the user side, which then reads zeros.

![Test pattern path. Follow the cyan path: with stpl_enable set, the generator replaces the user
samples at the TX transport input, and the checker takes the RX transport output and counts the
clocks with a mismatch.](tr_stpl.svg)

The value of sample position *j* of converter *i* comes from a seed, the converter index in the
high octet and the sample index in the low octet. With `stpl_random` set (the default), the seed
goes through a multiplication that spreads the bits over 16 bits; otherwise the seed is the
value.

The generator cuts the value to N bits. The checker compares with the full 16-bit value, so with
N under 16 it only works with `stpl_random` cleared ([Known issues](#debug-known-issues)). Both
ends must use the same setting.

```python
def seed_to_data(seed, random=True):
    return ((seed + 1)*0x31415979 + 1) & 0xffff if random else seed
```

The checker increments its 32-bit `errors` counter by one for each link clock in which at least
one sample differs. Software cannot clear the counter; only a reset of the `jesd` domain does. It
also counts while the checker is not selected, since its input is then zero, which differs from
the pattern in practice.

To test a link, enable the pattern at both ends, wait for the link to be ready, then read
`stpl_errors` twice: a link without error keeps the same value.

The pattern is the formula above, so the checker passes against a TX core of this project or
against a source programmed with the same sample values. The generator has an `errors` signal
that nothing drives.

## In the code {#tr-code}

| Class | File and role |
|--------------------------------------|-----------------------------------------------------|
| `LiteJESD204BTransportTX` | `litejesd204/transport.py`: samples to lane octets |
| `LiteJESD204BTransportRX` | `litejesd204/transport.py`: lane octets to samples |
| `LiteJESD204BSTPLGenerator` | `litejesd204/transport.py`: test pattern generator |
| `LiteJESD204BSTPLChecker` | `litejesd204/transport.py`: test pattern checker, `errors` |

The tests `test/test_transport.py` and `test/test_model.py` check the mapping against a Python
model of the standard ([Simulation and tests](#simulation)).

Where to go next: [JESD204B link layer](#link-204b) for what happens to the lane words,
[TX and RX cores](#cores) for `stpl_enable` and the `stpl_errors` register.
