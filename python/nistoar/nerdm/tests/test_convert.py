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

    def test_convert_file(self):
        cvtr = cvt.PODds2Res(jqlibdir)
        res = cvtr.convert_file(janaffile, "ark:ID")
        self.assertEquals(res["@id"], "ark:ID")
        self.assertEquals(res["accessLevel"], "public")

    def test_convert(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(janaffile) as fd:
            data = fd.read()
            
        res = cvtr.convert(data, "ark:ID")
        self.assertEquals(res["@id"], "ark:ID")
        self.assertEquals(res["accessLevel"], "public")

    def test_convert_data(self):
        cvtr = cvt.PODds2Res(jqlibdir)

        with open(janaffile) as fd:
            data = json.load(fd)
            
        res = cvtr.convert_data(data, "ark:ID")
        self.assertEquals(res["@id"], "ark:ID")
        self.assertEquals(res["accessLevel"], "public")

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
        self.assertEquals(hier, simplehier)
        
if __name__ == '__main__':
    unittest.main()
