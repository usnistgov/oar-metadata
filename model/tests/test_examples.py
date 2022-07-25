#!/usr/bin/python
#
import os, json, pdb
import unittest as test
import ejsonschema as ejs

nerdm = "https://data.nist.gov/od/dm/nerdm-schema/v0.1#"
nerdmpub = "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.1#"
poduri = "https://data.nist.gov/od/dm/pod-schema/v1.1#definitions/Dataset"
podrlxuri = "https://data.nist.gov/od/dm/pod-schema/relaxed-1.1#definitions/Dataset"

schemadir = os.path.dirname(os.path.dirname(__file__))
exdir = os.path.join(schemadir, "examples")
jqlib = os.path.join(os.path.dirname(schemadir), "jq")
datadir = os.path.join(jqlib, "tests", "data")
pdlfile = os.path.join(datadir, "nist-pdl-oct2016.json")

class TestExamples(test.TestCase):

    def setUp(self):
        loader = ejs.SchemaLoader.from_directory(schemadir)
        self.val = ejs.ExtValidator(loader, ejsprefix='_')

    def validate_file(self, filename, schemauri=None):
        fpath = os.path.join(exdir, filename)
        with open(fpath) as fd:
            data = json.load(fd)

        try:
            self.val.validate(data, False, True, schemauri)
        except ejs.ValidationError as ex:
            self.fail(os.path.basename(filename)+": Not Valid!\n"+str(ex))

    def test_validate_janaf(self):
        self.validate_file("janaf.json")

    def test_validate_janaf_hier(self):
        self.validate_file("janaf-hier.json")

    def test_validate_hitsc(self):
        self.validate_file("hitsc.json")

    def test_validate_ceramicsportal(self):
        self.validate_file("ceramicsportal.json")

    def test_validate_janaf_0_1(self):
        self.validate_file("janaf-0.1.json")

    def test_validate_janaf_hier_0_1(self):
        self.validate_file("janaf-hier-0.1.json")

    def test_validate_hitsc_0_1(self):
        self.validate_file("hitsc-0.1.json")

    def test_validate_ceramicsportal_0_1(self):
        self.validate_file("ceramicsportal-0.1.json")

    def test_validate_forensics_theme(self):
        samples = [f for f in os.listdir(os.path.join(exdir,"forensics")) if f.endswith(".json")]
        for samp in samples:
            self.validate_file(os.path.join("forensics", samp))

    def test_validate_pod(self):
        self.validate_file("pod.json", poduri)

    def test_validate_relaxed_pod(self):
        self.validate_file("pod.json", podrlxuri)

class TestSchemas(test.TestCase):

    def setUp(self):
        self.val = ejs.SchemaValidator()

    def validate_file(self, filename):
        fpath = os.path.join(schemadir, filename)
        with open(fpath) as fd:
            data = json.load(fd)

        self.val.validate(data, False, True)

    def test_nerdm(self):
        self.validate_file("nerdm-schema.json")

    def test_pub_nerdm(self):
        self.validate_file("nerdm-pub-schema.json")

    def test_bib_nerdm(self):
        self.validate_file("nerdm-bib-schema.json")

    def test_rls_nerdm(self):
        self.validate_file("nerdm-rls-schema.json")

    def test_agg_nerdm(self):
        self.validate_file("nerdm-agg-schema.json")

    def test_pod(self):
        self.validate_file("pod-schema.json")
        
    def test_relaxed_pod(self):
        self.validate_file("pod-relaxed-schema.json")
        

if __name__ == '__main__':
    test.main()

