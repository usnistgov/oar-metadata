import os, sys, pdb, shutil, logging, json
import unittest as test

from nistoar.nerdm import utils
from nistoar.nerdm import constants as const

class TestUtils(test.TestCase):

    def test_meta_prop_ch(self):
        data = { "_schema": "uri", "$schema": "URI", "*schema": "URB",
                 "_goob": "gurn", "$goob": "GURN", "#goob": "Gurn" }
        self.assertEqual(utils.meta_prop_ch(data), "_")
        self.assertEqual(utils.meta_prop_ch(data, "goob"), "_")
        self.assertEqual(utils.meta_prop_ch(data, "goob", "#$_"), "#")
        del data["#goob"]
        self.assertEqual(utils.meta_prop_ch(data, "goob", "#$_"), "$")
        del data["_schema"]
        self.assertEqual(utils.meta_prop_ch(data), "$")
        self.assertEqual(utils.meta_prop_ch(data, prefixchs="*$"), "*")
        del data["$schema"]
        with self.assertRaises(ValueError):
            utils.meta_prop_ch(data)

    def test_is_type(self):
        data = { "name": "Bob", "@type": [ "nrd:Resource", "dcat:Dataset", "Metadata" ]}
        self.assertTrue(utils.is_type(data, "Resource"))
        self.assertTrue(utils.is_type(data, "schema:Resource"))
        self.assertTrue(utils.is_type(data, "Dataset"))
        self.assertTrue(utils.is_type(data, "goob:Metadata"))
        self.assertTrue(not utils.is_type(data, "Randy"))
        data['@type'] = "dcat:Dataset"
        self.assertTrue(not utils.is_type(data, "Resource"))
        self.assertTrue(not utils.is_type(data, "schema:Resource"))
        self.assertTrue(utils.is_type(data, "Dataset"))

    def test_which_type(self):
        data = { "name": "Bob", "@type": [ "nrd:Resource", "dcat:Dataset", "Metadata" ]}
        self.assertEqual(utils.which_type(data, ["Goob", "Dataset", "Resource"]), "Dataset")
        self.assertIsNone(utils.which_type(data, ["Goob", "Foo"]))
        with self.assertRaises(TypeError):
            utils.which_type(data, "Goob")

    def test_is_any_type(self):
        data = { "name": "Bob", "@type": [ "nrd:Resource", "dcat:Dataset", "Metadata" ]}
        self.assertTrue(utils.is_any_type(data, ["Goob", "Dataset", "Resource"]))
        self.assertFalse(utils.is_any_type(data, ["Goob", "Foo"]))
        with self.assertRaises(TypeError):
            utils.is_any_type(data, "Goob")

    def test_nerdm_schema_version(self):
        self.assertEqual(utils.nerdm_schema_version(const.CORE_SCHEMA_URI), const.core_ver.lstrip('v'))
        self.assertEqual(utils.nerdm_schema_version("urn:goober/v3.0"), "3.0")
        self.assertEqual(utils.nerdm_schema_version("urn:goober/v3.0#"), "3.0")
        self.assertEqual(utils.nerdm_schema_version("urn:goober/v3.0#/definitions/Gurn"), "3.0")
        self.assertEqual(utils.nerdm_schema_version("urn:goober/beta"), "beta")
        with self.assertRaises(ValueError):
            utils.nerdm_schema_version("foo")
            

    def test_cmp_versions(self):
        self.assertEqual(utils.cmp_versions("1.0.0", "1.0.2"), -1)
        self.assertEqual(utils.cmp_versions("1.0.1", "1.0.1"),  0)
        self.assertEqual(utils.cmp_versions("1.0.2", "1.0.1"),  1)
        self.assertEqual(utils.cmp_versions("1.0", "1.0.2"), -1)
        self.assertEqual(utils.cmp_versions("1.0.0", "1.0"),  1)
        self.assertEqual(utils.cmp_versions("1", "1.0"),  -1)
        self.assertEqual(utils.cmp_versions("1.0.2", "1.1.0"), -1)
        self.assertEqual(utils.cmp_versions("1.2.1", "1.0.1"),  1)
        self.assertEqual(utils.cmp_versions("1.0.2", "4.0.1"), -1)
        self.assertEqual(utils.cmp_versions("12.0.2", "4.0.1"), 1)

    def test_schema_version_cmp(self):
        data = {"_schema": "https://data.nist.gov/od/dm/nerdm-schema/pub/v1.3"}
        self.assertEqual(utils.cmp_versions(utils.get_nerdm_schema_version(data), "0.5"), 1)
        self.assertEqual(utils.cmp_versions(utils.get_nerdm_schema_version(data), "2.5"), -1)
        self.assertEqual(utils.cmp_versions(utils.get_nerdm_schema_version(data), "1.3"), 0)
    
