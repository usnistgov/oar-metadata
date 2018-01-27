#! /bin/bash
#
mongod_ctl=/usr/local/bin/mongod_ctl.sh
[ "$1" = "" ] && exec /bin/bash

function launch_uwsgi {
    echo starting uwsgi...
    uwsgi --daemonize docker/_docker_uwsgi.log --plugin python    \
          --http-socket :9090 --wsgi-file scripts/ingest-uwsgi.py \
          --set-ph oar_config_file=docker/mdtests/ingest_conf.yml \
          --pidfile /tmp/ingest.pid
}

function crash_uwsgi {
    echo stopping uwsgi...
    uwsgi --stop /tmp/ingest.pid
}

function test_ingest_wsgi {
    launch_uwsgi
    
    set -x
    curl http://localhost:9090/ > ingest_out.txt && \
        python -c 'import sys, json; fd = open("ingest_out.txt"); data = json.load(fd); sys.exit(0 if len(data)==1 and data[0]=="nerdm" else 11)' || \
        stat=$?

    ( code=`curl -s -w '%{http_code}' -X POST -d @model/examples/hitsc.json http://localhost:9090/nerdm` && \
      [ "$code" == "200" ] ) || \
        stat=$?
    set +x

    crash_uwsgi
    return $stat
}

case "$1" in
    makedist)
        scripts/makedist
        ;;
    build)
        scripts/setversion.sh
        (cd python && python setup.py build)
        ;;
    testall)
        [ -x $mongo_ctl ] && $mongod_ctl start && sleep 1
        stat=0
        scripts/setversion.sh
        (cd python && python setup.py build)
        scripts/testall.py || stat=$?
        test_ingest_wsgi || stat=$?
        [ "$stat" != "0" ] && {
            echo "testall: One or more test packages failed (last=$stat)"
            echo NOT OK
            exit $stat
        }
        echo All OK
        ;;
    install)
        scripts/install.sh
        ;;
    testshell)
        [ -x $mongo_ctl ] && $mongod_ctl start && sleep 1
        exec /bin/bash
        ;;
    shell)
        exec /bin/bash
        ;;
    *)
        echo Unknown command: $1
        echo Available commands:  build testall install shell
        exit 100
        ;;
esac

EXCODE=$?
echo $EXCODE > $1.exit
exit $EXCODE
