import unittest, pdb, os, json
from collections import OrderedDict

import nistoar.nerdm.taxonomy as taxon

mddir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
schemadir = os.path.join(mddir, "model")


class TestResearchTopicsTaxonomy(unittest.TestCase):

    def setUp(self):
        self.tax = taxon.ResearchTopicsTaxonomy.from_schema_dir(schemadir)

    def test_ctor(self):
        self.assertEqual(self.tax.data['version'], "1.1")
        self.assertIsNotNone(self.tax.taillu)
        self.assertIsNotNone(self.tax.fulllu)
        self.assertIn('Bioscience', self.tax.taillu)
        self.assertIn('Bioscience', self.tax.fulllu)
        self.assertIn('Biomaterials', self.tax.taillu)
        self.assertNotIn('Biomaterials', self.tax.fulllu)
        self.assertNotIn('Bioscience: Biomaterials', self.tax.taillu)
        self.assertIn('Bioscience: Biomaterials', self.tax.fulllu)

    def test_match_theme_exactly(self):
        term = self.tax.match_theme("Chemistry", False)
        self.assertEqual(term.defn['term'], "Chemistry")
        self.assertEqual(str(term), "Chemistry")

        term = self.tax.match_theme("Biomaterials", False)
        self.assertEqual(term.defn['term'], "Biomaterials")
        self.assertEqual(str(term), "Bioscience: Biomaterials")

        term = self.tax.match_theme("Ground", False)
        self.assertEqual(term.defn['term'], "Ground")
        self.assertEqual(str(term), "Public Safety: Response robots: Ground")

        term = self.tax.match_theme("Response robots", False)
        self.assertEqual(term.defn['term'], "Response robots")
        self.assertEqual(str(term), "Public Safety: Response robots")

    def test_match_theme_caseinsen(self):
        term = self.tax.match_theme("buildings and construction", False)
        self.assertEqual(term.defn['term'], "Buildings and Construction")

        term = self.tax.match_theme("sustainable buildings", False)
        self.assertEqual(term.defn['term'], "Sustainable buildings")
        self.assertEqual(str(term), "Buildings and Construction: Sustainable buildings")

    def test_match_theme_deprecated(self):
        term = self.tax.match_theme("Internet of Things", False)
        self.assertEqual(term.defn['term'], "Internet of Things")

        term = self.tax.match_theme("Internet of Things", True)
        self.assertEqual(term.defn['term'], "Internet of Things (IoT)")

        term = self.tax.match_theme("internet of things")
        self.assertEqual(term.defn['term'], "Internet of Things (IoT)")

    def test_match_theme_words(self):
        term = self.tax.match_theme("Materials: Concrete and Cement", False)
        self.assertEqual(term.defn['term'], "Concrete/cement")

        term = self.tax.match_theme("Biological Nuclear Explosives", False)
        self.assertEqual(term.defn['term'], "Chemical/Biological/Radiological/Nuclear/Explosives (CBRNE)")

    def test_as_topic(self):
        term = self.tax.match_theme("Biomaterials", False)
        topic = term.as_topic()
        self.assertEqual(topic['@type'], "Concept")
        self.assertEqual(topic['scheme'], "https://www.nist.gov/od/dm/nist-themes/v1.1")
        self.assertEqual(topic['tag'], "Bioscience: Biomaterials")
        
        
if __name__ == '__main__':
    unittest.main()
