# syntax = docker/dockerfile:1.3

FROM ubuntu:20.10

ENV http_proxy=http://proxy-dmz.intel.com:911
ENV https_proxy=http://proxy-dmz.intel.com:912
ENV no_proxy=.intel.com

RUN --mount=type=cache,target=/var/cache/apt/ apt-get update && \
    apt-get -y install gcc g++ gcc-multilib g++-multilib \
                       gcc-8 g++-8 gcc-8-multilib g++-8-multilib \
                       doxygen  \
		       git wget curl \
                       linux-tools-common linux-tools-generic \
                       build-essential  \
                       libbz2-dev libxml2-dev  \
                       binutils-dev  lib32z1-dev lib32readline-dev nodejs\
		       libc6-dev libc6-dev-i386 libc6-i386 \
                       python3 python3-pip python3-venv  && \
    pip3 install --upgrade setuptools
    
    
