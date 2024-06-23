import json, os, sys, re, hashlib, json, logging, random
from datetime import datetime
from wsgiref.headers import Headers
from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from urllib.parse import parse_qs

JSONAPI_MT = "application/vnd.api+json"

try:
    import uwsgi
except ImportError:
    # print("Warning: running midas-uwsgi in simulate mode", file=sys.stderr)
    class uwsgi_mod(object):
        def __init__(self):
            self.opt={}
            self.started_on = None
    uwsgi=uwsgi_mod()

class SimIDRepo(object):
    def __init__(self):
        self.ids = OrderedDict()

    def add_id(self, id, md):
        if id in self.ids:
            raise ValueError("ID already exists: "+id)
        md = deepcopy(md)

        if id in md:
            del md['doi']

        ev = md.get('event', 'draft')
        if ev == 'draft':
            md['state'] = "draft"
        elif ev == "publish":
            md['state'] = "findable"
        elif ev == "register" or ev == "hide":
            md['state'] = "registered"
        if 'event' in md:
            del md['event']

        self.ids[id] = md
        return self.describe(id)

    def update_id(self, id, md):
        if id not in self.ids:
            raise ValueError("ID not found: "+id)
        md = deepcopy(md)

        if 'event' in md:
            if md['event'] == "publish":
                md['state'] = "findable"
            elif md['event'] == "register" or md['event'] == "hide":
                md['state'] = "registered"
            del md['event']

        self.ids[id].update(md)
        return self.describe(id)

    def describe(self, id):
        if id not in self.ids:
            raise ValueError("ID not found: "+id)

        out = deepcopy(self.ids[id])
        out['doi'] = id
        out['prefix'] = id.split('/', 1)[0]
        if 'state' not in out:
            out['state'] = "draft"

        return out

    def delete(self, id):
        if id not in self.ids:
            raise ValueError("ID not found: "+id)

        if 'state' in self.ids[id] and self.ids[id]['state'] != "draft":
            raise ValueError("Record not in draft state")

        del self.ids[id]

class SimIDService(object):

    def __init__(self, basepath, prefixes=[]):
        if not basepath.startswith('/'):
            basepath = '/'+basepath
        self.basepath = basepath
        self.prefs = prefixes
        self.repo = SimIDRepo()

    def handle_request(self, env, start_resp):
        handler = SimHandler(self.repo, self.basepath, self.prefs, env, start_resp)
        return handler.handle()

    def __call__(self, env, start_resp):
        return self.handle_request(env, start_resp)

