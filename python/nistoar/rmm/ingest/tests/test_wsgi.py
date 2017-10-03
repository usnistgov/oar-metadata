import pdb, os, json, urlparse, warnings, logging
from cStringIO import StringIO
import unittest as test
from pymongo import MongoClient
from ejsonschema import ExtValidator, SchemaValidator

from nistoar.tests import *
from nistoar.rmm.ingest import wsgi

pydir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
basedir = os.path.dirname(pydir)
schemadir = os.path.join(basedir, "model")
exdir = os.path.join(schemadir, "examples")
janaffile = os.path.join(exdir, "janaf.json")

dburl = None
if os.environ.get('MONGO_TESTDB_URL'):
    dburl = os.environ.get('MONGO_TESTDB_URL')

assert os.path.exists(schemadir), schemadir

loghdlr = None
rootlog = None
def setUpModule():
    ensure_tmpdir()
    rootlog = logging.getLogger()
    loghdlr = logging.FileHandler(os.path.join(tmpdir(),"test_wsgi.log"))
    loghdlr.setLevel(logging.INFO)
    rootlog.addHandler(loghdlr)

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
        self.config = {
            "db_url": dburl
        }
        
        try:
            self.svc = wsgi.app(self.config)
        except Exception, e:
            self.tearDown()
            raise
        self.resp = []

    def tearDown(self):
        client = MongoClient(dburl)
        db = client.get_default_database()
        if "record" in db.collection_names():
            db.drop_collection("record")
        
    def test_ctor(self):
        self.assertTrue(self.svc.dburl.startswith("mongodb://"))

    def test_get_types(self):
        req = {
            'PATH_INFO': '/',
            'REQUEST_METHOD': 'GET'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertEqual(body[0], '["nerdm"]')

    def test_is_ready(self):
        req = {
            'PATH_INFO': '/nerdm/',
            'REQUEST_METHOD': 'GET'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertEqual(body[0], 'Service ready\n')

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

    def test_bad_post_resource(self):
        with open(janaffile) as doc:
            req = {
                'PATH_INFO': '/nerdm/goober/',
                'REQUEST_METHOD': 'POST',
                'wsgi.input': doc
            }

            body = self.svc(req, self.start)

        self.assertIn("404", self.resp[0])

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

    def test_good_post(self):
        client = MongoClient(dburl)
        try:
            db = client.get_default_database()
            if "record" in db.collection_names():
                recs = db['record'].find()
                self.assertEqual(recs.count(), 0)
            client.close()
        finally:
            client.close()
        
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

        self.assertIn("200", self.resp[0])
        
        client = MongoClient(dburl)
        try:
            db = client.get_default_database()
            self.assertIn("record", db.collection_names())
            recs = db['record'].find()
            self.assertEqual(recs.count(), 1)
            self.assertIn("JANAF", recs[0]['title'])
        finally:
            client.close()
        

if __name__ == '__main__':
    test.main()

        


