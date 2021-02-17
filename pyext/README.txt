# This is a python3 extension to access XED functionality

# Obtain a shared library xed kit and put it in a directory called
# xedkit Or link it to a directory here called xedkit

On linux
------------
rm -rf build testinstall
ln -s PATH-TO-KIT/KITNAME xedkit   # replace 1st arg as appropriate
python3 setup.py install --home testinstall
setenv PYTHONPATH `pwd`/testinstall/lib/python

# put `pwd`/xedkit/lib on LD_LIBRARY_PATH (assumes it is set...)
   setenv LD_LIBRARY_PATH  `pwd`/xedkit/lib:$LD_LIBRARY_PATH
# or if LD_LIBRARY_PATH is not already set:
   setenv LD_LIBRARY_PATH  `pwd`/xedkit/lib
   
python3 example.py

On mac
-----------
# same as linux except instead of setting LD_LIBRARY_PATH do this:

   setenv DYLD_LIBRARY_PATH  `pwd`/xedkit/lib:$DYLD_LIBRARY_PATH
   
or if DYLD_LIBRARY_PATH is not already set:

   setenv DYLD_LIBRARY_PATH  `pwd`/xedkit/lib


On windows:
-----------
http://stackoverflow.com/questions/2817869/error-unable-to-find-vcvarsall-bat

To use MSVS14 (or some other version of the MSVS compiler than MSVS2008):
> set VS90COMNTOOLS=%VS140COMNTOOLS%

Put a copy of the xed kit in a directory named "xedkit" in the build
directory since windows does not support symlinks. One really only
needs the include & lib directories under "xedkit".

> C:\Python38\python.exe setup.py install --home testinstall

Copy the xed.dll to the current directory:
> cp xedkit\bin\xed.dll .

> set PYTHONPATH=testinstall\lib\python
> C:\python38\python example.py

