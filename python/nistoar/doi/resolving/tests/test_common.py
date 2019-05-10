import os, sys, pdb, shutil, logging, json
import unittest as test
from collections import Mapping
from nistoar.tests import *

import nistoar.doi.resolving.common as res

dcdoi = "10.18434/m33x0v"

class TestClienInfo(test.TestCase):

    def test_set(self):
        self.assertIsNone(res._client_info)
        res.set_client_info("NIST Open Access to Research", "oar-metadata tests",
                            "https://github.com/usnistgov/oar-metadata",
                            "datasupport@nist.gov")
        self.assertEqual(res._client_info[0], "NIST Open Access to Research")
        self.assertEqual(res._client_info[3], "datasupport@nist.gov")
        res.set_client_info(None, None, None, None)
        self.assertIsNone(res._client_info)

class TestDOIInfo(test.TestCase):

    def test_ctor(self):
        self.assertEqual(res.default_doi_resolver, "https://doi.org/")

        doi = res.DOIInfo(dcdoi)
        self.assertEqual(doi.id, dcdoi)
        self.assertEqual(doi.source, "unknown")
        self.assertEqual(doi.resolver, res.default_doi_resolver)
        self.assertIsNone(doi._data)
        self.assertIsNone(doi._cite)
        self.assertIsNone(doi._native)

        doi = res.DOIInfo("doi:"+dcdoi, "Datacite", "https://myresolver.net/")
        self.assertEqual(doi.id, dcdoi)
        self.assertEqual(doi.source, "Datacite")
        self.assertEqual(doi.resolver, "https://myresolver.net/")
        self.assertIsNone(doi._data)

        doi = res.DOIInfo("http://goob.net/"+dcdoi, "Goober")
        self.assertEqual(doi.id, dcdoi)
        self.assertEqual(doi.source, "Goober")
        self.assertEqual(doi.resolver, res.default_doi_resolver)
        self.assertIsNone(doi._data)

        doi = res.DOIInfo("https://doi.org/"+dcdoi, "Crossref")
        self.assertEqual(doi.id, dcdoi)
        self.assertEqual(doi.source, "Crossref")
        self.assertEqual(doi.resolver, res.default_doi_resolver)
        self.assertIsNone(doi._data)

    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_get_data(self):
        doi = res.DOIInfo(dcdoi)
        data = doi._get_data("text/turtle")
        self.assertGreater(len(data), 1)
        self.assertTrue(data.startswith("@prefix schema: "))

    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_cite(self):
        doi = res.DOIInfo(dcdoi)
        self.assertIsNone(doi._cite)
        self.assertTrue(doi.citation_text.startswith("Conny, J., "))
        self.assertTrue(doi._cite.startswith("Conny, J., "))
        self.assertTrue(doi.citation_text.startswith("Conny, J., "))

    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_data(self):
        doi = res.DOIInfo(dcdoi)
        self.assertIsNone(doi._data)
        self.assertTrue(isinstance(doi.data, Mapping))
        self.assertTrue(isinstance(doi._data, Mapping))
        self.assertIn('type', doi.data)
        self.assertEqual(doi.data['DOI'], dcdoi)
        
    def test_native(self):
        doi = res.DOIInfo(dcdoi)
        self.assertIsNone(doi._native)
        self.assertEqual(doi.native, {})
        self.assertEqual(doi._native, {})
        


if __name__ == '__main__':
    test.main()
