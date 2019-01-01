#!/bin/bash

# Read lines from stdin and create test cases for them
let start=156
while IFS='' read -r line || [[ -n "$line" ]]; do
    DIRNAME=`/usr/intel/pkgs/bash/4.4/bin/bash -c "printf test-%05d $start"`
    /bin/mkdir -p $DIRNAME
    echo BUILDDIR/xed $line > $DIRNAME/cmd
    echo ENC > $DIRNAME/codes
    echo 0 > $DIRNAME/retcode.reference
    touch $DIRNAME/stdout.reference
    touch $DIRNAME/stderr.reference
    let start=start+1
done
