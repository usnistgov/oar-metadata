"""
module for interacting with DataCite services and DataCite DOIs.  

Note that this differs from the sibling module, resolving, in that the latter 
handles an type of DOI in a generic way.  This module specifically addresses 
DataCite DOIs with a focus on creating them and updating their metadata via 
DataCite services.  
"""
import re
from collections import OrderedDict, Mapping
from copy import deepcopy
from io import StringIO
import requests

from .utils import strip_DOI, is_DOI
from .resolving.common import (DOIResolverError, DOICommunicationError,
                               DOIClientException, DOIDoesNotExist)

STATE_NONEXISTENT = ""
STATE_DRAFT = "draft"
STATE_REGISTERED = "registered"
STATE_FINDABLE = "findable"
DOI_STATE = [ STATE_NONEXISTENT, STATE_DRAFT, STATE_REGISTERED, STATE_FINDABLE ]

_doi_pfx = re.compile("\d+\.\d+/")

_pub_doi_resolver_re = re.compile('^https?://(\w+\.)*doi\.org/')
_doi_re = re.compile('^\d{2,}\.\d+/')
JSONAPI_MT = "application/vnd.api+json"

class DataCiteDOIClient(object):
    """
    a client to the DataCite DOI REST service for managing DOIs
    """

    def __init__(self, endpoint, credentials, prefixes=[], resdata={}):
        """
        initialize the client.  
        :param str endpoint:    the base URL for the datacite service
        :param credentials:     the login credentials to use to authenticate to 
                                  the service.  Currently, this should be a 
                                  2-element tuple giving the username and password.
                                  If None, no credentials will be sent to the service
        :param list prefixes:   a list of strings representing the set of prefixes 
                                  the client is authorized to create DOIs under.  
                                  The first prefix is the default that will be assumed
                                  when requests do not specify one.  When a request,
                                  does include a prefix, it will be checked to ensure 
                                  it matches a prefix from this list or an exception
                                  is thrown.  If no prefixes are provided here, requests
                                  must include a prefix (no client-side prefix 
                                  verification, of course, is done in this case).  
        :param dict resdata:    an object attributes that should be submitted by 
                                  default when reserving a DOI
        """
        self._ep = endpoint
        if not self._ep.endswith('/'):
            self._ep += '/'
        self.creds = credentials

        self.prefs = []
        if prefixes is not None and isinstance(prefixes, (list, tuple)):
            self.prefs = list(prefixes)

        self._resdata = {}
        if resdata:
            self._resdata = deepcopy(resdata)
        for prop in ['doi', 'event']:
            if prop in self._resdata:
                del self._resdata[prop]
        

    def supports_prefix(self, prefix):
        """
        return True if the given prefix is among the prefixes provided during 
        construction as one that the client is authorized to mint under.  
        """
        if self.prefs:
            return prefix in self.prefs
        else:
            return False

    @property
    def default_prefix(self):
        """
        the prefix that will be assumed in requests if a prefix is not specified
        """
        if self.prefs:
            return self.prefs[0]
        else:
            return None

    def exists(self, doipath, prefix=None):
        """
        return True if the given DOI path exists as a registered (or reserved)
        DOI.  
        :param str doipath:  the DOI to look for, which can include the prefix 
                             or be just the value appearing (after the slash)
                             after the prefix.  
        :param str prefix:   the prefix part of the DOI.  If not provided--
                             either here or as part of doipath--the default
                             prefix will be assumed.  No client-side checks 
                             are made to ensure the prefix is from the authorized
                             list.  
        """
        if not prefix and not _doi_pfx.search(doipath):
            prefix = self.default_prefix
        if prefix:
            doipath = "/".join([prefix, doipath])

        resp = self._request("HEAD", self._ep+doipath, doipath)

        if resp.status_code >= 200 and resp.status_code < 300:
            return True
        elif resp.status_code >= 400 and resp.status_code < 500:
            return False
        else:
            self._unexpected_resolver_err(doipath, resp)

    def _request(self, meth, url, doipath=None, data=None):
        hdrs={"Accept": JSONAPI_MT}
        if data:
            hdrs["Content-type"] = JSONAPI_MT

        try: 
            resp = requests.request(meth, url, headers=hdrs, auth=self.creds, json=data)
        except (requests.ConnectionError, requests.HTTPError, requests.Timeout) as ex:
            raise DOICommunicationError(doipath, self._ep, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(doipath, self._ep, cause=ex)

        if resp.status_code == 401:
            self._bad_credentials(doipath, resp)

        return resp

    def _to_json(self, resp, doi=None):
        try:
            return resp.json()   # Use OrderedDict?
        except ValueError as ex:
            raise DOIResolverError(doi, self._ep, resp.status_code,
                                   message="Error parsing response as JSON: "+str(ex))
        
    def _unexpected_resolver_err(self, doipath, resp, resj=None,
                                 title="Unexpected resolver error"):
        if resj is None:
            try:
                resj = resp.json()
            except ValueError as ex:
                resj = {'errors': [{'title': resp.reason, 'detail': resp.status_code}]}

        errdata = JAErr(resj.get('errors', []), title)._()
        raise DOIResolverError(doipath, self._ep, resp.status_code, **errdata)
    
    def _unexpected_client_err(self, doipath, resp, resj=None,
                               title="Unexpected client error"):
        if resj is None:
            try:
                resj = resp.json()
            except ValueError as ex:
                resj = {'errors': [{'title': resp.reason, 'detail': resp.status_code}]}

        errdata = JAErr(resj.get('errors', []), title)._()
        raise DOIClientException(doipath, self._ep, **errdata)
    
    def _bad_credentials(self, doipath, resp, resj=None):
        if resj is None:
            try:
                resj = resp.json()
            except ValueError as ex:
                resj = {}

        errdata = JAErr(resj['errors'], "Bad Credentials")._()
        raise DOIClientException(doipath, self._ep, **errdata)
    
    def lookup(self, doipath, prefix=None, relax=False):
        """
        retrieve the information describing the given DOI
        :param str doipath:  the DOI to look for, which can include the prefix 
                             or be just the value appearing (after the slash)
                             after the prefix.  
        :param str prefix:   the prefix part of the DOI.  If not provided--
                             either here or as part of doipath--the default
                             prefix will be assumed.  No client-side checks 
                             are made to ensure the prefix is from the authorized
                             list.  
        :param bool relax:   if False (default), an exception is raised if the 
                             server claims the DOI does not exist; otherwise,
                             this fact will be ignored, and an "empty" DataCiteDOI 
                             instance representing the DOI will be returned
        :rtype DataCiteDOI:  an object for updating (or publishing) the DOI
        """
        if not prefix:
            indoi = _doi_pfx.search(doipath)
            if indoi:
                prefix = indoi.group(0).strip('/')
                doipath = doipath[len(indoi.group(0)):]
            else:
                prefix = self.default_prefix
        doipath = prefix + '/' + doipath
        ro = prefix not in self.prefs

        resp = self._request("GET", self._ep+doipath, doipath)
        resj = self._to_json(resp, doipath)

        if resp.status_code == 404:
            # does not exist yet
            if relax:
                # prep an empty record
                resj = OrderedDict([
                    ('data', OrderedDict([
                        ('id', doipath),
                        ('attributes', OrderedDict([
                            ('prefix', prefix),
                            ('doi', doipath),
                            ('state', '')
                        ]))
                    ]))
                ])
            else:
                raise DOIDoesNotExist(doipath, self._ep)

        if resp.status_code == 200 or resp.status_code == 404:
            try:
                return DataCiteDOI(doipath, self, resj['data'], ro)
            except KeyError as ex:
                self._unexpected_resolver_err(doipath, resp, resj,
                                 "Unexpected JSON data: missing %s property" % str(ex))

        elif resp.status_code >= 400 and resp.status_code < 404:
            self._unexpected_client_err(doipath, resp, resj)

        else:
            self._unexpected_resolver_err(doipath, resp, resj)
            

    _envelope = OrderedDict([("data", OrderedDict([("type", "dois")]))])

    def _new_req(self, data=None):
        out = deepcopy(self._envelope)
        if data is not None:
            out['data']['attributes'] = data
        return out

    def create(self, prefix=None):
        """
        create a new draft DOI with a random path chosen by DataCite
        :param str  prefix:  the prefix to create the DOI under.  If 
                              not provided, the default will be assumed.  If provided,
                              it will be check to ensure it is among those registered
                              as allowed at construction time of this client.
        """
        if not prefix:
            prefix = self.default_prefix
        elif self.prefs and prefix not in self.prefs:
            raise ValueError("Not a recognized prefix: "+prefix)

        resj = self._create_doi({'prefix': prefix})

        try:
            return DataCiteDOI(resj['data']['attributes']['doi'], self, resj['data'])
        except KeyError as ex:
            self._unexpected_resolver_err(doipath, resp, resj,
                        "Unexpected JSON data returned: missing %s property" % str(ex))

    def _create_doi(self, data):
        dta = deepcopy(self._resdata)
        dta.update(data)
        req = self._new_req(dta)

        resp = self._request("POST", self._ep, dta.get('doi', dta.get('prefix')), req)

        if resp.status_code == 409:
            raise DOIStateError(dta.get('doi', '??'), self._ep,
      message="Unable to create doi:{0}: already exists: ".format(dta.get('doi', '??')))

        resj = self._to_json(resp, dta.get('doi', dta.get('prefix')))

        if resp.status_code >= 400 and resp.status_code < 500:
            self._unexpected_client_err(dta.get('doi','??'), resp, resj)

        elif resp.status_code < 200 or resp.status_code >= 300:
            self._unexpected_resolver_err(dta.get('doi','??'), resp, resj)

        return resj

    def reserve(self, doipath, prefix=None, relax=False):
        """
        create a reservation for a DOI with a given path.
        :param str doipath:  the DOI to look for, which can include the prefix 
                              or be just the value appearing (after the slash)
                              after the prefix.  
        :param str  prefix:  the prefix part of the DOI desired to be reserved.  If 
                              not provided, the default will be assumed.  If provided,
                              it will be check to ensure it is among those registered
                              as allowed at construction time of this client.
        :param bool  relax:  if False (default), an exception is raised if the 
                              server claims the DOI already exists; otherwise,
                              this fact will be ignored.  
        :raise Exception:  if the requested path already exists or is already reserved
        :rtype DataCiteDOI:  an object for updating and publishing the reserved DOI
        """
        if not prefix:
            indoi = _doi_pfx.search(doipath)
            if indoi:
                prefix = indoi.group(0).strip('/')
                doipath = doipath[len(indoi.group(0)):]
            else:
                prefix = self.default_prefix

        if prefix not in self.prefs:
            raise ValueError("Not a recognized prefix: "+prefix)

        out = self.lookup(doipath, prefix, relax=True)
        if out.exists:
            if not relax:
                msg = "doi:%s already registered/published" 
                if out.state == STATE_DRAFT:
                    msg = "doi:%s already reserved"
                raise DOIStateException(doipath, self._ep, out.state, msg % doipath)

        else:
            out.reserve()

        return out

        

class DOIStateError(DOIClientException):
    """
    An exception indicating that that a DOI is not in the correct state for the 
    requested operation.  
    """
    def __init__(self, doi, resolver=None, state=None, message=None, errdata=None):
        if not message:
            message = "doi:%s is not in correct state for operation" % doi
        super(DOIStateError, self).__init__(doi, resolver, message, errdata)
        self.state = state

class JSONAPIError(object):
    """
    a container for error data returned from a JSONAPI-compliant service
    """
    def __init__(self, edata, defmsg=None, code=0):
        if edata is not None and not isinstance(edata, list):
            raise TypeError("error data is not a list: "+str(type(edata)))
        self.edata = edata
        self.defmsg = defmsg
        self.code = code
        if not edata:
            if defmsg:
                self.edata = [ { "title": defmsg } ]
            else:
                self.edata = [ { "title": "Unknown error" } ]

    def message(self):
        out = self._format_error(self.edata[0])
        if len(self.edata) > 1:
            out += " (plus other errors)"
        return out

    def _format_error(self, error):
        out = StringIO()
        if 'title' in error:
            out.write(error['title'])
        else:
            out.write(error.get('source','(data)'))
        if 'detail' in error and error['detail']:
            out.write(": ")
            out.write(str(error['detail']))
        return out.getvalue()

    def explain(self):
        out = StringIO()
        out.write("DOI service error")
        if self.defmsg:
            out.write(": ")
            out.write(self.defmsg)
            code = self.edata[0].get('status', self.code)
            if code:
                out.write(" ({0})".format(code))
        if len(self.edata) > 1:
            out.write("\nDetails:")
        for err in self.edata:
            out.write("\n  ")
            out.write(self._format_error(err))
        return out.getvalue()

    def _(self):
        return {
            'message': self.message(),
            'errdata': self
        }

JAErr = JSONAPIError


class DataCiteDOI(object):
    """
    a description of a DataCite DOI and its registration status.  
    """

    def __init__(self, doi, reslvr, data=None, readonly=False, init=False):
        """
        initialize the instance.  
        :param str    doi:  the DOI being described.  
        :param str    reslvr:  the service client instance to use to update this DOI's 
                                 metadata with DataCite 
        :param dict     data:  the data object that provides metadata describing this 
                                 DOI; if None, default data will be used (see also
                                 init parameter)
        :param bool readonly:  if True, a call to update() and publish() will 
                                 raise an exception
        :param bool     init:  if True, retrieve an updated description from the DataCite
                                 service.  This would typically be used when data=None
                                 to initialize the data.  
        """
        self._doi = _pub_doi_resolver_re.sub('', doi)
        if not _doi_re.search(self._doi):
            raise ValueError("Not a DOI: "+self._doi)
        self._reslvr = reslvr
        self._data = data
        self._ro = readonly
                          
        if init:
            self.refresh()

    def refresh(self):
        doid = self._reslvr.lookup(self.doi)
        self._data = doid._data

    @property
    def doi(self):
        """
        the DOI string (i.e. the prefix and suffix concatonated but without the
        resolution URL base)
        """
        return self._doi

    @property
    def prefix(self):
        """the prefix for this DOI"""
        return self.doi.split('/', 1)[0]
            
    @property
    def state(self):
        """
        the current state in the DataCite database
        """
        return self.attrs.get('state', '')

    @property
    def url(self):
        """
        the current state in the DataCite database
        """
        return self.attrs.get('url', '')

    @property
    def exists(self):
        """
        True if the DOI has been reserved or published in the DataCite server.
        """
        return bool(self.state)

    @property
    def is_readonly(self):
        """True if this DOI cannot be updated (via this object)"""
        return self._ro

    def _get_prop(self, prop):
        if not self._data:
            self.refresh()
        return self._data.get(prop, {})

    @property
    def attrs(self):
        """
        the current attributes object (since the last refresh()) describing 
        the object identified by the DOI.
        """
        return self._get_prop('attributes')

    @property
    def links(self):
        return self._get_prop('links')

    @property
    def relationships(self):
        """
        the current links object (since the last refresh()) for accessing
        related information
        """
        return self._get_prop('relationships')

    @property
    def meta(self):
        return self._get_prop('meta')

    def reserve(self, attrs=None):
        """
        create this DOI in a draft state.
        :param dict attrs:   an initial set of DOI attributes to intialize the record
                             with.  If provided, it will be merged with the default
                             attribute data set in the service client
        """
        if self.state:
            raise DOIStateError(self.doi, self._reslvr._ep, self.state,
                                "doi:%s already exists" % self.doi)
        if self.attrs.get('prefix','') not in self._reslvr.prefs:
            raise DOIStateError(self.doi, self._reslvr._ep, "readonly",
                                "%s: No authority to reserve with this prefix" %
                                self.attrs.get('prefix','(prefix)'))
        if self.is_readonly:
            raise DOIStateError(self.doi, self._reslvr._ep, "readonly",
                                "doi:%s read-only; cannot reserve" % self.doi)

        if attrs is None:
            attrs = {}
        else:
            attrs = deepcopy(attrs)
        if 'event' in attrs:
            del attrs[prop]
        attrs['doi'] = self.doi

        resj = self._reslvr._create_doi(attrs)
        try:
            self._data = resj['data']
        except KeyError as ex:
            self._reslvr._unexpected_resolver_err(doipath, resp, resj,
                        "Unexpected JSON data returned: missing %s property" % str(ex))

    def update(self, attrs):
        """
        update the attributes that describe the object described by this identifier.
        :param dict attrs:  a dictionary with properties from a DataCite (dois) 
                                attributes object. This object should not include
                                the doi or event properties (if included, they will
                                be filtered out).
        """
        if not self.state:
            raise DOIStateError(self.doi, self._reslvr._ep, self.state,
                                "doi:%s has not been created yet" % self.doi)
        if self.is_readonly:
            raise DOIStateError(self.doi, self._reslvr._ep, "readonly",
                                "doi:%s read-only; cannot update" % self.doi)

        attrs = deepcopy(attrs)
        for prop in ['doi', 'event']:
            if prop in attrs:
                del attrs[prop]

        req = self._reslvr._new_req(attrs)
        resp = self._reslvr._request("PUT", self._reslvr._ep+self.doi, self.doi, req)
        resj = self._reslvr._to_json(resp, self.doi)

        if resp.status_code >= 400 and resp.status_code < 500:
            self._reslvr._unexpected_client_err(self.doi, resp, resj)

        elif resp.status_code < 200 or resp.status_code >= 300:
            self._reslvr._unexpected_resolver_err(self.doi, resp, resj)

        try:
            self._data = resj['data']
        except KeyError as ex:
            self._reslvr._unexpected_resolver_err(doipath, resp, resj,
                        "Unexpected JSON data returned: missing %s property" % str(ex))

    def publish(self, attrs=None):
        """
        create or update this DOI to a published state.
        :param dict attrs:   the set of DOI attributes to associate with the record.
                             If not provided, the attributes will not be changed.  The
                             DOI must be given or already have set the minimum required
                             metadata.
        :raises DOIStateError: if the DOI cannot be published for any of the following
                             reasons: the DOI is already published, the object is 
                             readonly, or their is not sufficient metadata set yet.
        """
        if self.state == STATE_FINDABLE:
            raise DOIStateError(self.doi, self._reslvr._ep, self.state,
                                "doi:%s has already been published" % self.doi)
        if self.is_readonly:
            raise DOIStateError(self.doi, self._reslvr._ep, "readonly",
                                "doi:%s read-only; cannot publish" % self.doi)

        if self.state == STATE_NONEXISTENT:
            defattrs = deepcopy(self._reslvr._resdata)
            if attrs:
                defattrs.update(attrs)
            attrs = defattrs
        elif attrs:
            attrs = deepcopy(attrs)
        else:
            attrs = OrderedDict()

        attrs['event'] = "publish"
        if self.state == STATE_NONEXISTENT:
            attrs['doi'] = self.doi
        elif 'doi' in self.doi:
            del attrs['doi']

        # make sure we have all the metadata we need to publish
        full = deepcopy(self.attrs)
        full.update(attrs)
        missing = []
        for prop in "url titles publisher publicationYear creators types".split():
            if prop not in full:
                missing.append(prop)
            elif prop.endswith('s') and len(full[prop]) < 1:
                missing.append(prop)
        if missing:
            raise DOIStateError(self.doi, self._reslvr._ep,
                   message="Insufficient metadata to publish: missing "+str(missing))

        # now send request to server
        req = self._reslvr._new_req(attrs)
        if self.state == STATE_DRAFT:
            # publishing draft (or registered) DOI
            resp = self._reslvr._request("PUT", self._reslvr._ep+self.doi,
                                         self.doi, req)
        else:
            # creating direct to published state
            resp = self._reslvr._request("POST", self._reslvr._ep, self.doi, req)
        resj = self._reslvr._to_json(resp, self.doi)

        if resp.status_code == 429:
            raise DOIStateError(self.doi, self._reslvr._ep, self.state,
                                JAErr(resp.get('errors',[]),
                                      "Insufficient metadata to publish")._())
        elif resp.status_code >= 400 and resp.status_code < 500:
            self._reslvr._unexpected_client_err(self.doi, resp, resj)

        elif resp.status_code < 200 or resp.status_code >= 300:
            self._reslvr._unexpected_resolver_err(self.doi, resp, resj)

        try:
            self._data = resj['data']
        except KeyError as ex:
            self._reslvr._unexpected_resolver_err(doipath, resp, resj,
                        "Unexpected JSON data returned: missing %s property" % str(ex))

    def delete(self, relax=False):
        if not self.state:
            raise DOIStateError(self.doi, self._reslvr._ep, self.state,
                                "doi:%s has not been reserved yet." % self.doi)
        if self.state != STATE_DRAFT:
            raise DOIStateError(self.doi, self._reslvr._ep, self.state,
                                "doi:%s is not in draft state." % self.doi)
        if self.is_readonly:
            raise DOIStateError(self.doi, self._reslvr._ep, "readonly",
                                "doi:%s read-only; cannot delete" % self.doi)
                                    
        resp = self._reslvr._request("DELETE", self._reslvr._ep+self.doi, self.doi)

        if resp.status_code == 404:
            # does not exist yet/anymore
            self.attrs['state'] = STATE_NONEXISTENT
            if not relax:
                raise DOIDoesNotExist(self.doi, self._reslvr._ep, "")

        elif resp.status_code >= 200 and resp.status_code <= 204:
            self.attrs['state'] = STATE_NONEXISTENT

        elif resp.status_code >= 400 and resp.status_code < 404:
            self._reslvr._unexpected_client_err(self.doi, resp)
        else:
            self._reslvr._unexpected_resolver_err(self.doi, resp)

