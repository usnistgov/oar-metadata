import unittest, os, json, pdb, pynoid as noid, logging
from random import randint

from nistoar.id import persist
from nistoar.testing import *

loghdlr = None
rootlog = None
def setUpModule():
    ensure_tmpdir()
#    logging.basicConfig(filename=os.path.join(tmpdir(),"test_builder.log"),
#                        level=logging.INFO)
    rootlog = logging.getLogger()
    loghdlr = logging.FileHandler(os.path.join(tmpdir(),"test_minter.log"))
    loghdlr.setLevel(logging.INFO)
#    loghdlr.setFormatter(logging.Formatter(bldr.DEF_BAGLOG_FORMAT))
    rootlog.addHandler(loghdlr)
    rootlog.setLevel(logging.INFO)

def tearDownModule():
    global loghdlr
    if loghdlr:
        if rootlog:
            rootlog.removeLog(loghdlr)
        loghdlr = None
    rmtmpdir()

class TestSimplePersistentIDRegistry(unittest.TestCase):

    def setUp(self):
        self.tf = Tempfiles()
        self.reg = persist.SimplePersistentIDRegistry(self.tf.root,
                                                  {'cache_on_register': False})
        self.tf.track("issued-ids.json")

    def tearDown(self):
        self.reg = None
        self.tf.clean()

    def test_ctor(self):
        self.assertTrue(self.reg.cfg)
        self.assertEqual(self.reg.store, os.path.join(self.tf.root,
                                                      'issued-ids.json'))
        self.assertEqual(self.reg.data, {})
        self.assertFalse(self.reg.cache_pending)

    def test_registerID(self):
        self.reg.registerID("id1", {"ediid": 'A9B8C7'})
        self.reg.registerID("id2", {"ediid": 'A9B8C8'})

        self.assertTrue(self.reg.registered("id1"))
        self.assertTrue(self.reg.registered("id2"))
        self.assertFalse(self.reg.registered("id3"))

        self.assertEqual(self.reg.get_data("id1"), {"ediid": 'A9B8C7'})
        self.assertEqual(self.reg.get_data("id2"), {"ediid": 'A9B8C8'})
        self.assertIsNone(self.reg.get_data("id3"))

        self.assertTrue(self.reg.cache_pending)
        self.assertFalse(os.path.exists(self.reg.store))

    def test_cache(self):
        self.reg.registerID("id1", {"ediid": 'A9B8C7'})
        self.reg.registerID("id2", {"ediid": 'A9B8C8'})
        self.assertTrue(self.reg.cache_pending)
        self.assertFalse(os.path.exists(self.reg.store))
        self.reg.cache_data()
        self.assertTrue(os.path.exists(self.reg.store))
        self.assertFalse(self.reg.cache_pending)

        with open(self.reg.store) as fd:
            data = json.load(fd)
        self.assertTrue(isinstance(data, dict))
        self.assertIn("id1", data)
        self.assertIn("id2", data)
        self.assertIn("ediid", data['id1'])
        self.assertEqual(data['id1']['ediid'], 'A9B8C7')

    def test_reload(self):
        self.reg.registerID("id1", {"ediid": 'A9B8C7'})
        self.reg.registerID("id2", {"ediid": 'A9B8C8'})
        self.reg.cache_data()
        self.assertTrue(os.path.exists(self.reg.store))

        self.reg.data = {}
        self.assertFalse("id1" in self.reg.data)
        self.assertFalse(self.reg.registered("id1"))

        self.reg.reload_data()
        
        self.assertTrue(self.reg.registered("id1"))
        self.assertTrue(self.reg.registered("id2"))
        self.assertFalse(self.reg.registered("id3"))

        self.assertEqual(self.reg.get_data("id1"), {"ediid": 'A9B8C7'})
        self.assertEqual(self.reg.get_data("id2"), {"ediid": 'A9B8C8'})
        self.assertIsNone(self.reg.get_data("id3"))

