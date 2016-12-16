#BEGIN_LEGAL
#Copyright (c) 2004-2015, Intel Corporation. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are
#met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of Intel Corporation nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#END_LEGAL

# Makefile for examples

####################################################################
# External tools
COMPILER=gnu
#COMPILER=ms

SHARED=0
#SHARED=1
ifeq ($(COMPILER),gnu)
  CC  = gcc
  CXX = g++
  CXX_LINKER = $(CXX)
  CC_LINKER = $(CC)
  RM=rm
  OBJEXT=o
  EXEEXT=
  CXXSRCEXT=cpp
  CCSRCEXT=c
  ifeq ($(SHARED),1)
     LIBEXT=so 
  else
     LIBEXT=a
  endif
  LINKOUT=-o 
  OUTOPT=-o 
  COPT=-c
  IOPT=-I
  DOPT=-D
  CXXFLAGS = -MMD
  CCFLAGS = -MMD

  #
  # Uncomment these next 2 if you want 32b object and executable 
  # files and are on a 64b system. (You must be using the ia32 
  # version of libxed).
  #
  #CCFLAGS += -m32
  #CXXFLAGS += -m32

  LDFLAGS  = 
  #The windows library does not work with cygwin, but in general on cygwin,
  # enable these:
  #CXXFLAGS += -mno-cygwin
  #CCFLAGS += -mno-cygwin
  #LDFLAGS += -mno-cygwin
else
  CC  = cl
  CXX = cl
  # you want MSVS's link, not cygwin's link.
  # make sure you move cygwin's /bin/link command out of the way!
  CXX_LINKER = link
  CC_LINKER = link
  RM=rm
  OBJEXT=obj
  EXEEXT=.exe
  CXXSRCEXT=cpp
  CCSRCEXT=c
  LIBEXT=lib
  LINKOUT=/OUT:
  OUTOPT=/Fo
  COPT=/c 
  IOPT=/I
  DOPT=/D
  CXXFLAGS = /nologo /EHsc
  CCFLAGS  = /nologo
  LDFLAGS  = /nologo
endif
###################################################################
CXXFLAGS += $(IOPT)../include  
CCFLAGS  += $(IOPT)../include  
LIBXED   = ../lib/libxed.${LIBEXT}
EXTRA_LDLIBS_TARGET =
###################################################################
.PHONY: demos cmdline  clean-examples test-xed

XED = xed
XED_DEMOS =  xed-min xed-tester xed-ex1  xed-ex3 xed-ex4 \
	xed-ex5-enc xed-ex6 xed-ex7

XED_DEMOS_SUFFIXED= $(XED_DEMOS:%=%$(EXEEXT))
XED_SUFFIXED= $(XED:%=%$(EXEEXT))

XED_TEST_APPS = ${XED_SUFFIXED} ${XED_DEMOS_SUFFIXED} 
all: ${XED_TEST_APPS}
demos: ${XED_DEMOS_SUFFIXED}
cmdline: ${XED_SUFFIXED}

######################################################################

%.${OBJEXT}: %.${CXXSRCEXT}
	${CXX} ${COPT} ${CXXFLAGS}  $< ${OUTOPT}$@
%.${OBJEXT}: %.${CCSRCEXT}
	${CC} ${COPT} ${CCFLAGS}  $< ${OUTOPT}$@

########################################################################
XED_CXX_COMMON_OBJ =  
XED_CCC_COMMON_OBJ =  
XED_CC_COMMON_OBJ += xed-enc-lang.${OBJEXT}
XED_CC_COMMON_OBJ += xed-disas-hex.${OBJEXT} 
XED_CC_COMMON_OBJ += xed-examples-util.${OBJEXT}
XED_CC_COMMON_OBJ += xed-dot-prep.${OBJEXT}
XED_CC_COMMON_OBJ += xed-dot.${OBJEXT}

xed-min${EXEEXT}: xed-min.${OBJEXT} ${LIBXED}
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^  ${EXTRA_LDLIBS_TARGET}

xed-tester${EXEEXT}: xed-tester.${OBJEXT} ${LIBXED}
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^  ${EXTRA_LDLIBS_TARGET}

xed-ex1${EXEEXT}: xed-ex1.${OBJEXT} ${XED_CC_COMMON_OBJ} ${LIBXED}
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^  ${EXTRA_LDLIBS_TARGET}

xed-ex3${EXEEXT}: xed-ex3.${OBJEXT} ${XED_CC_COMMON_OBJ} ${LIBXED} 
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^ ${EXTRA_LDLIBS_TARGET}

xed-ex4${EXEEXT}: xed-ex4.${OBJEXT} ${XED_CC_COMMON_OBJ} ${LIBXED} 
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^  ${EXTRA_LDLIBS_TARGET}
xed-ex5-enc${EXEEXT}: xed-ex5-enc.${OBJEXT} ${XED_CC_COMMON_OBJ} ${LIBXED} 
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^  ${EXTRA_LDLIBS_TARGET}
xed-ex6${EXEEXT}: xed-ex6.${OBJEXT} ${XED_CC_COMMON_OBJ} ${LIBXED} 
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^  ${EXTRA_LDLIBS_TARGET}
xed-ex7${EXEEXT}: xed-ex7.${OBJEXT} ${XED_CC_COMMON_OBJ} ${LIBXED} 
	${CC_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^  ${EXTRA_LDLIBS_TARGET}

#################################################################

XED_OBJ  = xed.${OBJEXT} 
XED_OBJ += xed-disas-macho.${OBJEXT}
XED_OBJ += xed-disas-pecoff.${OBJEXT}
XED_OBJ += xed-disas-raw.${OBJEXT}
XED_OBJ += xed-disas-elf.${OBJEXT}
XED_OBJ += xed-symbol-table.${OBJEXT}
XED_OBJ += avltree.${OBJEXT} 
XED_OBJ += ${XED_CC_COMMON_OBJ} 
XED_OBJ += ${XED_CXX_COMMON_OBJ}

# define DBGHELP=1 on the command line to enable using dbghelp.dll on windows
DBGHELP ?= 0
ifeq ($(DBGHELP),1)
  XED_OBJ += udhelp.${OBJEXT}
  CXXFLAGS += /DXED_DBGHELP
  EXTRA_LDLIBS_TARGET += dbghelp.lib version.lib
endif

xed${EXEEXT}: ${XED_OBJ} ${LIBXED}
	${CXX_LINKER}  ${LDFLAGS}  ${LINKOUT}$@ $^ ${EXTRA_LDLIBS_TARGET}

#################################################################

clean:
	-${RM} *.o *.obj  *.d *.exe > /dev/null 2>&1
	-${RM} ${XED_TEST_APPS} > /dev/null 2>&1

#################################################################
-include *.d
