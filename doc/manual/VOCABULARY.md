# Vocabulary of the LiteJESD204 manual

Project-specific writing rules, completing the generic `STYLE.md` of the manual kit.

## Names of the parts

- *the project* is LiteJESD204 (repository and Python package `litejesd204`). The old name
  LiteJESD204B appears only where the compatibility package `litejesd204b` is described.
- *TX core* sends samples to a DAC (`LiteJESD204BCoreTX`, `LiteJESD204CCoreTX`); *RX core*
  receives samples from an ADC (`LiteJESD204BCoreRX`, `LiteJESD204CCoreRX`). "The cores" means
  both. *Control module* is the register block of a core (`LiteJESD204BCoreControl`,
  `LiteJESD204CCoreControl`).
- *transport layer* (`transport.py`, shared by JESD204B and JESD204C), *link layer* (`link.py` for
  JESD204B, `link_204c.py` for JESD204C), *core* (`core.py`, `core_204c.py`). "Layer" is used as
  the standard uses it.
- *PHY* is the transceiver wrapper of one lane, a LiteICLink SerDes wrapper (`GTP`, `GTX`, `GTH`, `GTY`):
  the project has no PHY of its own. *Transceiver* is the hard block of the FPGA (GTP, GTX, GTH,
  GTY), as in the LiteICLink manual.
- *settings* are the Python objects that hold the link parameters (`JESD204BSettings`,
  `JESD204CSettings`); *configuration octets* are the 14 octets of link parameters sent in the
  ILAS.
- *link clock* is the clock of the `jesd` clock domain, one link beat per cycle: 4 octets per lane
  in JESD204B, one 66-bit block per lane in JESD204C. *Device clock* is the clock that the board
  clock chip sends to the converter device and to the FPGA; the link clock is derived from it.
- *register* in prose, never "CSR" (except the bus name "CSR bus" and identifiers).

## Protocol names

- Standards: *JESD204B* and *JESD204C* (no space, no hyphen); *JESD204* alone means the family.
  Sections cited as "JESD204B section 5.3.3.5" only where the code cites them.
- *converter* is one ADC or DAC channel, the unit that M counts; *converter device* is the chip.
  *Logic device* is the FPGA side, as the standard calls it.
- *sample*, *lane* (one serial pair, one direction), *link* (the lanes between one converter
  device and the FPGA), *frame*, *multiframe* (JESD204B); *block* (66 bits), *multiblock* (32
  blocks) and *extended multiblock* (E multiblocks) for JESD204C.
- *octet* for the 8-bit unit of a lane, never "byte" (except "byte alignment", the name of the
  JESD204B receiver step). *Nibble* is 4 bits.
- Parameters in capitals, upright, as the standard writes them: L, M, F, S, K, N, N', CS, CF, HD,
  E. Code identifiers keep their own case (`l`, `np`, `octets_per_lane`).
- *LMFC* (local multiframe clock, JESD204B) and *LEMC* (local extended multiblock clock,
  JESD204C); *SYSREF* in prose (`jref` in code); *SYNC~* in prose (`jsync` in code; the tilde
  marks an active-low signal); *CGS*, *ILAS*, *EoMB*, *EoEMB*, *CRC-12*.
- *STPL* is the transport layer test pattern of the core (the code expands it as "Simple Transport
  Layer Pattern"). The standard defines short and long transport layer test patterns; the values
  of the core's pattern are its own, not those of the standard.
- 8b/10b control characters as the standard writes them, between slashes: /K/ (K28.5), /R/
  (K28.0), /A/ (K28.3), /Q/ (K28.4), /F/ (K28.7). Symbol names such as K28.5 without code font.
- Line codes as *8b/10b* and *64b/66b*. *Sync header* is the 2-bit header of a 64b/66b block;
  *sync word* is the 32-bit word that the sync headers of one multiblock carry.
- *Subclass 0*, *subclass 1*, *subclass 2*; *deterministic latency*.

## Placeholders

- `<n>` is a lane index in a clock domain or register name (`jesd_phy<n>_rx`). Defined once in the
  Conventions of the front matter.

## Hardware names

- FPGA families: Artix-7, Kintex-7, Virtex-7, Kintex UltraScale, Kintex and Virtex UltraScale+,
  Zynq UltraScale+. Transceivers: GTP (Artix-7), GTX (Kintex-7), GTH (UltraScale GTHE3,
  UltraScale+ GTHE4), GTY (UltraScale+).
- Boards as LiteX-Boards names them: KC705, KCU105.
- Converter devices by part number only (AD9154, AD9174, AD937x), as the repository history and
  its public examples name them. An RF transceiver chip such as the AD937x is a *converter
  device*; *transceiver* stays the FPGA hard block.
- Units: line rates in Gbps, clocks in MHz.
