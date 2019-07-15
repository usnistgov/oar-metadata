import os, sys, pdb, shutil, logging, json
import unittest as test
from collections import Mapping
from nistoar.tests import *

import nistoar.doi.resolving.datacite as res

dcdoi = "10.18434/m33x0v"

class TestDataciteDOIInfo(test.TestCase):

    def test_ctor(self):
        doi = res.DataciteDOIInfo(dcdoi)
        self.assertEqual(doi.id, dcdoi)
        self.assertEqual(doi.source, "Datacite")
        self.assertIsNone(doi._data)
        self.assertIsNone(doi._cite)
        self.assertIsNone(doi._native)

    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_native(self):
        doi = res.DataciteDOIInfo(dcdoi)
        self.assertIsNone(doi._native)
        self.assertTrue(isinstance(doi.native, Mapping))
        self.assertTrue(isinstance(doi._native, Mapping))
        self.assertIn('url', doi.native)
        self.assertEqual(doi.native['doi'], dcdoi)
        
        
        


if __name__ == '__main__':
    test.main()
