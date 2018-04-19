import genutil

def read_file(fn):
    lines = open(fn,'r').readlines()
    lines = map(genutil.no_comments, lines)
    lines = list(filter(genutil.blank_line, lines))
    d = {} # isa-set to list of cpuid records
    for line in lines:
        wrds = line.split(':')
        isa_set = wrds[0].strip()
        cpuid_bits = wrds[1].upper().split()
        if isa_set in d:
            msg = "Duplicate cpuid definition for isa set. isa-set={} old ={} new={}"
            genutil.die(msg.format(isa_set, d[isa_set], cpuid_bits))
        d[isa_set] = cpuid_bits
    return d
