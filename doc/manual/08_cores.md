# TX and RX cores {#cores}

This chapter describes the four cores, the top-level classes a design instantiates: their
parameters and signals, the SYSREF and SYNC~ connections, the LMFC and LEMC counters, the RX lane
deskew and the control modules. Read it to instantiate a core and to understand what makes its
latency deterministic.

Subclass 1 and the role of SYSREF are explained in [JESD204 in a nutshell](#jesd204-primer).

## At a glance {#cores-glance}

| Core | Direction | Pads | Registers |
|-----------------------------|-----------|----------|---------------------------------------|
| `LiteJESD204BCoreTX` | FPGA to a DAC | SYSREF, SYNC~ in | `LiteJESD204BCoreControl` |
| `LiteJESD204BCoreRX` | ADC to the FPGA | SYSREF, SYNC~ out | `LiteJESD204BCoreControl` |
| `LiteJESD204CCoreTX` | FPGA to a DAC | SYSREF | `LiteJESD204CCoreControl` |
| `LiteJESD204CCoreRX` | ADC to the FPGA | SYSREF | `LiteJESD204CCoreControl` |

Each core contains the transport layer, the test pattern block, the LMFC or LEMC counter, and per
lane a link layer and a clock domain crossing; the RX cores add a skew FIFO per lane
([Architecture](#architecture)).

## Parameters {#cores-params}

The four constructors take the same first arguments: the list of PHYs, one per lane, the
settings and the width of a converter field.

```python
core = LiteJESD204BCoreRX(phys, settings, converter_data_width=32,
    scrambling  = True,  # Scrambler and descrambler of the link layers.
    ilas_check  = True,  # RX JESD204B only: go back to CGS on an ILAS mismatch.
    stpl_random = True,  # Test pattern formula, the same at both ends.
)
```

| Parameter | Cores | Default | Role |
|--------------------------------|--------|---------|---------------------------------------|
| `phys` | All | | PHYs in lane order |
| `jesd_settings` | All | | `JESD204BSettings` or `JESD204CSettings` |
| `converter_data_width` | All | | Bits per converter field ([Transport](#tr-records)) |
| `scrambling` | All | `True` | JESD204B scrambling; no effect in JESD204C |
| `ilas_check` | B RX | `True` | Initial value of the ILAS check |
| `stpl_random` | All | `True` | Test pattern values ([Test patterns](#tr-stpl)) |

In JESD204C, the scrambling follows the `scrambling` setting of `JESD204CSettings`
([Limitations](#lc-limitations)). With a control module, the `control` register sets the ILAS
check, whatever the value of `ilas_check` ([Control modules](#cores-control)).

## Signals {#cores-signals}

| Signal | Cores | Direction | Role |
|------------------|--------|-----------|-----------------------------------------------------|
| `sink` | TX | In | Converter samples, `converter0` to `converter<M-1>` |
| `source` | RX | Out | Converter samples |
| `enable` | All | In | Low: every link layer held in reset |
| `ready` | All | Out | All lanes in their data phase |
| `stpl_enable` | All | In | Test pattern instead of the samples |
| `jsync` | B | In or out | Logical SYNC~ level, 0 requests a synchronization; `polarity` applies at the pad |
| `jref` | All | In | SYSREF |
| `ilas_check` | B RX | In | ILAS comparison enabled |

All signals are in the `jesd` domain, except `jref` and the pad side of SYNC~. The user logic
reads `source` and writes `sink` once per link clock, without handshake: the samples flow on
every clock, and `ready` tells when they are meaningful.

`ready` of the TX core is the AND of its link layers, registered. It rises when all lanes enter
the data phase in JESD204B, and at the first LEMC boundary after `enable` in JESD204C. `ready`
of the RX core changes only on an LMFC or LEMC boundary, where it releases the skew FIFOs
([Lane deskew](#cores-deskew)).

## SYSREF and SYNC~ {#cores-pads}

Every core takes SYSREF through `register_jref`, and the JESD204B cores take SYNC~ through
`register_jsync`. Both accept a `Signal`, or a record with `p` and `n` fields for a differential
pad pair; anything else raises an error. A core checks at finalization that they were called.

```python
tx.register_jsync(platform.request("dac_sync"))           # Differential input.
tx.register_jref(sysref)                                   # Signal or pads.
rx.register_jsync(platform.request("adc_sync"), polarity=1) # Inverted output.
rx.register_jref(sysref)
```

The pad names above are examples of a platform file. On the TX core, SYNC~ is an input: it goes
through a differential input buffer if needed, then a synchronizer into `jesd`. On the RX core,
it is an output, through a differential output buffer for a record.

The `polarity` argument set to 1 inverts SYNC~ at the pad, for a board that swaps the pair. It
applies before the synchronizer on the TX core and after `jsync` on the RX core, so `jsync` is
always the logical level.

SYSREF goes through a differential input buffer for a record, then straight to the counter of
the core, which registers it in `jesd`. There is no synchronizer: subclass 1 requires SYSREF to
be sampled by the device clock at a known edge. The board and the timing constraints of the
design must give that setup and hold margin.

## LMFC and LEMC {#cores-lmfc}

Each core has one counter of link clocks, the local multiframe clock (LMFC) in JESD204B and the
local extended multiblock clock (LEMC) in JESD204C. Both are the class `LMFC`, sized with
`lmfc_cycles` or `lemc_cycles`. Its `zero` output marks the boundaries, on which the link layers
start their sequences and the RX core releases its lanes.

The counter increments on every link clock. On a rising edge of SYSREF, it reloads with a load
value instead. SYSREF is registered three times on its way, so the reload happens a few link
clocks after the edge. With a load value of x, the next boundary comes `lmfc_cycles` - x link
clocks after the reload when `lmfc_cycles` is a power of two.

A periodic SYSREF reloads the counter at each edge. Its period must be a multiple of the LMFC
period, and a power of two on this version: the counter does not wrap at `lmfc_cycles`
([Limitations](#cores-limitations)).

The figure below shows the counter in a JESD204B link: SYSREF sets its phase, and the boundaries
then pace the start of the ILAS on the TX side.

![LMFC in a JESD204B link. Look at the boundaries: SYSREF reloads the counter, the boundaries
follow every lmfc_cycles link clocks, and the TX lanes start their ILAS on the first boundary
after SYNC~ is released.](cores_lmfc.svg)

| Core | Default load | Comment in the code |
|---------|-----------------------------|-------------------------|
| TX | 5 | "jref + ebuf latency" |
| RX | `lmfc_cycles` - 5 | "jref + ebuf latency" |

The code comment attributes the 5 link clocks to the SYSREF registers and the elastic buffer of
the crossing: the TX counter runs ahead and the RX counter behind by that amount. The `lmfc`
register changes the load value at run time; a new value takes effect on the next SYSREF edge.

## Lane deskew {#cores-deskew}

The lanes of a link reach the RX core at different times: the converter, the board traces and the
transceivers each add their own delay. The RX core removes the difference with one skew FIFO per
lane, released for all lanes on the same boundary, as the figure below shows.

![Lane deskew. Follow the two lanes: each one enters its skew FIFO as soon as its link layer
reaches the data phase; the FIFOs fill by different amounts until the LMFC boundary releases
them together, and the transport layer receives aligned lanes.](cores_deskew.svg)

**JESD204B.** The skew FIFO of a lane is held empty until its link layer is ready, then written on
every link clock. At each LMFC boundary, the core samples the AND of the lane ready signals. Once
all are ready, `ready` rises and every FIFO is read from then on. Each FIFO then holds the
difference between the end of its ILAS and the release, and the lanes leave aligned.

**JESD204C.** A lane starts writing its FIFO at the first word of an extended multiblock, after
its extended multiblock lock. At the middle of the extended multiblock, the core checks that
every lane has started; a lane that started alone restarts on the next one, so that all lanes
start on the same extended multiblock. The release happens at a LEMC boundary once all lanes
have started.

A skew FIFO holds 4 multiframes (`4 x lmfc_cycles` words) or 4 extended multiblocks
(`4 x lemc_cycles`). The code comment explains the margin: lanes can become ready up to about two
multiframes apart. A FIFO that fills up sets a sticky overflow flag of its lane, cleared when the
lane goes back to synchronization.

## Deterministic latency {#cores-latency}

Deterministic latency means the same delay from a sample at the converter to the user logic, or
back, after every start of the link. The core contributes in three ways:

- **Counters.** The LMFC and LEMC take their phase from SYSREF, so the boundaries fall at the
  same time after every start, given a SYSREF captured at a known edge.
- **Boundaries.** The TX lanes start their ILAS on a boundary, and the RX skew FIFOs release on a
  boundary: the arrival time of each lane within a multiframe is absorbed.
- **Crossings.** The elastic buffers of the 32-bit and 64-bit PHY words keep the pointer offset
  they get at reset, whatever the data.

Three things are not fixed by the core:

- **16-bit PHY words.** The asynchronous FIFO and width converter of this path can change their
  latency from one start to the next ([Clock domains](#arch-clocks)).
- **Transceiver buffers.** The latency of the transceiver TX and RX buffers is the PHY's
  business ([PHYs: LiteICLink transceivers](#phys)).
- **Boundary crossing.** If the lanes become ready close to a release boundary, a small change of
  arrival can move the release by one multiframe. Moving the load value with the `lmfc` register
  moves the boundary away from the arrival time.

## Control modules {#cores-control}

A control module gives software access to a core through registers in `sys`. It takes the core
and synchronizes every field to and from `jesd`. `LiteJESD204BCoreControl` serves both JESD204B
cores and `LiteJESD204CCoreControl` both JESD204C cores.

```python
self.jesd_rx_control = LiteJESD204BCoreControl(self.jesd_rx, sys_clk_freq,
    default_enable             = 0, # control.enable at reset.
    default_ilas_check_disable = 0, # control.ilas_check_disable at reset.
    default_stpl_enable        = 0, # stpl_enable at reset.
    with_lane_status           = True, # RX only: per-lane registers.
)
```

| Register | Control | Content |
|----------------------|---------|--------------------------------------------------------------|
| `control` | B, C | `enable`; B: `ilas_check_disable` |
| `status` | B, C | `ready`, B: `sync_n`; `skew_fifo`: level of the lane 0 FIFO (RX) |
| `stpl_enable` | B, C | Test pattern on |
| `stpl_errors` | B, C | Count of the checker ([Test patterns](#tr-stpl)) |
| `lmfc` | B, C | `load_on_sysref`: load value of the LMFC or LEMC |
| `skew_levels` | B RX | FIFO levels of lanes 0 to 3, 8 bits each |
| `skew_overflows` | B RX | Sticky overflow flags of lanes 0 to 7 |
| `lane_align` | B RX | Byte alignment of lanes 0 to 3, sticky realign flags |
| `lane_status` | C | `sh_lock` and `emb_lock` of lanes 0 to 7 |
| `crc_errors` | C | CRC-12 errors of all lanes, accumulated |
| `emb_debug` | C | Lock state of lanes 0 to 3, sticky end-of-multiblock seen |

The JESD204B per-lane registers exist only with `with_lane_status`, on an RX core, so the default
register map stays the same. The register names in a SoC carry the name of the control module,
such as `jesd_rx_control_status`. [Register reference](#registers) lists every field.

The 32-bit counters, `stpl_errors` and `crc_errors`, cross to `sys` bit by bit, while they
change: one read can mix bits of two values. Read a counter twice and use the value when two
readings agree.

`sys_clk_freq` is accepted for compatibility and not used.

## Limitations {#cores-limitations}

- **LMFC period when M and L differ.** `lmfc_cycles` is computed from `octets_per_frame`, the
  octets of one converter in a frame, instead of F (`octets_per_lane`). With L = 2, M = 4, F = 4
  and K = 32, it gives 16 link clocks instead of F x K / 4 = 32; the framer uses the same wrong
  size while the ILAS uses the right one.
- **LMFC period not a power of two.** The counter has the width of `lmfc_cycles` but does not
  wrap at it: between two SYSREF edges, its period is the next power of two. F x K / 4 = 10 gives
  16; 32 x E with E = 3 gives 128 instead of 96.
- **Periodic SYSREF with such a period.** Each SYSREF edge reloads the counter before or after it
  wraps. When the load value plus the period does not exceed the next power of two, the counter
  never reaches 0: no boundary, a JESD204B TX core stays in CGS and a JESD204C TX core never
  becomes ready. Otherwise the boundaries come once per period, at a wrong position.
- **TX registers.** The TX control modules also create RX fields that stay at 0: `skew_fifo`, and
  in JESD204C `lane_status`, `crc_errors` and `emb_debug`.
- **Lane coverage.** The per-lane registers cover lanes 0 to 3 or 0 to 7 as the table shows; the
  8-bit level fields can be narrower than a FIFO level.
- **Counters.** The 32-bit counters cross to `sys` bit by bit (see above).
- **Tail bits.** The transport layer places a sample with N < N' in the low bits of its word
  ([Control bits and tail bits](#tr-tail-bits)).

Each item is listed with its workaround in [Known issues](#debug-known-issues).

## In the code {#cores-code}

| Class | File and role |
|---------------------------------|---------------------------------------------------------|
| `LiteJESD204BCoreTX` | `litejesd204/core.py`: JESD204B TX core |
| `LiteJESD204BCoreRX` | `litejesd204/core.py`: JESD204B RX core, skew FIFOs |
| `LiteJESD204BCoreControl` | `litejesd204/core.py`: JESD204B registers |
| `LMFC` | `litejesd204/core.py`: LMFC and LEMC counter |
| `LiteJESD204BTXCDC`, `RXCDC` | `litejesd204/core.py`: JESD204B crossings |
| `LiteJESD204CCoreTX` | `litejesd204/core_204c.py`: JESD204C TX core |
| `LiteJESD204CCoreRX` | `litejesd204/core_204c.py`: JESD204C RX core, block lock, skew FIFOs |
| `LiteJESD204CCoreControl` | `litejesd204/core_204c.py`: JESD204C registers |

Where to go next: [PHYs: LiteICLink transceivers](#phys) for the lanes, [Integration](#integration)
for a complete SoC, [Debugging](#debugging) for the bring-up order of the registers.
