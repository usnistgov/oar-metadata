#!/usr/bin/env python
#
import os, unittest, json, subprocess as subproc, types, pdb
from collections import OrderedDict
import ejsonschema as ejs

nerdm = "https://data.nist.gov/od/dm/nerdm-schema/v0.5#"
nerdmpub = "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.5#"
nerdmbib = "https://data.nist.gov/od/dm/nerdm-schema/bib/v0.5#"
datadir = os.path.join(os.path.dirname(__file__), "data")
janaffile = os.path.join(datadir, "janaf_pod.json")
corrfile =  os.path.join(datadir, "CORR-DATA.json")
minfile =  os.path.join(datadir, "minimal_pod.json")
pdlfile = os.path.join(datadir, "nist-pdl-oct2016.json")
jqlib = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
schemadir = os.path.join(os.path.dirname(jqlib), "model")

class TestJanaf(unittest.TestCase):  # 

    def setUp(self):
        # pdb.set_trace() # nerdm::podds2resourc
        self.out = send_file_thru_jq('nerdm::podds2resource', janaffile,
                                     {"id": "ark:ID"})

    def test_id(self): self.assertEqual(self.out['@id'], "ark:ID")
    def test_al(self): self.assertEqual(self.out['accessLevel'], "public")
    def test_rights(self):
        self.assertEquals(self.out['rights'], "data is free to use")
                          
    def test_context(self):
        self.assertEqual(self.out['@context'],
                        [ "https://data.nist.gov/od/dm/nerdm-pub-context.jsonld",
                          {"@base": "ark:ID"} ])
                          
    def test_schema(self):
        self.assertEqual(self.out['_schema'],
                         "https://data.nist.gov/od/dm/nerdm-schema/v0.5#")
    def test_extsch(self):
        
        exts = self.out['_extensionSchemas']
        self.assertEqual(len(exts), 1)
        self.assertIn(nerdmpub+"/definitions/PublicDataResource", exts)

    def test_restypes(self):
        types = self.out['@type']
        self.assertIsInstance(types, list)
        self.assertEqual(len(types), 3)
        self.assertEqual(types[0], "nrd:SRD")
        self.assertEqual(types[1], "nrdp:PublicDataResource")
        self.assertEqual(types[2], "dcat:Dataset")

    def test_arestr(self):
        props = "title modified ediid landingPage license".split()
        for prop in props:
            self.assertIn(prop, self.out, "Property not found: " + prop)
            self.assertIsInstance(self.out[prop], (str,),
                "Property '{0}' not a string: {1}".format(prop, self.out[prop]))

    def test_arearrays(self):
        props = "description bureauCode programCode language references components".split()
        for prop in props:
            self.assertIn(prop, self.out, "Property not found: " + prop)
            self.assertIsInstance(self.out[prop], list,
                "Property '{0}' not a list: {1}".format(prop, self.out[prop]))

    def test_description(self):
        self.assertFalse(any([p.strip() == "" for p in self.out['description']]))
        self.assertEqual(len(self.out['description']), 1)

    def test_ediid(self):
        self.assertEqual(self.out['ediid'],
                          "ECBCC1C1301D2ED9E04306570681B10735")

    def test_status(self):
        self.assertEqual(self.out['status'], "available")

    def test_components(self):
        comps = self.out['components']
        self.assertGreaterEqual(len(comps), 318,
                   "Missing components; only {0}/{1}".format(len(comps), 318))
        self.assertLessEqual(len(comps), 318,
                   "Extra components; have {0}/{1}".format(len(comps), 318))

        props = "title describedBy downloadURL mediaType filepath".split()
        for prop in props:
            self.assertIn(prop, comps[0], "Property not found: " + prop)
            self.assertIsInstance(comps[0][prop], (str,),
                "Property '{0}' not a string: {1}".format(prop, comps[0][prop]))

        exts = comps[0]['_extensionSchemas']
        self.assertEqual(len(exts), 1)
        self.assertIn(nerdmpub+"/definitions/DataFile", exts)

        typs = comps[0]['@type']
        self.assertEqual(len(typs), 3)
        self.assertEqual(typs[0], "nrdp:DataFile")
        self.assertEqual(typs[1], "nrdp:DownloadableFile")
        self.assertEqual(typs[2], "dcat:Distribution")

        props = "describedBy downloadURL".split()
        for prop in props:
            self.assertTrue(comps[0][prop].startswith("http://www.nist.gov/"),
                            prop+" property not a URL: "+comps[0][prop])

    def test_references(self):
        refs =self.out['references']
        self.assertEqual(len(refs), 1)

        self.assertIsInstance(refs[0]['@type'], list)
        self.assertIsInstance(refs[0]['@type'][0], (str,))
        self.assertEqual(refs[0]['@type'], ["deo:BibliographicReference"])
        self.assertEqual(refs[0]['refType'], "IsSupplementTo")
        self.assertEqual(refs[0]['location'],
                          "http://www.nist.gov/data/PDFfiles/jpcrdS1V14.pdf")

        exts = refs[0]['_extensionSchemas']
        self.assertEqual(len(exts), 1)
        self.assertIn(nerdmbib+"/definitions/DCiteReference", exts)

    def test_hierarchy(self):
        self.assertIn("dataHierarchy", self.out,
                      "record is missing 'dataHierarchy' field")
        hier = self.out['dataHierarchy']
        self.assertEqual(len(hier), 318)
        self.assertIn('filepath', hier[0])
        self.assertIn('filepath', hier[-1])

    def test_theme(self):
        self.assertIn("theme", self.out,
                      "record is missing 'theme' property")
        theme = self.out['theme']
        self.assertEqual(len(theme), 2)
        self.assertEqual(theme[0], "thermochemical properties")
        self.assertEqual(theme[1], "Standards: Reference data")
        

