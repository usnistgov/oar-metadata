import os, sys, pdb, shutil, logging, json
import unittest as test
from collections import Mapping
# from nistoar.tests import *

import nistoar.doi.resolving as res
import nistoar.doi.resolving.common as comm
from nistoar.doi.resolving import set_client_info

dcdoi = "10.18434/m33x0v"
crdoi = "10.1126/science.169.3946.635"
medradoi = "10.1392/onix_doi_schema_v1.1"

cli = ("NIST Open Access for Research", "testing",
       "http://github.com/usnistgov/oar-metadata/",
       "datasupport@nist.gov")
def setUpModule():
    set_client_info(*cli)
def tearDownModule():
    set_client_info(None, None, None, None)

logger = logging.getLogger("test")

class TestResolving(test.TestCase):

    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_resolve_dc(self):
        info = res.resolve(dcdoi, logger=logger)
        self.assertIn(info.source, ["Datacite", "Crosscite"])
        self.assertTrue(isinstance(info, res.DataciteDOIInfo))
        self.assertIsNotNone(info._data)
        self.assertEqual(info.data['DOI'], dcdoi)

    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_resolve_cr(self):
        info = res.resolve(crdoi)
        self.assertEqual(info.source, "Crossref")
        self.assertTrue(isinstance(info, res.CrossrefDOIInfo))
        self.assertIsNotNone(info._data)
        self.assertEqual(info.data['DOI'], crdoi)
        self.assertEqual(info.client_info.application_version, "testing")

    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_resolve_unknown(self):
        info = res.resolve(medradoi)
        self.assertEqual(info.source, "unknown")
        self.assertTrue(isinstance(info, res.DOIInfo))
        self.assertIsNotNone(info._data)
        # self.assertEqual(info.data['DOI'], crdoi)

    def test_resolve_notfound(self):
        with self.assertRaises(res.DOIDoesNotExist):
            res.resolve("10.10/goober")

    def test_resolve_badresolver(self):
        try:
            res.resolve("10.10/goober", "http://badhost/")
            self.fail("Failed to raise exception for bad resolver")
        except (res.DOIResolverError, res.DOICommunicationError):
            pass

class TestResolver(test.TestCase):

    def test_ctor(self):
        rslvr = res.Resolver(resolver="ftp:/goober.com/")
        self.assertEquals(rslvr._resolver, "ftp:/goober.com/")
        self.assertEquals(rslvr._client_info[1], "testing")

        ci = (comm._client_info[0], "testing2", comm._client_info[2],
              comm._client_info[3])
        
        rslvr = res.Resolver(ci)
        self.assertEquals(rslvr._resolver, "https://doi.org/")
        self.assertEquals(rslvr._client_info[1], "testing2")
        
        rslvr = res.Resolver()
        self.assertEquals(rslvr._resolver, "https://doi.org/")
        self.assertEquals(rslvr._client_info[1], "testing")


    @test.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                 "kindly skipping doi service checks")
    def test_cr_resolve(self):
        ci = (comm._client_info[0], "testing2", comm._client_info[2],
              comm._client_info[3])
        
        rslvr = res.Resolver(ci)
        info = rslvr.resolve(crdoi)
        self.assertEqual(info.client_info.application_version, "testing2")
        self.assertEqual(info.source, "Crossref")
        self.assertTrue(isinstance(info, res.CrossrefDOIInfo))
        self.assertIsNotNone(info._data)
        self.assertEqual(info.data['DOI'], crdoi)
        


if __name__ == '__main__':
    test.main()
