#BEGIN_LEGAL
#
#Copyright (c) 2021 Intel Corporation
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
#END_LEGAL
cmake_minimum_required(VERSION 3.1)
project(PackageTest CXX)

set(CONAN_CMAKE_SILENT_OUTPUT TRUE)
include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(NO_OUTPUT_DIRS TARGETS)

find_package(XED REQUIRED COMPONENTS xed xed-ild)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package XED::xed)
