# Simulation and tests {#simulation}

This chapter describes how LiteJESD204 is checked without a board: the Python models, the unit
tests of each layer, the core-level loopback, the waveforms and the continuous integration. It is
for contributors who change the gateware and for integrators who want to try a configuration or
reproduce a problem before building a bitstream.

## Verification strategy {#sim-strategy}

A JESD204 link that fails on a board shows little: SYNC~ stays low, `ready` never rises, or the
samples are wrong. Each layer is therefore checked in simulation first, at the cheapest level that
exercises it. Every test runs in the Migen simulator; none needs Verilator or a vendor tool.

| Level | What runs | Reference | Standard |
|---------------------|------------------------------------------------|------------------------------|-------------|
| Model | Python models of the protocol, alone | Hand-written vectors | B and C |
| Block | One module: scrambler, aligner, ILAS, CRC-12 | The Python models | B and C |
| Transport | Mapping of converters to lanes, STPL | Transport model | Shared |
| Link | Link TX datapath, link TX to RX | Models, data round trip | B and C |
| Core | Core TX to core RX through stand-in PHYs | Data round trip, latency | B and C |
| Elaboration | SoC with the four control modules | Register export | B and C |
| Hardware | A board, a transceiver and a converter | The converter | B and C |

The transceivers, the converters and the clock chips have no model in the project. The PHYs of
the tests are stand-ins that loop the TX words back to RX. The 8b/10b and 64b/66b coding of a
real PHY and the transceiver itself are therefore only exercised on a board ([PHYs: LiteICLink
transceivers](#phys)).

## Running the tests {#sim-run}

The tests are Python `unittest` classes in `test/`, run with pytest from the root of the
repository, as the continuous integration does. They import the `litejesd204` package of the
checkout and the models of `test/model/`.

```sh
# The whole suite, as the CI runs it
python3 -m pytest -v
# One file, or the tests whose name matches an expression
python3 -m pytest -v test/test_core_204c.py
python3 -m pytest -v -k "ilas or align"
```

The suite has 59 tests and runs in about three minutes; [Getting started](#getting-started)
shows a full run. The time goes to the simulations that run thousands of link clocks.

The `--durations` option of pytest lists the slowest tests; the run below, on the revision this
manual describes, shows that the two JESD204C core loopbacks take more than half of the total;
the JESD204B core loopbacks, with smaller multiframes, take a few seconds.

```console
$ python3 -m pytest -v --durations=8
[...]
61.83s call     test/test_core_204c.py::TestCore204C::test_core_loopback_e2
32.84s call     test/test_core_204c.py::TestCore204C::test_core_loopback
18.13s call     test/test_link_204c.py::TestLink204C::test_link_roundtrip_e2
8.91s call     test/test_link_204c.py::TestLink204C::test_link_roundtrip
8.73s call     test/test_link_204c.py::TestLink204C::test_link_crc_error_detection
8.60s call     test/test_link.py::TestLink::test_link_loopback
6.58s call     test/test_core_204c.py::TestCore204C::test_core_scrambling_argument
4.44s call     test/test_core.py::TestCore::test_core_loopback_f4
======== 59 passed, 1 warning, 71 subtests passed in 174.99s (0:02:54) =========
```

With the pytest-xdist plugin installed, `-n auto` spreads the tests over the CPU cores.

## Test files by area {#sim-tests}

The table below groups the test files by layer. Each file checks the gateware against a Python
model or against a known data sequence.

| File | Area | What it checks |
|------------------------------------------------|----------------|--------------------------------|
| `test_model.py` | Models | Transport mapping, test patterns, scrambling, alignment characters, 8b/10b encode and decode, model round trip |
| `test_scrambling.py` | 204B link | `Scrambler` and `Descrambler` against the model, loopback |
| `test_align.py` | 204B link | `Aligner` on words with /R/ at each octet position |
| `test_ilas.py` | 204B link | Configuration octets round trip, position and width of each field, `ILASGenerator` output, `ILASChecker` with injected errors |
| `test_link.py` | 204B link | TX datapath against the model (scrambling, /A/ and /F/), TX to RX datapath loopback |
| `test_link_alignment.py` | 204B link | Without scrambling: /A/ and /F/ inserted and restored for F=1, 2 and 4, constant data, repeated frames, full links through CGS and ILAS |
| `test_transport.py` | Transport | TX and RX mapping against the model, loopback, STPL generator and checker |
| `test_stpl.py` | Transport, cores | STPL checker enable and clear, N < 16 with `stpl_random`, no count while the RX core is not ready |
| `test_converter_data_width.py` | Cores | Invalid converter port widths rejected with a message |
| `test_settings_204c.py` | Settings | `JESD204CSettings` leaves the physical settings it receives unchanged |
| `test_link_204c.py` | 204C link | Scrambler, CRC-12 and sync word against bit-serial models, `BlockSync` lock and slip, link round trips with E=1 and E=2, CRC error injection |
| `test_lmfc.py` | Cores | `LMFC` period, also when it is not a power of two, reload on SYSREF, periodic SYSREF |
| `test_phy_clock_domains.py` | Cores | 204B and 204C cores on PHYs with `cd_tx` and `cd_rx`, one and two lanes, elaborated and run |
| `test_core.py` | 204B core | Core TX to core RX through stand-in PHYs, SYNC~ looped, F=2 and F=4: `ready`, STPL, constant latency |
| `test_core_204c.py` | 204C core | Core TX to core RX through stand-in PHYs, E=1 and E=2: `ready`, STPL, constant latency; `scrambling` argument of the cores |
| `test_control.py` | Control | Control modules with and without `sys_clk_freq` |
| `test_control_cdc.py` | Control | 32-bit error counters crossed to `sys` as whole words |
| `test_ilas_check.py` | Control | `ilas_check=False` of the RX core kept with a control module |
| `test_examples.py` | Examples | The KC705 example elaborated to Verilog, control registers in `csr.csv` |

[What is not simulated](#sim-not) lists the gaps.

## Python models {#sim-models}

The models in `test/model/` describe the protocol in plain Python, bit by bit or octet by octet,
without Migen. A test feeds the same input to a model and to the gateware and compares the
outputs, so a bug must be made twice, in two different styles, to pass.

| Model file | Content |
|-------------------------|-------------------------------------------------------------------------|
| `common.py` | `Control` octets, octet swap, the seed-to-data function of the patterns |
| `line_coding.py` | 8b/10b code tables and encoder, with running disparity |
| `link.py` | 204B scrambler and descrambler (1 + x^14 + x^15), /A/ and /F/ insertion and replacement |
| `transport.py` | Mapping of samples to lanes and back, short and long test patterns |
| `link_204c.py` | Bit-serial 204C scrambler and descrambler (1 + x^39 + x^58), CRC-12, sync word, block serialization |

The 204C models are bit-serial on purpose. The gateware computes 64 bits per clock, while the
model shifts one bit at a time as the standard describes it, so a parallel implementation that
reorders bits fails the comparison.

## Core loopback and stand-in PHYs {#sim-loopback}

`test_core_204c.py` and `test_core.py` are the core-level tests. `test_core_204c.py` builds a
JESD204C TX core and an RX core of the same settings, two lanes and four converters, and connects
each lane through a stand-in PHY.

The stand-in PHY has the stream ports of the PHY contract and copies its TX blocks to its RX side,
block aligned, so the sync header lock of the RX core locks without slipping.

The test declares the `jesd` domain and every `jesd_phy{n}_tx` and `jesd_phy{n}_rx` domain at the
same period. The elastic buffers of the clock domain crossings are therefore in the path, but
never see two different frequencies.

The test drives SYSREF with one pulse every four extended multiblocks, enables both cores with
the STPL selected, then checks four things:

- The TX core is ready no later than the RX core.
- The STPL error count of the RX core does not move once the pattern flows.
- A ramp written on the TX converter ports comes out of the RX converter ports with a constant
  latency.
- That latency is shorter than one extended multiblock.

`test_core.py` does the same for JESD204B, with two lanes and two converters, N = N' = 16,
K = 16 and F = 2 or 4, so a multiframe lasts 8 or 16 link clocks. Its stand-in PHY copies the
32-bit words and their K-character flags. The SYNC~ output of the RX core drives the TX core and
SYSREF comes every four multiframes, so the links run CGS and the ILAS before the data phase. The
checks are the same, with a latency shorter than two multiframes. Every run uses scrambling.

## Adding a configuration test {#sim-add}

A new converter mode starts with its settings. The test below checks the values the core
derives from them and the configuration octets of each lane; it runs in a fraction of a second
and catches a datasheet value typed wrong.

```python
import unittest

from litejesd204.common import *

class TestMyConfiguration(unittest.TestCase):
    def test_settings(self):
        # Parameters of the converter mode (datasheet).
        ps = JESD204BPhysicalSettings(l=2, m=2, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
        s  = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
        # Derived values used by the core.
        self.assertEqual(s.octets_per_lane, ts.f)
        self.assertEqual(s.lmfc_cycles, ts.f*ts.k//4)
        # Configuration octets of each lane, read back.
        for lid in range(ps.l):
            cd = JESD204BConfigurationData(s.get_configuration_data(lid))
            self.assertEqual(cd.lid, lid)
            self.assertEqual(cd.f + 1, ts.f)
            self.assertEqual(cd.k + 1, ts.k)
```

The first assertion checks that the settings agree with F, as the converter datasheet gives it;
the second compares the LMFC period with the one of the standard, F*K/4 link clocks. The second
fails for a mode with M different from L ([Known issues](#debug-known-issues)).

For a data-path test of a mode, copy `test_core.py` (JESD204B) or `test_core_204c.py` (JESD204C)
and change the settings function at its top. The cores need 32-bit (JESD204B) or 64-bit
(JESD204C) lanes and a converter width that is a multiple of N; they assert both
([Transport layer and test patterns](#transport)).

## Waveforms {#sim-vcd}

The tests that simulate gateware call the Migen `run_simulation`, which writes a VCD file when
it is given a name. Adding the argument to the call of the test under study is enough; the file
appears in the current directory and opens in GTKWave.

```python
run_simulation(fragment, {"jesd": generator(dut)}, clocks=clocks, vcd_name="core_204c.vcd")
```

```sh
python3 -m pytest -v test/test_core_204c.py -k "test_core_loopback"
gtkwave core_204c.vcd
```

A core run writes every signal of both cores. Look first at the `ready` signals of the links,
the state of the extended multiblock state machine of the RX link and the `zero` strobe of the
LEMC counter.

## Continuous integration {#sim-ci}

Every push and pull request runs `.github/workflows/ci.yml` on Ubuntu 22.04 with Python 3.9. The
job installs LiteX and its cores with `litex_setup.py --clone-depth=1 init install`, installs the
project, then runs two steps.

| Step | Command | Fails when |
|---------------------------|--------------------------------------------------|----------------------------------|
| Check Register Appendix | `csr_doc.py dump --check`, then `generate --check` | A register changed without regenerating the appendix |
| Run Tests | `python3 -m pytest -v` | A test fails |

The register step elaborates the reference SoC of [Register reference](#registers) without a
vendor toolchain, so it also catches a change that breaks the elaboration of a control module.
The manual itself is checked by `.github/workflows/doc.yml` ([Maintaining this
manual](#maintenance)).

## What is not simulated {#sim-not}

The simulations check the logic, not the electrical link or the converter. The list below is what
only a board, or a test yet to be written, can show.

- The unscrambled mode of the JESD204B link layer against a reference: the model of
  `test/model/link.py` does not implement it, so `test_link_alignment.py` only compares the RX
  data with the TX data, and the core loopbacks run with scrambling.
- The 16-bit PHY path of the JESD204B cores, through an asynchronous FIFO and a width converter:
  every test uses 32-bit words or 64-bit blocks.
- Clock domains at different frequencies or phases: all domains share one period.
- SYSREF sampling against a real device clock, the LMFC load values and the deterministic latency
  across a power cycle.
- A real transceiver: 8b/10b coding and comma alignment, 64b/66b gearbox slips, polarity, lane
  swaps and bit errors.
- The converter side: its configuration, its ILAS, its SYNC~ timing and its reaction to errors.

Where to go next: [Debugging](#debugging) for the same checks on a board, [Getting
started](#getting-started) for a first run of the test suite.
