#! /bin/bash
#
# This is intended to be sourced by install scripts to accept command-line
# options and set up the install environment.
#
# Prereq: execdir must be set to the directory where the install script lives
#
base=`(cd $execdir/.. > /dev/null 2>&1; pwd)`

##########
true ${SOURCE_DIR:=$base}
true ${INSTALL_DIR:=/usr/local}
##########

# handle command line options
while [ "$1" != "" ]; do 
  case "$1" in
    --prefix=*|--install-dir=*)
        INSTALL_DIR=`echo $1 | sed -e 's/[^=]*=//'`
        ;;
    --prefix|--install-dir)
        shift
        INSTALL_DIR=$1
        ;;
    --source-dir=*|--dir=*)
        SOURCE_DIR=`echo $1 | sed -e 's/[^=]*=//'`
        ;;
    -d|--dir|--source-dir)
        shift
        SOURCE_DIR=$1
        ;;
    -*)
        echo "$prog: unsupported option:" $1
        false
        ;;
    *)
        echo "Warning: ignoring argument: $1"
        ;;
  esac
  shift
done

[ "$INSTALL_DIR" = "/usr/local" ] && {
    true ${PY_LIBDIR:=$INSTALL_DIR/lib/python2.7/dist-packages}
}
[ "$INSTALL_DIR" = "/usr" ] && {
    true ${PY_LIBDIR:=$INSTALL_DIR/lib/python2.7}
}

true ${ETC_DIR:=$INSTALL_DIR/etc}
true ${MERGE_ETCDIR:=$ETC_DIR/merge}
true ${SCHEMA_DIR:=$ETC_DIR/schemas}
true ${JQ_LIBDIR:=$INSTALL_DIR/lib/jq}
true ${PY_LIBDIR:=$INSTALL_DIR/lib/python} 
true ${BINDIR:=$INSTALL_DIR/bin}

echo "Installing into $INSTALL_DIR..."
echo
