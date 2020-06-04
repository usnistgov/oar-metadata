"""
Utilities useful when handling DOIs
"""
import re

_doi_uri_re = re.compile(r'^doi:\d+\.\d+/')
_doi_url_re = re.compile(r'^https?://(dx.)?doi.org/\d+\.\d+/')

def is_DOI(id):
    """
    return true if the given ID can be interpreted as a DOI.  A DOI is 
    recognized as matching any of the following patterns:
      * a URI starting with "doi:"
      * a URL starting with "http[s]://doi.org/"
      * a URL starting with "http[s]://dx.doi.org/"
    """
    id = id.strip()
    if _doi_uri_re.match(id):
        return True
    if _doi_url_re.match(id):
        return True
    return False

default_doi_resolver = "https://doi.org/"

_url_server_re = re.compile(r'^https?://[^/]+/')

def strip_DOI(doi, resolver=None):
    """
    strip off a legal prefixes from a given DOI so that it starts with the 
    authority string (i.e. "10...")

    :param str doi:       the DOI string to strip
    :param str resolver:  a non-standard DOI resolver base URL to allow for.  It
                          should include a trailing / or ? if these are relevent.
    """
    doi = doi.strip()
    if doi.startswith("doi:"):
        doi = doi[4:]
    elif resolver and doi.startswith(resolver):
        doi = doi[len(resolver):]
    elif doi.startswith(default_doi_resolver):
        doi = doi[len(default_doi_resolver):]
    elif _url_server_re.match(doi):
        doi = _url_server_re.sub('', doi)

    return doi


    
