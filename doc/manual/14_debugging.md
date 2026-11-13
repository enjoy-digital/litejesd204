# Debugging {#debugging}

This chapter explains how to bring up and debug a JESD204 link on a board: a SYNC~ that stays low,
a core that never becomes ready, samples that come out wrong or with a latency that changes from
one start to the next.

It gives the method, a checklist for each standard, the probes to add for a logic analyzer capture
and the known issues of the code. Read it before touching hardware.

## Method {#debug-method}

The approach is to observe before changing anything, from the bottom of the stack to the top. A
JESD204 link fails in its lowest broken layer: a transceiver that does not lock makes every
register of the core look wrong.

The core has no debug module and no LiteScope groups of its own, so the registers come first and a
capture is only worth taking once the question is narrow.

1. Check the design: the bridge answers and the identifier matches the build.
2. Check the PHYs: PLL lock, transceiver initialization, a PRBS test on each lane, with the
   tools of LiteICLink ([PHYs: LiteICLink transceivers](#phys)).
3. Check the clocks: the device clock reaches the FPGA, the `jesd` domain runs, SYSREF toggles.
4. Enable the cores and follow the checklist of the standard, register by register.
5. Check the data with the STPL, then with real samples.
6. Capture a narrow LiteScope trace in the `jesd` domain only when a register cannot answer.
7. Reproduce the finding in simulation, fix it there, then check again on the board
   ([Simulation and tests](#simulation)).

The register names of this chapter are those of [Register reference](#registers). The banks take
the names of the control module attributes of the SoC; the examples use `jesd_tx_control` and
`jesd_rx_control`.

Note the converter, its mode (L, M, F, S, K, subclass) and the line rate of every test: link
bring-up depends on them, and a result without them cannot be compared.

## Access to the registers {#debug-access}

A LiteX SoC exposes the registers through a bridge (UARTBone, Etherbone or PCIe) and
`litex_server`. `litex_cli` then reads and writes them by name, through the `csr.csv` of the
build. Check the identifier first: a register map from another build gives wrong answers.

```sh
# Bridge over a serial port (or --udp for Etherbone)
litex_server --uart --uart-port /dev/ttyUSBx &
litex_cli --csr-csv csr.csv --ident
# Every register of the JESD204 control banks
litex_cli --csr-csv csr.csv --regs --filter jesd
# One register, then a write
litex_cli --csr-csv csr.csv --read jesd_rx_control_status
litex_cli --csr-csv csr.csv --write jesd_rx_control_control 0x1
```

The status flags and levels cross from the `jesd` domain to the system clock through `MultiReg`
synchronizers, bit by bit: a level that changes during the read, such as a skew FIFO level, can
come back inconsistent, so read it twice and trust two equal reads. The 32-bit counters,
`stpl_errors` and `crc_errors`, cross with a `BusSynchronizer` handshake and always read a value
the counter had.

## Bring-up checklist for JESD204B {#debug-checklist-b}

The steps below follow the link from its clocks to its data. Each step names the register to
read and what it shows when the step passes; stop at the first step that fails. The figure of
the link start-up is in [JESD204 in a nutshell](#jesd204-primer).

| Step | Check | Register (field) | Pass |
|-----|----------------------------------|----------------------------|--------------------------------|
| 1 | PHYs initialized, PRBS clean | LiteICLink PHY registers | No PRBS error on any lane |
| 2 | Cores enabled | `control` (`enable`) | 1 on TX and RX |
| 3 | RX: CGS received | RX `status` (`sync_n`) | Rises to 1 |
| 4 | RX: ILAS accepted | RX `status` (`ready`) | 1, `sync_n` stays 1 |
| 5 | TX: converter synchronized | TX `status` (`sync_n`) | 1 |
| 6 | TX: data phase | TX `status` (`ready`) | 1 |
| 7 | RX lanes deskewed | `skew_levels`, `skew_overflows` | Stable levels, no overflow |
| 8 | RX byte alignment stable | `lane_align` | Realign bits at 0 |
| 9 | Data | `stpl_enable`, `stpl_errors` | Error count 0 |

Steps 7 and 8 need the RX control built with `with_lane_status=True`; without it, the `skew_fifo`
field of `status` gives the level of lane 0 only. A TX core shows nothing for steps 3, 4, 7 and
8: the converter does the receiving, and its own status registers, read over its SPI port, give
the same information on its side.

SYSREF has no register. The LMFC counter reloads on each rising edge of SYSREF; without SYSREF it
free-runs, and the cores start, but with a latency that changes from one start to the next.
A capture of `jref` and of the `zero` strobe of the LMFC ([LiteScope probes](#debug-litescope))
shows whether SYSREF arrives.

## Reading SYNC~ {#debug-sync}

SYNC~ is the only signal the converter and the FPGA exchange outside the lanes, and the `sync_n`
field shows its level on both cores. Level 0 is a synchronization request; level 1 lets the
transmitter leave CGS. The table below reads its behaviour at the RX core, which drives SYNC~
towards an ADC.

| `sync_n` | `ready` | Meaning | Look at |
|------------------|---------|------------------------------------------|------------------------------------|
| Stays 0 | 0 | No valid CGS on every lane at an LMFC boundary | PHYs, comma alignment, lane rate, ADC lanes on |
| Toggles 0 and 1 | 0 | CGS seen, then ILAS rejected | ILAS check, configuration octets |
| Stays 1 | 0 | ILAS not started or not finished | ILAS start, F and K of both sides |
| Stays 1 | 1 | Data phase, lanes released | STPL, then samples |

The RX link waits for the four octets of a word to carry the K28.5 character before it raises
SYNC~, and only at an LMFC boundary.

It falls back to CGS when the ILAS differs from the expected one, unless the check is off, and
when CGS characters arrive again during the data phase. It never lowers SYNC~ to report an error.

At the TX core, which reads SYNC~ from a DAC, a low level held for four link clocks sends the link
back to CGS (`WaitTimer(4)`); shorter pulses are ignored. A `sync_n` that stays 0 means the DAC
does not receive CGS.

A `sync_n` that toggles means the DAC rejects the ILAS: compare its configuration with the
settings of the core. `polarity=1` of `register_jsync` inverts the level when the board inverts
SYNC~.

## ILAS mismatches {#debug-ilas}

The RX core compares every word of the ILAS it receives with the ILAS it would send: the
configuration octets of the lane, and a filler that counts the octets of the multiframe.

Any difference, one bit of one octet, sends the link back to CGS. Two causes cover most cases: a
parameter that differs between the converter and the settings, and a converter that fills the ILAS
differently.

The `ilas_check_disable` field of `control` makes the RX link accept any ILAS. When the link then
reaches the data phase, the lanes are good and the difference is in the content.

Print the configuration octets the core expects with `get_configuration_data(lid, debug=True)`
([Getting started](#getting-started)) and compare them, field by field, with the configuration the
converter reports; `JESD204BConfigurationData(octets=...)` parses received octets with the same
field table. The ILAS check is for bring-up; leave it on in a design that has passed.

With a control module, `ilas_check_disable` drives the check. Its reset value is 1 when
`default_ilas_check_disable=1` or when the core is built with `ilas_check=False`, 0 otherwise.

## Lanes, skew and alignment {#debug-lanes}

Once every lane has finished its ILAS, the RX core releases all lanes together at the next LMFC
boundary. Each lane waits in a skew FIFO of four multiframes; the level of each FIFO is the skew
of that lane, in link clocks, against the others.

| Register | Healthy | Unhealthy, and why |
|---------------------------|---------------------------------|-------------------------------------------------|
| `skew_levels` | Constant while running | A level that changes: a lane that restarts or slips |
| `skew_overflows` | All 0 | A lane finished its ILAS more than four multiframes before the release |
| `lane_align` (bits 0-7) | Same alignment at each start | Changing alignment: comma alignment of the PHY |
| `lane_align` (bits 8-11) | All 0 | /R/ seen at another octet position after lock: bit errors or a slip |

The byte alignment of a lane is the octet position of the K28.0 character (/R/) that starts the
ILAS. The aligner freezes it once the ILAS has started, so a bit error in the data phase cannot
rotate the lane; it only sets the realign flag. The sticky flags clear when the lane leaves the
data phase.

## Bring-up checklist for JESD204C {#debug-checklist-c}

A JESD204C link has no SYNC~, CGS or ILAS: each lane locks on its sync headers, then on the
extended multiblock structure of its sync words. A 64b/66b PHY of LiteICLink is needed on the
board ([status](#intro-status)). The steps below follow that order.

| Step | Check | Register (field) | Pass |
|-----|----------------------------------|----------------------------|--------------------------------|
| 1 | PHYs initialized | LiteICLink PHY registers | Transceivers ready |
| 2 | Cores enabled | `control` (`enable`) | 1 on TX and RX |
| 3 | Sync header lock | `lane_status` (`sh_lock`) | One bit per lane at 1 |
| 4 | Sync words found | `emb_debug` (`eomb_seen`) | One bit per lane at 1 |
| 5 | Extended multiblock lock | `lane_status` (`emb_lock`), `emb_debug` (`state`) | 1 per lane, state 2 (LOCK) |
| 6 | Lanes released | RX `status` (`ready`) | 1 |
| 7 | Payload intact | `crc_errors` | Constant |
| 8 | Data | `stpl_enable`, `stpl_errors` | Error count 0 |

A lane stuck at step 3 receives no valid 01 or 10 header: the gearbox slips one bit at a time
without finding 64 valid headers in a row. Check the lane rate, the 64b/66b mode of the PHY and
its slip input.

A lane that locks its headers but stays in state 0 (INIT) or 1 (HUNT) sees no end of extended
multiblock at the expected spacing: check E on both sides. When every lane locks but `ready`
stays 0, the lanes started on different extended multiblocks; the core restarts their skew FIFOs
until they agree.

## Data and the STPL {#debug-stpl}

The STPL replaces the converter samples with a known pattern, one value per converter and sample
position, so a mapping error shows as a count of wrong samples. On TX, `stpl_enable` replaces
the converter port with the generator; on RX, it sends the transport output to the checker
instead of the converter port.

`stpl_errors` counts the link clocks in which at least one sample differs from the pattern, not
the samples. It counts only while `stpl_enable` is set and the core is ready, and clears when
`stpl_enable` goes from 0 to 1. Set `stpl_enable` on both ends, wait for `ready`, and read
`stpl_errors`: 0 means no error since the pattern was enabled. To restart the count, write 0 then
1 to `stpl_enable`.

The pattern comes from the `seed_to_data` function of the transport layer; check that a converter
test mode produces the same values before using it against a converter. Between two LiteJESD204
cores, or in a lane loopback, it works as is.

## LMFC and deterministic latency {#debug-lmfc}

The latency of a link is deterministic when the LMFC (or LEMC) counters of the FPGA and of the
converter are aligned on the same SYSREF edge.

The `load_on_sysref` field of the `lmfc` register is the value the counter takes on that edge. Its
default, 5 on TX and the period minus 5 on RX, covers the SYSREF synchronizer and the elastic
buffer of the clock domain crossing.

To tune it, change the value, then wait for a SYSREF edge and restart the link: write 0 then 1 to
`enable`, on both sides. The value shifts the LMFC against SYSREF: the link starts with any value,
and the latency, measured on a ramp or a marker in the samples, moves with it.

The right value gives the expected latency, the same at every start. The 16-bit PHY path of the
JESD204B cores goes through an asynchronous FIFO whose latency is not fixed by construction; use
32-bit PHY words for deterministic latency ([TX and RX cores](#cores)).

## LiteScope probes {#debug-litescope}

The core has no LiteScope groups. The probes below, added to the SoC, show the start-up of the
first lane of a JESD204B RX core, cycle by cycle, in the `jesd` domain. The analyzer takes a
state machine directly and stores its state with the names of its states.

```python
from litescope import LiteScopeAnalyzer

analyzer_signals = [
    self.jesd_rx.jref,                    # SYSREF, as sampled.
    self.jesd_rx.lmfc.zero,               # LMFC boundary.
    self.jesd_rx.jsync,                   # SYNC~ driven by the core.
    self.jesd_rx.ready,                   # Lanes released.
    self.jesd_rx.links[0].fsm,            # RECEIVE-CGS, ASSERT-SYNC, RECEIVE-ILAS, RECEIVE-DATA.
    self.jesd_rx.links[0].sink.data,      # Octets from the PHY, after the CDC.
    self.jesd_rx.links[0].sink.ctrl,      # One K-character flag per octet.
    self.jesd_rx.links[0].alignment,      # Byte alignment.
    self.jesd_rx.links[0].realign,        # /R/ at another position.
    self.jesd_rx.skew_fifos[0].level,     # Skew FIFO level of lane 0.
]
self.analyzer = LiteScopeAnalyzer(analyzer_signals,
    depth        = 512,
    clock_domain = "jesd",
    samplerate   = jesd_clk_freq,
    csr_csv      = "analyzer.csv")
```

This list elaborates on the reference SoC of [Register reference](#registers), where it takes 52
bits per sample; `jesd_clk_freq` is the frequency of the `jesd` domain.

A TX core has no skew FIFO and no aligner, and the sink of its links carries the octets before
scrambling. Probe `jref`, `lmfc.zero`, `jsync`, `ready`, `links[0].fsm` (SEND-CGS, SEND-ILAS,
SEND-DATA), `links[0].source.data` and `links[0].source.ctrl`, the words sent to the PHY.

For a JESD204C RX core, probe `links[0].sync_word.state`, `links[0].ready`, `links[0].crc_error`
and `ready`; the sync header lock runs in the PHY RX domain and needs an analyzer of its own.

Trigger on the event of the question: the rising edge of SYNC~ for a CGS problem, a state of the
link for an ILAS problem.

```sh
litescope_cli --list
litescope_cli -r jsync --offset 128 --length 512
```

## Known issues {#debug-known-issues}

The code of the default branch has the limitations below. This is the one list of the manual:
other chapters link here. Each row gives the effect and how to work with it; "fix pending" names
the open pull request that changes the code, "issue" the open issue where a fix is discussed.

| Issue | Effect | Work with it |
|------------------------------|-----------------------------------------|------------------------------------|
| LMFC, framer and 204C multiblock check sized on the octets of one converter | LMFC period, frame marks and 204C frame check wrong when M differs from L | Use modes with M = L, check `lmfc_cycles`; fix pending (PR #14) |
| 204B frame size | The framer takes 1, 2 or 4 octets per frame only | Choose F = 1, 2 or 4 |
| F not checked | The F of the transport settings goes into the ILAS only; the framing uses the F derived from M, S, N' and L | Check F = M x S x N' / (8 x L); issue #31 |
| 204C frame size | F must divide 256 octets, whatever E: E > 1 does not enable F = 3 or 6 | Choose an F that divides 256; fix pending (PR #14) |
| Nibbles that do not fill octets | Octets per frame truncated | Use N' = 8 or 16 |
| Tail bits (N < N') | The N bits sit in the low bits of the N'-bit word | Shift samples in user logic; fix pending (PR #11) |
| Control bits | CS is advertised from the `cs` setting, but no control bit is sent | Keep `cs=0` |
| HD always 0 | Modes with F = 1 that split a sample over two lanes need HD = 1 | Choose modes with F of 2 or more |
| 204B unscrambled mode | Checked in simulation only, between a TX and an RX of this project | Keep scrambling on, the default, or check the link against the converter |
| 204B: two scrambling switches | Core argument and ILAS SCR bit can disagree | Give both the same value; issue #31 |
| RX error reporting | No SYNC~ error report, no /A/ check, no disparity or code counters | Use the converter's status and the STPL |
| STPL values | The core's own pattern, not the standard test patterns | Check against a LiteJESD204 TX only |
| Lane status width | 204B: levels and alignment of lanes 0-3, overflows of lanes 0-7; 204C: `emb_debug` of lanes 0-3 | Probe the other lanes with LiteScope |
| Skew levels, 8 bits | Levels of 256 or more wrap, also the 204C skew FIFO with E = 2 | Keep F*K/4 under 64 link clocks, E = 1; issue #31 |

The nibbles row follows from the settings: the core counts the nibbles of a sample with
`ceil(np//4)` and the octets per frame with an integer division. A frame whose nibbles do not
fill whole octets, as N' = 12 with S = 1, loses the remainder.

Where to go next: [Simulation and tests](#simulation) to reproduce a finding,
[Register reference](#registers) for the full register list.
