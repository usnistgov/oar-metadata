from __future__ import absolute_import
import os, pdb, requests, logging, time, json
import unittest as test
from copy import deepcopy
from StringIO import StringIO

testdir = os.path.dirname(os.path.abspath(__file__))
datadir = os.path.join(testdir, 'data')

import imp
simsrvrsrc = os.path.join(testdir, "sim_datacite_srv.py")
with open(simsrvrsrc, 'r') as fd:
    svc = imp.load_module("sim_datacite_svc", fd, simsrvrsrc,
                          (".py", 'r', imp.PY_SOURCE))

basedir = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(testdir)))))

port = 9091
baseurl = "http://localhost:{0}/".format(port)

class TestSimIDRepo(test.TestCase):

    def setUp(self):
        self.repo = svc.SimIDRepo()

    def test_add_id(self):
        id = "10/path"
        data = {
            "doi": "goob",
            "title": "Oh, hello"
        }

        saved = self.repo.add_id(id, data)
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['title'], "Oh, hello")
        self.assertEqual(saved['state'], "draft")
        self.assertFalse("author" in saved)

        self.assertTrue(id in self.repo.ids)

        saved = self.repo.describe(id)
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['title'], "Oh, hello")
        self.assertEqual(saved['state'], "draft")
        self.assertFalse("author" in saved)

        data["author"] = "Gurn Cranston"

        with self.assertRaises(ValueError):
            self.repo.add_id(id, data)

    def test_update_id(self):
        id = "10/path"
        data = {
            "doi": "goob",
            "title": "Oh, hello"
        }

        with self.assertRaises(ValueError):
            self.repo.update_id(id, data)

        saved = self.repo.add_id(id, data)
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['title'], "Oh, hello")
        self.assertEqual(saved['state'], "draft")
        self.assertFalse("author" in saved)

        self.assertTrue(id in self.repo.ids)

        data = {
            "title": "Oh, okay",
            "author": "Gurn Cranston",
            "event": "register"
        }

        saved = self.repo.update_id(id, data)
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['title'], "Oh, okay")
        self.assertEqual(saved['state'], "registered")
        self.assertTrue("author" in saved)
        self.assertEqual(saved['author'], "Gurn Cranston")

        data = {
            "event": "publish"
        }

        saved = self.repo.update_id(id, data)
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['title'], "Oh, okay")
        self.assertEqual(saved['state'], "findable")
        self.assertEqual(saved['author'], "Gurn Cranston")

    def test_delete(self):
        id = "10/path"
        data = {
            "doi": "goob",
            "title": "Oh, hello"
        }

        saved = self.repo.add_id(id, data)
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['title'], "Oh, hello")
        self.assertEqual(saved['state'], "draft")
        self.assertIn(id, self.repo.ids)

        self.repo.delete(id)
        self.assertNotIn(id, self.repo.ids)

        data['event'] = "publish"
        saved = self.repo.add_id(id, data)
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['title'], "Oh, hello")
        self.assertEqual(saved['state'], "findable")
        self.assertIn(id, self.repo.ids)

        with self.assertRaises(ValueError):
            self.repo.delete(id)


