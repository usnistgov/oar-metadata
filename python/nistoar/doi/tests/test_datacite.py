from __future__ import absolute_import
import os, pdb, sys, json, requests, logging, time, re, hashlib, shutil
import unittest as test

import nistoar.doi.datacite as dc

testdir = os.path.dirname(os.path.abspath(__file__))
datadir = os.path.join(testdir, 'data')
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(testdir))))

port = 9091
baseurl = "http://localhost:{0}/dois".format(port)
prefixes = ["10.88434", "20.88434"]

tmpname = "_test"
def tmpdir(basedir=None, dirname=None):
    if not dirname:
        dirname = tmpname + str(os.getpid())
    if not basedir:
        basedir = os.getcwd()
    tdir = os.path.join(basedir, dirname)
    if not os.path.isdir(tdir):
        os.makedirs(tdir)
    return tdir

def startService():
    tdir = tmpdir()
    srvport = port
    pidfile = os.path.join(tdir,"simsrv"+str(srvport)+".pid")
    
    wpy = "python/nistoar/doi/tests/sim_datacite_srv.py"
    cmd = "uwsgi --daemonize {0} --plugin python --http-socket :{1} " \
          "--wsgi-file {2} --pidfile {3} --set-ph prefixes={4}"
    cmd = cmd.format(os.path.join(tdir,"simsrv.log"), srvport,
                     os.path.join(basedir, wpy), pidfile, ",".join(prefixes))
    os.system(cmd)
    time.sleep(0.2)

def stopService():
    tdir = tmpdir()
    srvport = port
    pidfile = os.path.join(tdir,"simsrv"+str(srvport)+".pid")
    
    cmd = "uwsgi --stop {0}".format(os.path.join(tdir,
                                                 "simsrv"+str(srvport)+".pid"))
    os.system(cmd)
    time.sleep(1)

loghdlr = None
rootlog = None
def setUpModule():
    global loghdlr
    global rootlog
    rootlog = logging.getLogger()
    loghdlr = logging.FileHandler(os.path.join(tmpdir(),"test_simsrv.log"))
    loghdlr.setLevel(logging.DEBUG)
    rootlog.addHandler(loghdlr)
    tmpdir()
    startService()

def tearDownModule():
    global loghdlr
    if loghdlr:
        if rootlog:
            rootlog.removeHandler(loghdlr)
        loghdlr = None
    stopService()
    shutil.rmtree(tmpdir())
    
class TestDataCiteDOIClient(test.TestCase):

    def setUp(self):
        self.baseurl = baseurl
        self.cli = dc.DataCiteDOIClient(self.baseurl, None, prefixes=prefixes)

    def test_supports_prefix(self):
        self.assertTrue(not self.cli.supports_prefix("30.30303"))
        self.assertTrue(self.cli.supports_prefix("10.88434"))
        self.assertTrue(self.cli.supports_prefix("20.88434"))

    def test_default_prefix(self):
        self.assertTrue(self.cli.default_prefix, "10.88434")

    def test_not_doi_exists(self):
        self.assertTrue(not self.cli.doi_exists("10.88434/goober"))

    def test_no_doi_state(self):
        self.assertEquals(self.cli.doi_state("10.88434/goober"), "")

    def test_reserve(self):
        self.assertTrue(not self.cli.doi_exists("10.88434/goober"))

        data = self.cli.reserve("goober")
        self.assertEqual(data['data']['id'], "10.88434/goober")
        self.assertEqual(data['data']['attributes']['doi'], "10.88434/goober")
        self.assertEqual(data['data']['attributes']['state'], "draft")
        self.assertEquals(self.cli.doi_state("10.88434/goober"), "draft")
        self.assertTrue(self.cli.doi_exists("10.88434/goober"))
        self.assertTrue(self.cli.doi_exists("goober", "10.88434"))

        with self.assertRaises(dc.DOIClientException):
            data = self.cli.reserve("goober")

        self.cli.delete_reservation("10.88434/goober")
        self.assertTrue(not self.cli.doi_exists("10.88434/goober"))
        self.assertEquals(self.cli.doi_state("10.88434/goober"), "")

    def test_reserve_bad_prefix(self):
        self.assertTrue(not self.cli.doi_exists("30.88434/goober"))

        with self.assertRaises(ValueError):
            data = self.cli.reserve("goober", "30.88434")
        
    def test_update_draft(self):
        id = "20.88434/goober"

        data = self.cli.reserve("goober", "20.88434")
        self.assertEqual(data['data']['id'], "20.88434/goober")
        self.assertEqual(data['data']['attributes']['doi'], "20.88434/goober")
        self.assertTrue(self.cli.doi_exists("20.88434/goober"))

        atts = {
            "publicationYear": 2020,
            "titles": [{
                "title": "Junk"
            }]
        }
        data = self.cli.update(atts, "goober", "20.88434")
        self.assertEqual(data['data']['id'], "20.88434/goober")
        self.assertEqual(data['data']['attributes']['doi'], "20.88434/goober")
        self.assertEqual(data['data']['attributes']['publicationYear'], 2020)
        self.assertEqual(data['data']['attributes']['titles'], [{"title":"Junk"}])
        self.assertEqual(data['data']['attributes']['state'], "draft")
        
        self.cli.delete_reservation("goober", "20.88434")
        self.assertTrue(not self.cli.doi_exists("20.88434/goober"))
        self.assertEquals(self.cli.doi_state("20.88434/goober"), "")
        
    def test_publish_flow(self):
        id = "10.88434/goob"

        # reserve the DOI
        data = self.cli.reserve("goob", "10.88434")
        self.assertEqual(data['data']['id'], "10.88434/goob")
        self.assertEqual(data['data']['attributes']['doi'], "10.88434/goob")
        self.assertTrue(self.cli.doi_exists("10.88434/goob"))

        # update it
        atts = {
            "publicationYear": 2020,
            "titles": [{
                "title": "Junk"
            }]
        }
        data = self.cli.update(atts, "goob", "10.88434")
        self.assertEqual(data['data']['id'], "10.88434/goob")
        self.assertEqual(data['data']['attributes']['doi'], "10.88434/goob")
        self.assertEqual(data['data']['attributes']['publicationYear'], 2020)
        self.assertEqual(data['data']['attributes']['titles'], [{"title":"Junk"}])
        self.assertEqual(data['data']['attributes']['state'], "draft")

        # attempt to publish it with insufficient metadata
        atts = {
            "publisher": "NIST",
            "types": {}
        }
        data = self.cli.publish("goob", atts)
        self.assertEqual(data['data']['attributes']['state'], "draft")

        # provided all necessary metadata and publish
        atts = {
            "url": "https://goob.net/",
            "titles": [{ "title": "The Humble Peanut" }],
            "publisher": "NIST",
            "publicationYear": 2020,
            "creators": [{"fn": "me"}],
            "types": { "resourceType": "Dataset", "schemaOrg": "Dataset"}
        }
        data = self.cli.publish("goob", atts)
        self.assertEqual(data['data']['attributes']['state'], "findable")

        # update the metadata after publication
        data = self.cli.update({ "publicationYear": 2021 }, "goob")
        self.assertEqual(data['data']['attributes']['state'], "findable")
        self.assertEqual(data['data']['attributes']['publicationYear'], 2021)

        # attempt to DELETE a published DOI
        with self.assertRaises(dc.DOIClientException):
            self.cli.delete_reservation("10.88434/goob")
        
            
        
        
            

if __name__ == '__main__':
    test.main()

