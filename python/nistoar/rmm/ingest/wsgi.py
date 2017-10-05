"""
A WSGI web service for ingesting new records into the RMM.

This module provides the most basic implementation of a WSGI application 
necessary for integration into a WSGI server.  It should be replaced with 
a framework-based implementation if any further capabilities are needed.
"""

import os, sys, logging, json, cgi, re
from urlparse import urlsplit, urlunsplit
from wsgiref.headers import Headers

from ..mongo.nerdm import (NERDmLoader, LoadLog,
                           RecordIngestError, JSONEncodingError)
from ..exceptions import ConfigurationException

log = logging.getLogger("RMM").getChild("ingest")

DEF_BASE_PATH = "/"

class RMMRecordIngestApp(object):

    def __init__(self, config):
        self.base_path = config.get('base_path', DEF_BASE_PATH)
        self.dburl = config.get('db_url')
        if not self.dburl:
            self.log.error("Config param not set: db_url")
            raise ConfigurationException("Config param not set: db_url")

        if 'db_authn' in config:
            acfg = config['db_authn']
            if 'pass' in acfg and not acfg.get('pass'):
                raise ConfigurationException("Config: Missing password value "+
                                             "in db_authn.pass")
            if not acfg.get('user'):
                raise ConfigurationException("Config param not set: "+
                                             "db_authn.user")
            authn = acfg['user']
            if 'pass' in acfg:
                authn += ':' + acfg['pass']
                
            url = list(urlsplit(self.dburl))
            url[1] = "{0}@{1}".format(authn, url[1])
            self.dburl = urlunsplit(url)

        self.schemadir = config.get('nerdm_schema_dir',
                                    os.path.join('etc', 'schemas'))
        if not os.path.isabs(self.schemadir):
            if not os.path.exists(oar_home):
                raise RuntimeError("OAR home directory does not exists: " +
                                   oar_home)
            self.schemadir = os.path.join(oar_home, self.schemadir)
        if not os.path.exists(self.schemadir):
            raise RuntimeError("Schema directory doesn't exists: " +
                               self.schemadir)

        self._loaders = {}
        self._loaders['nerdm'] = NERDmLoader(self.dburl, self.schemadir,
                                             onupdate='quiet')
        
        self._auth = config.get('auth_key')

    def handle_request(self, env, start_resp):
        handler = Handler(self._loaders, env, start_resp, self._auth)
        return handler.handle()

    def __call__(self, env, start_resp):
        return self.handle_request(env, start_resp)

app = RMMRecordIngestApp

class Handler(object):

    def __init__(self, loaders, wsgienv, start_resp, authkey=None):
        self._env = wsgienv
        self._start = start_resp
        self._meth = wsgienv.get('REQUEST_METHOD', 'GET')
        self._hdr = Headers([])
        self._code = 0
        self._msg = "unknown status"
        self._auth = authkey

        self._loaders = loaders

    def send_error(self, code, message):
        status = "{0} {1}".format(str(code), message)
        self._start(status, [], sys.exc_info())
        return []

    def add_header(self, name, value):
        self._hdr.add_header(name, value)

    def set_response(self, code, message):
        self._code = 200
        self._msg = message

    def end_headers(self):
        status = "{0} {1}".format(str(self._code), self._msg)
        self._start(status, self._hdr.items())

    def handle(self):
        meth_handler = 'do_'+self._meth

        path = self._env.get('PATH_INFO', '/')[1:]
        params = cgi.parse_qs(self._env.get('QUERY_STRING', ''))
        if not self.authorize(params.get('auth',[])):
            return self.send_error(401, "Not authorized")

        if hasattr(self, meth_handler):
            return getattr(self, meth_handler)(path)
        else:
            return self.send_error(403, self._meth +
                                   " not supported on this resource")

    def authorize(self, auths):
        if self._auth:
            # match the last value provided
            return len(auths) > 0 and self._auth == auths[-1]  
        if len(auths) > 0:
            log.warn("Authorization key provided, but none has been configured")
        return len(auths) == 0

    def do_GET(self, path):
        path = path.strip('/')
        if not path:
            try:
                out = json.dumps(self._loaders.keys()) + '\n'
            except Exception, ex:
                log.exception("Internal error: "+str(ex))
                return self.send_error(500, "Internal error")

            self.set_response(200, "Supported Record Types")
            self.add_header('Content-Type', 'application/json')
            self.end_headers()
            return [out]
        elif path in self._loaders:
            self.set_response(200, "Service is ready")
            self.add_header('Content-Type', 'application/json')
            self.end_headers()
            return ["Service ready\n"]
        else:
            return self.send_error(404, "resource does not exist")
            
    def do_POST(self, path):
        path = path.strip('/')
        steps = path.split('/')
        if len(steps) == 0:
            return self.send_error(405, "POST not supported on this resource")
        elif len(steps) == 1:
            if steps[0] == 'nerdm':
                self.post_nerdm_record()
            else:
                return self.send_error(403, "new records are not allowed for " +
                                       "submission to this resource")
        else:
            return self.send_error(404, "resource does not exist")

    def post_nerdm_record(self):
        """
        Accept a NERDm record for ingest into the RMM
        """
        loader = self._loaders['nerdm']

        try:
            clen = int(self._env['CONTENT_LENGTH'])
        except KeyError, ex:
            log.exception("Content-Length not provided for input record")
            return self.send_error(411, "Content-Length is required")
        except ValueError, ex:
            log.exception("Failed to parse input JSON record: "+str(e))
            return self.send_error(400, "Content-Length is not an integer")

        try:
            bodyin = self._env['wsgi.input']
            doc = bodyin.read(clen)
            rec = json.loads(doc)
        except Exception, ex:
            log.exception("Failed to parse input JSON record: "+str(ex))
            log.warn("Input document starts...\n{0}...({1}/{2} chars)"
                     .format(doc[:75], len(doc), clen))
            return self.send_error(400,
                                   "Failed to load input record (bad format?): "+
                                   str(ex))

        try:
            res = loader.load(rec, validate=True)
            if res.failure_count > 0:
                res = res.failures()[0]
                logmsg = "Failed to load record with "+str(res.key)
                for e in res.errs:
                    logmsg += "\n  "+str(e)
                log.error(logmsg)
                self.set_response(400, "Input record is not valid")
                self.add_header('Content-Type', 'application/json')
                self.end_headers()
                return [ json.dumps([str(e) for e in res.errs]) + '\n' ]

        except RecordIngestError, ex:
            log.exception("Failed to load posted record: "+str(ex))
            self.set_response(400, "Input record is not valid (missing @id)")
            self.add_header('Content-Type', 'application/json')
            self.end_headers()
            return [ json.dumps([ "Record is missing @id property" ]) + '\n' ]

        except Exception, ex:
            log.exception("Loading error: "+str(ex))
            return self.send_error(500, "Load failure due to internal error")
            
        self.set_response(200, "Record accepted")
        self.end_headers()
        return []
        
        

def _get_oar_home():
    home = os.environ.get('OAR_HOME')
    if home:
        return home

    home = __file__
    try:
        for i in range(5):
            # up from python*/nistoar/rmm/ingest 
            home = os.path.dirname(home)
        if not home:
            return home
        if not os.path.exists(os.path.join(home, "etc")):
            home = os.path.dirname(home)
        return home
    except OSError, ex:
        log.exception("OSError while looking for OAR_HOME: "+str(e))
        return None

oar_home = _get_oar_home()
if not oar_home:
    log.error("Unable to determine OAR_HOME dir (set OAR_HOME env. var.)")
