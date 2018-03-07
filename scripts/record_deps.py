#! /usr/bin/python
#
# record_deps.py -- encode the dependencies of a distribution as JSON object,
#                   writing it to standard output.
#
# Usage:  record_deps.py DISTNAME VERSION PACKAGE_LOCK_FILE NPMVERSION
#
# where,
#   DISTNAME            the name of the distribution the dependencies apply to
#   VERSION             the version of the distribution
#
# The default package name (oar-sdp) can be over-ridden by the environment
# variable PACKAGE_NAME
#
from __future__ import print_function
import os, sys, json, re
from collections import OrderedDict

prog = os.path.basename(sys.argv.pop(0))
pkgname = os.environ.get('PACKAGE_NAME', 'oar-metadata')

def usage():
    print("Usage: %s DISTNAME VERSION" % prog, file=sys.stderr)

def fail(msg, excode=1):
    print(prog + ": " + msg, file=sys.stderr)
    sys.exit(excode)

def jqdep():
    import nistoar.jq as jq
    return OrderedDict([
        ("name", "jq"),
        ("version", jq.get_version()),
        ("comment", "Not used at build-time; runtime environment could differ"),
        ("dependencies", OrderedDict([
            ("libonig2", OrderedDict([
                ("version", "(unknown)")
            ]))
         ]))
    ])

def pydep():
    vers = sys.version.split()[0]
    return OrderedDict([
        ("name", "python"),
        ("version", vers),
        ("build", sys.version)
    ])

def jspecdep():
    import jsonspec
    return OrderedDict([
        ("name", "jsonspec"),
        ("version", jsonspec.__version__)
    ])

def jschemadep():
    import jsonschema
    return OrderedDict([
        ("name", "jsonschema"),
        ("version", jsonschema.__version__)
    ])

def ejschemadep():
    import ejsonschema
    try:
        vers = ejsonschema.__version__
    except AttributeError as ex:
        vers = 0.1
    return OrderedDict([
        ('name', 'ejsonschema'),
        ('version', vers),
        ("home", "https://github.com/usnistgov/ejsonschema"),
        ("dependencies", make_deps([ jschemadep() ]))
    ])

def jmergedep():
    import jsonmerge
    eggre = re.compile(r'^jsonmerge-(.*)\.egg-info$')
    modfile = jsonmerge.__file__
    libdir = os.path.dirname(os.path.dirname(modfile))
    vers="(unknown)"
    try:
        egginfo = [d for d in os.listdir(libdir) if eggre.match(d)]
        if len(egginfo) > 0:
            m = eggre.match(egginfo[0])
            vers = m.group(1)
    except Exception as ex:
        tb.print_exc()
    return OrderedDict([
        ("name", "jsonmerge"),
        ("version", vers)
    ])

def reqdep():
    import requests
    return OrderedDict([
        ("name", "requests"),
        ("version", requests.__version__)
    ])

def pymongodep():
    import pymongo
    return OrderedDict([
        ("name", "pymongo"),
        ("version", pymongo.__version__)
    ])

def pkgdep():
    import nistoar.nerdm as nerdm
    return OrderedDict([
        ("name", pkgname),
        ("version", nerdm.__version__)
    ])

def make_deps(deps):
    out = OrderedDict()
    for dep in deps:
        name = dep.pop('name')
        out[name] = dep
    return out

def make_depdata(compname, pkgver):
    deps = [ pkgdep(), pydep(), jqdep(), ejschemadep(),
             jmergedep(), jspecdep(), reqdep() ]
    try:
        pym = pymongodep()
        deps.append(pym)
    except ImportError:
        pass

    return OrderedDict([
        ("name", compname),
        ("version", pkgver),
        ("dependencies", make_deps(deps))
    ])

if len(sys.argv) < 2:
    usage()
    fail("Missing arguments -- need 2")
    
distname = sys.argv.pop(0)
distvers = sys.argv.pop(0)
    
data = make_depdata(distname, distvers)
json.dump(data, sys.stdout, indent=2)

