"""
classes and functions that assist with using terms from taxonomies

This module provides implementations for finding and accessing multiple taxonomies.  In 
particular, it provides the facilities to load a taxonomy's definitions and use that 
information to match terms and even test broader and narrower relationships.  

The module is designed to handle taxonomy definitions from multiple sources and using 
multiple formats and schemas.  (At this writing, only the OAR-specific "simple" schema
loaded from files is supported.)

The module is build around two key classes: :py:class:`~nistoar.taxonomy.base.Taxonomy` and 
:py:class:`~nistoar.taxonomy.base.TaxonomyCache`.  The latter is used to discover and register 
all taxonomies available to the system.  From that class, one can open up a taxonomy as a 
:py:class:`~nistoar.taxonomy.base.Taxonomy` instance given its identifier string.  With a 
:py:class:`~nistoar.taxonomy.base.Taxonomy` instance in hand, one can access specific terms 
in the taxonomy either via its identifier or its prefered label.  

The simplest way to initiate a :py:class:`~nistoar.taxonomy.base.TaxonomyCache` is via the 
function, :py:func:`nistoar.taxonomy.open_taxonomy_cache`: 

.. code-block::
   :caption: Example use of the taxonomy module

   import os
   from pathlib import Path
   from nistoar import taxonomy
   from nistoar.midas.dap.service.mds3 import NIST_THEMES  # the NIST research topics taxonomy URI

   taxdir = Path(os.environ['OAR_HOME']) / "etc" / "schemas"
   cache = taxonomy.open_taxonomy_cache(taxdir)
   taxon = cache.open_taxonomy(NIST_THEMES)
   biosci = taxon.match_label("Bioscience")

See the :py:class:`Taxonomy documentation <nistoar.taxonomy.base.Taxonomy>` for more on what 
you can do with a taxonomy.
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
    