class TestEDIBasedMinter(unittest.TestCase):

    def setUp(self):
        self.tf = Tempfiles()
        self.tf.track("issued-ids.json")
        cfg = { 'shoulder_for_seq': "pdr5",
                'shoulder_for_edi': "mds5",
                'registry': { 'cache_on_register': True }
        }
        self.mntr = persist.EDIBasedMinter(self.tf.root, cfg)

    def tearDown(self):
        self.mntr = None
        self.tf.clean()

    def test_ctor(self):
        self.assertTrue(self.mntr.seqminter)
        self.assertEqual(self.mntr.seedkey, 'ediid')
        self.assertEqual(self.mntr._seededmask, 'ark:/88434/mds5.zeeeeek')
        self.assertEqual(self.mntr._div, 1000000)
        self.assertIn("cache_on_register", self.mntr.registry.cfg)

    def test_hash(self):
        hx = '36FF2AB549C0F0CDE0531A570681F1E81474'
        sh = self.mntr._hash(hx)
        self.assertLessEqual(sh, 10**6)
        self.assertEqual(self.mntr._hash(hx), sh)

        hx = '3A1EE2F169DD3B8CE0531A570681DB5D1491'
        self.assertNotEqual(self.mntr._hash(hx), sh)
        sh = self.mntr._hash(hx)
        self.assertLessEqual(sh, 10**6)
        self.assertEqual(self.mntr._hash(hx), sh)

        hx = 'EBC9DB05EDEA5B0EE043065706812DF81'
        sh = self.mntr._hash(hx)
        self.assertLessEqual(sh, 10**6)
        self.assertEqual(self.mntr._hash(hx), sh)

        hx = 'EBC9DB05EDEA5B0EE043065706812DF82'
        sh = self.mntr._hash(hx)
        self.assertLessEqual(sh, 10**6)
        self.assertEqual(self.mntr._hash(hx), sh)

        hx = 'DBC9DB05EDEA5B0EE043065706812DF82'
        sh = self.mntr._hash(hx)
        self.assertLessEqual(sh, 10**6)
        self.assertEqual(self.mntr._hash(hx), sh)

    def test_seededmint(self):
        id = self.mntr._seededmint("zek", 5)
        self.assertFalse(self.mntr.issued(id))
        self.mntr.registry.registerID(id)
        self.assertTrue(self.mntr.issued(id))
        self.assertTrue(noid.validate(id))
        
        id2 = self.mntr._seededmint("zek", 5)
        self.assertNotEqual(id, id2)
        self.assertGreater(len(id2), len(id))
        self.assertEqual(id2[-3], '0')
        self.assertTrue(noid.validate(id2))
        self.assertEqual(self.mntr._collision_count, 1)

    def test_mint(self):
        seqid = self.mntr.mint()
        self.assertEqual(seqid[:15], 'ark:/88434/pdr5')
        self.assertEqual(len(seqid), 19)
        eid = self.mntr.mint({'ediid': 'EBC9DB05EDEA5B0EE043065706812DF81'})
        self.assertNotEqual(eid, seqid)
        self.assertEqual(eid[:15], 'ark:/88434/mds5')
        self.assertEqual(len(eid), 21)

        self.assertTrue(self.mntr.issued(eid))
        self.assertTrue(self.mntr.issued(seqid))

    def test_data(self):
        eid = self.mntr.mint({'ediid': 'EBC9DB05EDEA5B0EE043065706812DF81'})
        seqid = self.mntr.mint()
        self.assertEqual(
          self.mntr.datafor(eid), {'ediid': 'EBC9DB05EDEA5B0EE043065706812DF81'})
        self.assertIsNone(self.mntr.datafor(seqid))

    def test_cache(self):
        eid = self.mntr.mint({'ediid': 'EBC9DB05EDEA5B0EE043065706812DF81'})
        seqid = self.mntr.mint()
        
        with open(os.path.join(self.tf.root, "issued-ids.json")) as fd:
            data = json.load(fd)
        self.assertTrue(isinstance(data, dict))
        self.assertIn(eid, data)
        self.assertIn(seqid, data)

if __name__ == '__main__':
    unittest.main()
