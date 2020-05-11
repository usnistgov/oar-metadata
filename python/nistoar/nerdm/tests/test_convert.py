import unittest, pdb, os, json, re
from collections import OrderedDict

import nistoar.nerdm.convert as cvt

mddir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
# assert os.path.basename(mddir) == "metadata", "Bad mddir: "+mddir
jqlibdir = os.path.join(mddir, "jq")
datadir = os.path.join(jqlibdir, "tests", "data")
janaffile = os.path.join(datadir, "janaf_pod.json")
simplefile = os.path.join(datadir, "simple-nerdm.json")
schemadir = os.path.join(os.path.dirname(jqlibdir), "model")
nerddir = os.path.join(schemadir,"examples")

class TestPODds2Res(unittest.TestCase):

    def test_ctor(self):
        cvtr = cvt.PODds2Res(jqlibdir)
        self.assertFalse(cvtr.fetch_authors)
        self.assertFalse(cvtr.enrich_refs)
        self.assertFalse(cvtr.enrich_refs)
        self.assertTrue(cvtr.fix_themes)
        self.assertTrue(cvtr.should_massage)
        self.assertIsNotNone(cvtr.taxon)

        cvtr = cvt.PODds2Res(jqlibdir, {'enrich_refs': True})
        self.assertFalse(cvtr.fetch_authors)
        self.assertTrue(cvtr.enrich_refs)
        self.assertTrue(cvtr.fix_themes)
        self.assertTrue(cvtr.should_massage)

        cvtr = cvt.PODds2Res(jqlibdir, {'fix_themes': False})
        self.assertFalse(cvtr.fetch_authors)
        self.assertFalse(cvtr.enrich_refs)
        self.assertFalse(cvtr.fix_themes)
        self.assertFalse(cvtr.should_massage)

        cvtr = cvt.PODds2Res(jqlibdir, schemadir="/tmp/schemas")
        self.assertIsNone(cvtr.taxon)
        self.assertFalse(cvtr.fetch_authors)
        self.assertFalse(cvtr.enrich_refs)
        self.assertFalse(cvtr.fix_themes)
        self.assertFalse(cvtr.should_massage)
        cvtr.fix_themes = False
        with self.assertRaises(RuntimeError):
            cvtr.fix_themes = True

        cvtr = cvt.PODds2Res(jqlibdir, {'fetch_authors': True})
        self.assertTrue(cvtr.fetch_authors)
        self.assertFalse(cvtr.enrich_refs)
        self.assertTrue(cvtr.fix_themes)
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
        self.assertEquals(res["@id"], "ark:ID")
        self.assertEquals(res["accessLevel"], "public")

    def test_convert_data(self):
        cvtr = cvt.PODds2Res(jqlibdir)
        self.assertFalse(cvtr.enrich_refs)

        with open(janaffile) as fd:
            data = json.load(fd)
        data['theme'] = ['optical physics']

        res = cvtr.convert_data(data, "ark:ID")
        self.assertEquals(res["@id"], "ark:ID")
        self.assertEquals(res["accessLevel"], "public")

        self.assertEqual(len(res['references']), 1)
        self.assertNotIn('citation', res["references"][0])

        self.assertIn('topic', res)
        self.assertEqual(len(res['topic']), len(res['theme']))
        self.assertEqual(res['topic'][0]['tag'], "Physics: Optical physics")
        self.assertEqual(res['theme'][0], "Physics: Optical physics")
        
        cvtr.fix_themes = False
        res = cvtr.convert_data(data, "ark:ID")
        self.assertIn('topic', res)
        self.assertEqual(len(res['topic']), len(res['theme']))
        self.assertEqual(res['topic'][0]['tag'], "Physics: Optical physics")
        self.assertEqual(res['theme'][0], "optical physics")

    def test_themes2topics(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(simplefile) as fd:
            data = json.load(fd)
        self.assertEqual(data['theme'][0], "Optical physics")

        data['theme'].append("Goober and the Peas")
        data['theme'].append("Bioscience")
        data['theme'].append("chemistry")

        data['topic'] = cvtr.themes2topics(data['theme'])
        self.assertEqual(len(data['topic']), len(data['theme']))
        self.assertEqual(data['theme'][0], "Optical physics")
        self.assertEqual(data['topic'][0]['tag'], "Physics: Optical physics")
        self.assertTrue(data['topic'][0].get('scheme').startswith("https://data.nist.gov/od/dm/nist-themes/"))

        self.assertEqual(data['topic'][1]['tag'], "Goober and the Peas")
        self.assertFalse(data['topic'][1].get('scheme'))

        self.assertEqual(data['topic'][2]['tag'], "Bioscience")
        self.assertTrue(data['topic'][2].get('scheme').startswith("https://data.nist.gov/od/dm/nist-themes/"))
        self.assertEqual(data['topic'][3]['tag'], "Chemistry")
        self.assertTrue(data['topic'][3].get('scheme').startswith("https://data.nist.gov/od/dm/nist-themes/"))
        
    def test_topics2themes(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(simplefile) as fd:
            data = json.load(fd)
        self.assertEqual(data['theme'][0], "Optical physics")

        data['theme'].append("Goober and the Peas")
        data['theme'].append("Bioscience")
        data['theme'].append("chemistry")

        data['topic'] = cvtr.themes2topics(data['theme'])
        themes = cvtr.topics2themes(data['topic'])

        self.assertEqual(len(themes), len(data['topic']))
        self.assertEqual(themes[0], "Physics: Optical physics")
        self.assertEqual(themes[1], "Goober and the Peas")
        self.assertEqual(themes[2], "Bioscience")
        self.assertEqual(themes[3], "Chemistry")
        
        themes = cvtr.topics2themes(data['topic'], False)

        self.assertEqual(len(themes), len(data['topic'])-1)
        self.assertEqual(themes[0], "Physics: Optical physics")
        self.assertEqual(themes[1], "Bioscience")
        self.assertEqual(themes[2], "Chemistry")

        # test old URI
        data['topic'][0]['scheme'] = re.sub('data', 'www', data['topic'][0]['scheme'])
        themes = cvt.topics2themes(data['topic'], False) # as a module function
        self.assertEqual(len(themes), len(data['topic'])-1)
        self.assertEqual(themes[0], "Physics: Optical physics")
        

    def test_massage_themes(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(simplefile) as fd:
            data = json.load(fd)
        self.assertEqual(data['theme'][0], "Optical physics")
        data['theme'].append("Goober and the Peas")
        data['theme'].append("Bioscience")
        data['theme'].append("chemistry")

        data['topic'] = cvtr.themes2topics(data['theme'])
        cvtr.massage_themes(data)

        self.assertEqual(len(data['theme']), len(data['topic']))
        self.assertEqual(data['theme'][0], "Physics: Optical physics")
        self.assertEqual(data['theme'][1], "Goober and the Peas")
        self.assertEqual(data['theme'][2], "Bioscience")
        self.assertEqual(data['theme'][3], "Chemistry")
        
        

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
        self.assertEquals(res["@id"], "ark:ID")
        self.assertEquals(res["accessLevel"], "public")

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

class TestRes2PODds(unittest.TestCase):

    def test_ctor(self):
        cvtr = cvt.Res2PODds(jqlibdir)
        self.assertIn("midas", cvtr.jqt)

    def test_convert_file(self):
        cvtr = cvt.Res2PODds(jqlibdir)
        pod = cvtr.convert_file(os.path.join(nerddir,"janaf.json"))
        self.assertEquals(pod["accessLevel"], "public")
        self.assertEquals(pod["@type"], "dcat:Dataset")

        self.assertEqual(len(pod['references']), 2)
        self.assertEqual(len(pod['distribution']), 319)
        self.assertEqual(pod['contactPoint']['fn'], 'Thomas Allison')
        self.assertEqual(pod['contactPoint']['hasEmail'],
                         'mailto:thomas.allison@nist.gov')

    def test_convert(self):
        cvtr = cvt.Res2PODds(jqlibdir)
        with open(os.path.join(nerddir,"janaf.json")) as fd:
            data = json.load(fd)
        pod = cvtr.convert(json.dumps(data))
        self.assertEquals(pod["accessLevel"], "public")
        self.assertEquals(pod["@type"], "dcat:Dataset")

        self.assertEqual(len(pod['references']), 2)
        self.assertEqual(len(pod['distribution']), 319)
        self.assertEqual(pod['contactPoint']['fn'], 'Thomas Allison')
        self.assertEqual(pod['contactPoint']['hasEmail'],
                         'mailto:thomas.allison@nist.gov')

    def test_convert_data(self):
        cvtr = cvt.Res2PODds(jqlibdir)
        with open(os.path.join(nerddir,"janaf.json")) as fd:
            data = json.load(fd)
        pod = cvtr.convert_data(data)
        self.assertEquals(pod["accessLevel"], "public")
        self.assertEquals(pod["@type"], "dcat:Dataset")

        self.assertEqual(len(pod['references']), 2)
        self.assertEqual(len(pod['distribution']), 319)
        self.assertEqual(pod['contactPoint']['fn'], 'Thomas Allison')
        self.assertEqual(pod['contactPoint']['hasEmail'],
                         'mailto:thomas.allison@nist.gov')

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
        self.assertEquals(hier, simplehier)
        
if __name__ == '__main__':
    unittest.main()
