#! /bin/bash
#
# buildall.sh:  build all docker images in this directory
#
# Usage: buildall.sh
#
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
codedir=`(cd $execdir/.. > /dev/null 2>&1; pwd)`
set -e

## These are set by default via _run.sh; if necessary, uncomment and customize
#
# PACKAGE_NAME=oar-build
# 
## list the names of the image directories (each containing a Dockerfile) for
## containers to be built.  List them in dependency order (where a latter one
## depends the former ones).  
#
DOCKER_IMAGE_DIRS="pymongo jq ejsonschema mdtests"

. $codedir/oar-build/_dockbuild.sh

# set BUILD_OPTS and BUILD_IMAGES
# 
setup_build

log_intro   # record start of build into log

for container in $BUILD_IMAGES; do 
    echo '+ ' docker build $BUILD_OPTS -t $PACKAGE_NAME/$container $container | logit
    docker build $BUILD_OPTS -t $PACKAGE_NAME/$container $container 2>&1 | logit
done
