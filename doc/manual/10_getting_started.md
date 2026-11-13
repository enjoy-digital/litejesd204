```{=latex}
\part{Use it}
```

```{=html}
<h1 class="part">Part III. Use it</h1>
```

# Getting started {#getting-started}

This chapter takes you from a fresh machine to a JESD204 link running in simulation, with no
board and no FPGA tool. It installs the core, runs the tests, runs a link and prints its
configuration data. Each step gives the command, its output for this manual, and what to check
when yours differs.

## Prerequisites {#gs-install}

LiteJESD204 is a Python package, `litejesd204`, built on Migen and LiteX. The standard
installation of LiteX (`litex_setup.py`, see the installation page of the LiteX wiki) installs it
with LiteICLink and LiteX-Boards. It needs Python 3.7 or newer; the continuous integration runs
Python 3.9.

To work on a clone of the repository, install it in development mode:

```sh
git clone https://github.com/enjoy-digital/litejesd204
cd litejesd204
pip3 install -e .
```

The tools depend on what you run, as the table below shows. Nothing in this chapter needs a
vendor tool or Verilator: the tests run in the Migen simulator, in Python.

| Task | Tools |
|----------------------------------------|--------------------------------------------------|
| Tests and simulations of this chapter | Python 3, pytest, Migen, LiteX |
| Elaborating a SoC to Verilog | LiteX, LiteICLink, LiteX-Boards |
| Building a bitstream | The vendor tool of the FPGA (Vivado for AMD) |
| Accessing the registers from a host | `litex_server` and `litex_cli`, from LiteX |

## Step 1: run the test suite {#gs-tests}

The test suite checks each layer against Python models: the transport mapping, the scrambling,
the alignment characters, the ILAS, the JESD204C blocks and sync words, the control modules, a
JESD204B and a JESD204C core loopback, and the elaboration of the example design. Run it from the
root of the repository, as the continuous integration does:

```sh
python3 -m pytest -v
```

**What you should see.** Every test passes. The capture below was made on the default branch of
the repository; the list is cut.

```console
collecting ... collected 59 items

test/test_align.py::TestAlign::test_aligner PASSED                       [  1%]
[...]
test/test_core.py::TestCore::test_core_loopback PASSED                   [ 13%]
test/test_core.py::TestCore::test_core_loopback_f4 PASSED                [ 15%]
test/test_core_204c.py::TestCore204C::test_core_loopback PASSED          [ 16%]
test/test_core_204c.py::TestCore204C::test_core_loopback_e2 PASSED       [ 18%]
[...]
test/test_examples.py::TestExamples::test_kc705_gtx PASSED               [ 23%]
[...]
test/test_transport.py::TestTransport::test_transport_tx PASSED          [100%]

======== 59 passed, 1 warning, 71 subtests passed in 174.99s (0:02:54) =========
```

