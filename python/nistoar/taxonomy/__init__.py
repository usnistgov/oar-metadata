"""
classes and functions that assist with using terms from taxonomies
"""
from .base import *
from .simple import SimpleTaxonomy
from .cache.files import FileTaxonomyCache

OAR_TAXON_FILE_PATTERN = r'.*taxonomy.*'

def open_taxonomy_cache(taxondir: str, pattern: str=None, log: Logger=None):
    """
    return a :py:class:`~nistoar.pdr.utils.taxonomy.TaxonomyCache` instance which provides
    access to taxonomies known to the OAR system.  

    This implementation returns a 
    :py:class:`~nistoar.pdr.utils.taxonomy.cache.files.FileTaxonomyCache` instance,
    specifically.  When initializing, it is tolerant about problems with taxonomies (e.g. 
    missing taxonomy file, errors while parsing, etc.): it simply skips over problem 
    taxonomy files and its definitions will be considered "unknown".  Provide a Logger
    to record warnings about such errors.

    :param str|Path taxondir: the path to the directory containing the taxonomy files
    :param str       pattern: a Python regular expression for matching taxonomy file names 
                              in the directory; only files matching this pattern will be 
                              loaded into the cache.  If None (default), this function will 
                              rely on the presense of a taxonomyLocations.yml (or .json) 
                              file for finding the taxonomies
    :param Logger        log: a Logger to use to warn about unreadable taxonomy files.
    """
    return FileTaxonomyCache(taxondir, pattern, log)
    
