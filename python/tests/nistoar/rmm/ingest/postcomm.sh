#! /bin/bash
#
# Used by test_wsgi.py, this script prints arguments to a given output file
#
# USAGE: postcomm.sh OUTFILE [ARG ...]
#
set -e
[ -n "$1" ] || {
    echo "${0}: Missing output filename"
    exit 1
}
out=$1; shift

echo "$@" > $out
