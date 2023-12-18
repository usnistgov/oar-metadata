
import pdb, os, json, urllib.parse, warnings, logging
import unittest as test
from pymongo import MongoClient
from ejsonschema import ExtValidator, SchemaValidator

from nistoar.rmm.mongo import nerdm
from nistoar.rmm.mongo import loader

pydir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
basedir = os.path.dirname(pydir)
schemadir = os.path.join(basedir, "model")
exdir = os.path.join(schemadir, "examples")
janaffile = os.path.join(exdir, "janaf.json")
pdrfile = os.path.join(exdir, "mds2-2106.json")

dburl = None
if os.environ.get('MONGO_TESTDB_URL'):
    dburl = os.environ.get('MONGO_TESTDB_URL')

assert os.path.exists(schemadir), schemadir

# logger = logging.getLogger("test")

@test.skipIf(not os.environ.get('MONGO_TESTDB_URL'),
             "test mongodb not available")
class TestNERDmLoader(test.TestCase):

    def setUp(self):
        self.ldr = nerdm.NERDmLoader(dburl, schemadir)

    def tearDown(self):
        client = MongoClient(dburl)
        if not hasattr(client, 'get_database'):
            client.get_database = client.get_default_database
        db = client.get_database()
        if "recordMetrics" in db.list_collection_names():
            db.drop_collection("recordMetrics")
        if "fileMetrics" in db.list_collection_names():
            db.drop_collection("fileMetrics")    
        db.create_collection("recordMetrics")
        db.create_collection("fileMetrics")
        if "record" in db.list_collection_names():
            db.drop_collection("record")
        if "versions" in db.list_collection_names():
            db.drop_collection("versions")
        if "releasesets" in db.list_collection_names():
            db.drop_collection("releasesets")
        
    def test_ctor(self):
        self.assertEqual(self.ldr.coll, "versions")

    def test_validate(self):
        with open(janaffile) as fd:
            data = json.load(fd)
        res = self.ldr.validate(data, schemauri=nerdm.DEF_SCHEMA)
        self.assertEqual(res, [])

        del data['landingPage']
        res = self.ldr.validate(data, schemauri=nerdm.DEF_SCHEMA)
        self.assertEqual(len(res), 2)

    def test_load_data(self):
        with open(janaffile) as fd:
            data = json.load(fd)
        key = { '@id': "ark:/88434/sdp0fjspek351" }
        self.assertEqual(self.ldr.load_data(data, key, 'fail'), 1)
        self.assertEqual(self.ldr._client.get_database().record.count_documents({}), 0)
        self.assertEqual(self.ldr._client.get_database().releasesets.count_documents({}), 0)
        self.assertEqual(self.ldr._client.get_database().versions.count_documents({}), 1)
        c = self.ldr._client.get_database().versions.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351')

    def test_load(self):
        with open(janaffile) as fd:
            data = json.load(fd)
        data['title'] = "Version 1.0.0"
        data['version'] = "1.0.0"
        res = self.ldr.load(data)
        self.assertEqual(res.attempt_count, 3)
        self.assertEqual(res.success_count, 3)
        self.assertEqual(res.failure_count, 0)
        self.assertEqual(self.ldr._client.get_database().record.count_documents({}), 1)
        c = self.ldr._client.get_database().record.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351')
        self.assertEqual(c[0]['version'], '1.0.0')
        self.assertEqual(c[0]['title'], 'Version 1.0.0')
        self.assertEqual(self.ldr._client.get_database().releasesets.count_documents({}), 1)
        c = self.ldr._client.get_database().releasesets.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351/pdr:v')
        self.assertEqual(c[0]['version'], '1.0.0')
        self.assertEqual(c[0]['title'], 'Version 1.0.0')
        self.assertEqual(self.ldr._client.get_database().versions.count_documents({}), 1)
        c = self.ldr._client.get_database().versions.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351/pdr:v/1.0.0')
        self.assertEqual(c[0]['version'], '1.0.0')
        self.assertEqual(c[0]['title'], 'Version 1.0.0')

        # update with next version
        self.ldr.onupdate = 'quiet'
        data['title'] = "Version 1.0.1"
        data['version'] = "1.0.1"
        res = self.ldr.load(data)
        self.assertEqual(res.attempt_count, 3)
        self.assertEqual(res.success_count, 3)
        self.assertEqual(res.failure_count, 0)
        self.assertEqual(self.ldr._client.get_database().record.count_documents({}), 1)
        c = self.ldr._client.get_database().record.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351')
        self.assertEqual(c[0]['version'], '1.0.1')
        self.assertEqual(c[0]['title'], 'Version 1.0.1')
        self.assertEqual(self.ldr._client.get_database().releasesets.count_documents({}), 1)
        c = self.ldr._client.get_database().releasesets.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351/pdr:v')
        self.assertEqual(c[0]['version'], '1.0.1')
        self.assertEqual(c[0]['title'], 'Version 1.0.1')
        self.assertEqual(self.ldr._client.get_database().versions.count_documents({}), 2)
        c = self.ldr._client.get_database().versions.find()
        for i in range(1):
            v = c[i]['version']
            self.assertEqual(c[i]['@id'], 'ark:/88434/sdp0fjspek351/pdr:v/'+v)
            self.assertEqual(c[0]['version'], v)
            self.assertEqual(c[0]['title'], 'Version '+v)

        # update older version
        self.ldr.onupdate = 'quiet'
        data['title'] = "A Version 1.0.0"
        data['version'] = "1.0.0"
        res = self.ldr.load(data)
        self.assertEqual(res.attempt_count, 1)
        self.assertEqual(res.success_count, 1)
        self.assertEqual(res.failure_count, 0)
        self.assertEqual(self.ldr._client.get_database().record.count_documents({}), 1)
        c = self.ldr._client.get_database().record.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351')
        self.assertEqual(c[0]['version'], '1.0.1')
        self.assertEqual(c[0]['title'], 'Version 1.0.1')
        self.assertEqual(self.ldr._client.get_database().releasesets.count_documents({}), 1)
        c = self.ldr._client.get_database().releasesets.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351/pdr:v')
        self.assertEqual(c[0]['version'], '1.0.1')
        self.assertEqual(c[0]['title'], 'Version 1.0.1')
        self.assertEqual(self.ldr._client.get_database().versions.count_documents({}), 2)
        c = self.ldr._client.get_database().versions.find()
        for i in range(1):
            if c[i]['version'] == "1.0.0":
                self.assertEqual(c[0]['title'], 'A Version 1.0.0')
            else:
                self.assertEqual(c[0]['title'], 'Version 1.0.1')

        # update last version
        self.ldr.onupdate = 'quiet'
        data['title'] = "A Version 1.0.1"
        data['version'] = "1.0.1"
        res = self.ldr.load(data)
        self.assertEqual(res.attempt_count, 3)
        self.assertEqual(res.success_count, 3)
        self.assertEqual(res.failure_count, 0)
        self.assertEqual(self.ldr._client.get_database().record.count_documents({}), 1)
        c = self.ldr._client.get_database().record.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351')
        self.assertEqual(c[0]['version'], '1.0.1')
        self.assertEqual(c[0]['title'], 'A Version 1.0.1')
        self.assertEqual(self.ldr._client.get_database().releasesets.count_documents({}), 1)
        c = self.ldr._client.get_database().releasesets.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351/pdr:v')
        self.assertEqual(c[0]['version'], '1.0.1')
        self.assertEqual(c[0]['title'], 'A Version 1.0.1')
        self.assertEqual(self.ldr._client.get_database().versions.count_documents({}), 2)
        c = self.ldr._client.get_database().versions.find()
        for i in range(1):
            v = c[i]['version']
            self.assertEqual(c[i]['@id'], 'ark:/88434/sdp0fjspek351/pdr:v/'+v)
            self.assertEqual(c[0]['version'], v)
            self.assertEqual(c[0]['title'], 'A Version '+v)

    def test_load_from_file(self):
        res = self.ldr.load_from_file(janaffile)
        self.assertEqual(res.attempt_count, 3)
        self.assertEqual(res.success_count, 3)
        self.assertEqual(res.failure_count, 0)
        self.assertEqual(self.ldr._client.get_database().record.count_documents({}), 1)
        c = self.ldr._client.get_database().record.find()
        self.assertEqual(c[0]['@id'], 'ark:/88434/sdp0fjspek351')
        self.assertEqual(self.ldr._client.get_database().versions.count_documents({}), 1)
        self.assertEqual(self.ldr._client.get_database().releasesets.count_documents({}), 1)

    def test_init_metrics_for(self):
        with open(pdrfile) as fd:
            rec = json.load(fd)

        # this record has files in it
        self.assertTrue(any(['/od/ds/' in f.get('downloadURL','') for f in rec.get('components',[])]))

        self.ldr.connect()
        database = self.ldr._db
        nerdm.init_metrics_for(database, rec)
        c = self.ldr._client.get_database().recordMetrics.find()
        self.assertEqual(c[0]['pdrid'], 'ark:/88434/mds2-2106')
        c = self.ldr._client.get_database().fileMetrics.find()
        self.assertEqual(c[0]['pdrid'], 'ark:/88434/mds2-2106')
        self.assertEqual(c[0]['filepath'], "NIST_NPL_InterlabData2019.csv.sha256")
        # replace this with checks of successful loading into the database
        #self.fail("Tests not implemented")
        

        
            
if __name__ == '__main__':
    test.main()
