# AGENTS.md: LiteJESD204

JESD204B/JESD204C core for LiteX: link layer (8b/10b for 204B, 64b/66b for 204C), transport layer,
RX/TX cores; transceivers come from LiteICLink. Package `litejesd204` (`litejesd204b` kept as
a compatibility alias).

Read the LiteX agent page first: https://github.com/enjoy-digital/litex/wiki/LiteX-for-AI-Agents (framework map, conventions, how to
verify a change, contribute back). Index of the whole wiki for agents: https://github.com/enjoy-digital/litex/wiki/llms.txt.

## Where things are

- `litejesd204/link.py` (204B), `link_204c.py` (204C), `transport.py`, `core.py`, `core_204c.py`, `common.py`.
- `litejesd204b/`: compatibility package for existing imports; `test/`.

## Verify a change

```sh
python3 -m pytest -v                                                # what CI runs
```

- Keep `litejesd204b` imports working (compatibility package) when moving code.
- Link bring-up depends on the converter's configuration (L, M, F, S, K and subclass): say which
  device and mode were used on hardware.

## Rules

- Style: https://github.com/enjoy-digital/litex/blob/master/doc/coding_style.md (match the
  surrounding file; `module: Description of the change.` commit titles; one change per commit).
- Never edit generated files (`build/`, `csr.h`, `csr.csv`, the Verilog): change the Python.
- One topic per pull request, from the default development branch, with what was tested and on
  which hardware; say that an agent wrote it and who supervised. Do not rename options or
  reformat unrelated code.
- Hardware: never flash a board or write its SPI flash unless the user asked; `--load` (volatile)
  is the default for experiments.

## Debug on hardware

Method: https://github.com/enjoy-digital/litex/wiki/Debug-A-SoC-On-Hardware (check the link and `--ident` first, registers before
traces, narrow LiteScope captures). `litex_mcp` gives the same loop as MCP tools (CSRs by name,
LiteScope captures, builds with parsed timing, simulation): https://github.com/enjoy-digital/litex/wiki/LiteX-for-AI-Agents#drive-a-soc-through-mcp.
