import os, sys, pdb, shutil, logging, json
import unittest as test
from collections import Mapping
from nistoar.tests import *

import nistoar.doi.resolving.crossref as res
from nistoar.doi.resolving.common import set_client_info

crdoi = "10.1126/science.169.3946.635"
cli = ("NIST Open Access for Research", "testing",
       "http://github.com/usnistgov/oar-metadata/",
       "datasupport@nist.gov")

class TestCrossrefDOIInfo(test.TestCase):

    def test_ctor(self):
        res._comm._client_info = None
        doi = res.CrossrefDOIInfo(crdoi)
        self.assertEqual(doi.id, crdoi)
        self.assertEqual(doi.source, "Crossref")
        self.assertIsNone(doi._data)
        self.assertIsNone(doi._cite)
        self.assertIsNone(doi._native)
        self.assertIsNone(doi.client_info)

        doi = res.CrossrefDOIInfo(crdoi, client_info=cli)
        self.assertEqual(doi.id, crdoi)
        self.assertEqual(doi.source, "Crossref")
        self.assertIsNone(doi._native)
        self.assertIsNotNone(doi.client_info)
        self.assertEqual(doi.client_info.application_version, "testing")

        set_client_info(*cli)
        self.assertIsNotNone(res._comm._client_info)

        doi = res.CrossrefDOIInfo(crdoi)
        self.assertEqual(doi.id, crdoi)
        self.assertEqual(doi.source, "Crossref")
        self.assertIsNone(doi._native)
        self.assertIsNotNone(doi.client_info)
        self.assertEqual(doi.client_info.application_version, "testing")


    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_native(self):
        set_client_info(*cli)

        doi = res.CrossrefDOIInfo(crdoi)
        self.assertIsNone(doi._native)
        self.assertTrue(isinstance(doi.native, Mapping))
        self.assertTrue(isinstance(doi._native, Mapping))
        self.assertIn('URL', doi.native)
        self.assertEqual(doi.native['DOI'], crdoi)
        
    
        


if __name__ == '__main__':
    test.main()
