import os, sys, pdb, shutil, logging, json
import unittest as test
from collections.abc import Mapping
from nistoar.testing import *

import nistoar.doi.utils as utils

dcdoi = "10.18434/m33x0v"
crdoi = "10.1126/science.169.3946.635"

class TestUtils(test.TestCase):

    def test_uri(self):
        self.assertTrue(utils.is_DOI("doi:"+dcdoi))
        self.assertTrue(utils.is_DOI("doi:"+crdoi))
        self.assertFalse(utils.is_DOI(dcdoi))
        self.assertFalse(utils.is_DOI(crdoi))

    def test_url(self):
        self.assertTrue(utils.is_DOI("http://doi.org/"+dcdoi))
        self.assertTrue(utils.is_DOI("https://doi.org/"+dcdoi))
        self.assertTrue(utils.is_DOI("http://dx.doi.org/"+dcdoi))
        self.assertTrue(utils.is_DOI("https://dx.doi.org/"+dcdoi))
        self.assertTrue(utils.is_DOI("http://doi.org/"+crdoi))
        self.assertTrue(utils.is_DOI("https://doi.org/"+crdoi))
        self.assertTrue(utils.is_DOI("http://dx.doi.org/"+crdoi))
        self.assertTrue(utils.is_DOI("https://dx.doi.org/"+crdoi))
        self.assertFalse(utils.is_DOI(dcdoi))
        
        


if __name__ == '__main__':
    test.main()
