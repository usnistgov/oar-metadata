import os, sys, pdb, shutil, logging, json, re, importlib
import unittest as test
from pathlib import Path
from nistoar.testing import *

import nistoar.base.config as config

testdir = Path(__file__).resolve().parents[0]
datadir = str(testdir / "data")
basedir = testdir.parents[3]
schemadir = basedir / 'model'
tmpd = None

def setUpModule():
    global tmpd
    ensure_tmpdir()
    tmpd = tmpdir()

def tearDownModule():
    rmtmpdir()

class TestConfig(test.TestCase):

    def test_load_from_service(self):
        with self.assertRaises(NotImplementedError):
            config.load_from_service("goob/dev")

    def test_lookup_config_server(self):
        with self.assertRaises(NotImplementedError):
            config.lookup_config_server(8888)

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

        cfgfile = "file://" + cfgfile
        cfg = config.resolve_configuration(cfgfile)
        self.assertEqual(cfg['working_dir'], "/pdr/work")

        cfgfile = "http://goober.net/gurn.log"
        with self.assertRaises(NotImplementedError):
            cfg = config.resolve_configuration(cfgfile)

    def test_merge_config(self):
        app = {
            "foo": "bar",
            "goob": { "gurn": "cranston", "hank": "aaron" },
            "zub": "dub",
            "tell": { "a": 1 }
        }
        defc = {
            "black": "blue",
            "goob": { "gurn": "gomer", "patty": "duke" },
            "tell": 1,
            "zub": { "dub": 2}
        }
        out = config.merge_config(app, defc)
        self.assertEqual(out['foo'], 'bar')
        self.assertEqual(out['goob'], { 'gurn': 'cranston', "hank": "aaron",
                                        'patty': "duke" })
        self.assertEqual(out['zub'], 'dub')
        self.assertEqual(out['tell'], {"a": 1})

    def test_hget_jp(self):
        with open(schemadir/'nerdm-schema.json') as fd:
            schema = json.load(fd)

        self.assertEqual(config.hget_jp(schema, "definitions.Resource.properties.title.title"), "Title")
        self.assertEqual(config.hget_jp(schema, "definitions.ResourceReference.allOf[1].required"), ["title"])

        self.assertIsNone(config.hget_jp(schema, "definitions.goober.title"))
        self.assertEqual(config.hget_jp(schema, "definitions.goober.title", "Dr."), "Dr.")
        with self.assertRaises(KeyError):
            config.hget_jp(schema, "definitions.goober.title", config.RAISE)

        with self.assertRaises(KeyError):
            config.hget_jp(schema, "definitions.ResourceReference.allOf[23].required", config.RAISE)

        # make sure results are not copies of the original
        ressch = config.hget_jp(schema, "definitions.Resource")
        self.assertIn("required", ressch)
        del ressch['required']
        with self.assertRaises(KeyError):
            config.hget_jp(schema, "definitions.Resource.required", config.RAISE)


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
            'logfile': logfile,
            'loglevel': 'DEBUG'
        }

        self.logfile = os.path.join(tmpd, logfile)
        self.assertFalse(os.path.exists(self.logfile))

        config.configure_log(config=cfg)
        self.assertEqual(config.global_logdir, tmpd)
        self.assertEqual(config.global_logfile, self.logfile)

        self.rootlog.warning('Oops')
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
        self.rootlog.warning('Oops')
        self.assertTrue(os.path.exists(self.logfile))
        
