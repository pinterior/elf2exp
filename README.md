# elf2exp

script to convert ELF binary to `.EXP` file for 386|DOS-Extender.

## Toolchain

### binutils

```
git clone https://github.com/pinterior/binutils-gdb.git -b run386-binutils-2_38
mkdir binutils-gdb/build
cd binutils-gdb/build
../configure --target=i386-pc-run386 --prefix="$HOME"/local --disable-gdb --disable-nls
make
make install
```
