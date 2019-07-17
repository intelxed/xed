#BEGIN_LEGAL
#
#Copyright (c) 2019 Intel Corporation
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

_verbosity_options = []
def set_verbosity_options(options):
    global _verbosity_options
    _verbosity_options = options


def vflag():
   return 'flag' in _verbosity_options
def vnext():
   return 'next' in _verbosity_options
def vrearrange():
   return 'rearrange' in _verbosity_options
def vmacro():
   return 'macro' in _verbosity_options
def vreadyscan():
   return 'readyscan' in _verbosity_options
def vbitgroup():
   return 'bitgroup' in _verbosity_options
def vextract():
   return 'extract' in _verbosity_options
def vstack():
   return 'stack' in _verbosity_options
def vgraph_res():
   return 'graph_res' in _verbosity_options
def varraygen():
   return 'arraygen' in _verbosity_options
def viform():
   return 'iform' in _verbosity_options
def viclass():
   return 'iclass' in _verbosity_options
def vattr():
   return 'attribute' in _verbosity_options
def vopnd():
   return 'opnd' in _verbosity_options
def vlookup():
   return 'lookup' in _verbosity_options
def vopvis():
   return 'opvis' in _verbosity_options
def vcapture():
   return 'capture' in _verbosity_options
def vcapture1():
   return 'capture1' in _verbosity_options
def vcapture2():
   return 'capture2' in _verbosity_options
def vcapturefunc():
   return 'capture' in _verbosity_options
def vbind():
   return 'bind' in _verbosity_options
def vod():
   return 'od' in _verbosity_options
def vtrace():
   return 'trace' in _verbosity_options
def vparse():
   return 'parse' in _verbosity_options
def vpart():
   return 'partition' in _verbosity_options
def vbuild():
   return 'build' in _verbosity_options
def vmerge():
   return 'merge' in _verbosity_options

def verb1():
   return '1' in _verbosity_options
def verb2():
   return '2' in _verbosity_options
def verb3():
   return '3' in _verbosity_options
def verb4():
   return '4' in _verbosity_options
def verb5():
   return '5' in _verbosity_options
def verb6():
   return '6' in _verbosity_options
def verb7():
   return '7' in _verbosity_options

def vencfunc():
    return 'encfunc' in _verbosity_options
def vencode():
    return 'encode' in _verbosity_options
def vntname():
    return 'ntname' in _verbosity_options
def vtestingcond():
    return 'testingcond' in _verbosity_options
def vclassify():
    return 'classify' in _verbosity_options
def veparse():
    return 'eparse' in _verbosity_options
def veemit():
    return 'eemit' in _verbosity_options
def vignoreod():
    return 'ignoreod' in _verbosity_options
def vtuples():
    return 'tuples' in _verbosity_options
def vdumpinput():
    return 'dumpinput' in _verbosity_options
def vfinalize():
    return 'finalize' in _verbosity_options
def vopseq():
    return 'opseq' in _verbosity_options
def voperand():
    return 'operand' in _verbosity_options
def voperand2():
    return 'operand2' in _verbosity_options
def vinputs():
    return 'inputs' in _verbosity_options
def vread():
    return 'read' in _verbosity_options
def vrule():
    return 'rule' in _verbosity_options
def vaction():
    return 'action' in _verbosity_options
def vblot():
    return 'blot' in _verbosity_options

def vild():
    return 'ild' in _verbosity_options
def vfuncgen():
    return 'funcgen' in _verbosity_options
