FROM ubuntu:18.04


RUN apt-get update && \
    apt-get -y install gcc g++ gcc-multilib \
                       doxygen  \
		       git wget curl \
                       linux-tools-common linux-tools-generic \
                       build-essential  \
                       libbz2-dev libxml2-dev  \
                       binutils-dev  lib32z1-dev lib32readline-dev \
                       g++-multilib libc6-dev  \
                       libc6-dev-i386 libc6-i386 \
                       python3 python3-pip  && \
    pip3 install --upgrade setuptools
    
    
