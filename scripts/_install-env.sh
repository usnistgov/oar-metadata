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

function help {
    echo ${prog} -- install software from this repository
    cat <<EOF

This script installs the authbroker software as a package into a given 
or system location.  By default, this location is /usr/local/authbroker; 
below this directory, directories like "bin" and "lib/python" will be 
created and loaded up.

Usage:  $prog [OPTION ...] 

Options:
   --install-dir DIR    Install the softwared below an arbitrary location 
                        (other than the default, /usr/local/authbroker).
   --prefix DIR         An alias for --intall-dir
   --source-dir DIR     The directory containing the source code, overriding 
                        the default being the directory containing the 
                        scripts subdirectory where this script resides.
   --dir DIR            An alieas for --source-dir

EOF
}

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
    -h|--help)
        help
        exit 0
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
    true ${PY_LIBDIR:=$INSTALL_DIR/lib/python3.8/dist-packages}
}
[ "$INSTALL_DIR" = "/usr" ] && {
    true ${PY_LIBDIR:=$INSTALL_DIR/lib/python3.8}
}

true ${ETC_DIR:=$INSTALL_DIR/etc}
true ${MERGE_ETCDIR:=$ETC_DIR/merge}
true ${SCHEMA_DIR:=$ETC_DIR/schemas}
true ${JQ_LIBDIR:=$INSTALL_DIR/lib/jq}
true ${PY_LIBDIR:=$INSTALL_DIR/lib/python} 
true ${BINDIR:=$INSTALL_DIR/bin}

echo "Installing into $INSTALL_DIR..."
echo