The run time depends on the machine. The warning is the combinational cycle that LiteX reports
when `test_examples.py` writes the Verilog of the example ([Build](#integ-build)).
[Simulation and tests](#simulation) lists the tests by area and explains how to add one.

**If not.** An import error names the missing package: `migen` or `litex` for LiteX itself,
`litejesd204` when the repository is not installed and pytest runs from another directory.
Rerun the LiteX installation or `pip3 install -e .`, then run pytest from the root of the
repository.

## Step 2: run a core loopback {#gs-loopback}

The JESD204C core test builds a complete link in simulation, shown in the figure below. A TX core
sends two lanes into two stand-in PHYs (class `FakePHY` of the test), which return the blocks to
an RX core, already aligned.

The test drives SYSREF, enables both cores with the test pattern, then checks that a ramp comes
back with a constant delay.

![The JESD204C core loopback of test/test_core_204c.py. Follow the cyan lanes: the TX core feeds
two stand-in PHYs that return each 66-bit block to the RX core. The test generator drives the
samples and SYSREF; the checks read the test pattern errors and the returned ramp.](gs_loopback.svg)

The test uses L = 2, M = 4, N = N' = 16, F = 4, S = 1, K = 32 and E = 1. Its method
`core_loopback()` returns what it recorded, so a few lines of Python print it. Run them from the
root of the repository:

```sh
python3 - <<'EOF'
from test.test_core_204c import TestCore204C
settings, stats = TestCore204C().core_loopback(e=1)
print("lemc_cycles :", settings.lemc_cycles)
print("tx ready at :", stats["tx_ready_at"])
print("rx ready at :", stats["rx_ready_at"])
print("stpl errors :", sorted(set(stats["stpl_errors"])))
tx, rx = stats["tx_ramp"], stats["rx_ramp"]
first = [c for c, v in enumerate(rx) if v in tx][0]
print("latency     :", first - tx.index(rx[first]), "jesd cycles")
EOF
```

**What you should see.** For this manual, the script ran in under 30 seconds and printed:

```console
lemc_cycles : 32
tx ready at : 33
rx ready at : 234
stpl errors : [0]
latency     : 11 jesd cycles
```

Read the lines as follows:

- **`lemc_cycles`.** One extended multiblock lasts 32 link clock cycles: 32 blocks, E = 1.
- **Ready times.** The TX core is ready at its first LEMC boundary after the enable. The RX core
  first needs the sync header lock, the extended multiblock lock and a common LEMC boundary.
- **`stpl errors`.** The checker counts only while the STPL is enabled and the RX core is ready,
  so the link clocks before `rx ready at` do not count: 0 on every read means no wrong sample once
  the link was up. It adds at most one per link clock.
- **Latency.** The ramp came back 11 link clock cycles after it left, on every cycle of the
  capture. The test fails if any cycle differs.

**If not.** `rx ready at` stays `None` when the RX core never locks, and the test fails on its
first check. The locks and counters are described in [JESD204C link layer](#link-204c), the
release of the lanes in [TX and RX cores](#cores).

The JESD204B core loopback, `test/test_core.py`, does the same with two lanes and two converters,
F = 2 and F = 4. The SYNC~ output of the RX core drives the TX core, so the links go through code
group synchronization and the ILAS before the data phase. Run it with
`python3 -m pytest -v test/test_core.py`.

## Step 3: print the configuration data {#gs-ilas}

A JESD204B TX core sends 14 configuration octets in the second multiframe of the ILAS, and an RX
core compares the ones it receives with its own ([JESD204 in a nutshell](#jesd204-primer)). The
settings object computes them. With `debug=True`, it also prints each field and the checksum:

```sh
python3 - <<'EOF'
from litejesd204.common import *
ps = JESD204BPhysicalSettings(l=4, m=4, n=16, np=16)
ts = JESD204BTransportSettings(f=2, s=1, k=32, cs=0)
settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)
settings.get_configuration_data(lid=0, debug=True)
EOF
```

**What you should see.** One line per field, with its value in decimal and in hexadecimal:

```console
did       : 90 / 0x5a
bid       :  5 / 0x5
adjcnt    :  0 / 0x0
lid       :  0 / 0x0
phadj     :  0 / 0x0
adjdir    :  0 / 0x0
l         :  3 / 0x3
scr       :  1 / 0x1
f         :  1 / 0x1
k         : 31 / 0x1f
m         :  3 / 0x3
n         : 15 / 0xf
cs        :  0 / 0x0
np        : 15 / 0xf
subclassv :  1 / 0x1
s         :  0 / 0x0
jesdv     :  1 / 0x1
cf        :  0 / 0x0
hd        :  0 / 0x0
res1      :  0 / 0x0
res2      :  0 / 0x0
chksum    : 166 / 0xa6
```

Most fields hold a parameter minus one, as the standard encodes them: `l` is 3 for four lanes,
`k` is 31 for 32 frames per multiframe. `subclassv` is 1 because the core supports subclass 1
only, and `jesdv` 1 means JESD204B. The checksum is the sum of the fields modulo 256.

Compare these values with the configuration of the converter, as its datasheet or its registers
give it. With the ILAS check enabled, an RX core that receives different values goes back to code
group synchronization instead of starting the data phase.

**If not.** A Python error at construction points to settings that the core cannot size. Check
the parameters against the relation F = M x S x N' / (8 x L); [Architecture](#architecture) lists
the values the settings derive from them.

## Where to go next {#gs-next}

[Integration](#integration) builds the same cores into a LiteX SoC with real transceivers,
[Examples and boards](#examples) lists the designs to start from, and [Debugging](#debugging)
gives the bring-up checklist for a board.
