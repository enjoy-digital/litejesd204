# Build options {#build-options}

This appendix lists the parameters of the project: the settings classes, the constructors of the
cores and of their control modules, and the constants of the link layers that no constructor
exposes.

LiteJESD204 has no generator and no command line; every option is a Python argument of a class,
given in the SoC that instantiates it. The chapters explain when to use each option; this appendix
gives the names and the defaults.

## Settings {#opt-settings}

The settings describe the converter mode: they hold the parameters of the converter datasheet,
named as in the standard, and the values the core derives from them. One settings object serves
the TX and the RX core of a link ([JESD204 in a nutshell](#jesd204-primer)).

| Class and argument | Default | Meaning |
|------------------------------------------------|-------------|------------------------------------|
| `JESD204BPhysicalSettings(l)` | required | L, lanes |
| `JESD204BPhysicalSettings(m)` | required | M, converters |
| `JESD204BPhysicalSettings(n)` | required | N, conversion bits per sample |
| `JESD204BPhysicalSettings(np)` | required | N', bits per sample word |
| `JESD204BTransportSettings(f)` | required | F, octets per frame and lane |
| `JESD204BTransportSettings(s)` | required | S, samples per converter and frame |
| `JESD204BTransportSettings(k)` | required | K, frames per multiframe |
| `JESD204BTransportSettings(cs)` | required | CS, control bits per sample, advertised in the ILAS |
| `JESD204BSettings(did, bid)` | required | Device and bank identifiers of the ILAS |
| `JESD204BSettings(framing)` | `True` | Frame marks of the 204B TX datapath, for /A/ and /F/ |
| `JESD204BSettings(scrambling)` | `True` | SCR bit of the ILAS |
| `JESD204CSettings(e)` | `1` | E, multiblocks per extended multiblock |
| `JESD204CSettings(scrambling)` | `True` | Scrambling of the 204C links |

`JESD204BSettings` and `JESD204CSettings` take the physical and transport settings as their first
two arguments.

The physical settings fix the subclass to 1 and the JESD204 version to 204B.
`JESD204CSettings` sets the version to 204C in the physical settings object it receives, so give
it its own object, and forces `framing` to `False`. The ILAS advertises CS, but the transport
layer inserts no control bits; CF and HD are always 0.

The settings derive these values, used by the cores:

| Attribute | Value | Use |
|----------------------------|----------------------------------------|----------------------------------|
| `nconverters`, `nlanes` | M, L | Ports of the cores |
| `nibbles_per_word` | `ceil(np//4)` | Transport mapping |
| `octets_per_frame` | S times the nibbles, divided by 2 | Octets of one converter per frame |
| `octets_per_lane` | `octets_per_frame*M//L` | Octets per lane and frame, F |
| `lmfc_cycles` | `octets_per_frame*K//4` | LMFC period in link clocks (204B) |
| `lemc_cycles` | `32*E` | LEMC period in link clocks (204C) |

`octets_per_lane` equals F. `octets_per_frame` counts the octets of one converter, so it equals
F, and `lmfc_cycles` equals F*K/4, only when M equals L ([Known issues](#debug-known-issues)).
`JESD204CSettings` also asserts that a multiblock, 256 octets, holds a whole number of
`octets_per_frame`.

The JESD204B links assert that `octets_per_frame` is 1, 2 or 4 and that K is a multiple of the
frames per link clock. `get_configuration_data(lid, debug=False)` returns the 14 configuration
octets of lane `lid`, checksum included, and prints them with `debug=True`.

## Cores {#opt-cores}

The four cores take the arguments below; `ilas_check` exists on the JESD204B RX core
(`LiteJESD204BCoreRX`) only. `phys` is the list of PHYs, one per lane in lane order;
`converter_data_width` is the width of each converter port, in bits per link clock.

| Cores | Argument | Default | Effect |
|---------------|------------------------------------|--------------|-----------------------------------|
| All | `phys` | required | PHYs, one per lane |
| All | `jesd_settings` | required | `JESD204BSettings` or `JESD204CSettings` |
| All | `converter_data_width` | required | Bits per converter and link clock |
| All | `scrambling` | `True` | 204B: scrambler of the datapath; 204C: no effect |
| All | `stpl_random` | `True` | Pseudo-random STPL values, else the seeds |
| 204B RX | `ilas_check` | `True` | Reset value of the ILAS check |

The converter port carries `converter_data_width // N` samples per link clock. The lanes of the
transport layer are then that number of samples times N' times M/L bits wide, and the cores need
32-bit lanes for JESD204B and 64-bit lanes for JESD204C. The JESD204C cores assert this width;
the JESD204B cores do not check it ([Known issues](#debug-known-issues)).

With the default `scrambling`, the JESD204B datapath scrambles; the SCR bit of the ILAS comes from
the settings, so give both the same value. The JESD204C links take scrambling from
`JESD204CSettings` only. The control module overrides `ilas_check` with its own field.

| Method | Cores | Argument | Effect |
|-------------------------------|------------------|--------------------------|--------------------------------------|
| `register_jsync` | 204B TX, 204B RX | `jsync`, `polarity=0` | Connects SYNC~: a `Signal`, or a record with `p` and `n` for a differential pair; `polarity=1` inverts it |
| `register_jref` | All | `jref` | Connects SYSREF: a `Signal`, or a differential pair |

A JESD204B core must have both methods called before the SoC is finalized, and a JESD204C core
`register_jref`; the cores assert it. A PHY with an attribute `n` gives its clock domains the
names `jesd_phy{n}_tx` and `jesd_phy{n}_rx`; without it, the position of the PHY in `phys` is
used.

## Control modules {#opt-controls}

A control module gives a core its registers ([Register reference](#registers)). It takes the core
as its first argument.

| Classes | Argument | Default | Effect |
|------------|-------------------------------------------------|--------------|-------------------------|
| Both | `core` | required | Core to control |
| Both | `sys_clk_freq` | required | Unused |
| Both | `default_enable` | `0` | Reset value of the enable field |
| Both | `default_stpl_enable` | `0` | Reset value of `stpl_enable` |
| 204B | `default_ilas_check_disable` | `0` | Reset value of the ILAS check disable field |
| 204B | `with_lane_status` | `False` | Adds the lane status registers (RX) |

"Both" stands for `LiteJESD204BCoreControl` and `LiteJESD204CCoreControl`, "204B" for the first
only. The lane status registers are `skew_levels`, `skew_overflows` and `lane_align`. With
`default_enable=1`, the core starts after reset without software.

## Constants of the link layers {#opt-link}

The values below are fixed in the code: the cores create the modules with them and no argument
changes them. Changing one means changing the source.

| Constant | Value | Module |
|------------------------------------|-------------------------------|---------------------------------|
| Scrambler seed (204B) | `0x7f80` | `Scrambler`, `Descrambler` |
| ILAS length | 4 multiframes | `ILASGenerator`, `ILASChecker` |
| ILAS filler | Octet counter (`with_counter=True`) | `ILASGenerator`, `ILASChecker` |
| SYNC~ low time before CGS | 4 link clocks | `LiteJESD204BLinkTX` |
| Skew FIFO depth | 4 multiframes or 4 extended multiblocks | Core RX |
| Clock domain crossing depth | 4 words | Core TX and RX |
| LMFC and LEMC load, TX | 5 | Core TX |
| LMFC and LEMC load, RX | period minus 5 | Core RX |
| Valid headers to lock | 64 | `BlockSync` |
| Invalid headers to unlock | 16 (`thresh_sh_err`) | `BlockSync` |
| Wait after a slip | 32 PHY RX clocks (`slip_latency`) | `BlockSync` |
| Missing markers to unlock | 8 (`thresh_emb_err`) | `SyncWordRX` |
| End of extended multiblock to lock | 4 | `SyncWordRX` |

The LMFC and LEMC loads are the reset values of the `lmfc` register, which software can change at
run time ([Debugging](#debugging)).

## Register appendix {#opt-registers}

The register appendix has its own tool, `doc/manual/tools/csr_doc.py`. It elaborates the
reference SoC of `doc/manual/registers.py` without a toolchain and regenerates `A_registers.md`.

| Command | Effect |
|------------------------------------------|----------------------------------------------------|
| `csr_doc.py dump` | Writes the snapshot `doc/manual/csr/kc705_stand_in.json` |
| `csr_doc.py dump --check` | Fails if the snapshot differs from the gateware |
| `csr_doc.py generate` | Writes `A_registers.md` from the snapshot |
| `csr_doc.py generate --check` | Fails if the appendix is not up to date |