class TestSimIDService(test.TestCase):
        
    def start(self, status, headers=None, extup=None):
        self.resp.append(status)
        for head in headers:
            self.resp.append("{0}: {1}".format(head[0], head[1]))

    def setUp(self):
        self.svc = svc.SimIDService("/dois", ["10.88434", "20.88434"])
        self.resp = []

    def test_badGET(self):
        req = {
            'REQUEST_METHOD': 'GET',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'PATH_INFO': "/goob"
        }
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertEqual(body, [])

        self.resp = []
        req['PATH_INFO'] = "/dois"
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertIn("Ready", self.resp[0])
        self.assertEqual(body, [])

        self.resp = []
        req['PATH_INFO'] = "/dois/30.303030/"
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        self.resp = []
        req['PATH_INFO'] = "/dois/30.303030/goober"
        req['HTTP_ACCEPT'] = "application/json"
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("406", self.resp[0])
        doc = json.loads("\n".join(body))


    def test_badHEAD(self):
        req = {
            'REQUEST_METHOD': 'HEAD',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'PATH_INFO': "/goob"
        }
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertEqual(body, [])

        self.resp = []
        req['PATH_INFO'] = "/dois"
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertIn("Ready", self.resp[0])
        self.assertEqual(body, [])

        self.resp = []
        req['PATH_INFO'] = "/dois/30.303030/"
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertEqual(body, [])

    def test_badPOST(self):
        req = {
            'REQUEST_METHOD': 'POST',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT,
            'PATH_INFO': "/goog"
        }
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertEqual(body, [])

        req.update({
            'PATH_INFO': "/dois/20.88434/goober"
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("405", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        req.update({
            'CONTENT_TYPE': "application/json",
            'PATH_INFO': "/dois"
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("415", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        req.update({
            'HTTP_ACCEPT': "application/json",
            'CONTENT_TYPE': svc.JSONAPI_MT
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("406", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

    def test_badPUT(self):
        req = {
            'REQUEST_METHOD': 'PUT',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT,
            'PATH_INFO': "/goog"
        }
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertEqual(body, [])

        req.update({
            'PATH_INFO': "/dois"
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("405", self.resp[0])
        self.assertIn("Cannot PUT without ID", self.resp[0])
        self.assertEqual(body, [])

        req.update({
            'PATH_INFO': "/dois/30.303030"
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("405", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        req.update({
            'PATH_INFO': "/dois/30.303030/goober"
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("401", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        req.update({
            'CONTENT_TYPE': "application/json",
            'PATH_INFO': "/dois/20.88434/goober"
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("415", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        req.update({
            'HTTP_ACCEPT': "application/json",
            'CONTENT_TYPE': svc.JSONAPI_MT
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("406", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        req.update({
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT
        })
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

    def test_badPOST_input(self):
        inp = ''
        req = {
            'REQUEST_METHOD': 'POST',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT,
            'PATH_INFO': "/dois",
            'wsgi.input':  StringIO(inp)
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("400", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)
        
        inp = 'Tinker\nTailor\n'
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("400", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)
        
        inp = '{"goob":"gurn"}'
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("400", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)
        
        inp = '{"data":{}}'
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("400", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)
        
        inp = '{"data":{"attributes":{}}}'
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("400", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)
        
        inp = '{"data":{"type":"dois","attributes":{}}}'
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("400", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

    def test_create_update(self):
        id = "20.88434/goober"
        inp = json.dumps({
            "data": {
                "type": "dois",
                "attributes": {
                    "doi": id
                }
            }
        })
        req = {
            'REQUEST_METHOD': 'POST',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT,
            'PATH_INFO': "/dois",
            'wsgi.input':  StringIO(inp)
        }

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("201", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "draft")
        
        req = {
            'REQUEST_METHOD': 'GET',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'PATH_INFO': "/dois/"+id
        }
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])

        doc = json.loads("\n".join(body))
        self.assertEqual(doc['data']['attributes'], saved)
        
        req = {
            'REQUEST_METHOD': 'HEAD',
            'PATH_INFO': "/dois/"+id
        }
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertEqual(body, [])
        
        req = {
            'REQUEST_METHOD': 'HEAD',
            'PATH_INFO': "/dois/30.30303"
        }
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertEqual(body, [])
        
        inp = json.dumps({
            "data": {
                "type": "dois",
                "attributes": {
                    "title": "Peter Rabbit",
                    "author": "Stowe, H. B."
                }
            }
        })
        req = {
            'REQUEST_METHOD': 'PUT',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT,
            'PATH_INFO': "/dois/"+id,
            'wsgi.input':  StringIO(inp)
        }
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("201", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "draft")
        self.assertEqual(saved['title'], "Peter Rabbit")
        self.assertEqual(saved['author'], "Stowe, H. B.")

        # attempt to publish with insufficient metadata
        inp = json.dumps({
            "data": {
                "type": "dois",
                "attributes": {
                    "event": "publish",
                    "author": "Potter, Beatrix"
                }
            }
        })
        req['wsgi.input'] = StringIO(inp)
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("201", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "draft")
        self.assertEqual(saved['title'], "Peter Rabbit")
        self.assertEqual(saved['author'], "Potter, Beatrix")
        self.assertNotIn('publicationYear', saved)

        inp = json.dumps({
            "data": {
                "type": "dois",
                "attributes": {
                    "event": "publish",
                    "url": "https://goober.net/",
                    "titles": [{ "title": "Peter Rabbit" }],
                    "publisher": "NIST",
                    "publicationYear": 1902,
                    "creators": [{"fn": "Beatrix Potter"}],
                    "types": { "resourceType": "Book", "schemaOrg": "Book"}
                }
            }
        })
        req['wsgi.input'] = StringIO(inp)
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("201", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "findable")
        self.assertEqual(saved['title'], "Peter Rabbit")
        self.assertEqual(saved['titles'], [{"title": "Peter Rabbit"}])
        self.assertEqual(saved['author'], "Potter, Beatrix")
        self.assertEqual(saved['publicationYear'], 1902)

        inp = json.dumps({
            "data": {
                "type": "dois",
                "attributes": {
                    "size": "modest"
                }
            }
        })
        req['wsgi.input'] = StringIO(inp)

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("201", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "findable")
        self.assertEqual(saved['title'], "Peter Rabbit")
        self.assertEqual(saved['publicationYear'], 1902)
        self.assertEqual(saved['size'], "modest")
        self.assertEqual(saved['author'], "Potter, Beatrix")

    def test_DELETE(self):
        id = "20.88434/goober"

        # delete before creating
        req = {
            'REQUEST_METHOD': 'DELETE',
            'PATH_INFO': "/dois/"+id
        }
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)

        # create
        inp = {
            "data": {
                "type": "dois",
                "attributes": {
                    "doi": id
                }
            }
        }
        req = {
            'REQUEST_METHOD': 'POST',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT,
            'PATH_INFO': "/dois",
            'wsgi.input':  StringIO(json.dumps(inp))
        }
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("201", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "draft")

        # delete successfully
        req = {
            'REQUEST_METHOD': 'DELETE',
            'PATH_INFO': "/dois/"+id
        }
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])
        self.assertEqual(body, [])
        
        # record has been deleted
        req['REQUEST_METHOD'] = "HEAD"
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("404", self.resp[0])
        self.assertEqual(body, [])
        
        # create again but also attempt to publish without sufficient metadata
        inp['data']['attributes']['event'] = "publish"
        req = {
            'REQUEST_METHOD': 'POST',
            'HTTP_ACCEPT': svc.JSONAPI_MT,
            'CONTENT_TYPE': svc.JSONAPI_MT,
            'PATH_INFO': "/dois",
            'wsgi.input':  StringIO(json.dumps(inp))
        }
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("201", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "draft")

        # provide sufficient metadata
        inp['data']['attributes'].update({
            "url": "https://goob.net/",
            "titles": [{ "title": "The Humble Peanut" }],
            "publisher": "NIST",
            "publicationYear": 2020,
            "creators": [{"fn": "me"}],
            "types": { "resourceType": "Dataset", "schemaOrg": "Dataset"}
        })
        req['wsgi.input'] = StringIO(json.dumps(inp))
        
        self.resp = []

        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("200", self.resp[0])

        doc = json.loads("\n".join(body))
        saved = doc['data']['attributes']
        self.assertEqual(saved['doi'], id)
        self.assertEqual(saved['state'], "findable")


        # fail to delete published record
        req = {
            'REQUEST_METHOD': 'DELETE',
            'PATH_INFO': "/dois/"+id
        }
        self.resp = []
        body = self.svc(req, self.start)
        self.assertGreater(len(self.resp), 0)
        self.assertIn("403", self.resp[0])
        doc = json.loads("\n".join(body))
        self.assertIn('errors', doc)
        
            

if __name__ == '__main__':
    test.main()

        
        
