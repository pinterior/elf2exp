# elf2exp

script to convert ELF binary to `.EXP` file for 386|DOS-Extender.

## install

```
pip install https://github.com/pinterior/elf2exp.git@0.0.3
```

## toolchain

### binutils

```
git clone https://github.com/pinterior/binutils-gdb.git -b run386-binutils-2_38
mkdir binutils-gdb/build
cd binutils-gdb/build
../configure --target=i386-pc-run386 --prefix="$HOME"/.local --disable-gdb --disable-nls
make
make install
```

### gcc+newlib

```
git clone https://github.com/pinterior/gcc.git -b run386-gcc-12.1.0
git clone https://github.com/pinterior/newlib.git -b run386-newlib-4.1.0
ln -s ../newlib/newlib gcc/newlib
mkdir gcc/build
cd gcc/build
../configure --prefix="$HOME"/.local --target=i386-pc-run386 --with-newlib --disable-nls --enable-languages=c,c++ --disable-tls
make
make install
```

## example

```c
// hello.c
#include <stdio.h>

int main() {
   printf("Hello, World!\n");
   return 0;
}
```

```
# Linux
i386-pc-run386-gcc -o hello hello.c
elf2exp.py hello hello.exp
```

```
' MS-DOS
run386.exe -nocrtreset hello.exp
```

## TODO

- `argc`, `argv` and `environ`
- many missing system calls
- `-msoft-float` toolchain
- C++
