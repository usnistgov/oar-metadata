import unittest, pdb, os, json
from collections import Mapping

import ejsonschema as ejs

import nistoar.nerdm.validate as vld8

mddir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
datadir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
schemadir = os.path.join(mddir, "model")

class TestValidate(unittest.TestCase):

    def setUp(self):
        pass

    def test_get_mdval_flavor(self):

        data = { "goob": "gurn", "_schema": "xxx" }
        self.assertEquals(vld8.get_mdval_flavor(data), "_")

        data = { "goob": "gurn", "$schema": "xxx" }
        self.assertEquals(vld8.get_mdval_flavor(data), "$")

        data = { "goob": "gurn", "#schema": "xxx" }
        self.assertIsNone(vld8.get_mdval_flavor(data))

        data = { "goob": "gurn", "$extensionSchemas": [] }
        self.assertEquals(vld8.get_mdval_flavor(data), "$")

        data = { "goob": "gurn", "_extensionSchemas": [] }
        self.assertEquals(vld8.get_mdval_flavor(data), "_")

        data = { "goob": "gurn", "_schema": "xxx", "_extensionSchemas": [] }
        self.assertEquals(vld8.get_mdval_flavor(data), "_")

        data = { "goob": "gurn", "$schema": "xxx", "$extensionSchemas": [] }
        self.assertEquals(vld8.get_mdval_flavor(data), "$")

        with open(os.path.join(datadir, "janaf-orig.json")) as fd:
            data = json.load(fd)
        self.assertEquals(vld8.get_mdval_flavor(data), "_")

    def test_create_validator(self):
        v = vld8.create_validator(schemadir, "_")
        self.assertTrue(isinstance(v, ejs.ExtValidator))
        self.assertEqual(v._epfx, "_")

        v = vld8.create_validator(schemadir, "$")
        self.assertTrue(isinstance(v, ejs.ExtValidator))
        self.assertEqual(v._epfx, "$")

        with open(os.path.join(datadir, "janaf-orig.json")) as fd:
            data = json.load(fd)
        v = vld8.create_validator(schemadir, data)
        self.assertTrue(isinstance(v, ejs.ExtValidator))
        self.assertEqual(v._epfx, "_")

    def test_validate(self):
        with open(os.path.join(datadir, "janaf-orig.json")) as fd:
            data = json.load(fd)

        self.assertEqual(vld8.validate(data, schemadir), [])




        
if __name__ == '__main__':
    unittest.main()
