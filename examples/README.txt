=====================================================================
                    Building XED Examples (mfile.py)
=====================================================================

To build the XED examples, Python 3.9 or later is required.


=====================================================================
Static Library XED Build
=====================================================================

If your XED library is built as a static archive, use the following command:

  On Linux:
    $ ./mfile.py

  On Windows:
    $ C:\python3\python.exe mfile.py


=====================================================================
Shared Library XED Build
=====================================================================

If you are using a shared XED library (`.so` on Linux/macOS or `.dll` on Windows),
you must specify the `--shared` flag:

  On Linux:
    $ ./mfile.py --shared

  On Windows:
    $ C:\python3\python.exe mfile.py --shared
 

=====================================================================
Additional Options
=====================================================================

To view all available build options, use the `--help` flag:

    $ ./mfile.py --help
