"""
classes and functions that assist with using terms from taxonomies
"""
from .base import *
from .simple import SimpleTaxonomy
from .cache.files import FileTaxonomyCache

OAR_TAXON_FILE_PATTERN = r'.*-taxonomy.*'

def open_taxonomy_cache(taxondir: str, log: Logger=None):
    """
    return a :py:class:`~nistoar.pdr.utils.taxonomy.cache.files.FileTaxonomyCache` instance
    for accessing taxonomy definitions.
    """
    return FileTaxonomyCache(taxondir, OAR_TAXON_FILE_PATTERN, log)
    
