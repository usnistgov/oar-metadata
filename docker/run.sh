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

# Products mount: keep old behavior by default, but prefer the oar-docker compose
# products directory when it exists (so files land where your larger stack mounts from).
prodvol=
proddir_default="${codedir}/products"
compose_proddir="`(cd "${codedir}/.." > /dev/null 2>&1; pwd)`/oar-docker/apps/data/products"
proddir="$proddir_default"
user_set_proddir=0

cmd=
args=()
while [ "$1" != "" ]; do
    case "$1" in
        --dist-dir)
            shift
            distdir="$1"
            mkdir -p "$distdir"
            distdir=`(cd "$distdir" > /dev/null 2>&1; pwd)`
            distvol="-v ${distdir}:/app/dist"
            args=(${args[@]} "--dist-dir=/app/dist")
            ;;
        --dist-dir=*)
            distdir=`echo "$1" | sed -e 's/[^=]*=//'`
            mkdir -p "$distdir"
            distdir=`(cd "$distdir" > /dev/null 2>&1; pwd)`
            distvol="-v ${distdir}:/app/dist"
            args=(${args[@]} "--dist-dir=/app/dist")
            ;;
        --products-dir)
            shift
            proddir="$1"
            user_set_proddir=1
            ;;
        --products-dir=*)
            proddir=`echo "$1" | sed -e 's/[^=]*=//'`
            user_set_proddir=1
            ;;
        -*)
            args=(${args[@]} $1)
            ;;
        *)
            if [ -z "$cmd" ]; then
                cmd="$1"
            else
                args=(${args[@]} "$1")
            fi
            ;;
    esac
    shift
done

# If the caller didn't specify a products dir and the compose products dir exists,
# write products into that directory so they show up in the bigger docker-compose system.
if [ "$user_set_proddir" -eq 0 ] && [ -d "$compose_proddir" ]; then
    proddir="$compose_proddir"
fi

mkdir -p "$proddir"
proddir=`(cd "$proddir" > /dev/null 2>&1; pwd)`
prodvol="-v ${proddir}:/app/products"

# Copy patents.json from this repo into the host products dir (which is bind-mounted).
src_patents="${codedir}/products/patents.json"
if [ -f "$src_patents" ]; then
    cp -p "$src_patents" "${proddir}/"
fi

echo '+' docker run $ti --rm -v $codedir:/dev/oar-metadata $distvol $prodvol oar-metadata/mdtests $cmd "${args[@]}"
exec docker run $ti --rm -v $codedir:/dev/oar-metadata $distvol $prodvol oar-metadata/mdtests $cmd "${args[@]}"