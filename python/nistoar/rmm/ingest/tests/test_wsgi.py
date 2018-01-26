import pdb, os, json, urlparse, warnings, logging
from cStringIO import StringIO
from copy import deepcopy
import unittest as test
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
    from pymongo import MongoClient
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
        self.config = {
            "db_url": dburl,
            'nerdm_schema_dir': os.path.abspath(schemadir)
        }

        try:
            self.svc = wsgi.app(self.config)
        except Exception, e:
            self.tearDown()
            raise
        self.resp = []

    def tearDown(self):
        client = MongoClient(dburl)
        if not hasattr(client, 'get_database'):
            client.get_database = client.get_default_database
        db = client.get_database()
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
        self.assertEqual(body[0].strip(), '["nerdm"]')

    def test_is_ready(self):
        req = {
            'PATH_INFO': '/nerdm/',
            'REQUEST_METHOD': 'GET'
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertEqual(body[0], 'Service ready\n')

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
        self.assertEqual(body[0], 'Service ready\n')

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
        self.assertEqual(body[0], 'Service ready\n')

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
        if not hasattr(client, 'get_database'):
            client.get_database = client.get_default_database
        try:
            db = client.get_database()
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
            if not hasattr(client, 'get_database'):
                client.get_database = client.get_default_database
            db = client.get_database()
            self.assertIn("record", db.collection_names())
            recs = db['record'].find()
            self.assertEqual(recs.count(), 1)
            self.assertIn("JANAF", recs[0]['title'])
        finally:
            client.close()
        

if __name__ == '__main__':
    test.main()

        


