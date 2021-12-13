"""
A WSGI web service for ingesting new records into the RMM.

This module provides the most basic implementation of a WSGI application 
necessary for integration into a WSGI server.  It should be replaced with 
a framework-based implementation if any further capabilities are needed.
"""

import os, sys, logging, json, cgi, re, subprocess
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
            log.error("Config param not set: db_url")
            raise ConfigurationException("Config param not set: db_url")

        self.archdir = config.get('archive_dir')
        if not self.archdir:
            log.error("Config param not set: archive_dir")
            raise ConfigurationException("Config param not set: archive_dir")
        if not os.path.exists(self.archdir):
            raise RuntimeError("Requested archive directory, {0}, does not exist"
                               .format(self.archdir))
        cachedir = os.path.join(self.archdir, "_cache")
        if not os.path.exists(cachedir):
            try:
                os.mkdir(cachedir)
            except OSError as ex:
                raise RuntimeError("Failed to init archive cache: " + str(ex))

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
                                             onupdate='quiet', log=log)

        authkey = config.get('auth_key')
        authmeth= config.get('auth_method')
        if authmeth != 'header':
            authmeth = 'qparam'
        self._auth = (authmeth, authkey)
        if authkey:
            if authmeth == 'header':
                log.info("Authorization key is required of clients via HTTP Header")
            else:
                log.info("Authorization key is required of clients via query parameter")
        else:
            log.warning("No authorization key required of clients")

        # check for post-commit script request
        self._postexec = config.get('post_commit_exec')
        if self._postexec:
            try:
                self._postexec = _mkpostcomm(self._postexec, '{recid}', **config)
            except ValueError as ex:
                raise ConfigurationExcetpion("post_commit_exec contains bad formatting")

    def handle_request(self, env, start_resp):
        handler = Handler(self._loaders, env, start_resp,
                          self.archdir, self._auth, self._postexec)
        return handler.handle()

    def __call__(self, env, start_resp):
        return self.handle_request(env, start_resp)

app = RMMRecordIngestApp

