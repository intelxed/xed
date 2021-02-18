import os

from conans import ConanFile, tools
from conans.errors import ConanInvalidConfiguration


class XedCommonConan(ConanFile):
    name = "xed-common"
    description = "The X86 Encoder Decoder (XED) library for encoding/decoding X86 instructions."
    url = "https://gitlab.devtools.intel.com/xed-group/xed"
    homepage = "https://intelxed.github.io/"
    license = "Apache License 2.0"
    topics = ("intel", "xed", "encoder", "decoder", "x86")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    build_requires = "mbuild/1.0.0@xed/stable"
    exports_sources = (
        "LICENSE",
        "README.md",
        "datafiles/*",
        "examples/*",
        "include/*",
        "misc/*",
        "pysrc/*",
        "scripts/*",
        "src/*",
        "mfile.py",
        "xed_build_common.py",
        "xed_mbuild.py",
    )
    no_copy_source = True

    def export_sources(self):
        tools.save(os.path.join(self.export_sources_folder, "VERSION"), self.version)

    def _mbuild(self, *targets, **mbuild_options):
        cmd = [os.path.join(self.source_folder, "mfile.py"), "--silent"]
        if self.options.shared:
            cmd += ["--shared"]
        elif self.options.fPIC:
            cmd += ["--extra-cxxflags=-fPIC", "--extra-ccflags=-fPIC"]
        if self.settings.build_type == "Release":
            cmd += ["--opt=2"]
        elif self.settings.build_type == "Debug":
            cmd += ["--debug"]
        elif self.settings.build_type == "RelWithDebInfo":
            cmd += ["--opt=2", "--debug"]
        else:
            raise ConanInvalidConfiguration("build_type `{}' is not supported".format(
                self.settings.build_type))
        for name, val in mbuild_options.items():
            name = name.replace("_", "-")
            cmd += ["--{}={}".format(name, val)]
        cmd += list(targets)
        self.run(" ".join(cmd))

    def build(self):
        self._mbuild()

    def package(self):
        self._mbuild("install", install_dir=self.package_folder)
        with tools.chdir(self.package_folder):
            for dir in "mbuild", "examples", "extlib", "doc", "misc":
                tools.rmdir(dir)
        self.copy("LICENSE", dst="licenses")

    def package_info(self):
        self.cpp_info.name = "XED"
        self.cpp_info.components["xed"].libs = ["xed"]
        self.cpp_info.components["xed-ild"].libs = ["xed-ild"]