class TestCORR(unittest.TestCase):  # 

    def setUp(self):
        # pdb.set_trace() # nerdm::podds2resourc
        self.out = send_file_thru_jq('nerdm::podds2resource', corrfile,
                                     {"id": "ark:ID"})

    def test_id(self): self.assertEqual(self.out['@id'], "ark:ID")
    def test_al(self): self.assertEqual(self.out['accessLevel'], "public")
    def test_context(self):
        self.assertEqual(self.out['@context'],
                        [ "https://data.nist.gov/od/dm/nerdm-pub-context.jsonld",
                          {"@base": "ark:ID"} ])
                          
    def test_schema(self):
        self.assertEqual(self.out['_schema'],
                          "https://data.nist.gov/od/dm/nerdm-schema/v0.5#")
    def test_extsch(self):
        
        exts = self.out['_extensionSchemas']
        self.assertEqual(len(exts), 1)
        self.assertIn(nerdmpub+"/definitions/PublicDataResource", exts)

    def test_restypes(self):
        types = self.out['@type']
        self.assertIsInstance(types, list)
        self.assertEqual(len(types), 2)
        self.assertEqual(types[0], "nrdp:PublicDataResource")
        self.assertEqual(types[1], "dcat:Dataset")

    def test_arestr(self):
        props = "title modified ediid landingPage license".split()
        for prop in props:
            self.assertIn(prop, self.out, "Property not found: " + prop)
            self.assertIsInstance(self.out[prop], (str,),
                "Property '{0}' not a string: {1}".format(prop, self.out[prop]))

    def test_arearrays(self):
        props = "description bureauCode programCode language components".split()
        for prop in props:
            self.assertIn(prop, self.out, "Property not found: " + prop)
            self.assertIsInstance(self.out[prop], list,
                "Property '{0}' not a list: {1}".format(prop, self.out[prop]))

    def test_description(self):
        self.assertFalse(any([p.strip() == "" for p in self.out['description']]))
        self.assertEqual(len(self.out['description']), 3)

    def test_ediid(self):
        self.assertEqual(self.out['ediid'],
                          "54AE54FB37AC022DE0531A570681D4291851")

    def test_components(self):
        comps = self.out['components']