class SimHandler(object):

    def __init__(self, repo, basepath, prefixes, wsgienv, start_resp):
        self.repo = repo
        self.basepath = basepath
        self.prefs = prefixes
        self._env = wsgienv
        self._start = start_resp
        self._meth = wsgienv.get("REQUEST_METHOD", "GET")

        self._hdr = Headers([])
        self._code = 0
        self._msg = "unknown state"

    def send_error(self, code, message, errtitle=None, errdesc={}, tellexc=False):
        edata = None
        if errdesc and not errtitle:
            errtitle=message
        if errtitle:
            edata = { "errors": [ { "title": errtitle, "status": code } ] }
            if errdesc:
                edata['errors'][0].update(errdesc)

        if edata:
            edata = json.dumps(edata)
            self.add_header("Content-type", JSONAPI_MT)
            self.add_header("Content-length", len(edata))
        status = "{0} {1}".format(str(code), message)
        excinfo = None
        if tellexc:
            excinfo = sys.exc_info()
            if excinfo == (None, None, None):
                excinfo = None
        self._start(status, self._hdr.items(), excinfo)

        if edata:
            return [ edata.encode() ]
        return []

    def add_header(self, name, value):
        self._hdr.add_header(name, str(value))

    def set_response(self, code, message):
        self._code = code
        self._msg = message

    def end_headers(self):
        status = "{0} {1}".format(str(self._code), self._msg)
        self._start(status, self._hdr.items())

    def handle(self):
        meth_handler = 'do_'+self._meth

        path = self._env.get('PATH_INFO', '/')
        params = parse_qs(self._env.get('QUERY_STRING', ''))

        if path.startswith(self.basepath):
            path = path[len(self.basepath):]
        else:
            return self.send_error(404, "Unsupported service")

        if hasattr(self, meth_handler):
            return getattr(self, meth_handler)(path, params)
        else:
            return self.send_error(405, self._meth + " not supported on this resource")

    _envelope = OrderedDict([("data", OrderedDict([("type", "dois")]))])
    def _new_resp(self, id=None, attrs=None):
        out = deepcopy(self._envelope)
        if id:
            out['data']['id'] = id
        if attrs is not None:
            out['data']['attributes'] = attrs
        return out

    def do_GET(self, path, params=None):
        if path:
            path = path.strip('/')
        else:
            return self.send_error(200, "Ready")

        if 'HTTP_ACCEPT' in self._env and self._env['HTTP_ACCEPT'] != JSONAPI_MT:
            return self.send_error(406, "Not Acceptable", "Unsupported Accept value",
                                   {"detail": self._env['HTTP_ACCEPT']})

        try:
            out = self._new_resp(path, self.repo.describe(path))
        except ValueError as ex:
            return self.send_error(404, str(ex), "ID not found",
                                   errdesc={"detail": "path"})

        try:
            out = json.dumps(out)
            self.set_response(200, "Found")
            self.add_header("Content-type", JSONAPI_MT)
            self.add_header("Content-length", len(out))
            self.end_headers()
            return [out.encode()]
        except (ValueError, TypeError) as ex:
            return self.send_error(500, "JSON encoding error",
                                   errdesc={"detail": str(ex)}, tellexc=True)

    def do_HEAD(self, path, params=None):
        if path:
            path = path.strip('/')
        else:
            return self.send_error(200, "Ready")

        if path in self.repo.ids:
            return self.send_error(200, "ID Found")
        else: 
            return self.send_error(404, "ID Not Found")

    def do_POST(self, path, params=None):
        if path:
            path = path.strip('/')

        if path:
            return self.send_error(405, "Cannot POST to ID", errdesc={"detail": path})

        if 'HTTP_ACCEPT' in self._env and self._env['HTTP_ACCEPT'] != JSONAPI_MT:
            return self.send_error(406, "Not Acceptable", "Unsupported Accept value",
                                   {"detail": "self._env['HTTP_ACCEPT']"})
        if 'CONTENT_TYPE' in self._env and self._env['CONTENT_TYPE'] != JSONAPI_MT:
            return self.send_error(415, "Wrong Input Type",
                                   "Unsupported input content type",
                                   {"detail": self._env['CONTENT_TYPE']})

        try:
            bodyin = self._env['wsgi.input'].read().decode('utf-8')
            doc = json.loads(bodyin, object_pairs_hook=OrderedDict)
        except (ValueError, TypeError) as ex:
            return self.send_error(400, "Not JSON", "Failed to parse input as JSON",
                                   {"detail": str(ex)})
        
        doi = None
        event = None
        try:
            if doc['data']['type'] != "dois":
                return self.send_error(400, "Wrong input data type",
                                       {"detail": doc['data']['type'],
                                        "source": {"pointer": "/data/type"}})

            prefix = None
            if 'doi' in doc['data']['attributes']:
                doi = doc['data']['attributes']['doi']
                parts = doi.split('/', 1)
                if len(parts) < 2:
                    return self.send_error(400,"Bad doi syntax", errdesc={"detail": doi})
                                           
                prefix = parts[0]
            elif 'prefix' in doc['data']['attributes']:
                prefix = doc['data']['attributes']['prefix']
            if prefix and not doi:
                if 'suffix' in doc['data']['attributes']:
                    suffix = doc['data']['attributes']['suffix']
                else:
                    suffix = "rand"+str(random.randrange(10000,99999))
                doi = "%s/%s" % (prefix, suffix)

            if not doi:
                return self.send_error(400, "No prefix specified")

            if self.prefs and prefix not in self.prefs:
                return self.send_error(403, "Not Authorized for Prefix")

            event = doc['data']['attributes'].get('event')

        except KeyError as ex:
            return self.send_error(400, "Bad Input: Missing property",
                                   {"detail": str(ex)})
        state = "draft"
        errors = None
        if doi in self.repo.ids:
            state = self.repo.ids[doi]['state']
            out = self.repo.update_id(doi, doc['data']['attributes'])
            resp = {"code": 200, "message": "Updated"}
        else:
            out = self.repo.add_id(doi, doc['data']['attributes'])
            resp = {"code": 201, "message": "Created"}

        if (event == "publish" and state != "findable") or \
           (event == "register" and state != "registered"):
            missing = []
            for prop in "url titles publisher publicationYear creators types".split():
                if prop not in out or not out[prop]:
                    missing.append(prop)
                elif prop.endswith('s') and len(out[prop]) < 1:
                    missing.append(prop)
            if missing:
                self.repo.ids[doi]['state'] = state
                out['state'] = state
                errors = [{ 
                    "title": "Cannot publish due to missing metadata",
                    "detail": "Missing properties: "+str(missing)
                }]
                resp = {"code": 422, "message": "Unprocessable Entity"}

        try:
            out = self._new_resp(doi, out)
            if errors:
                out['errors'] = errors
            out = json.dumps(out)
            self.set_response(**resp)
            self.add_header("Content-type", JSONAPI_MT)
            self.add_header("Content-length", str(len(out)))
            self.end_headers()
            return [out.encode()]
        except (ValueError, TypeError) as ex:
            return self.send_error(500,"JSON encoding error", errdesc={"detail":str(ex)}, tellexc=True)

    def do_PUT(self, path, params=None):
        if path:
            path = path.strip('/')

        if not path:
            return self.send_error(405, "Cannot PUT without ID")

        if 'HTTP_ACCEPT' in self._env and self._env['HTTP_ACCEPT'] != JSONAPI_MT:
            return self.send_error(406, "Not Acceptable", "Unsupported Accept value",
                                   {"detail": self._env['HTTP_ACCEPT']})
        if 'CONTENT_TYPE' in self._env and self._env['CONTENT_TYPE'] != JSONAPI_MT:
            return self.send_error(415, "Wrong Input Type",
                                   "Unsupported input content type",
                                   {"detail": self._env['HTTP_ACCEPT']})

        parts = path.split('/', 1)
        if len(parts) < 2:
            return self.send_error(405, "Incomplete DOI", errdesc={"detail": path})
        if self.prefs and parts[0] not in self.prefs:
            return self.send_error(401, "Not authorized for prefix",
                                   errdesc={"detail": parts[0]})

        if path not in self.repo.ids:
            return self.send_error(404, "ID Not Found", errdesc={"detail": path})

        try:
            bodyin = self._env['wsgi.input'].read().decode('utf-8')
            doc = json.loads(bodyin, object_pairs_hook=OrderedDict)
        except (ValueError, TypeError) as ex:
            return self.send_error(400, "Not JSON", "Failed to parse input as JSON",
                                   {"detail": str(ex)})

        doi = path
        errors = None
        try:
            state = self.repo.ids[doi].get('state','draft')
            attrs = doc['data']['attributes']
            event = attrs.get('event')
            out = self.repo.update_id(path, attrs)
        except KeyError as ex:
            return self.send_error(400, "Bad Input: missing property",
                                   {"detail": str(ex)})
        except ValueError as ex:
            return self.send_error(404, "ID not found", errdesc={"detail": path})

        resp = {"code": 201, "message": "Updated"}
        if event == "publish" and state != "findable":
            missing = []
            for prop in "url titles publisher publicationYear creators types".split():
                if prop not in out or not out[prop]:
                    missing.append(prop)
                elif prop.endswith('s') and len(out[prop]) < 1:
                    missing.append(prop)
            if missing:
                self.repo.ids[doi]['state'] = state
                out['state'] = state
                errors = [{ 
                    "title": "Cannot publish due to missing metadata",
                    "detail": "Missing properties: "+str(missing)
                }]
                resp = {"code": 422, "message": "Unprocessable Entity"}

        try:
            out = self._new_resp(doi, out)
            if errors:
                out['errors'] = errors
            out = json.dumps(out)
            self.set_response(**resp)
            self.add_header("Content-type", JSONAPI_MT)
            self.add_header("Content-length", len(out))
            self.end_headers()
            return [out.encode()]
        except (ValueError, TypeError) as ex:
            return self.send_error(500, "JSON encoding error", tellexc=True)

    def do_DELETE(self, path, params=None):
        if path:
            path = path.strip('/')
        else:
            return self.send_error(405, "ID not deletable", errdesc={"detail": path})

        if path not in self.repo.ids:
            return self.send_error(404, "ID Not Found", errdesc={"detail": path})

        try:
            self.repo.delete(path)
        except ValueError as ex:
            return self.send_error(403, str(ex), errdesc={"detail": path})

        return self.send_error(204, "Deleted")

def get_uwsgi_opt(key, default=None):
    out = uwsgi.opt.get(key)
    if out is None:
        return default
    elif isinstance(out, bytes):
        return out.decode('utf-8')
    return out

prefixes = re.split(r'\s*,\s*', get_uwsgi_opt("prefixes", ""))
application = SimIDService("/dois", prefixes)
