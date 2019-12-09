import unittest, pdb, os, json
from collections import OrderedDict

import nistoar.nerdm.convert as cvt

mddir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
# assert os.path.basename(mddir) == "metadata", "Bad mddir: "+mddir
jqlibdir = os.path.join(mddir, "jq")
datadir = os.path.join(jqlibdir, "tests", "data")
janaffile = os.path.join(datadir, "janaf_pod.json")
simplefile = os.path.join(datadir, "simple-nerdm.json")

class TestPODds2Res(unittest.TestCase):

    def test_ctor(self):
        cvtr = cvt.PODds2Res(jqlibdir)
        self.assertFalse(cvtr.fetch_authors)
        self.assertFalse(cvtr.enrich_refs)
        self.assertFalse(cvtr.should_massage)

        cvtr = cvt.PODds2Res(jqlibdir, {'enrich_refs': True})
        self.assertFalse(cvtr.fetch_authors)
        self.assertTrue(cvtr.enrich_refs)
        self.assertTrue(cvtr.should_massage)

        cvtr = cvt.PODds2Res(jqlibdir, {'fetch_authors': True})
        self.assertTrue(cvtr.fetch_authors)
        self.assertFalse(cvtr.enrich_refs)
        self.assertTrue(cvtr.should_massage)

    def test_convert_file(self):
        cvtr = cvt.PODds2Res(jqlibdir)
        res = cvtr.convert_file(janaffile, "ark:ID")
        self.assertEqual(res["@id"], "ark:ID")
        self.assertEqual(res["accessLevel"], "public")

    def test_convert(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(janaffile) as fd:
            data = fd.read()
            
        res = cvtr.convert(data, "ark:ID")
        self.assertEqual(res["@id"], "ark:ID")
        self.assertEqual(res["accessLevel"], "public")

    def test_convert_data(self):
        cvtr = cvt.PODds2Res(jqlibdir)
        self.assertFalse(cvtr.enrich_refs)

        with open(janaffile) as fd:
            data = json.load(fd)
            
        res = cvtr.convert_data(data, "ark:ID")
        self.assertEqual(res["@id"], "ark:ID")
        self.assertEqual(res["accessLevel"], "public")

        self.assertEqual(len(res['references']), 1)
        self.assertNotIn('citation', res["references"][0])

    @unittest.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                     "kindly skipping doi service checks")
    def test_enrich_refs(self):
        cvtr = cvt.PODds2Res(jqlibdir)
        cvtr.enrich_refs = True
        self.assertTrue(cvtr.enrich_refs)

        with open(janaffile) as fd:
            data = json.load(fd)
        data['references'].append("https://doi.org/10.1126/science.169.3946.635")
            
        res = cvtr.convert_data(data, "ark:ID")
        self.assertEqual(res["@id"], "ark:ID")
        self.assertEqual(res["accessLevel"], "public")

        self.assertEqual(len(res['references']), 2)
        self.assertNotIn('citation', res["references"][0])
        self.assertIn('@id', res["references"][1])
        self.assertIn('citation', res["references"][1])
        self.assertIn('title', res["references"][1])
        self.assertEqual(res["references"][1]['refType'], 'IsCitedBy')

    @unittest.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                     "kindly skipping doi service checks")
    def test_massage_refs(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(janaffile) as fd:
            data = json.load(fd)
        data['references'].append("https://doi.org/10.1126/science.169.3946.635")
        res = cvtr.convert_data(data, "ark:ID")

        cvtr.massage_refs(res)
        self.assertEqual(len(res['references']), 2)
        self.assertNotIn('citation', res["references"][0])
        self.assertIn('@id', res["references"][1])
        self.assertIn('citation', res["references"][1])
        self.assertIn('title', res["references"][1])
        self.assertEqual(res["references"][1]['refType'], 'IsCitedBy')

    @unittest.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                     "kindly skipping doi service checks")
    def test_massage_authors(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(janaffile) as fd:
            data = json.load(fd)
        res = cvtr.convert_data(data, "ark:ID")
        self.assertNotIn('authors', res)
        res['doi'] = "doi:10.18434/m33x0v"

        cvtr.massage_authors(res)
        self.assertEqual(len(res['references']), 1)
        self.assertIn('authors', res)
        self.assertEqual(len(res['authors']), 2)
        self.assertEqual(res['authors'][0]['givenName'], "Joseph")
        self.assertEqual(res['authors'][0]['familyName'], "Conny")
        self.assertEqual(res['authors'][0]['fn'], "Joseph Conny")
        self.assertIn('affiliation', res['authors'][0])
        self.assertIn('affiliation', res['authors'][1])
        self.assertEqual(res['authors'][0]['affiliation'][0]['title'],
                         "National Institute of Standards and Technology")
        

with open(simplefile) as fd:
    simplenerd = json.load(fd, object_pairs_hook=OrderedDict)

trial3byty = [
    {
        "forType": "dcat:Distribution",
        "childCount": 1,
        "descCount": 1
    },
    {
        "forType": "nrdp:DataFile",
        "childCount": 1,
        "descCount": 1
    }
]
trial3inv = {
    "forCollection": "trial3",
    "childCount": 1,
    "descCount": 1,
    "byType": trial3byty,
    "childCollections": []
}
fullinv = [
{
    "forCollection": "",
    "childCount": 4,
    "descCount": 5,
    "byType": [
        {
            "forType": "dcat:Distribution",
            "childCount": 3,
            "descCount": 4
        },
        {
            "forType": "nrd:Hidden",
            "childCount": 1,
            "descCount": 1
        },
        {
            "forType": "nrdp:DataFile",
            "childCount": 2,
            "descCount": 3
        },
        {
            "forType": "nrdp:Subcollection",
            "childCount": 1,
            "descCount": 1
        }
    ],
    "childCollections": [ "trial3" ]
}, trial3inv ]

simplehier = [
    {
        "filepath": "trial1.json"
    },
    {
        "filepath": "trial2.json"
    },
    {
        "filepath": "trial3",
        "children": [
            {
                "filepath": "trial3/trial3a.json"
            }
        ]
    }
]

class TestComponentCounter(unittest.TestCase):

    def test_inventory_collection(self):
        cc = cvt.ComponentCounter(jqlibdir)
        inv = cc.inventory_collection(simplenerd['components'], "trial3")
        self.assertEqual(inv, trial3inv)
        
    def test_inventory_by_type(self):
        cc = cvt.ComponentCounter(jqlibdir)
        inv = cc.inventory_by_type(simplenerd['components'], "trial3")
        self.assertEqual(inv, trial3byty)
        
    def test_inventory(self):
        cc = cvt.ComponentCounter(jqlibdir)
        inv = cc.inventory(simplenerd['components'])
        self.assertEqual(inv, fullinv)

class TestHierarchyBuilder(unittest.TestCase):

    def test_build_hierarchy(self):
        hb = cvt.HierarchyBuilder(jqlibdir)
        hier = hb.build_hierarchy(simplenerd['components'])
        self.assertEqual(hier, simplehier)
        
if __name__ == '__main__':
    unittest.main()
