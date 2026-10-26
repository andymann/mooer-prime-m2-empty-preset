# Mooer Prime M2 — Empty Preset Generator

A Python tool for creating and inspecting preset files for the **Mooer Prime M2**
multi-effects unit (firmware 1.50).

![Mooer Prime M2](https://raw.githubusercontent.com/andymann/mooer-prime-m2-empty-preset/main/docs/mooer-prime-m2.png)

---

## The Problem

The Mooer app always pre-loads new presets with a full set of effect modules. You
can bypass each one individually, but you **cannot remove them**, and there is no
blank starting preset. Bypassed modules are not truly absent — they are still
stored in the preset file and still appear in the signal chain view.

This tool solves that by reverse-engineering the `.preset` file format and
generating new files directly, including a **truly empty preset** with no modules
at all.

The included `empty.preset` is ready to import into the Mooer app immediately —
no Python required.

---

## Files

| File | Description |
|---|---|
| `empty.preset` | Ready-to-use empty preset (zero modules, valid checksum) |
| `mooer_preset.py` | Python tool to inspect and generate preset files |

---

## Quick Start — Use the Preset Directly

1. Copy `empty.preset` to your device or import it via the Mooer app.
2. Rename it inside the app to whatever you like.
3. Add effects from scratch.

---

## Using the Python Tool

### Requirements

- Python 3.8 or newer
- No third-party packages needed — the tool uses only the standard library

### Set Up a Virtual Environment (recommended)

```bash
# Create a venv in the project folder
python3 -m venv .venv

# Activate it
# On macOS / Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# No packages to install — the script has no dependencies
```

To deactivate the venv when you're done:

```bash
deactivate
```

### Commands

#### `info` — Inspect a preset file

Prints the preset name, CRC validity and a list of all effect modules.

```bash
python3 mooer_preset.py info MyPreset.preset
```

Example output:

```
MyPreset.preset
  name='Brit RG'  crc=OK  modules=4
    @0x1a4  type=2  ON   params=[100, 0, 50, 75, 0, 0, 0, 0]
    @0x1c8  type=3  ON   params=[60, 0, 0, 0, 0, 0, 0, 0]
    @0x1ec  type=5  off  params=[0, 0, 0, 0, 0, 0, 0, 0]
    @0x210  type=7  ON   params=[30, 45, 0, 0, 0, 0, 0, 0]
```

You can pass multiple files at once:

```bash
python3 mooer_preset.py info *.preset
```

---

#### `empty` — Create a preset with no modules

Takes any valid `.preset` file as a structural template and produces a new file
with the module list completely cleared.

```bash
python3 mooer_preset.py empty template.preset output.preset "My Empty"
```

The name argument is optional and defaults to `Empty`.

The output file will have a valid checksum and will load correctly on the device.

---

#### `bypass` — Create a preset with all modules bypassed

Keeps all modules from the template but sets every one to bypassed (off).
Parameters are preserved, so switching a module back on restores its settings.

```bash
python3 mooer_preset.py bypass template.preset output.preset "All Off"
```

---

## File Format Summary

Every `.preset` file is exactly **1206 bytes**, little-endian throughout.

| Offset | Length | Contents |
|--------|--------|----------|
| `0x000` | 8 bytes | Fixed header / format signature |
| `0x008` | 320 bytes | Zero padding |
| `0x148` | 6 bytes | Magic marker `FF FF 44 AA 20 01` |
| `0x14E` | 64 bytes | Mirror field (device-managed copy of data at `+0x44`) |
| `0x18E` | 2 bytes | Global value (always `120`) |
| `0x190` | 16 bytes | Preset name, ASCII, null-padded |
| `0x1A4` | variable | Module list: 36-byte records, terminated by all-zero record |
| `0x474` | 2 bytes | Preset ID (not validated by device) |
| `0x476` | 62 bytes | `0xFF` padding |
| `0x4B4` | 2 bytes | CRC-16/GENIBUS over `0x148`–`0x4B3` |

Each module record (36 bytes):

| Bytes | Contents |
|-------|----------|
| 0–1 | Module type (1–9) |
| 2–3 | Enabled flag (1 = on, 0 = bypassed) |
| 4–35 | 16 × uint16 parameters |

The checksum is **CRC-16/GENIBUS**: polynomial `0x1021`, initial value `0xFFFF`,
no bit reflection, final XOR `0xFFFF`, stored little-endian. Any externally edited
preset must have this recomputed before the device will accept it.

---

## Background

This format was reverse-engineered from exported preset files by comparing binary
diffs between matched on/off pairs, then brute-forcing the CRC polynomial. The
variable-length module list (rather than fixed slots) was confirmed using a
4-module preset, which revealed the all-zero terminator pattern.

Full write-up: [andyland.info](https://andyland.info) *(coming soon)*

---

## License

MIT
