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
| Core | Core TX to core RX through stand-in PHYs | Data round trip, latency | C only |
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

The suite has 34 tests and runs in about two minutes; [Getting started](#getting-started) shows a
full run. The time goes to the simulations that run thousands of link clocks.

The `--durations` option of pytest lists the slowest tests; the run below, on the revision this
manual describes, shows that the two JESD204C core loopbacks take more than half of the total.

```console
$ python3 -m pytest -q --durations=8
[...]
53.80s call     test/test_core_204c.py::TestCore204C::test_core_loopback_e2
30.49s call     test/test_core_204c.py::TestCore204C::test_core_loopback
18.43s call     test/test_link_204c.py::TestLink204C::test_link_roundtrip_e2
9.29s call     test/test_link_204c.py::TestLink204C::test_link_roundtrip
9.27s call     test/test_link_204c.py::TestLink204C::test_link_crc_error_detection
7.17s call     test/test_link.py::TestLink::test_link_loopback
2.58s call     test/test_link.py::TestLink::test_link_tx
0.43s call     test/test_link_204c.py::TestCRC12::test_crc12_vs_model
34 passed in 133.32s (0:02:13)
```

With the pytest-xdist plugin installed, `-n auto` spreads the tests over the CPU cores.

## Test files by area {#sim-tests}

The table below groups the test files by layer. Each file checks the gateware against a Python
model or against a known data sequence.

| File | Area | What it checks |
|------------------------------|----------------|------------------------------------------------|
| `test_model.py` | Models | Transport mapping, test patterns, scrambling, alignment characters, 8b/10b encode and decode, model round trip |
| `test_scrambling.py` | 204B link | `Scrambler` and `Descrambler` against the model, loopback |
| `test_align.py` | 204B link | `Aligner` on words with /R/ at each octet position |
| `test_ilas.py` | 204B link | Configuration octets round trip, `ILASGenerator` output, `ILASChecker` with injected errors |
| `test_link.py` | 204B link | TX datapath against the model (scrambling, /A/ and /F/), TX to RX datapath loopback |
| `test_transport.py` | Transport | TX and RX mapping against the model, loopback, STPL generator and checker |
| `test_link_204c.py` | 204C link | Scrambler, CRC-12 and sync word against bit-serial models, `BlockSync` lock and slip, link round trips with E=1 and E=2, CRC error injection |
| `test_core_204c.py` | 204C core | Core TX to core RX through stand-in PHYs, E=1 and E=2: `ready`, STPL, constant latency |

The JESD204B tests stop at the link datapath: no test runs the JESD204B TX and RX cores
together, with the LMFC, SYNC~, CGS and ILAS state machines. [What is not
simulated](#sim-not) lists the other gaps.

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

`test_core_204c.py` is the only core-level test. It builds a TX core and an RX core of the same
settings, two lanes and four converters, and connects each lane through a stand-in PHY.

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

For a data-path test of a JESD204C mode, copy `test_core_204c.py` and change the settings
function at its top. The cores need 64-bit lanes and a converter width that holds an integer
number of samples ([Transport layer and test patterns](#transport)).

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

- The JESD204B cores end to end: no test runs a TX core into an RX core with SYNC~, the LMFC, CGS
  and ILAS.
- The unscrambled mode of the JESD204B link layer: the model of `test/model/link.py` does not
  implement it, and every link test runs with scrambling.
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
