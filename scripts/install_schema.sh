#! /bin/bash
#
# install_schema.sh:  install a JSON schema or context file into a directory
#                     tree based on its identifier
#
# Usage:  install_schema.sh JFILE DESTDIR
#
set -e
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD

jfile=$1
destdir=$2
[ -n "$jfile" ]   || { echo "Missing JSON model file argument"; false; }
[ -f "$jfile" ]   || { echo "$jfile: file not found"; false; }
[ -n "$destdir" ] || { echo "Missing destination dir argument"; false; }
[ -d "$destdir" ] || { echo "$destdir: directory not found"; false; }

id=`grep '^    "@id":' $jfile | perl -pe 's/^.*"\@id":[^"]*"//; s/"[^"]*$//'`
[ -n "$id" ] || {
    id=`grep '^    "id":' $jfile | perl -pe 's/^.*"@id":[^"]*"//; s/"[^"]*$//'`
}
idp=`echo $id   | perl -pe 's#.*https?://.*/od/dm/##'`
ver=`echo $idp  | perl -pe 's#.*/##; s/\/*#.*$//'`
path=`echo $idp | perl -pe 's#/[^/]*$##'`

set -x
mkdir -p $destdir/$path
cp $jfile $destdir/$path
(cd $destdir/$path && [ -e "$ver" ] || ln -s `basename $jfile` $ver)


