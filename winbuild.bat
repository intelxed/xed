pushd %~dp0

rmdir /s /q obj
rmdir /s /q kits\local

c:\python27\python.exe mfile.py --opt=3 --install-dir=kits/local --static --debug --verbose=3 install
pause
cd kits\local\examples
c:\python27\python.exe mfile.py --build-cpp-examples --debug

popd
pause
