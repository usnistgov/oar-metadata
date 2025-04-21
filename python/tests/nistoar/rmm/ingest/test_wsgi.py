import pdb, os, json, urllib.parse, warnings, logging
from io import StringIO
from copy import deepcopy
import unittest as test
from ejsonschema import ExtValidator, SchemaValidator

from nistoar.testing import *
from nistoar.rmm.ingest import wsgi

testdir = os.path.dirname(os.path.abspath(__file__))
pydir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(testdir))))
basedir = os.path.dirname(pydir)
schemadir = os.path.join(basedir, "model")
exdir = os.path.join(schemadir, "examples")
janaffile = os.path.join(exdir, "janaf.json")
postcomm = os.path.join(testdir, "postcomm.sh")

dburl = None
metrics_dburl = None 
if os.environ.get('MONGO_TESTDB_URL'):
    from pymongo import MongoClient
    dburl = os.environ.get('MONGO_TESTDB_URL')

if os.environ.get('MONGO_METRICS_TESTDB_URL'):
    from pymongo import MongoClient
    metrics_dburl = os.environ.get('MONGO_METRICS_TESTDB_URL')

assert os.path.exists(schemadir), schemadir

loghdlr = None
rootlog = None
tmpfiles = None
def setUpModule():

    global tmpfiles
    tmpfiles = Tempfiles()
    tmpfiles.track("test_wsgi.log")
    rootlog = logging.getLogger()
    loghdlr = logging.FileHandler(os.path.join(tmpfiles.root, "test_wsgi.log"))
    loghdlr.setLevel(logging.INFO)
    rootlog.addHandler(loghdlr)
    rootlog.setLevel(logging.INFO)

def tearDownModule():
    global loghdlr
    if loghdlr:
        if rootlog:
            rootlog.removeLog(loghdlr)
        loghdlr = None
    rmtmpdir()

@test.skipIf(not os.environ.get('MONGO_TESTDB_URL'),
             "test mongodb not available")
