#! /bin/bash
#
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
set -ex

docker build -t oarmeta/pymongo $execdir/pymongo
docker build -t oarmeta/jq $execdir/jq
docker build -t oarmeta/ejsonschema $execdir/ejsonschema
docker build -t oarmeta/mdtests $execdir/mdtests
