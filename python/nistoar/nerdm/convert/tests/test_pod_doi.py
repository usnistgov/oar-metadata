import unittest, pdb, os, json
from collections import OrderedDict

import nistoar.nerdm.convert.pod as cvt
from nistoar.doi.resolving import DOIInfo

citeproc_auths = [
    {u'affiliation': [], u'given': u'Carmen', u'family':
     u'Galen Acedo', u'sequence': u'first'},
    {u'authenticated-orcid': False, u'given': u'Victor',
     u'family': u'Arroyo', u'sequence': u'additional',
     u'affiliation': ["The Institute"],
     u'ORCID': u'http://orcid.org/0000-0002-0858-0324'},
    {u'affiliation': [], u'given': u'Ellen', u'family': u'Andresen',
     u'sequence': u'additional'},
    {u'affiliation': [], u'given': u'Ricard', u'family': u'Arasa-Gisbert',
     u'sequence': u'additional'}
]

datacite_auths = [
    {"name":"Fenner, Martin", "nameType":"Personal", "givenName":"Martin",
     "familyName":"Fenner","affiliation":[{"name": "DataCite"}],
     "contributorType":"Editor",
     "nameIdentifiers":[
         {"nameIdentifier":"https://orcid.org/0000-0001-6528-2027",
          "nameIdentifierScheme":"ORCID"}
     ]
    },
    {"name":"Ashton, Jan","nameType":"Personal","familyName":"Ashton","affiliation":"British Library","contributorType":"Editor"},
    {"name":"DataCite Metadata Working Group"}
]

rescfg = {
    "app_name": "NIST Open Access for Research: oar-metadata",
    "app_version": "testing",
    "app_url": "http://github.com/usnistgov/oar-metadata/",
    "email": "datasupport@nist.gov"
}

