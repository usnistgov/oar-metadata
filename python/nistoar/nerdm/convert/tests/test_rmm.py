import os, sys, pdb, shutil, logging, json
import unittest as test
from copy import deepcopy

from nistoar.nerdm.convert import rmm
import nistoar.nerdm.constants as const

basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(__file__))))))
schemadir = os.path.join(basedir, 'model')
datadir1 = os.path.join(schemadir, "examples")
datadir2 = os.path.join(basedir, "jq", "tests", "data")
hitsc = os.path.join(datadir1, "hitsc-0.2.json")
simplenerd = os.path.join(datadir2, "simple-nerdm.json")

NERDM_SCH_ID_BASE = const.core_schema_base

class TestNERDm2RMM(test.TestCase):

    def test_ctor(self):
        cvtr = rmm.NERDmForRMM()
        self.assertEqual(cvtr._lpsbase, "https://data.nist.gov/od/id/")
        
        cvtr = rmm.NERDmForRMM(pubeps={"portalBase": "https://testdata.nist.gov/"})
        self.assertEqual(cvtr._lpsbase, "https://testdata.nist.gov/od/id/")

        cvtr = rmm.NERDmForRMM(pubeps={"portalBase": "https://bit.ly/pdr/",
                                       "landingPageService": "lps/show"})
        self.assertEqual(cvtr._lpsbase, "https://bit.ly/pdr/lps/show")

        cvtr = rmm.NERDmForRMM(pubeps={"portalBase": "https://oardev.nist.gov/pdr/",
                                       "landingPageService": "http://localhost/lps/show?id="})
        self.assertEqual(cvtr._lpsbase, "http://localhost/lps/show?id=")

        self.assertTrue(os.path.isdir(schemadir))
        cvtr = rmm.NERDmForRMM(schemadir=schemadir)
        self.assertTrue(cvtr._valid8r)

    def test_to_rmm(self):
        lpsep = "https://testdata.nist.gov/od/id/"
        cvtr = rmm.NERDmForRMM(pubeps={"landingPageService": lpsep})

        with open(hitsc) as fd:
            nerdm = json.load(fd)
        self.assertTrue(nerdm['_schema'].endswith("/v0.2#"))
        self.assertIn('versionHistory', nerdm)

        ing = cvtr.to_rmm(nerdm)

        for prop in "record version releaseSet".split():
            self.assertIn(prop, ing)

        self.assertEqual(ing['record']['@id'], nerdm['@id'])
        self.assertEqual(ing['record']['title'], nerdm['title'])
        self.assertEqual(ing['record']['_schema'], const.CORE_SCHEMA_URI+"#")
        self.assertEqual(ing['record']['version'], "1.0")
        self.assertNotIn('versionHistory', ing['record'])
        self.assertIn('releaseHistory', ing['record'])
        self.assertEqual(len(ing['record']['releaseHistory']['hasRelease']), 1)
        self.assertEqual(ing['version']['releaseHistory']['hasRelease'][0]['version'], "1.0")
        self.assertEqual(ing['version']['releaseHistory']['hasRelease'][0]['description'], "initial release")

        self.assertEqual(ing['releaseSet']['@id'], nerdm['@id']+".rel")
        self.assertEqual(ing['releaseSet']['title'], nerdm['title'])
        self.assertEqual(ing['releaseSet']['_schema'], const.CORE_SCHEMA_URI+"#")
        self.assertEqual(ing['releaseSet']['version'], "1.0")
        self.assertIn('version', ing['releaseSet'])
        self.assertNotIn('versionHistory', ing['releaseSet'])
        self.assertNotIn('releaseHistory', ing['releaseSet'])
        self.assertIn('hasRelease', ing['releaseSet'])
        self.assertEqual(len(ing['releaseSet']['hasRelease']), 1)
        self.assertEqual(ing['releaseSet']['hasRelease'][0]['version'], "1.0")
        self.assertEqual(ing['releaseSet']['hasRelease'][0]['description'], "initial release")
        


                    
                         
if __name__ == '__main__':
    test.main()
