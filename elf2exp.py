#!/usr/bin/env python3

import argparse
import functools
import struct
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
from elftools.elf.relocation import RelocationSection

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('input', help='input ELF file')
parser.add_argument('output', help='output EXP file')
parser.add_argument('-s', "--stack", help='stack size', default=4096, type=int)
parser.add_argument('--objcopy', help='objcopy command to use', default='i386-pc-run386-objcopy')
args = parser.parse_args()

with open(args.input, 'rb') as ins:
    elf = ELFFile(ins)

    sections = list(map(elf.get_section, range(elf.num_sections())))

    reloc_sects = filter(lambda s: isinstance(s, RelocationSection), sections)
    relocs = sum(map(lambda s: s.num_relocations(), reloc_sects))

    if relocs != 0:
        raise RuntimeError('cannot have relocations.')

    alloc_sects = filter(lambda s: bool(s['sh_flags'] & SH_FLAGS.SHF_ALLOC), sections)
    (base, size) = functools.reduce(
        lambda a, e: (min(a[0], e['sh_addr']), max(a[1], e['sh_addr'] + e['sh_size'])),
        alloc_sects, (0xffffffff, 0))

    if base != 0:
        raise RuntimeError('minimum base address must be 0.')

    entry = elf.header['e_entry']

with tempfile.NamedTemporaryFile('rb') as temp:
    r = subprocess.run([args.objcopy, '-O', 'binary', args.input, temp.name], check=True)
    image = temp.read().rstrip(b'\x00')

def ceil_n(n, m):
    return n + (m - n) % m

stack_end = ceil_n(size + args.stack, 4096)

# https://github.com/nabe-abk/free386/blob/main/doc-ja/dosext/mp_head.txt

mp_hdr = bytearray(32)
exp = mp_hdr + image
exp[0x00:0x02] = b'MP'
exp[0x02:0x04] = struct.pack('<H', len(exp) % 512)
exp[0x04:0x06] = struct.pack('<H', ceil_n(len(exp), 512) // 512)
exp[0x06:0x08] = struct.pack('<H', 0)
exp[0x08:0x0a] = struct.pack('<H', len(mp_hdr) // 16)
exp[0x0a:0x0c] = struct.pack('<H', ceil_n(stack_end, 4096) // 4096)
exp[0x0c:0x0e] = struct.pack('<H', 0xffff)
exp[0x0e:0x12] = struct.pack('<L', stack_end)
exp[0x14:0x18] = struct.pack('<L', entry)
exp[0x18:0x1a] = struct.pack('<H', 0x1e)
exp[0x1a:0x1c] = struct.pack('<H', 0)
exp[0x1c:0x1e] = struct.pack('<H', 1)

exp[0x12] = functools.reduce(lambda a, b: a ^ b, exp[::2])
exp[0x13] = functools.reduce(lambda a, b: a ^ b, exp[1::2])

with open(args.output, 'wb') as outs:
    outs.write(exp)
