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

See source build documentation for more information.