class TestRMMRecordIngestApp(test.TestCase):

    def start(self, status, headers=None, extup=None):
        self.resp.append(status)
        for head in headers:
            self.resp.append("{0}: {1}".format(head[0], head[1]))

    def setUp(self):
        self.archdir = tmpfiles.mkdir("ingest_archive")
        self.commitfile = os.path.join(self.archdir, "postcommit.txt")
        self.config = {
            "db_url": dburl,
            "metrics_db_url": metrics_dburl,
            'nerdm_schema_dir': os.path.abspath(schemadir),
            'archive_dir': self.archdir,
            'post_commit_exec': postcomm + ' ' + self.commitfile + " {db_url} {recid} {recfile}"
        }

        try:
            self.svc = wsgi.app(self.config)
        except Exception as e:
            self.tearDown()
            raise
        self.resp = []

    def tearDown(self):
        client = MongoClient(dburl)
        if not hasattr(client, 'get_database'):
            client.get_database = client.get_default_database
        db = client.get_database()
        if "record" in db.list_collection_names():
            db.drop_collection("record")
        if "versions" in db.list_collection_names():
            db.drop_collection("versions")
        if "releaseSets" in db.list_collection_names():
            db.drop_collection("releaseSets")
        if "taxonomy" in db.list_collection_names():
            db.drop_collection("taxonomy")
        if "fields" in db.list_collection_names():
            db.drop_collection("fields")
        tmpfiles.clean()
        


    def test_ctor(self):
        self.assertTrue(self.svc.dburl.startswith("mongodb://"))

        del self.config['archive_dir']
        with self.assertRaises(wsgi.ConfigurationException):
            self.svc = wsgi.app(self.config)

    def test_get_types(self):
        req = {
            'PATH_INFO': '/',
            'REQUEST_METHOD': 'GET'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertEqual(body[0].decode().strip(), '["nerdm"]')
        self.assertFalse(os.path.exists(self.commitfile), "Commit file created unexpectedly")

    def test_is_ready(self):
        req = {
            'PATH_INFO': '/nerdm/',
            'REQUEST_METHOD': 'GET'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertEqual(body[0].decode(), 'Service ready\n')
        self.assertFalse(os.path.exists(self.commitfile), "Commit file created unexpectedly")

    def test_auth(self):
        # test rejection when auth key provided but wsgi is not configured to
        # take one
        req = {
            'PATH_INFO': '/nerdm/',
            'REQUEST_METHOD': 'GET',
            'QUERY_STRING': 'goob=able&auth=9e73'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("401", self.resp[0])
        self.assertNotIn("WWW-Authenticate: Bearer", self.resp)
        self.assertEqual(body, [])

        # now configure the service to require a key
        cfg = deepcopy(self.config)
        cfg['auth_key'] = '9e73'
        self.svc = wsgi.app(cfg)

        # test successful acceptance of key
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertGreater(len(body), 0)
        self.assertEqual(body[0].decode(), 'Service ready\n')

        # test single rejection
        req['QUERY_STRING'] = 'goob=able&auth=gurn'
        self.resp = []
        body = self.svc(req, self.start)
        self.assertIn("401", self.resp[0])
        self.assertNotIn("WWW-Authenticate: Bearer", self.resp)
        self.assertEqual(body, [])

        # test lack of auth key
        del req['QUERY_STRING']
        self.resp = []
        body = self.svc(req, self.start)
        self.assertIn("401", self.resp[0])
        self.assertEqual(body, [])

        # test header access key
        cfg['auth_method'] = 'header'
        self.svc = wsgi.app(cfg)

        self.resp = []
        body = self.svc(req, self.start)
        self.assertIn("401", self.resp[0])
        self.assertIn("WWW-Authenticate: Bearer", self.resp)
        self.assertEqual(body, [])

        self.resp = []
        req['HTTP_AUTHORIZATION'] = 'Bearer 9e73'
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertGreater(len(body), 0)
        self.assertEqual(body[0].decode(), 'Service ready\n')

        self.resp = []
        req['HTTP_AUTHORIZATION'] = 'Token 9e73'
        body = self.svc(req, self.start)
        self.assertIn("401", self.resp[0])
        self.assertIn("WWW-Authenticate: Bearer", self.resp)
        self.assertEqual(body, [])

        self.resp = []
        req['HTTP_AUTHORIZATION'] = 'Bearer'
        body = self.svc(req, self.start)
        self.assertIn("401", self.resp[0])
        self.assertIn("WWW-Authenticate: Bearer", self.resp)
        self.assertEqual(body, [])
        
        
        

    def test_is_not_ready(self):
        req = {
            'PATH_INFO': '/fields/',
            'REQUEST_METHOD': 'GET'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])

    def test_is_not_found(self):
        req = {
            'PATH_INFO': '/nerdm/goober/',
            'REQUEST_METHOD': 'GET'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertFalse(os.path.exists(self.commitfile), "Commit file created unexpectedly")

    def test_bad_post_resource(self):
        with open(janaffile) as doc:
            req = {
                'PATH_INFO': '/nerdm/goober/',
                'REQUEST_METHOD': 'POST',
                'wsgi.input': doc
            }

            body = self.svc(req, self.start)

        self.assertIn("404", self.resp[0])
        self.assertFalse(os.path.exists(self.commitfile), "Commit file created unexpectedly")

    def test_no_content_length(self):
        with open(janaffile) as doc:
            req = {
                'PATH_INFO': '/nerdm/',
                'REQUEST_METHOD': 'POST',
                'wsgi.input': doc
            }

            body = self.svc(req, self.start)

        self.assertIn("411", self.resp[0])
        self.assertIn("Content-Length", self.resp[0])
        self.assertFalse(os.path.exists(self.commitfile), "Commit file created unexpectedly")

    def test_bad_content_length(self):
        with open(janaffile) as doc:
            req = {
                'PATH_INFO': '/nerdm/',
                'REQUEST_METHOD': 'POST',
                'CONTENT_LENGTH': 32,
                'wsgi.input': doc
            }

            body = self.svc(req, self.start)

        self.assertIn("400", self.resp[0])
        self.assertFalse(os.path.exists(self.commitfile), "Commit file created unexpectedly")

    def test_bad_post_input(self):
        doc = StringIO('title <a href="http://bad.url">hello world</a>')
        req = {
            'PATH_INFO': '/nerdm/',
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': 46,
            'wsgi.input': doc
        }

        body = self.svc(req, self.start)
        self.assertIn("400", self.resp[0])
        self.assertFalse(os.path.exists(self.commitfile), "Commit file created unexpectedly")

    def test_good_post(self):
        client = MongoClient(dburl)
        if not hasattr(client, 'get_database'):
            client.get_database = client.get_default_database
        try:
            db = client.get_database()
            if "record" in db.list_collection_names():
                recs = db['record'].find()
                self.assertEqual(db['record'].count_documents(), 0)
            client.close()
        finally:
            client.close()
        
        # self.svc = wsgi.app(self.config)
        with open(janaffile) as doc:
            clen = len(doc.read())
        with open(janaffile) as doc:
            req = {
                'PATH_INFO': '/nerdm/',
                'REQUEST_METHOD': 'POST',
                'CONTENT_LENGTH': clen,
                'wsgi.input': doc
            }
            body = self.svc(req, self.start)

        archfile = os.path.join(self.archdir, "sdp0fjspek351-v1_0_0.json")
        self.assertTrue(os.path.isfile(archfile))

        self.assertIn("200", self.resp[0])
        self.assertTrue(os.path.isfile(self.commitfile), "Failed to create commit file")
        with open(self.commitfile) as fd:
            content = fd.read()
        self.assertIn("sdp0fjspek351", content)
        self.assertIn("mongodb:", content)
        
        client = MongoClient(dburl)
        try:
            if not hasattr(client, 'get_database'):
                client.get_database = client.get_default_database
            db = client.get_database()
            self.assertIn("record", db.list_collection_names())
            recs = db['record'].find()
            self.assertEqual(db['record'].count_documents({}), 1)
            self.assertIn("JANAF", recs[0]['title'])
        finally:
            client.close()

class TestArchive(test.TestCase):

    def setUp(self):
        self.archdir = tmpfiles.mkdir("ingest_archive")
        os.mkdir(os.path.join(self.archdir, "_cache"))
        self.hdlr = wsgi.Handler(None, {"REQUEST_METHOD": "GET"}, None,
                                 self.archdir)

    def tearDown(self):
        tmpfiles.clean()

    def test_mkpostcomm(self):
        commexec = "echo {recfile} goober {recid} {file}"
        commexec = wsgi._mkpostcomm(commexec, file="/tmp/gurn.txt")
        self.assertTrue(isinstance(commexec, list), "Output is not a list")
        self.assertEqual(len(commexec), 5)
        self.assertEqual(commexec[4], "/tmp/gurn.txt")
        self.assertEqual(commexec[0], "echo")
        self.assertEqual(commexec[1], "{recfile}")
        self.assertEqual(commexec[2], "goober")
        self.assertEqual(commexec[3], "{recid}")

        commexec = wsgi._mkpostcomm(commexec, "mds2-5555", file="/tmp/gary.txt")
        self.assertEqual(commexec[4], "/tmp/gurn.txt")
        self.assertEqual(commexec[0], "echo")
        self.assertEqual(commexec[1], "{recfile}")
        self.assertEqual(commexec[2], "goober")
        self.assertEqual(commexec[3], "mds2-5555")

        commexec = wsgi._mkpostcomm(commexec, "mds2-5556", "/tmp", file="/tmp/gary.txt")
        self.assertEqual(commexec[4], "/tmp/gurn.txt")
        self.assertEqual(commexec[0], "echo")
        self.assertEqual(commexec[1], "/tmp/mds2-5556.json")
        self.assertEqual(commexec[2], "goober")
        self.assertEqual(commexec[3], "mds2-5555")

        commexec = "echo {recfile} goober {recid} {file}"
        commexec = wsgi._mkpostcomm(commexec, "mds2-5555", "/tmp", file="/tmp/gary.txt")
        self.assertEqual(commexec[4], "/tmp/gary.txt")
        self.assertEqual(commexec[0], "echo")
        self.assertEqual(commexec[1], "/tmp/mds2-5555.json")
        self.assertEqual(commexec[2], "goober")
        self.assertEqual(commexec[3], "mds2-5555")

        
    def test_nerdm_archive_cache(self):
        with open(janaffile) as fd:
            rec = json.load(fd)
        self.assertTrue(rec)

        recid = self.hdlr.nerdm_archive_cache(rec)
        self.assertEqual(recid, "sdp0fjspek351-v1_0_0")
        cachefile = os.path.join(self.archdir, "_cache",
                                 os.path.basename(recid)+".json")

        self.assertTrue(os.path.isdir(os.path.dirname(cachefile)))
        self.assertTrue(os.path.isfile(cachefile))

        with open(cachefile) as fd:
            self.assertEqual(json.load(fd), rec)

        archfile = os.path.join(self.archdir, os.path.basename(recid)+".json")
        self.assertFalse(os.path.exists(archfile))

        self.hdlr.nerdm_archive_commit(recid)
        self.assertTrue(os.path.isfile(archfile))
        self.assertFalse(os.path.exists(cachefile))
        
        with open(archfile) as fd:
            self.assertEqual(json.load(fd), rec)

                                 

if __name__ == '__main__':
    test.main()

        