#        self.assertGreaterEqual(len(comps), 5,
#                   "Missing components; only {0}/{1}".format(len(comps), 5))
        self.assertLessEqual(len(comps), 5,
                   "Extra components; have {0}/{1}".format(len(comps), 5))

        props = "downloadURL mediaType filepath".split()
        for prop in props:
            self.assertIn(prop, comps[3], "Property not found: " + prop)
            self.assertIsInstance(comps[3][prop], (str,),
                "Property '{0}' not a string: {1}".format(prop, comps[3][prop]))

        exts = comps[3]['_extensionSchemas']
        self.assertEqual(len(exts), 1)
        self.assertIn(nerdmpub+"/definitions/DataFile", exts)

        typs = comps[3]['@type']
        self.assertEqual(len(typs), 3)
        self.assertEqual(typs[0], "nrdp:DataFile")
        self.assertEqual(typs[1], "nrdp:DownloadableFile")
        self.assertEqual(typs[2], "dcat:Distribution")

        props = "downloadURL".split()
        for prop in props:
            self.assertTrue(comps[3][prop].startswith("https://opendata.nist.gov/"),
                            prop+" property not a URL: "+comps[3][prop])

        # check for inserted subcollection
        self.assertEqual(comps[0]['@type'], ["nrdp:Subcollection"])
        self.assertEqual(comps[0]['@id'], "cmps/sha256")
        self.assertEqual(comps[0]['filepath'], "sha256")
        self.assertEqual(comps[4]['filepath'],
                         "sha256/CORR-DATA_Database.zip.sha256")
        self.assertIn("_extensionSchemas", comps[0])

    def test_hierarchy(self):
        self.assertIn("dataHierarchy", self.out,
                      "record is missing 'dataHierarchy' field")
        hier = self.out['dataHierarchy']
        self.assertEqual(len(hier), 2)
        self.assertIn('filepath', hier[0])
        self.assertIn('filepath', hier[-1])
        
    def test_theme(self):
        self.assertIn("theme", self.out,
                      "record is missing 'theme' property")
        theme = self.out['theme']
        self.assertEqual(len(theme), 2)
        self.assertEqual(theme[0], "Metals")
        self.assertEqual(theme[1], "Materials characterization")
        

class TestMinimal(unittest.TestCase):  # 

    def setUp(self):
        # pdb.set_trace() # nerdm::podds2resourc
        self.out = send_file_thru_jq('nerdm::podds2resource', minfile,
                                     {"id": "ark:ID"})

    def test_id(self): self.assertEqual(self.out['@id'], "ark:ID")
    def test_al(self): self.assertEqual(self.out['accessLevel'], "public")
    def test_context(self):
        self.assertEqual(self.out['@context'],
                         [ "https://data.nist.gov/od/dm/nerdm-pub-context.jsonld",
                           {"@base": "ark:ID"} ])
                          
    def test_arestr(self):
        props = "title modified ediid landingPage".split()
        for prop in props:
            self.assertIn(prop, self.out, "Property not found: " + prop)
            self.assertIsInstance(self.out[prop], (str,),
                "Property '{0}' not a string: {1}".format(prop, self.out[prop]))

    def test_default_landingPage(self):
        self.assertIsNotNone(self.out.get('landingPage'))
        self.assertEqual(self.out.get('landingPage'),
                         "https://data.nist.gov/od/id/EBC9DB05EDF05B0EE043065706812DF87")

class TestValidateNerdm(unittest.TestCase):

    def setUp(self):
        loader = ejs.SchemaLoader.from_directory(schemadir)
        self.val = ejs.ExtValidator(loader, ejsprefix='_')

    def test_janaf(self):
        out = send_file_thru_jq('nerdm::podds2resource', janaffile,
                                {"id": "ark:ID"})
        self.val.validate(out, False, True)

    def test_with_doi(self):
        with open(pdlfile) as fd:
            cat = json.load(fd)

        ds = cat['dataset'][-1]
        ds = json.dumps(ds)
        out = send_jsonstr_thru_jq('nerdm::podds2resource', ds, {"id": "ark:ID"})

        self.val.validate(out, False, True)
        self.assertIn("doi", out)
        self.assertEqual(out.get("doi"), "doi:10.18434/T42C7D")

def format_argopts(argdata):
    """
    format the input dictionary into --argjson options
    """
    argopts = []
    if argdata:
        if not isinstance(argdata, dict):
            raise ValueError("args parameter is not a dictionary: "+str(argdata))
        for name in argdata:
            argopts += [ "--argjson", name, json.dumps(argdata[name]) ]

    return argopts

