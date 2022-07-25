#!/usr/bin/env python3
#
import os, sys, unittest, pdb
# from nistoar.rmm.mongo.tests import warnings
# sys.modules['warnings'] = warnings

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jqlib = os.path.join(basedir, "jq")
testdir = os.path.join(jqlib, "tests")
jqtest = [os.path.join(testdir, "test_pod2nerdm.jqt"),
          os.path.join(testdir, "test_nerdm2pod.jqt"),
          os.path.join(testdir, "test_nerdm2datacite.jqt")]
nerdmtest = [os.path.join(testdir, "test_podds2resource.py"),
             os.path.join(testdir, "test_resource2midaspodds.py")]
pdltest = os.path.join(basedir, "scripts", "test_pdl2resources.py")
extest = os.path.join(basedir, "model", "tests", "test_examples.py")
pydir = os.path.join(basedir, "python")
pytestdir = os.path.join(pydir, "tests")

print("Executing all tests...")

print("Executing jq translation library tests...")

status = 0
notok = os.system("jq -L {0} --run-tests {1}".format(jqlib, jqtest[0]))
notok2 = os.system("jq -L {0} --run-tests {1}".format(jqlib, jqtest[1]))
notok3 = os.system("jq -L {0} --run-tests {1}".format(jqlib, jqtest[2]))
if notok or notok2 or notok3:
    print("**ERROR: some or all jq tests have failed")
    status += 1

print("Executing validation tests...")

notok  = os.system("/usr/bin/env python3 {0}".format(nerdmtest[0]))
notok2 = os.system("/usr/bin/env python3 {0}".format(nerdmtest[1]))
if notok or notok2:
    print("**ERROR: some or all basic validation tests have failed")
    status += 2
notok = os.system("/usr/bin/env python3 {0}".format(extest))
if notok:
    print("**ERROR: some or all example files have failed validation")
    status += 4
notok = os.system("/usr/bin/env python3 {0}".format(pdltest))
if notok:
    print("**ERROR: some or all pdl2resources output files have failed validation")
    status += 8

print("Executing nistoar python tests...")
os.environ.setdefault('OAR_TEST_INCLUDE', '')
os.environ['OAR_TEST_INCLUDE'] += " noreload"

ldr = unittest.TestLoader()
suite = ldr.discover(pytestdir, "test_*.py", pydir)
result = unittest.TextTestRunner().run(suite)
if not result.wasSuccessful():
    status += 16

if status:
    print("NOT OK!")
sys.exit(status)

