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
    
class TestJSONAPIError(test.TestCase):

    def setUp(self):
        pass

    def test_badinput(self):
        with self.assertRaises(TypeError):
            je = dc.JSONAPIError("goob")

    def test_none(self):
        je = dc.JSONAPIError(None)
        self.assertEqual(je.code, 0)
        self.assertIsNone(je.defmsg)
        self.assertEqual(len(je.edata), 1)
        self.assertEqual(je.edata[0]['title'], "Unknown error")
        msg = je.message()
        self.assertEqual(msg, "Unknown error")
        self.assertEqual(je.explain(), "DOI service error\n  Unknown error")
        self.assertEqual(je._(), {"message": msg, "errdata": je})

    def test_def_msg_only(self):
        je = dc.JSONAPIError(None, "Not funny", 420)
        self.assertEqual(je.code, 420)
        self.assertEqual(je.defmsg, "Not funny")
        self.assertEqual(len(je.edata), 1)
        self.assertEqual(je.edata[0]['title'], "Not funny")
        msg = je.message()
        self.assertEqual(msg, "Not funny")
        self.assertEqual(je.explain(), "DOI service error: Not funny (420)\n  Not funny")
        self.assertEqual(je._(), {"message": msg, "errdata": je})

        
    def test_def_errdata(self):
        edata = [
            { "title": "Dr.",  "detail": "Tuesdays",      "source": "for fiber"},
            { "title": "NoNo", "detail": "Don't do that", "source": "devil"},
            { "detail": "It's really bad", "source": "your mom" }
        ]
        je = dc.JSONAPIError(edata, "Not funny", 420)
        self.assertEqual(je.code, 420)
        self.assertEqual(je.defmsg, "Not funny")
        self.assertEqual(len(je.edata), 3)
        self.assertEqual(je.edata[0]['title'], "Dr.")

        msg = je.message()
        self.assertEqual(msg, "Dr.: Tuesdays (plus other errors)")
        self.assertEqual(je.explain(), "DOI service error: Not funny (420)\nDetails:\n  Dr.: Tuesdays\n  NoNo: Don't do that\n  your mom: It's really bad")

