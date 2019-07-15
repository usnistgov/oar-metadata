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


    
