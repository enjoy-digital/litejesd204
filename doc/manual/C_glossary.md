# Glossary {#glossary}

The terms of JESD204 and of LiteJESD204 used in this manual, in alphabetical order. Each entry
points to the chapter that explains it. Parameters are written in capitals, as in the standard.

| Term | Meaning |
|------------------------|----------------------------------------------------------------------------------|
| 8b/10b | Line code of JESD204B: each octet is sent as a 10-bit symbol, with control symbols for alignment. See [JESD204 in a nutshell](#jesd204-primer) |
| 64b/66b | Line code of JESD204C: each 64-bit block is sent with a 2-bit sync header. See [JESD204C and 64b/66b](#jesd204c-primer) |
| ADC | Analog-to-digital converter: sends samples to the FPGA, through an RX core. See [JESD204 in a nutshell](#jesd204-primer) |
| Block | 64 bits of payload of a JESD204C lane plus its sync header, one link clock of the core. See [JESD204C and 64b/66b](#jesd204c-primer) |
| CDC | Clock domain crossing between the `jesd` domain and the clock domains of a PHY. See [Architecture](#architecture) |
| CF | Control words per frame clock and link; always 0 in LiteJESD204. See [JESD204 in a nutshell](#jesd204-primer) |
| CGS | Code group synchronization: the K28.5 characters a JESD204B transmitter sends while SYNC~ is low. See [JESD204B link layer](#link-204b) |
| Comma | Bit pattern of the K28.5 symbol that lets a receiver find the symbol boundaries. See [JESD204 in a nutshell](#jesd204-primer) |
| Configuration octets | The 14 octets of the second ILAS multiframe that describe the link (L, M, F, K and others). See [JESD204 in a nutshell](#jesd204-primer) |
| Converter | One ADC or DAC channel, the source or sink of one stream of samples; M converters per link. See [Transport layer and test patterns](#transport) |
| CRC-12 | Check of each JESD204C multiblock, carried in the sync word of the next one. See [JESD204C link layer](#link-204c) |
| CS | Control bits per sample; LiteJESD204 inserts none. See [Transport layer and test patterns](#transport) |
| DAC | Digital-to-analog converter: receives samples from the FPGA, through a TX core. See [JESD204 in a nutshell](#jesd204-primer) |
| Deterministic latency | A link latency that is the same at every start, set by SYSREF and the LMFC. See [TX and RX cores](#cores) |
| Device clock | Clock of the converter from the clock chip; the `jesd` domain of the FPGA runs from it. See [PHYs: LiteICLink transceivers](#phys) |
| E | Multiblocks per extended multiblock (JESD204C). See [JESD204C and 64b/66b](#jesd204c-primer) |
| Elastic buffer | Small FIFO between two clocks of the same frequency, with a fixed latency. See [Architecture](#architecture) |
| EMB | Extended multiblock: E multiblocks, the JESD204C equivalent of the multiframe. See [JESD204C and 64b/66b](#jesd204c-primer) |
| EoEMB | End of extended multiblock: bit of the sync word that marks the last multiblock of an EMB. See [JESD204C and 64b/66b](#jesd204c-primer) |
| EoMB | End of multiblock: pattern of the sync word that marks the end of a multiblock. See [JESD204C and 64b/66b](#jesd204c-primer) |
| F | Octets per frame and lane. See [JESD204 in a nutshell](#jesd204-primer) |
| Frame | F octets of each lane, carrying S samples of each converter. See [JESD204 in a nutshell](#jesd204-primer) |
| Gearbox | The part of a 64b/66b PHY that cuts the bit stream into blocks; a slip moves the block boundary by one bit. See [JESD204C link layer](#link-204c) |
| HD | High density: a sample split across lanes; always 0 in LiteJESD204. See [JESD204 in a nutshell](#jesd204-primer) |
| ILAS | Initial lane alignment sequence: four multiframes a JESD204B transmitter sends after CGS, with the configuration octets. See [JESD204B link layer](#link-204b) |
| K | Frames per multiframe. See [JESD204 in a nutshell](#jesd204-primer) |
| K character | 8b/10b control symbol, as K28.5; the JESD204B characters /R/, /A/, /Q/, /K/ and /F/ are K characters. See [JESD204 in a nutshell](#jesd204-primer) |
| L | Lanes of a link. See [JESD204 in a nutshell](#jesd204-primer) |
| Lane | One serial line between the converter and the FPGA, on one transceiver. See [JESD204 in a nutshell](#jesd204-primer) |
| LEMC | Local extended multiblock clock: the JESD204C counterpart of the LMFC. See [TX and RX cores](#cores) |
| Link | The lanes, the SYNC~ signal and the logic that connect one converter device to the FPGA. See [JESD204 in a nutshell](#jesd204-primer) |
| Link clock | Clock of the `jesd` domain: one 32-bit word (204B) or one block (204C) per lane and clock. See [Architecture](#architecture) |
| LMFC | Local multiframe clock: counter of the multiframe period, reloaded by SYSREF. See [TX and RX cores](#cores) |
| M | Converters of a link. See [JESD204 in a nutshell](#jesd204-primer) |
| Multiblock | 32 blocks of a JESD204C lane, the period of one sync word. See [JESD204C and 64b/66b](#jesd204c-primer) |
| Multiframe | K frames, the period of the LMFC (JESD204B). See [JESD204 in a nutshell](#jesd204-primer) |
| N | Conversion bits per sample. See [JESD204 in a nutshell](#jesd204-primer) |
| N' | Bits of the word that carries a sample, N plus control and tail bits. See [JESD204 in a nutshell](#jesd204-primer) |
| Octet | Eight bits, the unit of the JESD204 lanes. See [JESD204 in a nutshell](#jesd204-primer) |
| PHY | The LiteICLink transceiver wrapper of a lane. See [PHYs: LiteICLink transceivers](#phys) |
| PRBS | Pseudo-random bit sequence sent by a PHY to test a lane. See [PHYs: LiteICLink transceivers](#phys) |
| S | Samples per converter and frame. See [JESD204 in a nutshell](#jesd204-primer) |
| Sample | One value of one converter, N bits in an N'-bit word. See [Transport layer and test patterns](#transport) |
| Scrambler | Self-synchronous scrambler of the lanes: 1 + x^14 + x^15 (204B), 1 + x^39 + x^58 (204C). See [JESD204B link layer](#link-204b) |
| Skew FIFO | Per-lane buffer of an RX core that releases all lanes together. See [TX and RX cores](#cores) |
| STPL | Transport layer test pattern of the cores: known values per converter and sample position, generated by TX and checked by RX. See [Transport layer and test patterns](#transport) |
| Subclass | Deterministic latency mode of JESD204B: 0 without, 1 with SYSREF, 2 with SYNC~; LiteJESD204 implements subclass 1. See [JESD204 in a nutshell](#jesd204-primer) |
| Slip | A one-bit shift of the block boundary of a 64b/66b PHY, requested by the RX core until the sync headers lock. See [JESD204C link layer](#link-204c) |
| Sync header | The two bits in front of a JESD204C block, 01 or 10. See [JESD204C and 64b/66b](#jesd204c-primer) |
| Sync word | The 32 sync header bits of a multiblock: EoMB, EoEMB, CRC-12 and command bits. See [JESD204C and 64b/66b](#jesd204c-primer) |
| SYNC~ | Active-low signal from the JESD204B receiver to the transmitter that requests synchronization (`jsync` in the code). See [JESD204B link layer](#link-204b) |
| SYSREF | Reference signal of the clock chip that aligns the LMFC or LEMC of every device (`jref` in the code). See [TX and RX cores](#cores) |
| Tail bits | Bits of an N'-bit word beyond the N conversion bits and the control bits. See [Transport layer and test patterns](#transport) |
| Transport layer | Mapping of the converter samples to the octets of the lanes. See [Transport layer and test patterns](#transport) |
