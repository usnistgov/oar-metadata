import os, sys, pdb, json, time, logging
import unittest as test
from pathlib import Path
from typing import Mapping

from nistoar.testing import *
from nistoar.taxonomy import simple

testdir = Path(__file__).parents[0]
basedir = testdir.parents[3]
taxdir = basedir / 'model'
ymlconf = basedir / 'docker' / 'ingestservice' / 'ingest_config.yml'
taxfile = taxdir / 'theme-taxonomy.json'

class TaxonomyTest(test.TestCase):

    def setUp(self):
        pass

    def test_load_file(self):
        data = simple._load_file(ymlconf)
        self.assertIn('logfile', data)

        data = simple._load_file(taxfile)
        self.assertIn('@id', data)

        try:
            data = simple._load_file("goober.txt", "goober")
            self.fail("Failed to raise on missing file")
        except IOError as ex:
            self.assertIn("goober file", str(ex))

        try:
            data = simple._load_file(basedir/'LICENSE.md')
            self.fail("Failed to raise on missing file")
        except IOError as ex:
            self.assertIn("unsupported", str(ex))

    def test_from_file(self):
        uri = simple._load_file(taxfile)['@id']
        
        tax = simple.SimpleTaxonomy.from_file(taxfile)
        self.assertEqual(tax.id, uri)
        about = tax.about()
        self.assertIn('title', about)
        self.assertIn('schema', about)
        self.assertIn('description', about)
        self.assertNotIn('vocab', about)

        title = about['title']
        about['title'] = "Hacked!"
        about = tax.about()
        self.assertEqual(about['title'], title)

        self.assertGreater(tax.count(), 100)
#        self.assertEqual(tax.count(), 277)   #this number will change as taxon evolves
        
    def test_get(self):
        tax = simple.SimpleTaxonomy.from_file(taxfile)

        term = tax.about_term("Bioscience: Biomaterials")
        self.assertTrue(isinstance(term, Mapping))
        self.assertEqual(term['label'], "Bioscience: Biomaterials")
        self.assertEqual(term['level'], 2)
        self.assertEqual(term['parent'], "Bioscience")
        self.assertEqual(term['id'], tax.id+'#Bioscience%3A%20Biomaterials')

        term2 = tax.get(term['id'])
        self.assertTrue(isinstance(term2, Mapping))
        self.assertEqual(term2['label'], "Bioscience: Biomaterials")
        self.assertEqual(term2['id'], tax.id+'#Bioscience%3A%20Biomaterials')
        self.assertEqual(tax.compare_meaning(term, term2), 0)
        self.assertTrue(tax.equivalent(term, term2))
        self.assertTrue(tax.equivalent(term2, term))

        term = tax.about_term("Bioscience")
        self.assertEqual(term['label'], "Bioscience")
        self.assertEqual(term['level'], 1)
        self.assertNotIn('parent', term)
        self.assertEqual(term['id'], tax.id+'#Bioscience')
        
        self.assertTrue(not tax.equivalent(term, term2))
        self.assertTrue(not tax.equivalent(term2, term))
        self.assertEqual(tax.compare_meaning(term, term2), -1)
        self.assertEqual(tax.compare_meaning(term2, term),  1)
        self.assertTrue(tax.is_broader_than(term, term2))
        self.assertTrue(not tax.is_broader_than(term2, term))
        self.assertTrue(tax.is_narrower_than_or_equiv(term2, term))
        self.assertTrue(not tax.is_narrower_than_or_equiv(term, term2))

        self.assertIsNotNone(tax.about_term("Materials"))
        self.assertIsNotNone(tax.about_term("Materials: Materials characterization"))
        term = tax.about_term("Materials: Materials characterization: Thermal properties")
        self.assertIsNotNone(term)
        self.assertEqual(term['label'],
                         "Materials: Materials characterization: Thermal properties")
        self.assertEqual(term['level'], 3)
        self.assertEqual(term['parent'], "Materials: Materials characterization")
        self.assertEqual(term['id'],
                tax.id+'#Materials%3A%20Materials%20characterization%3A%20Thermal%20properties')

        self.assertIsNone(tax.compare_meaning(term, term2))
        self.assertIsNone(tax.compare_meaning(term2, term))
        self.assertTrue(not tax.equivalent(term, term2))
        self.assertTrue(not tax.equivalent(term2, term))
        self.assertTrue(not tax.is_broader_than(term, term2))
        self.assertTrue(not tax.is_broader_than(term2, term))
        self.assertTrue(not tax.is_narrower_than_or_equiv(term2, term))
        self.assertTrue(not tax.is_narrower_than_or_equiv(term, term2))
        
        self.assertIsNone(tax.about_term("Health: Cancer"))
        self.assertIsNone(tax.about_term("Cancer"))

    def test_iter(self):
        tax = simple.SimpleTaxonomy.from_file(taxfile)

        self.assertTrue(all('label' in t for t in tax.terms()))
        self.assertTrue(all('id' in t for t in tax.terms()))
        self.assertTrue(all('term' in t for t in tax.terms()))
        self.assertTrue(all('level' in t for t in tax.terms()))
        self.assertEqual(len(list(tax.terms())), tax.count())
        mat = tax.about_term("Materials")
        matly = [t for t in tax.terms() if tax.is_narrower_than_or_equiv(t, mat)]
        self.assertTrue(all(t['label'].startswith('Materials') for t in matly))
        self.assertEqual(  len([t for t in matly if t['level'] == 1]), 1)
        self.assertGreater(len([t for t in matly if t['level'] == 2]), 1)
        self.assertGreater(len([t for t in matly if t['level'] == 3]), 1)
        self.assertEqual(  len([t for t in matly if t['level']  > 3]), 0)
#        self.assertEqual(len(matly), 12)   #this number will change as taxon evolves

    def test_summary_from(self):
        content = simple._load_file(taxfile)
        data = simple.SimpleTaxonomy._summary_from(content)
        self.assertNotIn('vocab', data)
        self.assertNotIn('_schema', data)
        self.assertNotIn('@id', data)
        self.assertTrue(data.get('id'))
        self.assertTrue(data.get('schema'))
        
        

if __name__ == '__main__':
    test.main()
