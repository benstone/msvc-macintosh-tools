# msvc-macintosh-tools

This project contains tools for use
with [Microsoft Visual C++ Cross Development Edition for Macintosh](https://www.macintoshrepository.org/2607-microsoft-visual-c-4-0-cross-development-edition-for-macintosh).

## PE2MacBinary

PE2MacBinary is a script for converting build outputs from Microsoft Visual C++ Cross Development Edition
to [MacBinary](https://en.wikipedia.org/wiki/MacBinary) format.

### Build Process

Compiling a program for the Macintosh with Visual C++ Cross Development Edition consists of the following stages:

1. Use ``mrc.exe`` (Macintosh Resource Compiler) to compile resources from MPW/Rez format to produce a resource fork
2. Use ``cl.exe`` to compile each C++ source file to object files containing M68k/PowerPC code
3. Use ``link.exe`` to produce a Portable Executable (PE) file. This PE is not the final program executable, and will
   not run on the Macintosh.
4. Use ``mfile.exe`` to transfer the program to the Macintosh configured for remote debugging. The code and data
   sections from the PE are merged into the resource fork produced by mrc to produce the final program executable on the
   Macintosh.

The problem with this process is that the final build output is always transferred to the Macintosh. I wanted to avoid
having to run a Macintosh emulator just to build my program.

I reverse engineered ``mfile.exe`` and found the conversion from PEs to resource forks is performed by
calling ``mrc.exe`` with some undocumented arguments. The command line used for this
is: ``mrc.exe -q -e <path-to-PE-file> -o <path-to-resource-fork-file> -w <path-to-data-file> -x <path-to-attributes-file>``
. This produces the resource fork containing the program, an empty data fork, and an attributes file containing Finder
info for the file (eg. type/creator/flags). The attributes file uses the same format used by Services for Macintosh in
Windows NT to store file information. This is usually stored in an alternate data stream called AFP_FileInfo.

### Using this script

This script requires ``mrc.exe`` from Visual C++ Cross Development Edition. If you have Visual C++ Cross Development
Edition installed, the executable is located using the registry. Otherwise, you can copy ``mrc.exe``
from ``C:\MSDEV\mac\bin`` and place it on your path.

Run ``pe2macbinary.py <path-to-EXE> <output-file.bin>`` to convert the PE to a MacBinary file.

* Add ``--name`` to set the file name to use when the MacBinary file is unpacked
* Add ``--data`` to use another file as the data fork

## File2MacBinary

File2MacBinary creates a MacBinary file from a data and resource fork. Sample usage:

```
file2macbinary.py --data data-fork.bin --rsrc resource-fork.rsrc --creator CRTR --type TYPE --name "My File" output.bin
```