class Handler(object):

    def __init__(self, loaders, wsgienv, start_resp, archdir, auth=None, postexec=None):
        self._env = wsgienv
        self._start = start_resp
        self._meth = wsgienv.get('REQUEST_METHOD', 'GET')
        self._hdr = Headers([])
        self._code = 0
        self._msg = "unknown status"
        self._auth = auth
        self._archdir = archdir
        self._postexec = postexec

        self._loaders = loaders

    def send_error(self, code, message):
        status = "{0} {1}".format(str(code), message)
        self._start(status, [], sys.exc_info())
        return []

    def add_header(self, name, value):
        self._hdr.add_header(name, value)

    def set_response(self, code, message):
        self._code = code
        self._msg = message

    def end_headers(self):
        status = "{0} {1}".format(str(self._code), self._msg)
        self._start(status, self._hdr.items())

    def handle(self):
        meth_handler = 'do_'+self._meth

        path = self._env.get('PATH_INFO', '/')[1:]
        if not self.authorize():
            return self.send_unauthorized()

        if hasattr(self, meth_handler):
            return getattr(self, meth_handler)(path)
        else:
            return self.send_error(403, self._meth +
                                   " not supported on this resource")

    def authorize(self):
        if self._auth[0] == 'header':
            return self.authorize_via_headertoken()
        else:
            return self.authorize_via_queryparam()

    def authorize_via_queryparam(self):
        params = cgi.parse_qs(self._env.get('QUERY_STRING', ''))
        auths = params.get('auth',[])
        if self._auth[1]:
            # match the last value provided
            return len(auths) > 0 and self._auth[1] == auths[-1]  
        if len(auths) > 0:
            log.warning("Authorization key provided, but none has been configured")
        return len(auths) == 0

    def authorize_via_headertoken(self):
        authhdr = self._env.get('HTTP_AUTHORIZATION', "")
        log.debug("Request HTTP_AUTHORIZATION: %s", authhdr)
        parts = authhdr.split()
        if self._auth[1]:
            return len(parts) > 1 and parts[0] == "Bearer" and \
                self._auth[1] == parts[1]
        if authhdr:
            log.warning("Authorization key provided, but none has been configured")
        return authhdr == ""

    def send_unauthorized(self):
        self.set_response(401, "Not authorized")
        if self._auth[0] == 'header':
            self.add_header('WWW-Authenticate', 'Bearer')
        self.end_headers()
        return []

    def do_GET(self, path):
        path = path.strip('/')
        if not path:
            try:
                out = json.dumps(list(self._loaders.keys())) + '\n'
            except Exception as ex:
                log.exception("Internal error: "+str(ex))
                return self.send_error(500, "Internal error")

            self.set_response(200, "Supported Record Types")
            self.add_header('Content-Type', 'application/json')
            self.add_header('Content-Length', str(len(out)))
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
                return self.ingest_nerdm_record()
            else:
                return self.send_error(403, "new records are not allowed for " +
                                       "submission to this resource")
        else:
            return self.send_error(404, "resource does not exist")

    def nerdm_archive_cache(self, rec):
        """
        cache a NERDm record into a local disk archive.  The cache is for 
        records that have been accepted but not ingested.  
        """
        try:
            arkid = rec['@id']
            outfile = os.path.join(self._archdir, '_cache',
                                   os.path.basename(arkid)+".json")
            with open(outfile, 'w') as fd:
                json.dump(rec, fd, indent=2)

            return arkid
        
        except KeyError as ex:
            # this shouldn't happen if the record was already validated
            raise RecordIngestError("submitted record is missing the @id "+
                                    "property")
        except ValueError as ex:
            # this shouldn't happen if the record was already validated
            raise RecordIngestError("submitted record is apparently invalid; "+
                                    "unable to submit")
        except OSError as ex:
            raise RuntimeError("Failed to cache record ({0}): {1}"
                               .format(arkid, str(ex)))

    def nerdm_archive_commit(self, arkid):
        """
        commit a previously cached record to the local disk archive.  This
        method is called after the record has been successfully ingested to
        the RMM's database.
        """
        outfile = os.path.join(self._archdir, '_cache',
                               os.path.basename(arkid)+".json")
        if not os.path.exists(outfile):
            raise RuntimeError("record to commit ({0}) not found in cache: {1}"
                               .format(arkid, outfile))
        try:
            os.rename(outfile,
                      os.path.join(self._archdir, os.path.basename(outfile)))
        except OSError as ex:
            raise RuntimeError("Failed to archvie record ({0}): {1}"
                               .format(arkid, str(ex)))
        

    def ingest_nerdm_record(self):
        """
        Accept a NERDm record for ingest into the RMM
        """
        loader = self._loaders['nerdm']

        try:
            clen = int(self._env['CONTENT_LENGTH'])
        except KeyError as ex:
            log.exception("Content-Length not provided for input record")
            return self.send_error(411, "Content-Length is required")
        except ValueError as ex:
            log.exception("Failed to parse input JSON record: "+str(e))
            return self.send_error(400, "Content-Length is not an integer")

        try:
            bodyin = self._env['wsgi.input']
            doc = bodyin.read(clen)
            rec = json.loads(doc)
        except Exception as ex:
            log.exception("Failed to parse input JSON record: "+str(ex))
            log.warning("Input document starts...\n{0}...\n...{1} ({2}/{3} chars)"
                        .format(doc[:75], doc[-20:], len(doc), clen))
            return self.send_error(400,
                                   "Failed to load input record (bad format?): "+
                                   str(ex))

        try:
            recid = self.nerdm_archive_cache(rec)
            
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

        except RecordIngestError as ex:
            log.exception("Failed to load posted record: "+str(ex))
            self.set_response(400, "Input record is not valid (missing @id)")
            self.add_header('Content-Type', 'application/json')
            self.end_headers()
            out = json.dumps([ "Record is missing @id property" ]) + '\n'
            return [ out.encode() ]

        except Exception as ex:
            log.exception("Loading error: "+str(ex))
            return self.send_error(500, "Load failure due to internal error")

        try:
            self.nerdm_archive_commit(recid)
        except Exception as ex:
            log.exception("Commit error: "+str(ex))

        if self._postexec:
            # run post-commit script
            try:
                self.nerdm_post_commit(recid)
            except Exception as ex:
                log.exception("Post-commit error: "+str(ex))

        log.info("Accepted record %s with @id=%s",
                 rec.get('ediid','?'), rec.get('@id','?'))
        self.set_response(200, "Record accepted")
        self.end_headers()
        return []

    def nerdm_post_commit(self, recid):
        """
        run an external executable for further processing after the record is commited to 
        the database (e.g. update an external index)
        """
        cmd = _mkpostcomm(self._postexec, recid, self._archdir)

        try:
            log.debug("Executing post-commit script:\n  %s", " ".join(cmd))
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = p.communicate()
            if p.returncode != 0:
                log.error("Error occurred while running post-commit script:\n"+(err or out))
        except OSError as ex:
            log.error("Failed to execute post-commit script:\n  %s\n%s", " ".join(cmd), str(ex))
        except Exception as ex:
            log.error("Unexpected failure executing post-commit script:\n  %s\n%s", " ".join(cmd), str(ex))

def _mkpostcomm(cmd, recid='{recid}', archdir=None, recfile=None, **vals):
    if not isinstance(cmd, (list, tuple)):
        cmd = cmd.split()

    vals['recid'] = recid
    if recfile is None:
        recfile = '{recfile}'
        if archdir:
            recfile = os.path.join(archdir, re.sub(r'^ark:/\d+/', '', recid)+".json")
    vals['recfile'] = recfile

    cmd = [arg.format(**vals) for arg in cmd]
    return cmd

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
    except OSError as ex:
        log.exception("OSError while looking for OAR_HOME: "+str(e))
        return None

oar_home = _get_oar_home()
if not oar_home:
    log.error("Unable to determine OAR_HOME dir (set OAR_HOME env. var.)")