class TestDataCiteDOIClient(test.TestCase):
    defargs = { "publisher": "NIST", "url": "", "title": "", "special": "yes" }

    def setUp(self):
        self.cli = dc.DataCiteDOIClient(baseurl, None, prefixes, self.defargs)

    def test_supports_prefix(self):
        self.assertTrue(not self.cli.supports_prefix("30.30303"))
        self.assertTrue(self.cli.supports_prefix("10.88434"))
        self.assertTrue(self.cli.supports_prefix("20.88434"))

    def test_default_prefix(self):
        self.assertTrue(self.cli.default_prefix, "10.88434")

    def test_not_doi_exists(self):
        self.assertTrue(not self.cli.exists("10.88434/goober"))

    def test_lookup_notfound(self):
        with self.assertRaises(dc.DOIDoesNotExist):
            self.cli.lookup("10.88434/nonexistent")
        with self.assertRaises(dc.DOIDoesNotExist):
            self.cli.lookup("nonexistent", "10.88434")

        doid = self.cli.lookup("nonexistent", "10.88434", relax=True)
        self.assertEqual(doid.doi, "10.88434/nonexistent")
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "")
        self.assertFalse(doid.exists)
        self.assertFalse(doid.is_readonly)

        self.assertEqual(len(doid.attrs.keys()), 3)
        self.assertEqual(doid.attrs['prefix'], "10.88434")
        self.assertEqual(doid.attrs['doi'], "10.88434/nonexistent")
        self.assertEqual(doid.attrs['state'], "")
        self.assertEqual(doid.meta, {})
        self.assertEqual(doid.links, {})
        self.assertEqual(doid.relationships, {})
            
        doid = self.cli.lookup("40.88434/nonexistent", relax=True)
        self.assertEqual(doid.doi, "40.88434/nonexistent")
        self.assertEqual(doid.prefix, "40.88434")
        self.assertEqual(doid.state, "")
        self.assertFalse(doid.exists)
        self.assertTrue(doid.is_readonly)

    def test_reserve(self):
        self.assertTrue(not self.cli.exists("10.88434/goober"))

        doid = self.cli.reserve("goober")
        self.assertEqual(doid.doi, "10.88434/goober")
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "draft")
        self.assertTrue(doid.exists)
        self.assertFalse(doid.is_readonly)

        self.assertEqual(doid.attrs['prefix'], "10.88434")
        self.assertEqual(doid.attrs['doi'], "10.88434/goober")
        self.assertEqual(doid.attrs['state'], "draft")
        self.assertEqual(doid.attrs['publisher'], "NIST")
        self.assertEqual(doid.attrs['special'], "yes")
        self.assertEqual(doid.attrs['url'], "")
        self.assertEqual(doid.attrs['title'], "")

        self.assertTrue(self.cli.exists("10.88434/goober"))
        doid = self.cli.lookup("goober")
        self.assertEqual(doid.doi, "10.88434/goober")
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "draft")
        self.assertTrue(doid.exists)
        self.assertFalse(doid.is_readonly)

        self.assertEqual(doid.attrs['prefix'], "10.88434")
        self.assertEqual(doid.attrs['doi'], "10.88434/goober")
        self.assertEqual(doid.attrs['state'], "draft")
        self.assertEqual(doid.attrs['publisher'], "NIST")
        self.assertEqual(doid.attrs['url'], "")
        self.assertEqual(doid.attrs['title'], "")

        doid.attrs['title'] = "Goober"
        doid.refresh()
        self.assertEqual(doid.doi, "10.88434/goober")
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "draft")
        self.assertTrue(doid.exists)
        self.assertFalse(doid.is_readonly)

        self.assertEqual(doid.attrs['prefix'], "10.88434")
        self.assertEqual(doid.attrs['doi'], "10.88434/goober")
        self.assertEqual(doid.attrs['state'], "draft")
        self.assertEqual(doid.attrs['publisher'], "NIST")
        self.assertEqual(doid.attrs['url'], "")
        self.assertEqual(doid.attrs['title'], "")

        doid._ro = True
        with self.assertRaises(dc.DOIStateError):
            doid.delete()
        doid._ro = False
        doid.delete()
        self.assertFalse(self.cli.exists(doid.doi))
        self.assertFalse(doid.exists)

    def test_reserve_from_nonex(self):
        self.assertTrue(not self.cli.exists("10.88434/goob5"))

        # lookup as non-existent DOI
        doid = self.cli.lookup("goob5", relax=True)
        self.assertEqual(doid.doi, "10.88434/goob5")
        self.assertTrue(not doid.exists)
        self.assertEqual(doid.state, "")
        self.assertNotIn("publisher", doid.attrs)
        self.assertFalse(doid.is_readonly)

        doid.reserve()
        self.assertTrue(doid.exists)
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs["publisher"], "NIST")
        self.assertEqual(doid.attrs["special"], "yes")
        self.assertFalse(doid.is_readonly)

        self.assertTrue(self.cli.exists("10.88434/goob5"))

        doid.delete()
        self.assertTrue(not doid.exists)
        self.assertEqual(doid.state, "")
        self.assertTrue(not self.cli.exists("10.88434/goob5"))

        doid.reserve({"publisher": "NISTy"})
        self.assertTrue(doid.exists)
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs["publisher"], "NISTy")
        self.assertEqual(doid.attrs["special"], "yes")
        self.assertFalse(doid.is_readonly)

        self.assertTrue(self.cli.exists("10.88434/goob5"))

        doid.delete()
        self.assertTrue(not doid.exists)
        self.assertEqual(doid.state, "")
        self.assertTrue(not self.cli.exists("10.88434/goob5"))

        
    def test_create(self):
        with self.assertRaises(ValueError):
            self.cli.create("40.404040")

        doid = self.cli.create("20.88434")
        doi = doid.doi
        self.assertEqual(doid.prefix, "20.88434")
        self.assertEqual(doid.state, "draft")
        self.assertTrue(doid.exists)
        self.assertFalse(doid.is_readonly)

        doid = self.cli.lookup(doi)
        self.assertEqual(doid.doi, doi)
        self.assertEqual(doid.prefix, "20.88434")
        self.assertEqual(doid.state, "draft")
        self.assertTrue(doid.exists)
        self.assertFalse(doid.is_readonly)

        doid.delete()
        self.assertFalse(self.cli.exists(doid.doi))
        self.assertFalse(doid.exists)
        
        doid = self.cli.create()
        doi = doid.doi
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "draft")
        self.assertTrue(doid.exists)
        self.assertFalse(doid.is_readonly)

        doid.delete()
        self.assertFalse(self.cli.exists(doid.doi))
        self.assertFalse(doid.exists)

    def test_update(self):
        doid = self.cli.lookup("nonexistent", "40.88434", relax=True)
        with self.assertRaises(dc.DOIStateError):
            doid.update({"title": "Star Wars"})

        doid = self.cli.reserve("goob2")
        self.assertEqual(doid.doi, "10.88434/goob2")
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs['publisher'], "NIST")
        self.assertEqual(doid.attrs['url'], "")
        self.assertEqual(doid.attrs['title'], "")
        self.assertNotIn('publicationYear', doid.attrs)

        doid.update({"title": "Star Wars", "publicationYear": 1977, "event": "publish"})
        self.assertEqual(doid.doi, "10.88434/goob2")
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs['publisher'], "NIST")
        self.assertEqual(doid.attrs['url'], "")
        self.assertEqual(doid.attrs['title'], "Star Wars")
        self.assertEqual(doid.attrs['publicationYear'], 1977)


        doid.update({"title": "Star Wars Episode IV: a New Hope"})
        self.assertEqual(doid.doi, "10.88434/goob2")
        self.assertEqual(doid.prefix, "10.88434")
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs['publisher'], "NIST")
        self.assertEqual(doid.attrs['url'], "")
        self.assertEqual(doid.attrs['title'], "Star Wars Episode IV: a New Hope")
        self.assertEqual(doid.attrs['publicationYear'], 1977)

    def test_publish_draft(self):
        self.assertTrue(not self.cli.exists("20.88434/goob3"))

        # reserve the DOI
        doid = self.cli.reserve("goob3", "20.88434")
        self.assertEqual(doid.attrs['state'], 'draft')
        self.assertEqual(doid.doi, "20.88434/goob3")
        self.assertTrue(self.cli.exists("goob3", "20.88434"))

        # update it
        atts = {
            "publicationYear": 2020,
            "titles": [{
                "title": "Junk"
            }]
        }
        data = doid.update(atts)
        
        # attempt to publish it with insufficient metadata
        atts = {
            "types": {}
        }
        with self.assertRaises(dc.DOIStateError):
            doid.publish(atts)
        self.assertEqual(doid.state, "draft")
        doid = self.cli.lookup("goob3", "20.88434")
        self.assertEqual(doid.state, "draft")
        self.assertNotIn("types", doid.attrs)

        # publish with all needed metadata
        atts = {
            "url": "https://goob.net/",
            "titles": [{ "title": "The Humble Peanut" }],
            "publicationYear": 2020,
            "creators": [{"fn": "me"}],
            "types": { "resourceType": "Dataset", "schemaOrg": "Dataset"}
        }
        doid.publish(atts)
        self.assertEqual(doid.attrs['url'], "https://goob.net/")
        self.assertEqual(doid.state, "findable")

        # update the metadata after publication
        doid.update({"url": "https://goob.net/goob3"})
        self.assertEqual(doid.attrs['url'], "https://goob.net/goob3")
        self.assertEqual(doid.state, "findable")
        
        # attempt to DELETE a published DOI
        with self.assertRaises(dc.DOIStateError):
            doid.delete()

        doid = self.cli.lookup("20.88434/goob3")
        self.assertEqual(doid.attrs['url'], "https://goob.net/goob3")
        self.assertEqual(doid.state, "findable")

    def test_publish_new(self):
        self.assertTrue(not self.cli.exists("goob4"))

        # lookup non-existent DOI
        doid = self.cli.lookup("goob4", relax=True)
        self.assertEqual(doid.doi, "10.88434/goob4")
        self.assertEqual(doid.state, "")
        self.assertNotIn("publisher", doid.attrs)
        self.assertFalse(doid.is_readonly)

        # try to publish with insufficient metadata
        with self.assertRaises(dc.DOIStateError):
            doid.publish()
        self.assertEqual(doid.doi, "10.88434/goob4")
        self.assertEqual(doid.state, "")
        self.assertNotIn("publisher", doid.attrs)
        self.assertFalse(doid.is_readonly)
        
        # publish with all needed metadata
        atts = {
            "url": "https://goob.net/",
            "titles": [{ "title": "The Humble Peanut" }],
            "publisher": "NISTy",
            "publicationYear": 2020,
            "creators": [{"fn": "me"}],
            "types": { "resourceType": "Dataset", "schemaOrg": "Dataset"}
        }
        doid.publish(atts)

        self.assertEqual(doid.doi, "10.88434/goob4")
        self.assertEqual(doid.state, "findable")
        self.assertEqual(doid.attrs["publisher"], "NISTy")
        self.assertEqual(doid.attrs["special"], "yes")

        # attempt to DELETE a published DOI
        with self.assertRaises(dc.DOIStateError):
            doid.delete()
        self.assertEqual(doid.state, "findable")

    def test_publish_noarg(self):
        self.assertTrue(not self.cli.exists("20.88434/goob6"))

        # reserve the DOI
        doid = self.cli.reserve("goob6", "20.88434")
        self.assertEqual(doid.attrs['state'], 'draft')
        self.assertEqual(doid.doi, "20.88434/goob6")
        self.assertTrue(self.cli.exists("goob3", "20.88434"))

        # update with all needed metadata
        atts = {
            "url": "https://goob.net/",
            "titles": [{ "title": "The Humble Peanut" }],
            "publicationYear": 2020,
            "creators": [{"fn": "me"}],
            "types": { "resourceType": "Dataset", "schemaOrg": "Dataset"}
        }
        doid.update(atts)

        # now publish
        doid.publish()
        self.assertEqual(doid.attrs['url'], "https://goob.net/")
        self.assertEqual(doid.state, "findable")



        
        
        

if __name__ == '__main__':
    test.main()

