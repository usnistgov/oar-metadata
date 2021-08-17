import os, sys, pdb, shutil, logging, json
import unittest as test
from copy import deepcopy

from nistoar.nerdm.convert import latest
import nistoar.nerdm.constants as const

NERDM_SCH_ID_BASE = const.core_schema_base

class TestNERDm2Latest(test.TestCase):
    def test_schuripat(self):
        self.assertTrue(latest._nrdpat.match("https://data.nist.gov/od/dm/nerdm-schema/pub/v1.0#Res") )
        self.assertTrue(latest._nrdpat.match("https://data.nist.gov/od/dm/nerdm-schema/goob/v0.3") )
        self.assertTrue(latest._nrdpat.match("https://data.nist.gov/od/dm/nerdm-schema/foo/bar/v0.3#"))

        self.assertFalse(latest._nrdpat.match("https://www.nist.gov/od/id/nerdm-schema/blue/v0.3#"))
        self.assertFalse(latest._nrdpat.match("https://data.nist.gov/od/dm/nerdm-schema/v0.3#Res"))

        pat = latest._schuripatfor(NERDM_SCH_ID_BASE)
        self.assertTrue(pat.match("https://data.nist.gov/od/dm/nerdm-schema/v0.3#pub"))
        pat = latest._schuripatfor(NERDM_SCH_ID_BASE+"pub/")
        self.assertTrue(pat.match("https://data.nist.gov/od/dm/nerdm-schema/pub/v0.3#pub"))
        self.assertFalse(pat.match("https://data.nist.gov/od/dm/nerdm-schema/goob/v0.3#pub"))

    def test_upd_schema_ver(self):
        cvtr = latest.NERDm2Latest(defver="1.0", byext={})
        self.assertEqual(cvtr._upd_schema_ver("https://data.nist.gov/od/dm/nerdm-schema/pub/v0.3#Res",
                                              cvtr.byext, cvtr.defver),
                         "https://data.nist.gov/od/dm/nerdm-schema/pub/1.0#Res")
        
        byext = {
            latest._schuripatfor("http://example.com/anext/"): "v0.1",
            latest._schuripatfor(NERDM_SCH_ID_BASE+"pub/"):   "v1.2",
            latest._schuripatfor(NERDM_SCH_ID_BASE):          "v2.2"
        }

        self.assertEqual(cvtr._upd_schema_ver("https://data.nist.gov/od/dm/nerdm-schema/pub/v0.3#Res",
                                              byext, cvtr.defver),
                         "https://data.nist.gov/od/dm/nerdm-schema/pub/v1.2#Res")
        self.assertEqual(cvtr._upd_schema_ver("https://data.nist.gov/od/dm/nerdm-schema/v0.3",
                                              byext, cvtr.defver),
                         "https://data.nist.gov/od/dm/nerdm-schema/v2.2")
        self.assertEqual(cvtr._upd_schema_ver("http://example.com/anext/v88#goob", byext, cvtr.defver),
                         "http://example.com/anext/v0.1#goob")
        self.assertEqual(cvtr._upd_schema_ver("https://data.nist.gov/od/dm/nerdm-schema/blue/v0.3#Res",
                                              byext, cvtr.defver),
                         "https://data.nist.gov/od/dm/nerdm-schema/blue/1.0#Res")
        
    def test_upd_schema_ver_on_node(self):
        defver = "1.0"
        byext = {
            latest._schuripatfor("http://example.com/anext/"): "v0.1",
            latest._schuripatfor(NERDM_SCH_ID_BASE+"pub/"):   "v1.2",
            latest._schuripatfor(NERDM_SCH_ID_BASE):          "v2.2"
        }
        cvtr = latest.NERDm2Latest(defver=defver, byext={})

        data = {
            "goob": "https://data.nist.gov/od/dm/nerdm-schema/v0.3",
            "foo": [{
                "goob": [ "http://example.com/anext/v88#goob",
                          "http://goober.com/foop/v99#big" ],
                "blah": "snooze"
            }],
            "bar": {
                "hank": "aaron",
                "tex": {
                    "goob": "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.3#Contact",
                    "blah": "blah"
                },
                "goob": []
            }
        }

        cvtr._upd_schema_ver_on_node(data, "goob", byext, "1.0")
        self.assertEqual(data['goob'], 
                         "https://data.nist.gov/od/dm/nerdm-schema/v2.2")
        self.assertEqual(data['foo'][0]['goob'], 
                         [ "http://example.com/anext/v0.1#goob",
                           "http://goober.com/foop/v99#big" ])
        self.assertEqual(data['bar']['tex']['goob'], 
                     "https://data.nist.gov/od/dm/nerdm-schema/pub/v1.2#Contact")
        self.assertEqual(data['bar']['goob'], [])

        cvtr._upd_schema_ver_on_node(data, "goob", {}, "1.0")
        self.assertEqual(data['goob'], 
                         "https://data.nist.gov/od/dm/nerdm-schema/v2.2")
        self.assertEqual(data['foo'][0]['goob'], 
                         [ "http://example.com/anext/v0.1#goob",
                           "http://goober.com/foop/v99#big" ])
        self.assertEqual(data['bar']['tex']['goob'], 
                     "https://data.nist.gov/od/dm/nerdm-schema/pub/1.0#Contact")
        self.assertEqual(data['bar']['goob'], [])

    def test_update_nerdm_schema(self):
        defver = "v1.0"
        byext = {
            "http://example.com/anext/": "v0.1",
            "pub":  "v1.2",
            "bib":  "v0.8",
            "":     "v2.2"
        }
        cvtr = latest.NERDm2Latest(defver=defver, byext=byext)

        nerdmd = {
            "$schema": "https://data.nist.gov/od/dm/nerdm-schema/v0.3",
            "foo": {
                "$extensionSchemas": [ "http://example.com/anext/v88#goob",
                          "http://goober.com/foop/v99#big" ],
                "blah": "snooze"
            },
            "bar": {
                "hank": "aaron",
                "tex": {
                    "$extensionSchemas": "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.3#Contact",
                    "blah": "blah"
                },
                "$extensionSchemas": []
            },
            "references": [
                {
                    'location': 'https://tinyurl.com/asdf',
                    "$extensionSchemas": [
                        "https://data.nist.gov/od/dm/nerdm-schema/v0.3#/definitions/BibliographicReference",
                        "https://data.nist.gov/od/dm/nerdm-schema/v0.3#/definitions/DCiteReference"
                    ]
                }
            ]
        }

        data = cvtr.update_nerdm_schema(nerdmd)
        self.assertEqual(data['$schema'], 
                         "https://data.nist.gov/od/dm/nerdm-schema/v2.2")
        self.assertEqual(nerdmd['$schema'], "https://data.nist.gov/od/dm/nerdm-schema/v0.3")
        self.assertEqual(data['foo']['$extensionSchemas'], 
                         [ "http://example.com/anext/v0.1#goob",
                           "http://goober.com/foop/v99#big" ])
        self.assertEqual(data['bar']['tex']['$extensionSchemas'], 
                     "https://data.nist.gov/od/dm/nerdm-schema/pub/v1.2#Contact")
        self.assertEqual(data['bar']['$extensionSchemas'], [])
        self.assertEqual(data['references'][0]['$extensionSchemas'][0],
                         "https://data.nist.gov/od/dm/nerdm-schema/v2.2#/definitions/BibliographicReference")
        self.assertEqual(data['references'][0]['$extensionSchemas'][1],
                         "https://data.nist.gov/od/dm/nerdm-schema/bib/v0.8#/definitions/DCiteReference")
        
        nerdmd = {
            "_schema": "https://data.nist.gov/od/dm/nerdm-schema/v0.3",
            "foo": {
                "_extensionSchemas": [ "http://example.com/anext/v88#goob",
                          "http://goober.com/foop/v99#big" ],
                "blah": "snooze"
            },
            "bar": {
                "hank": "aaron",
                "tex": {
                    "_extensionSchemas": "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.3#Contact",
                    "blah": "blah"
                },
                "_extensionSchemas": []
            }
        }

        cvtr = latest.NERDm2Latest()
        data = cvtr.update_nerdm_schema(nerdmd)
        self.assertEqual(data['_schema'], const.CORE_SCHEMA_URI)
        self.assertEqual(nerdmd['_schema'], "https://data.nist.gov/od/dm/nerdm-schema/v0.3")
        self.assertEqual(data['foo']['_extensionSchemas'], 
                         [ "http://example.com/anext/v88#goob",
                           "http://goober.com/foop/v99#big" ])
        self.assertEqual(data['bar']['tex']['_extensionSchemas'], const.PUB_SCHEMA_URI+"#Contact")
        self.assertEqual(data['bar']['_extensionSchemas'], [])
        
        latest.update_nerdm_schema(nerdmd)
        self.assertEqual(nerdmd['_schema'], const.CORE_SCHEMA_URI)

    def test_create_release_history(self):
        cvtr = latest.NERDm2Latest()
        nerdm = {
            "$schema": "https://data.nist.gov/od/dm/nerdm-schema/v0.3",
            "@id": "ark:/88888/goob",
            "versionHistory": [
                {
                    "version": "1.0.0"
                },
                {
                    "version": "1.0.1"
                }
            ]
        }
        hist = cvtr.create_release_history(nerdm, "_r")
        self.assertEqual(hist.get("@id"), nerdm['@id']+"_r")
        self.assertEqual(len(hist['hasRelease']), 2)
        self.assertEqual(hist['hasRelease'][0]['version'], "1.0.0")
        self.assertEqual(hist['hasRelease'][1]['version'], "1.0.1")
        hist = cvtr.create_release_history(nerdm)
        self.assertEqual(hist.get("@id"), nerdm['@id']+".rel")

    def test_convert(self):
        cvtr = latest.NERDm2Latest()
        nerdm = {
            "$schema": "https://data.nist.gov/od/dm/nerdm-schema/v0.3",
            "@id": "ark:/88888/goob",
            "versionHistory": [
                {
                    "version": "1.0.0"
                },
                {
                    "version": "1.0.1"
                }
            ]
        }
        data = cvtr.convert(nerdm)
        self.assertIn("$schema", data)
        self.assertNotIn("_schema", data)
        self.assertEqual(data["$schema"], const.CORE_SCHEMA_URI)
        self.assertNotIn("versionHistory", data)
        self.assertIn("releaseHistory", data)
        self.assertEqual(data['releaseHistory']['@id'], nerdm['@id']+".rel")
                    
                         
if __name__ == '__main__':
    test.main()
