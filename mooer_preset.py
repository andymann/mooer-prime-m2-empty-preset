#!/usr/bin/env python3
"""Mooer Prime M2 (FW 1.50) .preset tool.

Usage:
  python3 mooer_preset.py info     file.preset ...
  python3 mooer_preset.py empty    template.preset out.preset [name]
  python3 mooer_preset.py bypass   template.preset out.preset [name]

Commands:
  info    Print name, CRC status and module list for one or more preset files.
  empty   Create a new preset with no effect modules at all (truly empty signal
          chain), using the given file as a structural template.
  bypass  Create a new preset that keeps all modules from the template but sets
          every one to bypassed.

Layout (1206 bytes, little-endian uint16):
  0x000  header 03 00 42 01 00 02 6C 01, zero padding
  0x148  record start: FF FF 44 AA, 0x0120
  0x14E  mirror of 0x192..0x1D1 (device writes a copy 0x44 bytes earlier;
         the first 6 bytes of the copy are overwritten by the marker)
  0x18E  uint16 global value (120 in every preset seen)
  0x190  preset name, 16 bytes null-padded ASCII
  0x1A4  module list: 36-byte records [model][enabled][16 x param],
         terminated by an all-zero record; up to 9 modules (one per type 1..9)
  0x474  uint16 preset ID (not validated, survives edits)
  0x476  62 x 0xFF
  0x4B4  uint16 CRC-16/GENIBUS over 0x148..0x4B3
"""
import struct
import sys

SIZE, REC, MIRROR = 1206, 0x148, 0x44
NAME_OFF, NAME_LEN = 0x190, 16
MOD_OFF, MOD_SIZE, MOD_END = 0x1A4, 0x24, 0x474
CRC_OFF = 0x4B4


def crc16_genibus(data: bytes) -> int:
    """CRC-16/GENIBUS: poly 0x1021, init 0xFFFF, no reflection, xorout 0xFFFF."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc ^ 0xFFFF


def modules(buf):
    """Return a list of (offset, model, enabled, params) for each active module."""
    out = []
    for s in range(MOD_OFF, MOD_END - MOD_SIZE + 1, MOD_SIZE):
        rec = buf[s:s + MOD_SIZE]
        if not any(rec):
            break
        model, enabled = struct.unpack_from('<HH', rec)
        out.append((s, model, enabled, struct.unpack_from('<16H', rec, 4)))
    return out


def finalize(buf: bytearray, name: str):
    """Write the preset name, rebuild the mirror field and recalculate the CRC."""
    nb = name.encode('ascii')[:NAME_LEN - 1]
    buf[NAME_OFF:NAME_OFF + NAME_LEN] = nb.ljust(NAME_LEN, b'\0')
    # Rebuild the mirror exactly as the device does on save
    buf[0x14E:0x18E] = buf[0x14E + MIRROR:0x18E + MIRROR]
    struct.pack_into('<H', buf, CRC_OFF, crc16_genibus(buf[REC:CRC_OFF]))


def load(path):
    buf = bytearray(open(path, 'rb').read())
    assert len(buf) == SIZE, f"{path}: expected {SIZE} bytes, got {len(buf)}"
    return buf


def info(path):
    buf = load(path)
    stored = struct.unpack_from('<H', buf, CRC_OFF)[0]
    ok = stored == crc16_genibus(buf[REC:CRC_OFF])
    name = bytes(buf[NAME_OFF:NAME_OFF + NAME_LEN]).split(b'\0')[0].decode('ascii', 'replace')
    print(f"{path}")
    print(f"  name={name!r}  crc={'OK' if ok else 'BAD'}  modules={len(modules(buf))}")
    for s, model, en, p in modules(buf):
        print(f"    @{s:#05x}  type={model}  {'ON ' if en else 'off'}  params={list(p[:8])}")
    return ok


def make_empty(template, out, name="Empty"):
    """Create a preset with no modules (empty signal chain)."""
    buf = load(template)
    buf[MOD_OFF:MOD_END] = bytes(MOD_END - MOD_OFF)   # zero out all module slots
    finalize(buf, name)
    open(out, 'wb').write(buf)
    print(f"Written: {out}  (0 modules, name={name!r})")


def make_bypass(template, out, name="Bypassed"):
    """Create a preset that keeps all modules from the template but bypasses them all."""
    buf = load(template)
    for s, *_ in modules(buf):
        struct.pack_into('<H', buf, s + 2, 0)          # set enabled = 0
    finalize(buf, name)
    open(out, 'wb').write(buf)
    print(f"Written: {out}  (all modules bypassed, name={name!r})")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, *a = sys.argv[1:]
    if cmd == 'info':
        sys.exit(0 if all(info(p) for p in a) else 1)
    elif cmd == 'empty':
        make_empty(*a)
    elif cmd == 'bypass':
        make_bypass(*a)
    else:
        print(f"Unknown command: {cmd!r}", file=sys.stderr)
        sys.exit(1)
