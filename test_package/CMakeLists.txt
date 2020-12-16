cmake_minimum_required(VERSION 3.1)
project(PackageTest CXX)

set(CONAN_CMAKE_SILENT_OUTPUT TRUE)
include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(NO_OUTPUT_DIRS)

find_package(XED REQUIRED COMPONENTS xed xed-ild)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package XED::xed)
