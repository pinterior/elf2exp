#!/usr/bin/env python3

import itertools
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
from elftools.elf.relocation import RelocationSection


@dataclass
class ElfAddress:
    base: int
    end: int
    entry: int


@dataclass
class LinkerOptions:
    stack: int


def check_relocation(elf: ELFFile):
    for s in elf.iter_sections():
        if isinstance(s, RelocationSection) and 0 < s.num_relocations():
            raise RuntimeError("input file must not contain relocations.")


def get_addrs(elf: ELFFile) -> ElfAddress:
    entry = elf.header["e_entry"]

    alloc_sects = [s for s in elf.iter_sections() if bool(s["sh_flags"] & SH_FLAGS.SHF_ALLOC)]
    if len(alloc_sects) == 0:
        return ElfAddress(base=0, end=0, entry=entry)

    ranges: list[tuple[int, int]] = [(a["sh_addr"], a["sh_addr"] + a["sh_size"]) for a in alloc_sects]
    base = min(r[0] for r in ranges)
    end = max(r[1] for r in ranges)

    return ElfAddress(base=base, end=end, entry=entry)


def get_image(objcopy: str, input: Path) -> bytes:
    with NamedTemporaryFile("rb") as temp:
        subprocess.run([objcopy, "-O", "binary", "--", input, temp.name], check=True)
        return temp.read()


def align(x: int, u: int):
    return (x // -u) * -u


def make_exp_image(image: bytes, addrs: ElfAddress, opts: LinkerOptions) -> bytes:
    h = bytearray(384)
    p = bytearray(128)

    def hdr_word(n: int, v: int):
        struct.pack_into("<H", h, n, v)

    def hdr_dword(n: int, v: int):
        struct.pack_into("<L", h, n, v)

    initial_esp = align(addrs.end + opts.stack, 4)

    struct.pack_into("2s", h, 0x00, b"P3")
    hdr_word(0x02, 1)                              # flat model
    hdr_word(0x04, len(h))                         # header size
    hdr_dword(0x06, len(h) + len(p) + len(image))  # file size

    hdr_dword(0x0c, len(h))  # offset of parameter
    hdr_dword(0x10, len(p))  # size of parameter

    hdr_dword(0x14, len(h) + len(p))  # offset of relocations
    hdr_dword(0x18, 0)                # size of relocations

    hdr_dword(0x26, len(h) + len(p))  # offset of load image
    hdr_dword(0x2a, len(image))       # size of load image

    hdr_dword(0x56, initial_esp - addrs.base - len(image))  # minimum alloc
    hdr_dword(0x5a, 0xffffffff)                             # maximum alloc

    hdr_dword(0x5e, addrs.base)   # offset
    hdr_dword(0x62, initial_esp)  # ESP
    hdr_dword(0x68, addrs.entry)  # EIP

    hdr_dword(0x74, len(image))  # size of loaded image

    def param_word(n: int, v: int):
        struct.pack_into("<H", p, n, v)

    def param_dword(n: int, v: int):
        struct.pack_into("<L", p, n, v)

    struct.pack_into("2s", p, 0x00, b"DX")
    param_word(0x02, 0)     # minreal (paragraphs)
    param_word(0x04, 0)     # maxreal (paragraphs)
    param_word(0x06, 0x01)  # minibuf (kilobytes)
    param_word(0x08, 0x40)  # maxibuf (kilobytes)
    param_word(0x0a, 0x06)  # nistack
    param_word(0x0c, 0x01)  # istksize (kilobytes)
    param_dword(0x0e, 0)    # realbreak
    param_word(0x12, 0)     # callbufs (kilobytes)
    param_word(0x14, 0)     # flags
    param_word(0x16, 0)     # 0: privileged

    exp = h + p + image
    csum = 0xffff - sum(p[0] + p[1] * 256 for p in itertools.zip_longest(exp[::2], exp[1::2], fillvalue=0)) % 0x10000
    struct.pack_into("<H", exp, 0x0a, csum)
    return exp


def main():
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input", help="input ELF file", type=Path)
    parser.add_argument("output", help="output .EXP file", type=Path)
    parser.add_argument("--stack", help="size of stack (in bytes)", default=4096, type=int)
    parser.add_argument("--objcopy", help="objcopy command to use", default="i386-pc-run386-objcopy")
    args = parser.parse_args()

    opts = LinkerOptions(args.stack)

    with ELFFile.load_from_path(args.input) as elf:
        check_relocation(elf)
        addrs = get_addrs(elf)

    image = get_image(args.objcopy, args.input)
    exp = make_exp_image(image, addrs, opts)
    args.output.write_bytes(exp)


if __name__ == "__main__":
    main()
