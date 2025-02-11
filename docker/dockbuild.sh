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

## These are set by default via _dockbuild.sh; if necessary, uncomment and customize
#
PACKAGE_NAME=oar-metadata

## list the names of the image directories (each containing a Dockerfile) for
## containers to be built.  List them in dependency order (where a latter one
## depends the former ones).  
#
# NOTE: ejsonschema is tag provided for backward compatibility; other repos that
#       build their docker images on those of oar-metadata should build on "mdenv".
#
DOCKER_IMAGE_DIRS="pymongo jq mdenv ejsonschema mdtests"

. $codedir/oar-build/_dockbuild.sh

# Override, if need be, the UID of the user to run as in the container; the 
# default is the user running this script.
#
# OAR_DOCKER_UID=

# set BUILD_OPTS and BUILD_IMAGES
# 
setup_build

log_intro   # record start of build into log

# install CA certs into containers that can use them
if { echo $BUILD_IMAGES | grep -qs pymongo; }; then
    cp_ca_certs_to pymongo
fi

for container in $BUILD_IMAGES; do
    if [ "$container" != "ejsonschema" ]; then
        echo '+ ' docker build $BUILD_OPTS -t $PACKAGE_NAME/$container $container | logit
        docker build $BUILD_OPTS -t $PACKAGE_NAME/$container $container 2>&1 | logit
    else
        # provided for backward compatibility (to oar-pdr-py, oar-auth-py)
        echo '+' docker tag $PACKAGE_NAME/mdenv $PACKAGE_NAME/$container
        docker tag $PACKAGE_NAME/mdenv $PACKAGE_NAME/$container
    fi
done
