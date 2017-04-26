#! /bin/bash
#
# This script installs the various metadata tools into a deployment (i.e.
# install) directory.
#
set -e
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD

. $execdir/_install-env.sh

#install the nerdm library
mkdir -p $PY_LIBDIR
echo Installing python libraries into $PY_LIBDIR...
(cd $SOURCE_DIR/python && python setup.py install --install-purelib=$PY_LIBDIR --install-scripts=$BINDIR)

#install the JAVA jars
# None at this time

#install the extras
echo bash $execdir/install_extras.sh --install-dir=$INSTALL_DIR --source-dir=$SOURCE_DIR
bash $execdir/install_extras.sh --install-dir=$INSTALL_DIR --source-dir=$SOURCE_DIR

