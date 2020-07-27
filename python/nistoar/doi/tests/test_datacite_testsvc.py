from __future__ import absolute_import
import os, pdb, sys, json, requests, logging, time, re, hashlib, shutil
import unittest as test

import nistoar.doi.datacite as dc

testdir = os.path.dirname(os.path.abspath(__file__))
datadir = os.path.join(testdir, 'data')
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(testdir))))

baseurl = "https://api.test.datacite.org/dois"
prefixes = ["10.80443"]

@test.skipIf(not os.environ.get("OAR_TEST_DATACITE_CREDS"),
             "No credentials provided")
class TestDataCiteTestService(test.TestCase):

    creds = tuple(os.environ.get("OAR_TEST_DATACITE_CREDS","").split(':'))
    defattrs = { "publisher": "National Institute of Standards and Technology" }

    def setUp(self):
        self.cli = dc.DataCiteDOIClient(baseurl, self.creds, prefixes, self.defattrs)

    def test_default_prefix(self):
        self.assertTrue(self.cli.default_prefix, "10.80443")

    def test_supports_prefix(self):
        self.assertTrue(not self.cli.supports_prefix("10.88434"))
        self.assertTrue(self.cli.supports_prefix("10.80443"))

    def test_not_exists(self):
        self.assertTrue(not self.cli.exists("doesnotexist"))

        with self.assertRaises(dc.DOIDoesNotExist):
            doid = self.cli.lookup("doesnotexist")

        doid = self.cli.lookup("doesnotexist", relax=True)
        self.assertEqual(doid.doi, "10.80443/doesnotexist")
        self.assertEqual(doid.prefix, "10.80443")
        self.assertEqual(doid.state, "")
        self.assertFalse(doid.exists)
        self.assertFalse(doid.is_readonly)

    def test_lookup_notallowed(self):
        
        doid = self.cli.lookup("10.00100/notallowed", relax=True)
        self.assertEqual(doid.doi, "10.00100/notallowed")
        self.assertEqual(doid.prefix, "10.00100")
        self.assertEqual(doid.state, "")
        self.assertFalse(doid.exists)
        self.assertTrue(doid.is_readonly)

    def test_reserve_notallowed(self):
        self.cli.prefs += ["10.00100"]

        with self.assertRaises(dc.DOIClientException):
            doid = self.cli.reserve("10.00100/notallowed")

    def test_reserve_delete(self):
        self.assertTrue(not self.cli.exists("utst0d001"))

        doid = self.cli.reserve("utst0d001")
        self.assertEqual(doid.doi, "10.80443/utst0d001")
        self.assertEqual(doid.prefix, "10.80443")
        self.assertEqual(doid.state, "draft")
        self.assertTrue(doid.exists)
        self.assertFalse(doid.is_readonly)
        self.assertEqual(doid.attrs['publisher'],
                         "National Institute of Standards and Technology")
        self.assertFalse(doid.attrs['url'])

        doid.update({"url": "http://example.com/utst0d001",
                     "publicationYear": 2020 })
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs['publisher'],
                         "National Institute of Standards and Technology")
        self.assertEqual(doid.attrs['url'], "http://example.com/utst0d001")
        self.assertEqual(doid.attrs['publicationYear'], 2020)
        
        doid.delete()
        self.assertFalse(doid.exists)
        self.assertEquals(doid.state, "")

        self.assertTrue(not self.cli.exists("utst0d001"))

    def test_create_publish(self):
        doid = self.cli.create()
        self.assertTrue(doid.exists)
        self.assertEqual(doid.prefix, "10.80443")
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs['publisher'],
                         "National Institute of Standards and Technology")
        self.assertFalse(doid.attrs['url'])
        self.assertTrue(doid.attrs['suffix'])
        self.assertEqual(doid.attrs['creators'], [])
        self.assertEqual(doid.attrs['types'], {})

        self.assertTrue(self.cli.exists(doid.doi))

        url = "https://example.nist.gov/utst0/"+doid.attrs['suffix']
        doid.update({
            "titles": { 'title': "A Unit-test Published DOI" },
            "url": url,
            "publicationYear": 2020,
            "creators": [{
                "name": "Plante, Ray",
                "givenName": "Ray",
                "familyName": "Plante",
                "affiliation": "NIST"
            }],
            "types": {
                "resourceType": "Test Resource",
                "resourceTypeGeneral": "Dataset",
                "schemaOrg": "Dataset"
            },
            "descriptions": [{"description": "This DOI refers to a fictional dataset as a test of the nistoar Python DataCite client.",  "descriptionType": "Abstract"}]
        })

        self.assertTrue(doid.exists)
        self.assertEqual(doid.state, "draft")
        self.assertEqual(doid.attrs['publisher'],
                         "National Institute of Standards and Technology")
        self.assertEquals(doid.attrs['url'], url)
        self.assertEquals(doid.attrs['publicationYear'], 2020)

        doid.publish()
        self.assertTrue(doid.exists)
        self.assertEqual(doid.state, "findable")
        self.assertEqual(doid.attrs['publisher'],
                         "National Institute of Standards and Technology")
        self.assertEquals(doid.attrs['url'], url)
        self.assertEquals(doid.attrs['publicationYear'], 2020)

        doid.attrs['state'] = 'draft'
        with self.assertRaises(dc.DOIResolverError):
            doid.delete()
        
        doid = self.cli.lookup(doid.doi)
        self.assertTrue(doid.exists)
        self.assertEqual(doid.state, "findable")
        self.assertEqual(doid.attrs['publisher'],
                         "National Institute of Standards and Technology")
        self.assertEquals(doid.attrs['url'], url)
        self.assertEquals(doid.attrs['publicationYear'], 2020)
        
        
        

        


        
        
        

if __name__ == '__main__':
    test.main()

