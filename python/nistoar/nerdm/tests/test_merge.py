import unittest, pdb, os, json
from collections import OrderedDict

from jsonmerge.strategies import Strategy
import jsonmerge

import nistoar.nerdm.merge as mrg

mddir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
mrgdir = os.path.join(mddir, "model", "merge")
assert os.path.exists(mrgdir), "Missing merge dir"
datadir = os.path.join(os.path.dirname(__file__), "data")

class TestKeepBase(unittest.TestCase):

    def test_ctor(self):
        keep = mrg.KeepBase()
        self.assertIsNotNone(keep)
        self.assertIsInstance(keep, Strategy)

    def test_merge(self):
        keep = mrg.KeepBase()
        schema = {'mergeStrategy': 'keepBase'}
        merger = jsonmerge.Merger(schema=schema, strategies={'keepBase': keep},
                                  def_objclass='OrderedDict')

        mrgd = merger.merge(None, {'a': 1})
        self.assertIsNone(mrgd)
        mrgd = merger.merge({'b': 2}, {'a': 1})
        self.assertEqual(mrgd, {'b': 2})
        mrgd = merger.merge("goof", {'a': 1})
        self.assertEqual(mrgd, "goof")
        mrgd = merger.merge("goof", "head")
        self.assertEqual(mrgd, "goof")
        mrgd = merger.merge(3, 2)
        self.assertEqual(mrgd, 3)
        mrgd = merger.merge([3], [2, 1])
        self.assertEqual(mrgd, [3])

class TestDirBaseMergerFactory(unittest.TestCase):

    def test_ctor(self):
        fact = mrg.DirBasedMergerFactory(mrgdir)
        self.assertIsNotNone(fact.logger)
        self.assertIn('keepBase', fact.strategies)

    def test_conventions(self):
        fact = mrg.DirBasedMergerFactory(mrgdir)
        conventions = fact.strategy_conventions()
        self.assertIsInstance(conventions, list)
        self.assertIn('dev', conventions)
    
    def test_make_merger(self):
        fact = mrg.DirBasedMergerFactory(mrgdir)
        merger = fact.make_merger("dev", "Resource")
        self.assertIsInstance(merger, jsonmerge.Merger)
        self.assertTrue(merger.schema['id'].endswith("/Resource#"))
        schema = merger.get_schema()
        self.assertTrue(merger.schema['id'].endswith("/Resource#"))
        self.assertIn('properties', schema)
        self.assertIn('contactPoint', schema['properties'])
        self.assertIn('properties', schema['properties']['contactPoint'])

    def test_merge(self):
        fact = mrg.DirBasedMergerFactory(mrgdir)
        merger = fact.make_merger("dev", "Resource")

        with open(os.path.join(datadir, "janaf-orig.json")) as fd:
            orig = json.load(fd, object_pairs_hook=OrderedDict)
        with open(os.path.join(datadir, "janaf-annot.json")) as fd:
            annot = json.load(fd, object_pairs_hook=OrderedDict)

        merged = merger.merge(orig, annot)

        self.assertNotIn("postalAddress", orig["contactPoint"])
        self.assertIn("postalAddress", merged["contactPoint"])
        self.assertEquals(len(orig['description']), 1)
        self.assertEquals(len(annot['description']), 1)
        self.assertEquals(len(merged['description']), 2)
        self.assertNotIn("abbrev", orig)
        self.assertIn("abbrev", merged)
        self.assertNotIn("authors", orig)
        self.assertIn("authors", merged)
        self.assertNotEqual(orig["ediid"], annot["ediid"])
        self.assertEqual(orig["ediid"], merged["ediid"])
        self.assertEquals(len(orig['references']), 1)
        self.assertEquals(len(annot['references']), 2)
        self.assertEquals(len(merged['references']), 3)
        comp = [c for c in merged['components']
                if c['@id'] == "#cmp/cryolite/srd13_Al-053.json"][0]
        self.assertIn("title", comp)



        
        
if __name__ == '__main__':
    unittest.main()
