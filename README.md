# Intel X86 Encoder Decoder  (Intel XED)

## Doxygen API manual and source build manual:

https://intelxed.github.io

## Bugs:

### Intel internal employee users/developers:

http://mjc.intel.com
       
### Everyone else:

https://github.com/intelxed/xed/issues/new
       

## Abbreviated building instructions:

    git clone https://github.com/intelxed/xed.git xed
    git clone https://github.com/intelxed/mbuild.git mbuild
    cd xed
    ./mfile.py

then get your libxed.a from the obj directory.
Add " --shared" if you want a shared object build.
Add " install" if you want the headers & libraries put in to a kit in the "kits" directory.
Add "C:/python27/python " before "./mfile.py" if on windows.

## How to build the examples:

There are two options:

1) When building libxed you can also build the examples, from the main directory (above examples):

    ./mfile.py examples

and the compiled examples will be in obj/examples.
    
2) Build a compiled "kit" and the build the examples from within the kit:

    ./mfile.py install
    cd kits
    cd <whatever the kit is called>
    cd examples
    ./mfile.py
    

See source build documentation for more information.

## Binary size?

Concerned about large libraries or binaries? There are several options:
 
1. Consider building with "--limit-strings"
2. Strip the binaries
3. Consider doing an encoder-only or decoder-only build if you only need one or the other.

