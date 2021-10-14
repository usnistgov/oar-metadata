import unittest, pdb, os, json
from collections import OrderedDict

import nistoar.jq as jq

mddir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
jqlibdir = os.path.join(mddir, "jq")
datadir = os.path.join(jqlibdir, "tests", "data")
janaffile = os.path.join(datadir, "janaf_pod.json")

class TestJqCommand(unittest.TestCase):

    def setUp(self):
        self.jqc = jq.JqCommand()

    def test_version(self):
        self.assertGreater(len(self.jqc.version), 1)
        self.assertGreater(len(jq.get_version()), 1)

    def test_library(self):
        self.assertIsNone(self.jqc.library)
        self.jqc.library = jqlibdir
        self.assertEqual(self.jqc.library, jqlibdir)

    def test_form_argopts(self):
        opts = self.jqc.form_argopts(
            OrderedDict([("id", "ark:ID"), ("goober", [ 1, 2 ])]))
        self.assertEqual(opts,
            ['--argjson', 'id', '"ark:ID"', '--argjson', 'goober', '[1, 2]'])

    def test_bad_form_argopts(self):
        with self.assertRaises(ValueError):
            opts = self.jqc.form_argopts(["id", "ark:ID", "goober", [ 1, 2 ]])

    def test_form_cmd(self):
        self.assertEqual(self.jqc.form_cmd(".goober | [.]"),
                          ['jq', '.goober | [.]'])
        self.jqc.library = jqlibdir
        self.assertEqual(self.jqc.form_cmd(".goober | [.]",
                          OrderedDict([("id", "ark:ID"), ("goober", [ 1, 2 ])])),
                          ['jq', '-L'+jqlibdir,
                           '--argjson', 'id', '"ark:ID"', '--argjson', 'goober',
                           '[1, 2]', '.goober | [.]'])
        self.assertEqual(self.jqc.form_cmd(".goober | [.]",
                          OrderedDict([("id", "ark:ID"), ("goober", [ 1, 2 ])]),
                                              'data.json'),
                          ['jq', '-L'+jqlibdir,
                           '--argjson', 'id', '"ark:ID"', '--argjson', 'goober',
                           '[1, 2]', '.goober | [.]', 'data.json'])
        
    def test_format_cmd(self):
        cmd = ['jq', '-L', 'jqlib', 'import "pod2nerdm" as nerdm; .accessLevel',
               'janaf_pod.json']
        self.assertEqual(self.jqc._format_cmd(cmd),
     "jq -L jqlib 'import \"pod2nerdm\" as nerdm; .accessLevel' janaf_pod.json")
        
    def test_process_file(self):
        out = self.jqc.process_file(".accessLevel", janaffile)
        self.assertEqual(out, 'public')
        
    def test_process_file_w_args(self):
        out = self.jqc.process_file(".accessLevel", janaffile,
                                {"id": "ID", "goob": "gurn"})
        self.assertEqual(out, 'public')

    def test_process_data(self):
        data = {"id": "ID", "goob": "gurn"}
        out = self.jqc.process_data("[.goob]", json.dumps(data))
        self.assertEqual(out, ["gurn"])

class TestJq(unittest.TestCase):

    def test_ctr(self):
        jqt = jq.Jq("[.goob]")
        self.assertEqual(jqt.filter, "[.goob]")
        self.assertIsNone(jqt.cmd.library)
        self.assertEqual(jqt.args, {})
        
        jqt = jq.Jq("[.goob]", jqlibdir)
        self.assertEqual(jqt.filter, "[.goob]")
        self.assertEqual(jqt.cmd.library, jqlibdir)
        self.assertEqual(jqt.args, {})
        
        jqt = jq.Jq("[.goob]", jqlibdir, ["gurn"])
        self.assertEqual(jqt.filter, 'import "gurn" as gurn; [.goob]')
        self.assertEqual(jqt.cmd.library, jqlibdir)
        self.assertEqual(jqt.args, {})

        with self.assertRaises(ValueError):
            jqt = jq.Jq("[.goob]", modules=["gurn"])
        with self.assertRaises(ValueError):
            jqt = jq.Jq("[.goob]", args=["gurn"])
        
        jqt = jq.Jq("[.goob]", jqlibdir, ["gurn", "pod2nerdm:nerdm"])
        self.assertEqual(jqt.filter,
                  'import "gurn" as gurn; import "pod2nerdm" as nerdm; [.goob]')
        self.assertEqual(jqt.cmd.library, jqlibdir)
        self.assertEqual(jqt.args, {})
        
        jqt = jq.Jq("[.goob]", jqlibdir, ["gurn"],
                    {"id": "ark:ID", "goob": "gurn"})
        self.assertEqual(jqt.filter, 'import "gurn" as gurn; [.goob]')
        self.assertEqual(jqt.cmd.library, jqlibdir)
        self.assertEqual(jqt.args, {"id": "ark:ID", "goob": "gurn"})
        
        jqt = jq.Jq("[.goob]", args={"id": "ark:ID", "goob": "gurn"})
        self.assertEqual(jqt.filter, '[.goob]')
        self.assertIsNone(jqt.cmd.library)
        self.assertEqual(jqt.args, {"id": "ark:ID", "goob": "gurn"})

    def test_transform(self):
        jqt = jq.Jq("[.goob]")
        data = {"id": "ID", "goob": "gurn"}
        out = jqt.transform(json.dumps(data))
        self.assertEqual(out, ["gurn"])

    def test_transform_w_args(self):
        data = {"id": "ID", "goob": "gurn"}
        jqt = jq.Jq("[$goob]", args=data)
        out = jqt.transform(json.dumps({}))
        self.assertEqual(out, ["gurn"])

        out = jqt.transform(json.dumps({}), {"goob": "hank"})
        self.assertEqual(out, ["hank"])

    def test_transform_file(self):
        jqt = jq.Jq(".accessLevel")
        out = jqt.transform_file(janaffile)
        self.assertEqual(out, 'public')

    def test_transform_file_w_mod(self):
        jqt = jq.Jq('nerdm::podds2resource | .["@id"]',
                    jqlibdir, ["pod2nerdm:nerdm"],
                    {"id": "ID", "goob": "gurn"})
        out = jqt.transform_file(janaffile)
        self.assertEqual(out, 'ID')
        
        out = jqt.transform_file(janaffile, {"id": "ark:ID"})
        self.assertEqual(out, 'ark:ID')
        
        
        
if __name__ == '__main__':
    unittest.main()
