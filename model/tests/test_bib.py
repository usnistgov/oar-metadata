#!/usr/bin/python
#
import os, json, pdb
import unittest as test
import ejsonschema as ejs

from jsonschema.exceptions import ValidationError

nerdm = "https://data.nist.gov/od/dm/nerdm-schema/v0.5#"
nerdmbib = "https://data.nist.gov/od/dm/nerdm-schema/bib/v0.4#"

schemadir = os.path.dirname(os.path.dirname(__file__))
exdir = os.path.join(schemadir, "examples")
jqlib = os.path.join(os.path.dirname(schemadir), "jq")
datadir = os.path.join(jqlib, "tests", "data")
pdlfile = os.path.join(datadir, "nist-pdl-oct2016.json")

class TestExamples(test.TestCase):

    def setUp(self):
        loader = ejs.SchemaLoader.from_directory(schemadir)
        self.val = ejs.ExtValidator(loader, ejsprefix='_')

    def validate_file(self, filename):
        fpath = os.path.join(exdir, filename)
        with open(fpath) as fd:
            data = json.load(fd)

        self.val.validate(data, False, True)

    def test_refType(self):
        schema = nerdmbib + "/definitions/DCiteRefType"
        self.val.validate("References", False, True, schema, True)
        self.val.validate("IsReferencedBy", False, True, schema, True)
        self.val.validate("IsSupplementTo", False, True, schema, True)
        self.val.validate("IsDocumentedBy", False, True, schema, True)
        self.val.validate("IsCitedBy", False, True, schema, True)
        self.val.validate("Cites", False, True, schema, True)
        with self.assertRaises(ValidationError):
            self.val.validate("IsSupplementedTo", False, True, schema, True)
        
    def test_DCiteReference(self):
        tstref = {
            "@id": "https://doi.org/10.88434/goober",
            "@type": ["dcat:Dataset"],
            "location": "https://data.nist.gov/goober",
            "refType": "References"
        }

        schema = nerdmbib + "/definitions/DCiteReference"
        self.val.validate(tstref, False, True, schema, True)

    def test_attype(self):
        tstref = {
            u'refType': u'IsDocumentedBy',
            u'location': u'http://kinetics.nist.gov/janaf/pdf/JANAF-FourthEd-1998-1Vol1-Intro.pdf',
            u'_extensionSchemas': [
                u'https://data.nist.gov/od/dm/nerdm-schema/bib/v0.4#/definitions/DCiteReference'
            ],
            u'@type': [u'schema:Book'],
            u'label': u'JPCRD Monograph: NIST-JANAF Thermochemical Tables, Pt. 1 (AL-C'
        }

        schema = nerdm + "/definitions/BibliographicReference"
        self.val.validate(tstref, False, True, schema, True)


        
        

if __name__ == '__main__':
    test.main()

