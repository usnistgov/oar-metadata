"""
test logging server
"""
import os, sys, json, logging, subprocess, argparse, pdb, time, tempfile
import unittest as test
from pathlib import Path
from copy import deepcopy
import logging.config

from nistoar.base.logging import server as logsrvr

tmpdir = tempfile.TemporaryDirectory(prefix="_test_logger.")
testdir = Path(__file__).parents[0]

server_config = {
    "logdir": tmpdir.name,
    "logfile": "test.log",
    "loglevel": "DEBUG",
    "port": 9200
}

def setUpModule():
    with open(os.path.join(tmpdir.name, "config.json"), 'w') as fd:
        json.dump(server_config, fd, indent=2)

def tearDownModule():
    tmpdir.cleanup()

class TestLogServer(test.TestCase):

    def setUp(self):
        self.logfile = os.path.join(tmpdir.name, server_config['logfile'])

        cmd = "python -m nistoar.base.logging.server -c %s -T testLogServer" % \
              os.path.join(tmpdir.name, "config.json")
        self.serverproc = subprocess.Popen(cmd.split())
        time.sleep(0.2)

        clicfg = {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s %(name)s %(message)s"
                }
            },
            "handlers": {
                "socket": {
                    "class": "logging.handlers.SocketHandler",
                    "host": "localhost",
                    "port": 9200
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["socket"]
            }
        }
        logging.config.dictConfig(clicfg)

    def tearDown(self):
        status = self.serverproc.poll() 
        if status is None or status <= 0:
            self.serverproc.kill()
            self.serverproc.wait(5)

        if os.path.isfile(self.logfile):
            os.remove(self.logfile)

    def test_log(self):
        with open(self.logfile) as fd:
            # contains just the log opener record
            self.assertEqual(len([line for line in fd]), 1)
            
        logging.info("msg1")
        time.sleep(0.1)
        logging.debug("msg2")
        try:
            raise RuntimeError("test exception")
        except Exception as ex:
            logging.exception(ex)
        logging.warning("msg3")
        time.sleep(0.2)

        with open(self.logfile) as fd:
            self.assertEqual(len([line for line in fd]), 11)

    def no_test_stop(self):
        self.assertIsNone(self.serverproc.poll())

        cmd = "python -m nistoar.base.logging.server -c %s -k" % \
              os.path.join(tmpdir.name, "config.json")
        kproc = subprocess.Popen(cmd.split())
        try:
            kproc.wait(0.5)
        except Exception:
            pass

        self.assertIsNotNone(self.serverproc.poll())

                         
if __name__ == '__main__':
    test.main()




        
            
