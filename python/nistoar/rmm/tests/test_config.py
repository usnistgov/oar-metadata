import os, sys, pdb, shutil, logging, json
import unittest as test
from nistoar.tests import *

import nistoar.rmm.config as config

datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
tmpd = None

csurl = None
if os.environ.get('CONFIG_SERVER_URL'):
    csurl = os.environ.get('CONFIG_SERVER_URL')

def setUpModule():
    global tmpd
    ensure_tmpdir()
    tmpd = tmpdir()

def tearDownModule():
    rmtmpdir()

class TestConfig(test.TestCase):

    def test_load_from_file(self):
        cfgfile = os.path.join(datadir, "config.json")
        cfg = config.load_from_file(cfgfile)

        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg['working_dir'], "/pdr/work")

        cfgfile = os.path.join(datadir, "config.yaml")
        cfg = config.load_from_file(cfgfile)

        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg['working_dir'], "/pdr/work")

    def test_resolve_configuration(self):
        cfgfile = os.path.join(datadir, "config.json")
        cfg = config.resolve_configuration(cfgfile)
        self.assertEqual(cfg['working_dir'], "/pdr/work")

        cfg = config.resolve_configuration("config.json", "file://"+datadir)
        self.assertEqual(cfg['working_dir'], "/pdr/work")

        cfgfile = "file://" + cfgfile
        cfg = config.resolve_configuration(cfgfile)
        self.assertEqual(cfg['working_dir'], "/pdr/work")

    def test_extract_from_cs(self):
        cfgfile = os.path.join(datadir, "csconfig.json")
        with open(cfgfile) as fd:
            csdata = json.load(fd)

        cfg = config._extract_config_from_csdata(csdata)
        names = "oar.mongodb.port oar.mongodb.host oar.mongodb.database.name stuff name".split()
        for name in names:
            self.assertIn(name, cfg)
        self.assertEqual(len(cfg.keys()), len(names))
        self.assertEqual(cfg['oar.mongodb.database.name'], "TestDB")
        self.assertEqual(cfg['oar.mongodb.port'], "3333")
        self.assertEqual(cfg['name'], "Hank")
        self.assertEqual(cfg['stuff'], { "filter": "off" })

    @test.skipIf(not os.environ.get('CONFIG_SERVER_URL'),
                 "test config server not available")
    def test_resolve_configuration_fromcs(self):
        cfgfile = "http://goober.net/gurn.log"
        with self.assertRaises(NotImplementedError):
            cfg = config.resolve_configuration(cfgfile)


class TestLogConfig(test.TestCase):

    def resetLogfile(self):
        if config._log_handler:
            self.rootlog.removeHandler(config._log_handler)
        if self.logfile and os.path.exists(self.logfile):
            os.remove(self.logfile)
        self.logfile = None

    def setUp(self):
        if not hasattr(self, 'logfile'):
            self.logfile = None
        if not hasattr(self, 'rootlog'):
            self.rootlog = logging.getLogger()
        self.resetLogfile()

    def tearDown(self):
        self.resetLogfile()

    def test_from_config(self):
        logfile = "cfgd.log"
        cfg = {
            'logdir': tmpd,
            'logfile': logfile
        }

        self.logfile = os.path.join(tmpd, logfile)
        self.assertFalse(os.path.exists(self.logfile))

        config.configure_log(config=cfg)
        self.rootlog.warn('Oops')
        self.assertTrue(os.path.exists(self.logfile))
        with open(self.logfile) as fd:
            words = fd.read()
        self.assertIn("Oops", words)
        
    def test_abs(self):
        self.logfile = os.path.join(tmpd, "cfgfile.log")
        cfg = {
            'logfile': "goob.log"
        }

        self.assertFalse(os.path.exists(self.logfile))
        config.configure_log(logfile=self.logfile, config=cfg)
        self.rootlog.warn('Oops')
        self.assertTrue(os.path.exists(self.logfile))
        
        


if __name__ == '__main__':
    test.main()
