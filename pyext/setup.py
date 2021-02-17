from distutils.core import setup, Extension

# need a symlink called xedkit pointing to a XED kit in the current
# directory
module1 = Extension('xed',
                    # define_macros = [('XEDFOO', '1') ],
                    include_dirs = ['xedkit/include'],
                    libraries = ['xed' ],
                    library_dirs = ['xedkit/lib'],
                    sources = ['xed.c'])

setup (name = 'xed',
       version = '1.0',
       description = 'This is a XED extension package',
       ext_modules = [module1])

