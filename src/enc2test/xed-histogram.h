#include "xed/xed-types.h"
#include "xed/xed-portability.h"
#include <string.h>
#include <stdio.h>

#if !defined(XED_HISTO_MAX_CYCLES) 
# define XED_HISTO_MAX_CYCLES 10000 // must be divisible by cycles/bin
#endif
#if !defined(XED_HISTO_CYCLES_PER_BIN) 
# define XED_HISTO_CYCLES_PER_BIN 10
#endif


#define XED_HISTO_BINS (XED_HISTO_MAX_CYCLES/XED_HISTO_CYCLES_PER_BIN)

#define DCAST(x) XED_CAST(double,(x))

typedef struct {
    xed_uint64_t bad_times;
    xed_uint64_t histo[XED_HISTO_BINS];
} xed_histogram_t;

static void
xed_histogram_update(xed_histogram_t* p,
                     xed_uint64_t t1,
                     xed_uint64_t t2)
{
    xed_uint64_t delta;
    xed_uint32_t bin;
    
    if (t2 >= t1) {
        delta = t2-t1;
        if (delta  < XED_HISTO_MAX_CYCLES)
            bin = XED_CAST(xed_uint32_t, delta / XED_HISTO_CYCLES_PER_BIN);
        else
            bin = XED_HISTO_BINS-1;
        p->histo[bin]++;
    }
    else {
        p->bad_times++;
    }
}

static void
xed_histogram_initialize(xed_histogram_t* p) {
    p->bad_times =0;
    memset(p->histo, 0, sizeof(xed_uint64_t)*XED_HISTO_BINS);
}

static void
xed_histogram_dump(xed_histogram_t* p, int include_zero_bins)
{
    xed_uint32_t i=0;
    xed_uint64_t total=0;
    double cdf = 0;
    const xed_uint32_t bins = XED_HISTO_BINS;
    const xed_uint32_t cycles_per_bin = XED_HISTO_CYCLES_PER_BIN;
    for(i=0;i< bins;i++) 
        total += p->histo[i];
    printf("Total    : " XED_FMT_LU12 "\n", total);
    printf("Bad times: " XED_FMT_LU12 "\n", p->bad_times);
    if (total == 0)
        return;
    printf("CYCLE-RANGE               bCOUNT   PERCENT  CUMULATIVE%%\n");
      //    [    0 ...    9 ]             0     0.00%     0.00%

    for(i=0;i<bins;i++)  {
        if (p->histo[i] || include_zero_bins) {
            double pct = 100.0*DCAST(p->histo[i])/DCAST(total);
            cdf += pct;
            printf("[ %4u ... %4u ]  " XED_FMT_LU12 "  %7.2lf%%  %7.2lf%%\n",
                   i*cycles_per_bin,
                   (i+1)*cycles_per_bin-1,
                   p->histo[i],
                   pct,
                   cdf);
        }
    }
}

