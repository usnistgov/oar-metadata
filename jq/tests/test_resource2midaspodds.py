#!/usr/bin/python
#
import os, unittest, json, subprocess as subproc, types, pdb
import ejsonschema as ejs

nerdm = "https://data.nist.gov/od/dm/nerdm-schema/v0.2#"
nerdmpub = "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.2#"
podds = "https://data.nist.gov/od/dm/pod-schema/v1.1#/definitions/Dataset"
jqlib = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
schemadir = os.path.join(os.path.dirname(jqlib), "model")
datadir = os.path.join(schemadir,"examples")

loader = ejs.SchemaLoader.from_directory(schemadir)
val = ejs.ExtValidator(loader, ejsprefix='_')


class TestSamples(unittest.TestCase):

    def convert(self, filename):
        nerdfile = os.path.join(datadir, filename)
        return send_file_thru_jq('nerdm::resource2midaspodds', nerdfile)

    def test_janaf(self):
        pod = self.convert("janaf.json")
        val.validate(pod, schemauri=podds)

        for key in "references landingPage distribution issued license".split():
            self.assertIn(key, pod)

        self.assertEqual(len(pod['references']), 2)
        self.assertEqual(len(pod['distribution']), 319)
        self.assertEqual(pod['contactPoint']['fn'], 'Thomas Allison')
        self.assertEqual(pod['contactPoint']['hasEmail'],
                         'mailto:thomas.allison@nist.gov')

        self.assertEqual(len(pod['theme']), 2)
        self.assertEqual(pod['theme'][0], "Chemistry-> Thermochemical properties")
        self.assertEqual(pod['theme'][1], "Standards-> Reference data")

    def test_hitsc(self):
        pod = self.convert("hitsc.json")
        val.validate(pod, schemauri=podds)

        for key in "references landingPage dataQuality".split():
            self.assertIn(key, pod)
        self.assertNotIn('distribution', pod)

        self.assertEqual(len(pod['references']), 1)

    def test_hitsc01(self):
        pod = self.convert("hitsc-0.1.json")
        val.validate(pod, schemauri=podds)

        for key in "references landingPage dataQuality".split():
            self.assertIn(key, pod)
        self.assertNotIn('distribution', pod)

        self.assertEqual(len(pod['references']), 1)
        
    def test_ceramics(self):
        pod = self.convert("ceramicsportal.json")
        val.validate(pod, schemauri=podds)

        for key in "landingPage dataQuality distribution".split():
            self.assertIn(key, pod)
        self.assertNotIn('references', pod)

        self.assertEqual(len(pod['keyword']), 9)
        self.assertEqual(len(pod['distribution']), 1)
        
    def test_ceramics01(self):
        pod = self.convert("ceramicsportal-0.1.json")
        val.validate(pod, schemauri=podds)

        for key in "landingPage dataQuality distribution".split():
            self.assertIn(key, pod)
        self.assertNotIn('references', pod)

        self.assertEqual(len(pod['keyword']), 9)
        self.assertEqual(len(pod['distribution']), 1)


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
        return 'import "nerdm2pod" as nerdm; ' + filter

    cmd.extend([impnerdm(jqfilter), filepath])

    proc = subproc.Popen(cmd, stdout=subproc.PIPE, stderr=subproc.PIPE)
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


          
    

if __name__ == '__main__':
    unittest.main()