class TestConfigService(test.TestCase):
    
    def test_ctor(self):
        srvc = config.ConfigService("https://config.org/oar/", "dev")
        self.assertEqual(srvc._base, "https://config.org/oar/")
        self.assertEqual(srvc._prof, "dev")

        srvc = config.ConfigService("https://config.org/oar")
        self.assertEqual(srvc._base, "https://config.org/oar/")
        self.assertIsNone(srvc._prof)

        srvc = config.ConfigService("https://config.org")
        self.assertEqual(srvc._base, "https://config.org/")
        self.assertIsNone(srvc._prof)

    def test_bad_url(self):
        with self.assertRaises(config.ConfigurationException):
            srvc = config.ConfigService("config.org")

        with self.assertRaises(config.ConfigurationException):
            srvc = config.ConfigService("https://")

    def test_url_for(self):
        srvc = config.ConfigService("https://config.org/oar/", "dev")
        self.assertEqual(srvc.url_for("goob"), "https://config.org/oar/goob/dev")
        self.assertEqual(srvc.url_for("goob", "dumb"),
                         "https://config.org/oar/goob/dumb")

    def test_from_env(self):
        try:
            if 'OAR_CONFIG_SERVICE' in os.environ:
                del os.environ['OAR_CONFIG_SERVICE']
            self.assertIsNone(config.ConfigService.from_env())
            
            os.environ['OAR_CONFIG_SERVICE'] = "https://config.org/oar/"
            srvc = config.ConfigService.from_env()
            self.assertEqual(srvc._base, "https://config.org/oar/")
            self.assertIsNone(srvc._prof)
            
            os.environ['OAR_CONFIG_ENV'] = "test"
            srvc = config.ConfigService.from_env()
            self.assertEqual(srvc._base, "https://config.org/oar/")
            self.assertEqual(srvc._prof, "test")
        finally:
            if 'OAR_CONFIG_SERVICE' in os.environ:
                del os.environ['OAR_CONFIG_SERVICE']
            if 'OAR_CONFIG_ENV' in os.environ:
                del os.environ['OAR_CONFIG_ENV']

    def test_cvtarrays(self):
        d = {
            "a": {
                "[1]": "ia",
                "[5]": {
                    "ib": {
                        "[0]": "ibb",
                        "[3]": "ibe"
                    },
                    "[0]": "0a",
                },
                "[0]": "ic",
                "[3]": "id"
            }
        }
        out = {
            "a": [ "ic", "ia", "id", {
                "ib": [ "ibb", "ibe" ],
                "[0]": "0a"
            }]
        }
        self.assertEqual(config.ConfigService._cvtarrays(d), out)

    def test_inflate(self):
        d = {
            "working_dir": "/data/pdr",
            "store_dir":   "/data/store",
            'notifier.alerts[1].type': "preserve.success",
            'notifier.alerts[1].targets[0]': "dev",
            'notifier.alerts[0].type': "preserve.failure",
            'notifier.alerts[0].targets[0]': "oarop",
            'sip_type.midas.common.review_dir': "/data/review",
            'sip_type.midas.common.upload_dir': "/data/upload",
        }
        out = {
            "working_dir": "/data/pdr",
            "store_dir":   "/data/store",
            "notifier": {
                "alerts": [{
                    "type": "preserve.failure",
                    "targets": [ "oarop" ]
                }, {
                    "type": "preserve.success",
                    "targets": [ "dev" ]
                }]
            },
            "sip_type": {
                "midas": {
                    "common": {
                        "review_dir": "/data/review",
                        "upload_dir": "/data/upload"
                    }
                }
            }
        }
        self.assertEqual(config.ConfigService._inflate(d), out)

    def test_deep_update(self):
        d = {
            "a": {
                "a.b": 1,
                "a.c": 2,
                "a.d": {
                    "ad.a": 4,
                    "ad.b": 5
                }
            }
        }
        u = {
            "a": {
                "a.c": 20,
                "a.d": {
                    "ad.b": 50,
                    "ad.c": 60
                }
            }
        }
        out = {
            "a": {
                "a.b": 1,
                "a.c": 20,
                "a.d": {
                    "ad.a": 4,
                    "ad.b": 50,
                    "ad.c": 60
                }
            }
        }
        n = config.ConfigService._deep_update(d, u)
        self.assertEqual(n, out)
        self.assertIs(n, d)

    def test_extract1(self):
        data = \
{
    "propertySources": [
        {
            "source": {
                "RMMAPI": "https://goob/rmm/",
                "LANDING": "https://localhost/rmm/", 
                "SDPAPI": "https://localhost/sdp/", 
            },
            "name": "classpath:config/oar-uri/oar-uri.yml"
        },
        {
            "source": {
                "RMMAPI": "https://localhost/rmm/", 
                "SDPAPI": "https://localhost/sdp/", 
            }, 
            "hail": "fire"
        }
    ], 
    "version": None, 
    "name": "oaruri", 
    "profiles": [
        "local"
    ], 
    "label": None
}
        out = {
            "RMMAPI": "https://goob/rmm/",
            "SDPAPI": "https://localhost/sdp/", 
            "LANDING": "https://localhost/rmm/", 
        }

        self.assertEqual(config.ConfigService.extract(data), out)

    def test_extract2(self):
        data = \
{
    "propertySources": [
        {
            "source": {
                "store_dir":   "/var/data/store",
                'sip_type.midas.common.review_dir': "/var/data/review",
                'notifier.alerts[1].type': "preserve.win",
                'notifier.alerts[1].targets[3]': "oarop",
            },
            "name": "classpath:config/oar-uri/oar-uri.yml"
        },
        {
            "source": {
                "working_dir": "/data/pdr",
                "store_dir":   "/data/store",
                'notifier.alerts[1].type': "preserve.success",
                'notifier.alerts[1].targets[0]': "dev",
                'notifier.alerts[0].type': "preserve.failure",
                'notifier.alerts[0].targets[0]': "oarop",
                'sip_type.midas.common.review_dir': "/data/review",
                'sip_type.midas.common.upload_dir': "/data/upload",
            }, 
            "name": "classpath:config/oar-uri/oar-uri-dev.yml"
        }
    ], 
    "version": None, 
    "name": "oaruri", 
    "profiles": [
        "local"
    ], 
    "label": None
}

        out = {
            "working_dir": "/data/pdr",
            "store_dir":   "/var/data/store",
            "notifier": {
                "alerts": [{
                    "type": "preserve.failure",
                    "targets": [ "oarop" ]
                }, {
                    "type": "preserve.win",
                    "targets": [ "dev", "oarop" ]
                }]
            },
            "sip_type": {
                "midas": {
                    "common": {
                        "review_dir": "/var/data/review",
                        "upload_dir": "/data/upload"
                    }
                }
            }
        }
        self.assertEqual(config.ConfigService.extract(data), out)

    def test_extract3(self):
        data = \
{
    "propertySources": [
        {
            "source": {
                "store_dir":   "/var/data/store",
                'sip_type.midas.common.review_dir': "/var/data/review",
                'notifier.alerts[1].type': "preserve.win",
                'notifier.alerts[1].targets[3]': "oarop",
            },
            "name": "classpath:config/oar-uri/oar-uri.yml"
        },
        {
            "source": {
                "working_dir": "/data/pdr",
                "store_dir":   "/data/store",
                'notifier.alerts[1].type': "preserve.success",
                'notifier.alerts[1].targets[0]': "dev",
                'notifier.alerts[0].type': "preserve.failure",
                'notifier.alerts[0].targets[0]': "oarop",
                'sip_type.midas.common.review_dir': "/data/review",
                'sip_type.midas.common.upload_dir': "/data/upload",
            }, 
            "name": "classpath:config/oar-uri/oar-uri-dev.yml"
        }
    ], 
    "version": None, 
    "name": "oaruri", 
    "profiles": [
        "local"
    ], 
    "label": None
}

        out = { "working_dir": "/data/pdr",
                "store_dir":   "/var/data/store",
                'notifier.alerts[1].type': "preserve.win",
                'notifier.alerts[1].targets[0]': "dev",
                'notifier.alerts[1].targets[3]': "oarop",
                'notifier.alerts[0].type': "preserve.failure",
                'notifier.alerts[0].targets[0]': "oarop",
                'sip_type.midas.common.review_dir': "/var/data/review",
                'sip_type.midas.common.upload_dir': "/data/upload"  }

        self.assertEqual(config.ConfigService.extract(data, flat=True), out)
        
    @test.skipIf("noreload" in os.environ.get("OAR_TEST_INCLUDE", ""),
                 "Avoid reloading modules when part of larger TestSuite")
    def test_defservice_reload(self):
        config.service = None
        self.assertNotIn('OAR_CONFIG_SERVICE', os.environ)
        self.assertIsNone(config.service)
        try:
            os.environ['OAR_CONFIG_SERVICE'] = "https://config.org/oar/"
            importlib.reload(config)
            self.assertIsNotNone(config.service)
            self.assertEqual(config.service._base, "https://config.org/oar/")
            self.assertIsNone(config.service._prof)
        finally:
            if 'OAR_CONFIG_SERVICE' in os.environ:
                del os.environ['OAR_CONFIG_SERVICE']
            config.service = None

    def test_defservice(self):
        self.assertNotIn('OAR_CONFIG_SERVICE', os.environ)
        self.assertIsNone(config.service)
        try:
            os.environ['OAR_CONFIG_SERVICE'] = "https://config.org/oar/"
            config.service = config.ConfigService.from_env()
            self.assertIsNotNone(config.service)
            self.assertEqual(config.service._base, "https://config.org/oar/")
            self.assertIsNone(config.service._prof)
        finally:
            if 'OAR_CONFIG_SERVICE' in os.environ:
                del os.environ['OAR_CONFIG_SERVICE']
            config.service = None
            


if __name__ == '__main__':
    test.main()
