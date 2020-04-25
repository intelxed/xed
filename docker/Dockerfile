FROM ubuntu:18.04


RUN apt-get update && \
    apt-get -y install gcc g++ gcc-multilib g++-multilib \
                       gcc-8 g++-8 gcc-8-multilib g++-8-multilib \
                       doxygen  \
		       git wget curl \
                       linux-tools-common linux-tools-generic \
                       build-essential  \
                       libbz2-dev libxml2-dev  \
                       binutils-dev  lib32z1-dev lib32readline-dev \
		       libc6-dev libc6-dev-i386 libc6-i386 \
                       python3 python3-pip  && \
    pip3 install --upgrade setuptools
    
    