class TestVersion(test.TestCase):

    def test_ctor(self):
        ver = utils.Version("3.3.5.0")
        self.assertEqual(ver._vs, "3.3.5.0")
        self.assertEqual(ver.fields, [3,3,5,0])

    def testEQ(self):
        ver = utils.Version("3.3.0")
        self.assertEqual(ver, utils.Version("3.3.0"))
        self.assertTrue(ver == "3.3.0")
        self.assertFalse(ver == "3.3.1")
        self.assertFalse(ver == "1.3")

    def testNE(self):
        ver = utils.Version("3.3.0")
        self.assertNotEqual(ver, utils.Version("3.3.2"))
        self.assertFalse(ver != "3.3.0")
        self.assertTrue(ver != "3.3.1")
        self.assertTrue(ver != "1.3")

    def testGE(self):
        ver = utils.Version("3.3.0")
        self.assertTrue(ver >= "3.2.0")
        self.assertTrue(ver >= "3.3.0")
        self.assertTrue(ver >= "1.3")

        self.assertFalse(ver >= "5.3")
        self.assertFalse(ver >= utils.Version("5.3"))

    def testGT(self):
        ver = utils.Version("3.3.0")
        self.assertTrue(ver > "3.2.0")
        self.assertTrue(ver > "1.3")

        self.assertFalse(ver > "3.3.0")
        self.assertFalse(ver >= "5.3")
        self.assertFalse(ver >= utils.Version("5.3"))

    def testLE(self):
        ver = utils.Version("3.3.0")
        self.assertTrue(ver <= "3.5.0")
        self.assertTrue(ver <= "3.3.1")
        self.assertTrue(ver <= "3.3.0")
        self.assertTrue(ver <= "5.3")

        self.assertFalse(ver <= "1.3")
        self.assertFalse(ver <= utils.Version("2.3"))

    def testLT(self):
        ver = utils.Version("3.3.0")
        self.assertTrue(ver < "3.5.0")
        self.assertTrue(ver < "3.3.1")
        self.assertTrue(ver < "5.3")

        self.assertFalse(ver < "3.3.0")
        self.assertFalse(ver < "1.3")
        self.assertFalse(ver < utils.Version("2.3"))

    def testIsProper(self):
        self.assertTrue(utils.Version.is_proper_version("33"))
        self.assertTrue(utils.Version.is_proper_version("3.3"))
        self.assertTrue(utils.Version.is_proper_version("13_3_0"))
        self.assertTrue(utils.Version.is_proper_version("1.23_400.10"))

        self.assertFalse(utils.Version.is_proper_version("-33"))
        self.assertFalse(utils.Version.is_proper_version("3.3r23"))
        self.assertFalse(utils.Version.is_proper_version("13.3.0-1"))
        self.assertFalse(utils.Version.is_proper_version("dev"))

    def test_sorted(self):
        vers = "2.0.1 3.0 0.1.1 0 12.3 2.0.1.0".split()
        expect = "0 0.1.1 2.0.1 2.0.1.0 3.0 12.3".split()
        self.assertEqual(sorted(vers, key=utils.Version), expect)



                         
if __name__ == '__main__':
    test.main()
