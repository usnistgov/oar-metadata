import unittest, pdb, os, json
from collections import OrderedDict

from jsonmerge.strategies import Strategy
import jsonmerge

import nistoar.nerdm.merge as mrg

mddir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
mrgdir = os.path.join(mddir, "etc", "merge")
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
        merger = jsonmerge.Merger(schema, {'keepBase': keep},
                                  'OrderedDict')

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

class TestPreferBase(unittest.TestCase):

    def test_ctor(self):
        strat = mrg.PreferBase()
        self.assertIsNotNone(strat)
        self.assertIsInstance(strat, Strategy)

    def test_merge(self):
        strat = mrg.PreferBase()
        schema = {'mergeStrategy': 'preferBase'}
        merger = jsonmerge.Merger(schema,
                                  {'preferBase': strat},
                                  'OrderedDict')

        mrgd = merger.merge(None, {'a': 1})
        self.assertEqual(mrgd, {'a': 1})
        mrgd = merger.merge({'b': 2}, {'a': 1})
        self.assertEqual(mrgd, {'b': 2})
        mrgd = merger.merge("goof", {'a': 1})
        self.assertEqual(mrgd, "goof")
        mrgd = merger.merge("goof", "head")
        self.assertEqual(mrgd, "goof")
        mrgd = merger.merge(None, 2)
        self.assertEqual(mrgd, 2)
        mrgd = merger.merge(None, [2, 1])
        self.assertEqual(mrgd, [2, 1])

class TestUniqueArray(unittest.TestCase):

    def test_ctor(self):
        strat = mrg.UniqueArray()
        self.assertIsNotNone(strat)
        self.assertIsInstance(strat, Strategy)

    def test_merge(self):
        strat = mrg.UniqueArray()
        schema = {'mergeStrategy': 'uniqueArray'}
        merger = jsonmerge.Merger(schema,
                                  {'uniqueArray': strat},
                                  'OrderedDict')

        base = [ "a", "e", "i" ]
        head = [ "b", "i", "z", "a" ]
        mrgd = merger.merge(base, head)
        self.assertIsInstance(mrgd, list)
        self.assertEquals(mrgd, [ "a", "e", "i", "b", "z" ])

    def test_incompat(self):
        strat = mrg.UniqueArray()
        schema = {'mergeStrategy': 'uniqueArray',
                  'mergeOptions': {
                      'incompatible': [[ "a", "e", "i", "o", "u" ],
                                       [ 1, 3, 5, 7, 11 ]]
                  }}
        merger = jsonmerge.Merger(schema,
                                  {'uniqueArray': strat},
                                  'OrderedDict')

        base = [ "a", "e", "c", 3 ]
        head = [ "b", "i", 4, 5, "z" ]
        mrgd = merger.merge(base, head)
        self.assertIsInstance(mrgd, list)
        self.assertEquals(mrgd, [ "c", "b", "i", 4, 5, "z" ])

class TestArrayMergeByMultiId(unittest.TestCase):

    def test_ctor(self):
        strat = mrg.ArrayMergeByMultiId()
        self.assertIsNotNone(strat)
        self.assertIsInstance(strat, Strategy)

    def test_merge_def(self):
        strat = mrg.ArrayMergeByMultiId()
        schema = {'mergeStrategy': 'arrayMergeByMultiId'}
        merger = jsonmerge.Merger(schema,
                                  {'arrayMergeByMultiId': strat},
                                  'OrderedDict')

        base = [ { "@id": "goob", "foo": "bar" },
                 { "@id": "hank", "foo": "bin" } ]
        head = [ { "@id": "goob", "gurn": "cranston" },
                 { "@id": "bob", "tells": "alice" } ]
        mrgd = merger.merge(base, head)
        self.assertIsInstance(mrgd, list)
        self.assertEquals(mrgd, [
            { "@id": "goob", "foo": "bar", "gurn": "cranston" },
            { "@id": "hank", "foo": "bin" },
            { "@id": "bob", "tells": "alice" }
        ])
        
    def test_merge(self):
        strat = mrg.ArrayMergeByMultiId()
        schema = {'mergeStrategy': 'arrayMergeByMultiId',
                  'mergeOptions': {
                      'idRef': [ "@id", "foo" ]
                  }}
        merger = jsonmerge.Merger(schema,
                                  {'arrayMergeByMultiId': strat},
                                  'OrderedDict')

        base = [ { "@id": "goob", "foo": "bar" },
                 { "@id": "goob", "foo": "bin" } ]
        head = [ { "@id": "goob", "foo": "bar", "gurn": "cranston" },
                 { "@id": "goob", "gurn": "cranston" },
                 { "@id": "bob", "tells": "alice" } ]
        mrgd = merger.merge(base, head)
        self.assertIsInstance(mrgd, list)
        self.assertEquals(mrgd, [
            { "@id": "goob", "foo": "bar", "gurn": "cranston" },
            { "@id": "goob", "foo": "bin" },
            { "@id": "goob", "gurn": "cranston" },
            { "@id": "bob", "tells": "alice" }
        ])
        
    def test_merge_ignore(self):
        strat = mrg.ArrayMergeByMultiId()
        schema = {'mergeStrategy': 'arrayMergeByMultiId',
                  'mergeOptions': {
                      'idRef': [ "@id", "foo" ],
                      'ignoreId': { "@id": "goob" }
                  }}
        merger = jsonmerge.Merger(schema,
                                  {'arrayMergeByMultiId': strat}, 'OrderedDict')

        base = [ { "@id": "goob", "foo": "bar" },
                 { "@id": "goob", "foo": "bin" } ]
        head = [ { "@id": "goob", "foo": "bar", "gurn": "cranston" },
                 { "@id": "goob", "gurn": "cranston" },
                 { "@id": "bob", "tells": "alice" } ]
        mrgd = merger.merge(base, head)
        self.assertIsInstance(mrgd, list)
        self.assertEquals(mrgd, [
            { "@id": "goob", "foo": "bar", "gurn": "cranston" },
            { "@id": "goob", "foo": "bin" },
            { "@id": "bob", "tells": "alice" }
        ])
        
class TestTopicArray(unittest.TestCase):

    def test_ctor(self):
        strat = mrg.TopicArray()
        self.assertIsNotNone(strat)
        self.assertIsInstance(strat, Strategy)

    def test_merge_def(self):
        strat = mrg.TopicArray()
        schema = {'mergeStrategy': 'topicArray'}
        merger = jsonmerge.Merger(schema,
                                  {'topicArray': strat},
                                  'OrderedDict')


        base = [
            { "@id": "goob", "tag": "physics" },
            { "@id": "gurn", "scheme": "hsr", "tag": "physics" }, 
            { "scheme": "hsr", "tag": "biology" }
        ]
        head = [
            { "@id": "goob", "tag": "Physics" },
            { "scheme": "hsr", "tag": "physics", "lab": "MML" }, 
            { "scheme": "hsr", "tag": "biology" }
        ]

        mrgd = merger.merge(base, head)
        self.assertIsInstance(mrgd, list)
        self.assertEquals(mrgd, [
            { "@id": "goob", "tag": "Physics" },
            { "@id": "gurn", "scheme": "hsr", "tag": "physics", "lab": "MML" }, 
            { "scheme": "hsr", "tag": "biology" }
        ])


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
        self.assertIsInstance(merged, OrderedDict)

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
