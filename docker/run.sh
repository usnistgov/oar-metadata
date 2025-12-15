#! /bin/bash
#
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
codedir=`(cd $execdir/.. > /dev/null 2>&1; pwd)`

set -e

(docker images | grep -qs oar-metadata/mdtests) || {
    echo "${prog}: Docker image mdtests not found; building now..."
    echo '+' $execdir/dockbuild.sh -q
    $execdir/dockbuild.sh -q || {
        echo "${prog}: Failed to build docker containers; see" \
             "docker/dockbuild.logfor details."
        false
    }
}

ti=
(echo "$@" | grep -qs shell) && ti="-ti"

distvol=
distdir=
prodvol=
proddir="${codedir}/products"          # default products dir on host
mkdir -p "$proddir"
prodvol="-v ${proddir}:/app/products"  # default mount into container
cmd=
args=()
while [ "$1" != "" ]; do
    case "$1" in
        --dist-dir)
            shift
            distdir="$1"
            mkdir -p $distdir
            distdir=`(cd $distdir > /dev/null 2>&1; pwd)`
            distvol="-v ${distdir}:/app/dist"
            args=(${args[@]} "--dist-dir=/app/dist")
            ;;
        --dist-dir=*)
            distdir=`echo $1 | sed -e 's/[^=]*=//'`
            mkdir -p $distdir
            distdir=`(cd $distdir > /dev/null 2>&1; pwd)`
            distvol="-v ${distdir}:/app/dist"
            args=(${args[@]} "--dist-dir=/app/dist")
            ;;
        --products-dir)
            shift
            proddir="$1"
            mkdir -p $proddir
            proddir=`(cd $proddir > /dev/null 2>&1; pwd)`
            prodvol="-v ${proddir}:/app/products"
            ;;
        --products-dir=*)
            proddir=`echo $1 | sed -e 's/[^=]*=//'`
            mkdir -p $proddir
            proddir=`(cd $proddir > /dev/null 2>&1; pwd)`
            prodvol="-v ${proddir}:/app/products"
            ;;
        -*)
            args=(${args[@]} $1)
            ;;
        *)
            if [ -z "$cmd" ]; then
                cmd=$1
            else
                args=(${args[@]} $1)
            fi
            ;;
    esac
    shift
done

echo '+' docker run $ti --rm -v $codedir:/dev/oar-metadata $distvol $prodvol oar-metadata/mdtests $cmd "${args[@]}"
exec docker run $ti --rm -v $codedir:/dev/oar-metadata $distvol $prodvol oar-metadata/mdtests $cmd "${args[@]}"