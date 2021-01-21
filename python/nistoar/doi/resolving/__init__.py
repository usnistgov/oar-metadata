"""
functions and classes for resolving digital object identifiers (DOIs).
"""
import re
from .common import *
from .datacite import DataciteDOIInfo
from .crossref import CrossrefDOIInfo
from .crosscite import CrossciteDOIInfo
from . import common as _comm

_dc_resolver_re = re.compile(r'^https?://[^/]+\.datacite\.org/')
_cr_resolver_re = re.compile(r'^https?://[^/]+\.crossref\.org/')
_cc_resolver_re = re.compile(r'^https?://data\.crosscite\.org/')

class Resolver(object):
    """
    a class for resolving DOIs.  An instance encapsulates a resolver base 
    URL and client/applicaiton identity information.  
    """

    def __init__(self, client_info=None, resolver=None, logger=None):
        """
        instantiate the resolver

        :param 4-tuple client_info:  the client/application information 
        """
        if not client_info and _comm._client_info:
            client_info = tuple(_comm._client_info)
        if client_info is not None and \
           (not isinstance(client_info, (list, tuple)) or len(client_info) != 4):
            raise TypeError("client_info: Not a 4-tuple: "+str(client_info))
        self._client_info = client_info

        if not resolver:
            resolver = default_doi_resolver
        self._resolver = resolver

        self._log = logger

    def resolve(self, doi):
        """
        resolve a DOI to its metadata.  This is expected to make one or more 
        calls to a web service.

        :param str doi:  the DOI to resolve.  This can be given in any of its 
                         legal forms including with the "doi:" prefix, in URL
                         format, or without any prefix.
        """
        doi = _comm.strip_DOI(doi, self._resolver)
        url = self._resolver + doi

        hdrs = {"Accept": CT.Citeproc_JSON}
        ua = get_default_user_agent()
        if ua:
            hdrs['User-Agent'] = ua

        # Do a HEAD request on the DOI to examine where it gets forwarded to
        try:
            resp = requests.head(url, headers=hdrs, allow_redirects=False)
        except (requests.ConnectionError,
                requests.HTTPError,
                requests.ConnectTimeout)   as ex:
            raise DOICommunicationError(doi, self._resolver, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(doi, self._resolver, cause=ex)
                
        if resp.status_code < 200 or resp.status_code >= 400:
            if resp.status_code == 406:
                raise DOIUnsupportedContentType(CT.Citeproc_JSON, doi,
                                                self._resolver)

            if resp.status_code == 404:
                raise DOIDoesNotExist(doi, self._resolver)

            raise DOIResolverError(doi, self._resolver,
                                   resp.status_code, resp.reason)

        # Use the redirect Location URL to determine the source of DOI it is
        loc = resp.headers.get('Location', '')
        info = None
        if resp.status_code < 300:
            # resolver was expected to redirect; instead it responded as if its
            # the source; treat as unknown
            info = DOIInfo(doi, resolver=self._resolver, logger=self._log)

        elif _cc_resolver_re.match(loc):
            info = CrossciteDOIInfo(doi, resolver=self._resolver, logger=self._log,
                                    client_info=self._client_info)
        elif _dc_resolver_re.match(loc):
            info = DataciteDOIInfo(doi, resolver=self._resolver,logger=self._log,
                                   client_info=self._client_info)
        elif _cr_resolver_re.match(loc):
            info = CrossrefDOIInfo(doi, resolver=self._resolver,logger=self._log,
                                   client_info=self._client_info)
        else:
            info = DOIInfo(doi, resolver=self._resolver, logger=self._log)

        # pre-load the data
        info.data

        return info


def resolve(doi, resolver=None, logger=None):
    """
    resolve a DOI to its metadata.  This is expected to make one or more 
    calls to a web service.

    :param str doi:  the DOI to resolve.  This can be given in any of its 
                     legal forms including with the "doi:" prefix, in URL
                     format, or without any prefix.
    :param str resolver:  the base URL to use as the resolver service.  If 
                     not given, "https://doi.org/" is used.
    :param Logger logger:  a Logger instance to send debug messages to.  
                     Generally, the URLs used to retrieve metadata are 
                     recorded at the debug level.
    :return DOIInfo: a DOI metadata container instance, usually a subclass 
                     of DOIInfo, specialized for the type of DOI provided
                     (e.g. Datacite, Crossref).  
    """
    return Resolver(resolver=resolver, logger=logger).resolve(doi)

