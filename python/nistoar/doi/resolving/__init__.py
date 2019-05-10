"""
functions and classes for resolving digital object identifiers (DOIs).
"""
import re
from .common import *
from .datacite import DataciteDOIInfo
from .crossref import CrossrefDOIInfo

_dc_resolver_re = re.compile(r'^https?://[^/]+\.datacite\.org/')
_cr_resolver_re = re.compile(r'^https?://[^/]+\.crossref\.org/')

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
    if not resolver:
        resolver = default_doi_resolver

    url = resolver + doi

    # Do a HEAD request on the DOI to examine where it gets forwarded to
    try:
        resp = requests.head(url, headers={"Accept": CT.Citeproc_JSON},
                             allow_redirects=False)
    except (requests.ConnectionError,
            requests.HTTPError,
            requests.ConnectTimeout)   as ex:
        raise DOICommunicationError(self.id, self.resolver, ex)
    except requests.RequestException as ex:
        raise DOIResolverError(self.id, self.resolver, cause=ex)
            
    if resp.status_code < 200 or resp.status_code >= 400:
        if resp.status_code == 406:
            raise DOIUnsupportedContentType(CT.Citeproc_JSON, doi, resolver)

        if resp.status_code == 404:
            raise DOIDoesNotExist(doi, resolver)

        raise DOIResolverError(doi, resolver, resp.status_code, resp.reason)

    # Use the redirect Location URL to determine the source of DOI it is
    loc = resp.headers.get('Location', '')
    info = None
    if resp.status_code < 300:
        # resolver was expected to redirect; instead it responded as if its
        # the source; treat as unknown
        info = DOIInfo(doi, resolver=resolver, logger=logger)

    elif _dc_resolver_re.match(loc):
        info = DataciteDOIInfo(doi, resolver=resolver, logger=logger)
    elif _cr_resolver_re.match(loc):
        info = CrossrefDOIInfo(doi, resolver=resolver, logger=logger)
    else:
        info = DOIInfo(doi, resolver=resolver, logger=logger)

    # pre-load the data
    info.data

    return info

