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

class DataCiteDOIClient(object):
    """
    a client interface to the DataCite DOI services.  With this client, users 
    can request to reserve, create, and update DOIs.
    """

    _env = OrderedDict([("data", OrderedDict([("type", "dois")]))])

    def __init__(self, endpoint, credentials, prefixes=[]):
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
        """
        self.ep = endpoint
        if not self.ep.endswith('/'):
            self.ep += '/'
        self.creds = credentials

        self.prefs = []
        if prefixes is not None and isinstance(prefixes, (list, tuple)):
            self.prefs = list(prefixes)

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

    def doi_exists(self, doipath, prefix=None):
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

        try: 
            resp = requests.head(self.ep+'/'+doipath, auth=self.creds)
        except (requests.ConnectionError, requests.HTTPError,
                requests.connecttimeout) as ex:
            raise DOICommunicationError(doipath, self.ep, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(doipath, self.ep, cause=ex)
        
        if resp.status_code >= 200 and resp.status_code < 300:
            return True
        elif resp.status_code >= 400 and resp.status_code < 500:
            return False
        else:
            edata = self._getedata(resp)
            raise DOIResolverError(doipath, self.ep, resp.status_code,
                                   "Unexpected resolve response: " +
                                   self._mkemsg(resp, edata), edata)

    def doi_state(self, doipath, prefix=None):
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
        try:
            desc = self.describe(doipath, prefix)
            return desc['data']['attributes']['status']
        except DOIDoesNotExist as ex:
            return STATE_NONEXISTENT
        except KeyError as ex:
            raise DOIResolverExcption(doipath, self.ep,
                              message="Unexpected response: missing property: "+str(ex))

    def _ensure_prefix(self, prefix):
        if self.prefs:
            if not prefix:
                prefix = self.default_prefix
            elif prefix not in self.prefs:
                raise ValueError("reserve(): Not a recognized prefix: "+prefix)
        else:
            raise ValueError("reserve(): missing prefix; no default defined")

        return prefix

    def _new_req(self, data=None):
        out = deepcopy(self._env)
        if data is not None:
            out['data']['attributes'] = data
        return out

    def _headers(self, withct=False):
        hdrs = { "Accept": "application/vnd.api+json" }
        if withct:
            hdrs['Content-type'] = "application/vnd.api+json" 
        return hdrs

    def _getedata(self, resp):
        try:
            return resp.json()
        except Exception as ex:
            return [{"error": {
                "title":  resp.reason,
                "detail": "(Note: Bad JSON-API error response)"
            }}]
        
    def _mkemsg(self, resp, edata=None):
        if edata is None:
            edata = self._getdata(resp)
        out = StringIO()
        if len(edata) == 0:
            out.write(resp.reason)
        else:
            out.write(edata[0]['title'])
            if 'detail' in edata[0] and edata[0]['detail']:
                out.write(": ")
                out.write(edata[0]['detail'])
        if len(edata) > 1:
            out.write(" (plus other errors)")
            

    def reserve(self, doipath, prefix=None, relax=False):
        """
        create a reservation for a DOI with a given path.
        :param str doipath:    the suffix part of the DOI desired to be reserved.  Set
                                to None to request that the service pick the suffix.
        :param str  prefix:    the prefix part of the DOI desired to be reserved.  If 
                                not provided, the default will be assumed.  If provided,
                                it will be check to ensure it is among those registered
                                as allowed at construction time of this client.
        :param bool  relax:    if False (default), an exception is raised if the 
                                server claims the DOI already exists; otherwise,
                                this fact will be ignored.  
        :raise Exception:  if the requested path already exists or is already reserved
        """
        prefix = self._ensure_prefix(prefix)
        if doipath:
            data = {"doi": prefix+'/'+doipath}

            if self.doi_exists(data['doi']):
                if not relax:
                    raise DOIClientException(data['doi'],
                                             message="DOI already exists: "+data['doi'])
                return
        else:
            data = {"prefix": prefix}

        req = self._new_req(data)
        try:
            resp = requests.post(self.ep, auth=self.creds, 
                                 headers=self._headers(True), json=req)
        except (requests.ConnectionError, requests.HTTPError,
                requests.connecttimeout) as ex:
            raise DOICommunicationError(data['doi'], self.ep, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(data['doi'], self.ep, cause=ex)
        
        if resp.status_code == 409:
            raise DOIClientException(data['doi'], "Unable to reserve %s: already exists"
                                     % data['doi'])
        elif resp.status_code < 200 or resp.status_code >= 300:
            edata = self._getedata(resp)
            raise DOIResolverError(data['doi'], self.ep, resp.status_code,
                                   "Unexpected reserve response: " +
                                   self._mkemsg(resp,edata))

        try:
            return resp.json()
        except (ValueError, TypeError) as ex:
            raise DOIResolverError(data['doi'], self.ep, resp.status_code,resp.reason,ex,
                                   "reserve(): response not parseable as JSON: "+str(ex))

    def delete_reservation(self, doipath, prefix=None):
        """
        return True if the given DOI path exists as a registered (or reserved)
        DOI.  
        :param str doipath:  the DOI to look for, which can include the prefix 
                             or be just the value appearing (after the slash)
                             after the prefix.  
        :param str prefix:   the prefix part of the DOI.  If not provided--
                             either here or as part of doipath--the default
                             prefix will be assumed.  
        """
        m = _doi_pfx.search(doipath)
        if m:
            prefix = m.group().strip('/')
            doipath = doipath[len(prefix)+1:]
        if not prefix:
            prefix = self.default_prefix
        if self.prefs and prefix not in self.prefs:
            raise ValueError("delete_reservation(): Not a recognized prefix: "+prefix)

        doipath = "/".join([prefix, doipath])
        status = self.doi_state(doipath)
        if status == STATE_NONEXISTENT:
            raise DOIDoesNotExist(doipath, self.ep)
        elif status != STATE_DRAFT:
            raise DOIClientException(doipath, self.ep, "DOI not in draft state")

        try: 
            resp = requests.delete(self.ep+'/'+doipath, auth=self.creds)
        except (requests.ConnectionError, requests.HTTPError,
                requests.connecttimeout) as ex:
            raise DOICommunicationError(doipath, self.ep, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(doipath, self.ep, cause=ex)

        if resp.status_code == 404:
            raise DOIDoesNotExist(doipath, self.ep)
        elif resp.status_code == 403:
            raise DOIClientException(doipath, self.ep, "DOI not in draft state")
        elif resp.status_code < 200 or resp.status_code >= 300:
            edata = self._getedata(resp)
            raise DOIResolverError(doipath, self.ep, resp.status_code, resp.reason,
                                   message="Unexpected delete result: " +
                                           self._mkemsg(resp, edata), errdata=edata)
            
    def publish(self, doipath, attributes=None, prefix=None, nocreate=False):
        """
        publish a previously reserved DOI or create and publish new one.  If the 
        DOI has not been previously provided, attributes must be provided and those 
        attributes must include at the minimumally required metadata, including the 
        'url' property.  
        The service will pick an unclaimed, random doipath if neither the doipath 
        parameter is set nor one is given in the input attributes.  
        :param str doipath: the doipath to publish.  When given, this will override 
               a path specified in the attributes data.  This can include optionally
               include the requested prefix.  If nocreate=True, this 
               must refer to an existing draft DOI.  
        :param dict attributes:  the DOI metadata as an attributes node of a DOI 
               request.  This is optional if the DOI was previously reserved and 
               its metadata was fully set.  If the DOI was previously reserved,
               the attributes will be used to update the metadata.  
        :param str prefix:  the prefix to publish this DOI under.  If not provided
               (either here or as part of doipath), the default prefix will be 
               assumed.  
        :param bool nocreate:  If True, require that the DOI has been previously 
               reserved; otherwise (the default), creating a new DOI is allowed.  
        :raise Exception:  if ...
        """
        prefix = self._ensure_prefix(prefix)
        if doipath:
            doi = prefix+'/'+doipath
            status = self.doi_state(doipath, prefix)
            if status == STATE_NONEXISTENT:
                meth = "POST"
                url = self.ep
            elif status != STATE_DRAFT:
                raise DOIClientException(doi,  message=doi+": not in draft state")
            else:
                meth = "PUT"
                url = self.ep+'/'+doi
        else:
            doi = prefix+'/'
            meth = "POST"
            url = self.ep

        if meth == "POST":
            if nocreate:
                raise DOIClientException(doi, message=doi+": not reserved yet")
            if not attributes:
                raise ValueError("new DOI requested without attributes")
            missing = []
            for prop in "url titles publisher publicationYear creators types".split():
                if prop not in attributes:
                    missing.append(prop)
                elif prop.endswith('s') and len(attributes[prop]) < 1:
                    missing.append(prop)
                    
            if missing:
                raise ValueError("properties missing from attributes: " +
                                 ", ".join(missing))
        if attributes:
            attributes = deepcopy(attributes)
        else:
            attributes = OrderedDict()
        attributes['event'] = "publish"

        req = self._new_req(attributes)
        try:
            resp = requests.request(meth, url, headers=self._headers(True),
                                    auth=self.creds, json=req)
        except (requests.ConnectionError, requests.HTTPError,
                requests.connecttimeout) as ex:
            raise DOICommunicationError(doi, self.ep, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(doi, self.ep, cause=ex)
        
        if resp.status_code == 409:
            raise DOIClientException(data['doi'], "Unable to reserve %s: already exists"
                                     % data['doi'])
        elif resp.status_code < 200 or resp.status_code >= 300:
            edata = self._getedata(resp)
            raise DOIResolverError(data['doi'], self.ep, resp.status_code,
                                   "Unexpected reserve response: " +
                                   self._mkemsg(resp,edata))

        try:
            return resp.json()
        except (ValueError, TypeError) as ex:
            raise DOIResolverError(data['doi'], self.ep, resp.status_code,resp.reason,ex,
                                   "reserve(): response not parseable as JSON: "+str(ex))

    def update(self, attributes, doipath, prefix=None):
        """
        update an existing DOI with updated metadata
        :param dict attributes:  the DOI metadata to update, given as an attributes 
               node of a DOI request
        :param str doipath: the doipath to request.  When given, this will override 
               a path specified in the attributes data.
        """
        if not attributes or not isinstance(attributes, Mapping):
            raise TypeError("update(): attributes not an dict: "+str(type(attributes)))

        m = _doi_pfx.search(doipath)
        if m:
            prefix = m.group().strip('/')
            doipath = doipath[len(prefix)+1:]
        if not prefix:
            prefix = self.default_prefix
        if self.prefs and prefix not in self.prefs:
            raise ValueError("delete_reservation(): Not a recognized prefix: "+prefix)

        doipath = "/".join([prefix, doipath])
        req = self._new_req(attributes)
        for prop in ['doi', 'event']:
            if prop in req['data']['attributes']:
                del req['data']['attributes'][prop]

        try:
            resp = requests.put(self.ep+'/'+doipath, auth=self.creds,
                                headers=self._headers(True), json=req)
        except (requests.ConnectionError, requests.HTTPError,
                requests.connecttimeout) as ex:
            raise DOICommunicationError(doipath, self.ep, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(doipath, self.ep, cause=ex)

        if resp.status_code >= 204:
            return {"data":{"attributes":{}}}
        elif resp.status_code >= 200 and \
             (resp.status_code < 300 or resp.status_code >= 400):
            try:
                rec = resp.json()
            except (ValueError, KeyError) as ex:
                raise DOIResolverError(data['doi'], self.ep, resp.status_code,
                                       resp.reason, ex,
                            "update_id: response not parseable as JSON: "+str(ex))

            if resp.status_code >= 200 and resp.status_code < 300:
                return rec
            elif resp.status_code >= 500:
                raise DOIResolverError(data['doi'], self.ep, resp.status_code,
                                       resp.reason,
                                       message="Server errror: "+self._mkemsg(resp, rec),
                                       errdata=rec)
            else:
                raise DOIResolverError(data['doi'], self.ep, resp.status_code,
                                       resp.reason,
                                       message="Unexpected response: "+
                                               self._mkemsg(resp, rec),
                                       errdata=rec)

    def describe(self, doipath, prefix=None):
        """
        retrieve the metadata associated with the given DOI path
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

        try: 
            resp = requests.get(self.ep+'/'+doipath, auth=self.creds,
                                headers=self._headers())
        except (requests.ConnectionError, requests.HTTPError,
                requests.connecttimeout) as ex:
            raise DOICommunicationError(doipath, self.ep, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(doipath, self.ep, cause=ex)
        
        if resp.status_code == 200:
            try: 
                return resp.json()
            except (ValueError, TypeError) as ex:
                raise DOIResolverError(doipath, self.ep, resp.status_code, resp.reason,
                                       ex, "Response not parseable as JSON: " + str(ex))
        elif resp.status_code == 404:
            raise DOIDoesNotExist(doipath, self.ep)
        elif resp.status_code >= 400 and resp.status < 404:
            edata = self._getedata(resp)
            raise DOIClientException(doipath, self.ep,
                                     "Unexpected Client Exception: {0} ({1})"+
                                     self._mkemsg(resp, edata), edata)
        else:
            raise DOIResolverError(doipath, self.ep, resp.status_code, resp.reason,
                                   message="Unexpected resolver response: " +
                                           self._mkemsg(resp, edata), errdata=edata)



