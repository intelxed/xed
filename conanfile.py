# BEGIN_LEGAL
#
# Copyright (c) 2021 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
# END_LEGAL

import os

from conans import ConanFile, tools
from conans.errors import ConanInvalidConfiguration


class XedConan(ConanFile):
    name = "xed"
    description = "The X86 Encoder Decoder (XED) library for encoding/decoding X86 instructions."
    url = "https://gitlab.devtools.intel.com/xed-group/xed"
    homepage = "http://mjc.intel.com/xeddoc/doc-build-internal"
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

    @property
    def _package_src_folder(self):
        return os.path.join(self.package_folder, "src", self.name)

    def package(self):
        self._mbuild("install", install_dir=self.package_folder)
        self.copy("*", src=self.source_folder, dst=self._package_src_folder)
        with tools.chdir(self.package_folder):
            for dir in "mbuild", "examples", "extlib", "doc", "misc":
                tools.rmdir(dir)
        self.copy("LICENSE", dst="licenses")

    def package_info(self):
        self.cpp_info.name = "XED"
        self.cpp_info.components["libxed"].names["cmake_find_package"] = "xed"
        self.cpp_info.components["libxed"].includedirs.append(os.path.join("include", "xed"))
        self.cpp_info.components["libxed"].libs = ["xed"]
        self.cpp_info.components["libxed-ild"].names["cmake_find_package"] = "xed-ild"
        self.cpp_info.components["libxed-ild"].libs = ["xed-ild"]

        self.user_info.ROOTPATH = self.package_folder

        self.output.info(f"Appending PYTHONPATH environment var: {self._package_src_folder}")
        self.env_info.PYTHONPATH.append(self._package_src_folder)
