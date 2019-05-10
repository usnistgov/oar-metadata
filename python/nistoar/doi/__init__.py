"""
a module for interacting with Digital Object Identifiers (DOI).  Most notably,
DOIs can be resolved to their metadata.  

DOI metdata is accessible via resovle() which returns a DOIInfo object.

See https://doi.org/ for more information about DOIs.
"""
from .resolving.common import (set_client_info, CT, DOIInfo,
                               DOIResolutionException, DOICommunicationError,
                               DOIResolverError, DOIClientException,
                               DOIDoesNotExist, DOIUnsupportedContentType)
from .resolving import resolve

