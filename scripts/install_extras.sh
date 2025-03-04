#! /bin/bash
#
# This script installs all miscellaneous parts of this package.  That is,
# it installs pieces not covered by the language specific installatin scripts.
#
set -e
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD

. $execdir/_install-env.sh

# install the schemas
mkdir -p $SCHEMA_DIR
schemafiles=`ls -d $SOURCE_DIR/model/*.json{,ld} | grep -v nerdm-fields-help`
echo cp $schemafiles $SCHEMA_DIR
cp $schemafiles $SCHEMA_DIR
echo

# install the jq modules
mkdir -p $JQ_LIBDIR
echo "cp $SOURCE_DIR/jq/*.jq $JQ_LIBDIR"
cp $SOURCE_DIR/jq/*.jq $JQ_LIBDIR
echo

# install the merge configurations
mkdir -p $MERGE_ETCDIR
merge_etcpath=`(cd $MERGE_ETCDIR && pwd)`
echo tar cf - merge \| \(cd $MERGE_ETCDIR/.. \&\& tar xf -\)
(cd $SOURCE_DIR/etc && (tar cf - --exclude-backups --exclude=README\* merge | (cd $merge_etcpath/.. && tar xf -)))
echo

#install extra scripts
mkdir -p $BINDIR
# No extra scripts at this time

# install uwsgi config files
echo tar cf - uwsgi \| \(cd $ETC_DIR \&\& tar xf -\)
(cd $SOURCE_DIR/etc && tar cf - --exclude=README\* uwsgi) | (cd $ETC_DIR && tar xf -)
echo
uwsgipath=`which uwsgi` || true
[ -z "$uwsgipath" ] || {
    cfgfile=
    if [ "$uwsgipath" == "/usr/local/bin/uwsgi" ]; then
        cfgfile=pipinstalled.ini
    elif [ "$uwsgipath" == "/usr/bin/uwsgi" ]; then
        cfgfile=osinstalled.ini
    fi
    [ -z "$cfgfile" ] || {
        [ \! -f "$ETC_DIR/uwsgi/oar_uwsgi.ini" ] || \
            rm "$ETC_DIR/uwsgi/oar_uwsgi.ini"
        echo \(cd $ETC_DIR/uwsgi \&\& ln -s $cfgfile oar_uwsgi.ini\)
        (cd $ETC_DIR/uwsgi && ln -s $cfgfile oar_uwsgi.ini)
    }
}

#install miscellaneous data files
mkdir -p $ETC_DIR/samples
echo cp $SOURCE_DIR/jq/tests/data/nist-pdl-oct2016.json $ETC_DIR/samples
cp $SOURCE_DIR/jq/tests/data/nist-pdl-oct2016.json $ETC_DIR/samples
echo cp $SOURCE_DIR/model/nerdm-fields-help.json $ETC_DIR/samples
cp $SOURCE_DIR/model/nerdm-fields-help.json $ETC_DIR/samples

for f in `ls -d $SOURCE_DIR/model/examples/*.json`; do
    echo cp $f $ETC_DIR/samples
    cp $f $ETC_DIR/samples
done

