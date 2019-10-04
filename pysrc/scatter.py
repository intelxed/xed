#!/usr/bin/env python
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

# scatter bits from b in to a, one bit at a time. Emit C code to do it.

# optimizations:
#   - avoid 0 shifts (done)
#   - work with groups of bits (harder) must find bit runs. Compiler's optimizer does a good job
#   - don't or-in initial value, just assign it (done)

from __future__ import print_function
import re
import genutil
underscore_pattern = re.compile(r'_')

def scatter_generate_chunks(length, trimmed_bits, fields, code, verbose=False):
    """
    @type length: integer
    @param length: length of trimmed_bits
    @type trimmed_bits: string
    @param trimmed_bits: bit pattern without underscores
    @type fields: list 
    @param fields: [(field_name, bits)]
    @type code: dictionary 
    @param code: dictionary of code snippets
    @type verbose: boolean
    @param verbose: verbosity

    @rtype: string
    @return: None if cannot map using this function, or a string if we can map it
    """
    runs = genutil.find_runs(list(trimmed_bits))
    s = []
    first = True
    total_bit_count = 0
    for (letter,count) in runs:
        found = False
        for (field_name, bits) in fields:
            field_len = len(bits)
            t=bits[0]*field_len
            if t == bits: # all bits in the field are the same...
                if bits[0] == letter: # and we match the current run-component
                    total_bit_count += count
                    shift = length - total_bit_count
                    if first:
                        first=False
                    else:
                        s.append('|')
                    s.append("(%s" % code[bits])
                    if shift != 0:
                        s.append("<< %s" % shift)
                    s.append(")")
                    found = True
                    break
        if not found:
            return None
    return ''.join(s)
            
    
def scatter_generate_bit_by_bit(length, trimmed_bits, code, verbose=False):
    """Generate c-code expressions one bit at a time.
    @type length: integer
    @param length: length of trimmed_bits
    @type trimmed_bits: string
    @param trimmed_bits: bit pattern without underscores
    @type code: dictionary 
    @param code: dictionary of code snippets
    @type verbose: boolean
    @param verbose: verbosity
    @rtype: string
    @return: C code expression 
    """
    bit_count = {}  # count number of each kind of bit
    s = [] # the return string
    first = True
    vbar = ''
    # go bit by bit through the pattern
    for (i,b) in enumerate(trimmed_bits):
        shift = length-i-1
        if not first:
            vbar = '|'
        first = False            
        if b == '0' or b == '1': # binary bits, just jam them in there...
            if shift == 0:
                s.append("%s %s " % (vbar, b))
            else:
                s.append("%s  (%s << %s)" % (vbar, b, length-i-1))
        else: # letter -- need to extract from field
            if b in bit_count:
                bit_count[b] += 1
            else:
                bit_count[b] = 0
            nth_b = bit_count[b]
            key = b + str(nth_b)
            if verbose:
                print("#", i,b, nth_b,key)
            if shift == 0:
                s.append("%s %s " % (vbar, code[key] ))
            else:
                s.append("%s  (%s << %s)" % (vbar, code[key], length-i-1))
    return ''.join(s)



def scatter_gen(pattern, fields):
    """Generate packer code to fill in patter from fields. Fields is a
    list of tuples of (fieldname, bits). pattern is a string of bits
    in the order we need them.
    @type pattern: string
    @param pattern: 
    @type fields: list of tuples
    @param fields:  [(fieldname, bits) ]
    @rtype: string
    @return: C-code for packing the bits from the input fields
    """
    # generate code patterns for the bits in fields
    verbose = False
    #verbose = True
    if verbose:
        print("pattern: %s fields: %s" %(pattern, str(fields)))
    code = {}
    for (n,p) in fields:
        length = len(p) # we need length bits from n
        mask = (1 << length) - 1
        # we use this for bit runs we recognize
        #code[p] = '(%s & 0x%x)' % (n, mask) # the whole field
        code[p] = n
        if verbose:
            print(p, code[p])

             
        # we must handle hetergenous bit sequences like jii. In this
        # case, j is 0 (j0), the first i is zero (i0) and the 2nd i is
        # 1 (i1). If we used the enumerate index, then the 1st i would
        # be one and that would not handle the 'ii' subseqeunce that
        # we need to emit.

        
        bit_sequence = 0
        last = None
        for (i,s) in enumerate(p):
            shift = length-i-1
            if shift == 0:
                c =  "(%s & %s)" % ( n, 1)
            else:
                c =  "((%s >> %s) & %s)" % ( n, shift, 1)
            # OLD key = s + str(i) # the i'th letter s
            if last and s != last:
                bit_sequence = 0
            key = s + str(bit_sequence)
            bit_sequence += 1
            last = s
            code[key] = c
            if verbose:
                print('key: %s   c-expression: %s' % (key, c))

    trimmed = underscore_pattern.sub('', pattern)
    length = len(trimmed)
    
    # Scatter those code patterns and cobble together a output code that
    # assigns to some variable.
    c_code = scatter_generate_chunks(length, trimmed, fields, code, verbose)
    if c_code == None:
        c_code = scatter_generate_bit_by_bit(length, trimmed, code, verbose)
    
    return (length, c_code)

def test_scatter():
    # this is a pattern for encoding
    a = 'ss_iii_bbb'

    # these are the bound fields
    b = [ ('SCALE','ss'),
          ('INDEX', 'iii'),
          ('BASE', 'bbb') ]

    (length,s) = scatter_gen(a,b)
    #s += ';'
    print(length)
    print(s)


    # this is a pattern for encoding
    a = '11_i1i_b01'

    # these are the bound fields
    b = [ ('SCALE','ss'),
          ('INDEX', 'iii'),
          ('BASE', 'bbb') ]

    (length,s) = scatter_gen(a,b)
    #s += ';'
    print(length)
    print(s)

    # this is a pattern for encoding
    a = 'xxx_yyyyy'

    # these are the bound fields
    b = [ ('IMM','yyyy'),
          ('IGNORED', 'xxx')          ]


    (length,s) = scatter_gen(a,b)
    #s += ';'
    print(length)
    print(s)


if __name__ == '__main__':
    test_scatter()