class TestConvertAuthors(unittest.TestCase):

    def test_citeproc_author2nerdm_author(self):
        author = cvt.citeproc_author2nerdm_author(citeproc_auths[0])
        self.assertEqual(author['familyName'], "Galen Acedo")
        self.assertEqual(author['givenName'], "Carmen")
        self.assertNotIn('middleName', author)
        self.assertNotIn('affiliation', author)
        self.assertNotIn('orcid', author)
        self.assertEqual(author['fn'], "Carmen Galen Acedo")
        
        author = cvt.citeproc_author2nerdm_author(citeproc_auths[1])
        self.assertEqual(author['familyName'], "Arroyo")
        self.assertEqual(author['givenName'], "Victor")
        self.assertEqual(author['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "The Institute"}])
        self.assertNotIn('middleName', author)
        self.assertEqual(author['orcid'], "0000-0002-0858-0324")
        self.assertEqual(author['fn'], "Victor Arroyo")

    def test_citeproc_authors2nerdm_authors(self):
        authors = cvt.citeproc_authors2nerdm_authors(citeproc_auths)
        self.assertEqual(len(authors), 4)
        
        self.assertEqual(authors[0]['familyName'], "Galen Acedo")
        self.assertEqual(authors[0]['givenName'], "Carmen")
        self.assertNotIn('middleName', authors[0])
        self.assertNotIn('affiliation', authors[0])
        self.assertNotIn('orcid', authors[0])
        self.assertEqual(authors[0]['fn'], "Carmen Galen Acedo")

        self.assertEqual(authors[1]['familyName'], "Arroyo")
        self.assertEqual(authors[1]['givenName'], "Victor")
        self.assertEqual(authors[1]['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "The Institute"}])
        self.assertNotIn('middleName', authors[1])
        self.assertEqual(authors[1]['orcid'], "0000-0002-0858-0324")
        self.assertEqual(authors[1]['fn'], "Victor Arroyo")
        
    def test_crossref_author2nerdm_author(self):
        author = cvt.citeproc_author2nerdm_author(citeproc_auths[0])
        self.assertEqual(author['familyName'], "Galen Acedo")
        self.assertEqual(author['givenName'], "Carmen")
        self.assertNotIn('middleName', author)
        self.assertNotIn('affiliation', author)
        self.assertNotIn('orcid', author)
        self.assertEqual(author['fn'], "Carmen Galen Acedo")
        
        author = cvt.citeproc_author2nerdm_author(citeproc_auths[1])
        self.assertEqual(author['familyName'], "Arroyo")
        self.assertEqual(author['givenName'], "Victor")
        self.assertEqual(author['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "The Institute"}])
        self.assertNotIn('middleName', author)
        self.assertEqual(author['orcid'], "0000-0002-0858-0324")
        self.assertEqual(author['fn'], "Victor Arroyo")

    def test_crossref_authors2nerdm_authors(self):
        authors = cvt.citeproc_authors2nerdm_authors(citeproc_auths)
        self.assertEqual(len(authors), 4)
        
        self.assertEqual(authors[0]['familyName'], "Galen Acedo")
        self.assertEqual(authors[0]['givenName'], "Carmen")
        self.assertNotIn('middleName', authors[0])
        self.assertNotIn('affiliation', authors[0])
        self.assertNotIn('orcid', authors[0])
        self.assertEqual(authors[0]['fn'], "Carmen Galen Acedo")

        self.assertEqual(authors[1]['familyName'], "Arroyo")
        self.assertEqual(authors[1]['givenName'], "Victor")
        self.assertEqual(authors[1]['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "The Institute"}])
        self.assertNotIn('middleName', authors[1])
        self.assertEqual(authors[1]['orcid'], "0000-0002-0858-0324")
        self.assertEqual(authors[1]['fn'], "Victor Arroyo")
        
    def test_datacite_creator2nerdm_author(self):
        author = cvt.datacite_creator2nerdm_author(datacite_auths[0])
        self.assertEqual(author['givenName'], "Martin")
        self.assertEqual(author['familyName'], "Fenner")
        self.assertEqual(author['fn'], "Martin Fenner")
        self.assertEqual(author['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "DataCite"}])
        self.assertEqual(author['orcid'], "0000-0001-6528-2027")

        author = cvt.datacite_creator2nerdm_author(datacite_auths[1])
        self.assertEqual(author['givenName'], "Jan")
        self.assertEqual(author['familyName'], "Ashton")
        self.assertEqual(author['fn'], "Jan Ashton")
        self.assertEqual(author['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "British Library"}])
        self.assertNotIn('orcid', author)

        author = cvt.datacite_creator2nerdm_author(datacite_auths[2])
        self.assertEqual(author['fn'], "DataCite Metadata Working Group")
        self.assertNotIn('orcid', author)
        self.assertNotIn('givenName', author)
        self.assertNotIn('familyName', author)
        self.assertNotIn('affiliation', author)

    def test_datacite_creators2nerdm_authors(self):
        authors = cvt.datacite_creators2nerdm_authors(datacite_auths)
        self.assertEqual(len(authors), 3)

        self.assertEqual(authors[0]['givenName'], "Martin")
        self.assertEqual(authors[0]['familyName'], "Fenner")
        self.assertEqual(authors[0]['fn'], "Martin Fenner")
        self.assertEqual(authors[0]['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "DataCite"}])
        self.assertEqual(authors[0]['orcid'], "0000-0001-6528-2027")

        self.assertEqual(authors[1]['givenName'], "Jan")
        self.assertEqual(authors[1]['familyName'], "Ashton")
        self.assertEqual(authors[1]['fn'], "Jan Ashton")
        self.assertEqual(authors[1]['affiliation'],
                         [{"@type": "schema:affiliation",
                           "title": "British Library"}])
        self.assertNotIn('orcid', authors[1])

        self.assertEqual(authors[2]['fn'], "DataCite Metadata Working Group")
        self.assertNotIn('orcid', authors[2])
        self.assertNotIn('givenName', authors[2])
        self.assertNotIn('familyName', authors[2])
        self.assertNotIn('affiliation', authors[2])

crossref = {
  "title": "Ecological traits of the world\u2019s primates", 
  "URL": "http://dx.doi.org/10.1038/s41597-019-0059-9", 
  "publisher": "Springer Science and Business Media LLC", 
  "issued": {
    "date-parts": [
      [
        2019, 
        5, 
        13
      ]
    ]
  }, 
  "container-title": "Scientific Data", 
  "article-number": "55"
}

datacite = {
  "publisher": "National Institute of Standards and Technology", 
  "DOI": "10.18434/t40p4r", 
  "language": "eng", 
  "author": [
    {
      "given": "TN", 
      "family": "Bhat"
    }
  ], 
  "URL": "http://bioinfo.nist.gov/", 
  "issued": {
    "date-parts": [
      [
        2002
      ]
    ]
  }, 
  "title": "Human Mitochondrial Protein Database, NIST Standard Reference Database 131", 
  "type": "dataset", 
  "id": "https://doi.org/10.18434/t40p4r"
}

        
class TestConvertReferences(unittest.TestCase):

    def test_crossref_doiinfo2reference(self):
        info = DOIInfo("10.10/XXX", source="Crossref")
        info._data = crossref
        info._cite = "ibid"

        ref = cvt._doiinfo2reference(info, "https://goober.org/")
        self.assertEqual(ref['@type'], ['schema:Article'])
        self.assertEqual(ref['@id'], 'doi:10.10/XXX')
        self.assertEqual(ref['refType'], 'IsCitedBy')
        self.assertEqual(ref['title'],
                         "Ecological traits of the world\u2019s primates")
        self.assertEqual(ref['location'], "https://goober.org/10.10/XXX")
        self.assertEqual(ref['issued'], '2019-05-13')
        self.assertEqual(ref['citation'], 'ibid')

    def test_datacite_doiinfo2reference(self):
        info = DOIInfo("10.10/XXX", source="Datacite")
        info._data = datacite
        info._cite = "ibid"

        ref = cvt._doiinfo2reference(info, "https://goober.org/")
        self.assertEqual(ref['@type'], ['schema:Dataset'])
        self.assertEqual(ref['@id'], 'doi:10.10/XXX')
        self.assertEqual(ref['refType'], 'References')
        self.assertEqual(ref['title'],
   "Human Mitochondrial Protein Database, NIST Standard Reference Database 131")
        self.assertEqual(ref['location'], "https://goober.org/10.10/XXX")
        self.assertEqual(ref['issued'], '2002')
        self.assertEqual(ref['citation'], 'ibid')
        self.assertIn('_extensionSchemas', ref)
        self.assertTrue(isinstance(ref['_extensionSchemas'], list))
        self.assertTrue(ref['_extensionSchemas'][0].startswith("https://data.nist.gov/od/dm/nerdm-schema/v0.2#/definitions/"), msg="Unexpected extension schema URI: "+ref['_extensionSchemas'][0])

class TestDOIResolver(unittest.TestCase):

    def test_ctor(self):
        rslvr = cvt.DOIResolver()
        self.assertIsNone(rslvr.resolver._client_info)
        self.assertEqual(rslvr.resolver._resolver, "https://doi.org/")
        
        rslvr = cvt.DOIResolver(resolver="https://goob.org/")
        self.assertEqual(rslvr.resolver._resolver, "https://goob.org/")
        
        rslvr = cvt.DOIResolver(('a', 'b', 'c', 'd'), "https://goob.org/")
        self.assertEqual(rslvr.resolver._client_info, ('a', 'b', 'c', 'd'))
        self.assertEqual(rslvr.resolver._resolver, "https://goob.org/")

    def test_from_config(self):
        rslvr = cvt.DOIResolver.from_config({})
        self.assertEqual(rslvr.resolver._resolver, "https://doi.org/")
        self.assertIn("unspecified", rslvr.resolver._client_info[0])
        self.assertEqual(rslvr.resolver._client_info[1], "unknown")
        self.assertIn("oar-metadata", rslvr.resolver._client_info[2])
        self.assertIn("datasupport", rslvr.resolver._client_info[3])

        rslvr = cvt.DOIResolver.from_config({
            "app_name": "Fred",
            "resolver_url": "https://goob.org/",
            "foo": "bar"
        })
        self.assertEqual(rslvr.resolver._resolver, "https://goob.org/")
        self.assertEqual("Fred", rslvr.resolver._client_info[0])
        self.assertEqual(rslvr.resolver._client_info[1], "unknown")
        self.assertIn("oar-metadata", rslvr.resolver._client_info[2])
        self.assertIn("datasupport", rslvr.resolver._client_info[3])

        
                         
    @unittest.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                     "kindly skipping doi service checks")
    def test_toReference(self):
        rslvr = cvt.DOIResolver.from_config(rescfg)
        ref = rslvr.to_reference("10.18434/m33x0v")

        self.assertEqual(ref['@type'], ['schema:Dataset'])
        self.assertEqual(ref['@id'], 'doi:10.18434/m33x0v')
        self.assertEqual(ref['refType'], 'References')
        self.assertTrue(ref['title'].startswith("Effect of Heterogeneity"))
        self.assertEqual(ref['location'], "https://doi.org/10.18434/m33x0v")
        self.assertEqual(ref['issued'], '2017')
        self.assertTrue(ref['citation'].startswith("Conny, J."))

    @unittest.skipIf("doi" not in os.environ.get("OAR_TEST_INCLUDE",""),
                     "kindly skipping doi service checks")
    def test_to_authors(self):
        rslvr = cvt.DOIResolver.from_config(rescfg)
        auths = rslvr.to_authors("10.18434/m33x0v")

        self.assertEqual(len(auths), 2)
        self.assertEqual(auths[0]['givenName'], "Joseph")
        self.assertEqual(auths[0]['familyName'], "Conny")
        self.assertEqual(auths[0]['fn'], "Joseph Conny")
        # self.assertIn('affiliation', auths[0])
        # self.assertIn('affiliation', auths[1])
        # self.assertEqual(auths[0]['affiliation'][0]['title'],
        #                  "National Institute of Standards and Technology")
        self.assertNotIn('orcid', auths[0])
        self.assertNotIn('orcid', auths[1])



        
if __name__ == '__main__':
    unittest.main()