def send_jsonstr_thru_jq(jqfilter, datastr, args=None):
    """
    This executes jq with JSON data from the given JSON string and returns the 
    converted output.

    :param str jqfilter:  The jq filter to apply to the input
    :param str datastr:   The input data as a JSON-formatted string
    :param dict args:     arguments to pass in via --argjson
    """
    argopts = format_argopts(args)
    
    cmd = "jq -L {0}".format(jqlib).split() + argopts

    def impnerdm(filter):
        return 'import "pod2nerdm" as nerdm; ' + filter
    cmd.append(impnerdm(jqfilter))
    
    proc = subproc.Popen(cmd, stdout=subproc.PIPE, stderr=subproc.PIPE,
                         stdin=subproc.PIPE, universal_newlines=True)
    (out, err) = proc.communicate(datastr)

    if proc.returncode != 0:
        raise RuntimeError(err + "\nFailed jq command: "+formatcmd(cmd))

    return json.loads(out)

def send_file_thru_jq(jqfilter, filepath, args=None):
    """
    This executes jq with JSON data from the given file and returns the converted
    output.

    :param str jqfilter:  The jq filter to apply to the input
    :param str filepath:  the path to the input JSON data file
    :param dict args:     arguments to pass in via --argjson
    """
    argopts = format_argopts(args)
    
    with open(filepath):
        pass
    if not isinstance(jqfilter, (str,)):
        raise ValueError("jqfilter parameter not a string: " + str(jqfilter))

    cmd = "jq -L {0}".format(jqlib).split() + argopts

    def impnerdm(filter):
        return 'import "pod2nerdm" as nerdm; ' + filter

    cmd.extend([impnerdm(jqfilter), filepath])

    proc = subproc.Popen(cmd, stdout=subproc.PIPE, stderr=subproc.PIPE,
                         universal_newlines=True)
    (out, err) = proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(err + "\nFailed jq command: "+formatcmd(cmd))

    return json.loads(out)

def formatcmd(cmd):
    if not isinstance(cmd, (list, tuple)):
        return str(cmd)
    if isinstance(cmd, tuple):
        cmd = list(cmd)    
    for i in range(len(cmd)):
        if len(cmd[i].split()) > 1:
            cmd[i] = "'{0}'".format(cmd[i])
        elif cmd[i].startswith('"') and cmd[i].endswith('"'):
            cmd[i] = "'{0}'".format(cmd[i])
    return " ".join(cmd)

class TestSelf(unittest.TestCase):

    def test_format_argopts(self):
        opts = format_argopts(OrderedDict([("id", "ark:ID"), ("goober", [ 1, 2 ])]))
        self.assertEqual(opts,
            ['--argjson', 'id', '"ark:ID"', '--argjson', 'goober', '[1, 2]'])

    def test_bad_format_argopts(self):
        with self.assertRaises(ValueError):
            opts = format_argopts(["id", "ark:ID", "goober", [ 1, 2 ]])

    def test_send_file_badfile(self):
        with self.assertRaises(IOError):
            send_file_thru_jq('.', "nonexistent_file.json")
        
    def test_send_file_badfilter(self):
        with self.assertRaises(IOError):
            send_file_thru_jq({}, "nonexistent_file.json")

    def test_formatcmd(self):
        cmd = ['jq', '-L', 'jqlib', 'import "pod2nerdm" as nerdm; .accessLevel',
               'janaf_pod.json']
        self.assertEqual(formatcmd(cmd),
     "jq -L jqlib 'import \"pod2nerdm\" as nerdm; .accessLevel' janaf_pod.json")
        
    def test_send_file(self):
        out = send_file_thru_jq(".accessLevel", janaffile)
        self.assertEqual(out, 'public')
        
    def test_send_file_w_args(self):
        out = send_file_thru_jq(".accessLevel", janaffile,
                                {"id": "ID", "goob": "gurn"})
        self.assertEqual(out, 'public')
        

if __name__ == '__main__':
    unittest.main()



          
    
