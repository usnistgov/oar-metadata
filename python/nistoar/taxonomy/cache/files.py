"""
An implementation of the :py:class:`~nistoar.pdr.utils.TaxonomyCache` in which taxonomy 
definitions are stored in files.  

In this implementation, taxonomy definition files are discovered either by scanning a 
directory for files with a given pattern or by reading in a schema location file 
(``taxonomyLocation.yml`` or ``taxonomyLocation.json``).  

By design, multiple taxonomy definition schemes/formats are supported.  (At the moment,
only the "simple" scheme is supported.)
"""
import re, os, json
from logging import Logger
from typing import Iterator, Mapping
from pathlib import Path
from copy import deepcopy

import yaml

from ..base import TaxonomyCache, Taxonomy, _load_file
from ..simple import SimpleTaxonomy

class FileTaxonomyCache(TaxonomyCache):
    """
    a class that manages access to taxonomy definitions stored in files.

    In this implementation, a cache is a set of locations of taxonomy definition files on 
    disk.  The cache is initialized either by scanning a directory for files with a given 
    pattern or by loading a schema locaiton file.  

    A taxonomy location file can be encoded in JSON or YAML format, but the schema is the 
    same, where the following properties are supported:

    ``baseDirectory``
         a directory path for which all taxonomy location paths are relative to (see 
         ``taxonomy.location`` below).  If given relative as a relative path, it will be 
         interpreted as relative to the directory where this location file is found.
    ``pattern``
         a Python regular expression used to identify taxonomy files in the base directory.
         When provided and ``taxonomy`` is not provided, the base directory will be scanned 
         for taxonomy definition files.  
    ``include``
         a list of file or directory paths to consult for additional taxonomies.  If the path
         points to a file, it will be interpreted as a taxonomy location file.  If the path 
         is a directory, it will be scanned using the file pattern given by ``pattern``.
    ``taxonomy``
         a list of taxonomy file summaries to be included in the cache.  Each element summarizes
         a txonomy and where it can be found using the following sub-properties:

         ``location``
              (str) required. The path to the file defining the taxonomy.  If not absolute,
              it should be relative to the base directory.
         ``id``
              (str) required. the unique identifier for the taxonomy (usually a URI)
         ``version``
              (str) optional. the version of the taxonomy
         ``title``
              (str) optional. a title for the taxonomy
         ``description``
              (str) optional. a brief description of the taxonomy's use and purpose
         ``released``
              (str) optional. the date the taxonomy was released
       
    """
    LOCATION_FILE_BASE = "taxonomyLocation"

    def __init__(self, source: str, pattern: str=None, log: Logger=None):
        """
        initialize the cache with taxonomies found in a source location

        :param str  source:  a path to a file or a directory.  If it is a directory and 
                             the ``pattern`` argument is not provided, this class will 
                             look for a ``taxonomyLocation.yml`` or ``taxonomyLocation.json``
                             file which will be used to load the locations and metadata for 
                             taxonomies in the cache.  If one does not exist, it will use 
                             ``pattern`` to taxonomies from files in the directory.  If the 
                             value points to a file, it will be taken as a location file. 
        :param str pattern:  a regular expression pattern for identifying taxonomy files in the 
                             ``source`` directory.  If provided, the presence of a taxonomy 
                             location file is ignored.  This pattern is ignored if ``source`` 
                             does not point to a directory.
        """
        super(FileTaxonomyCache, self).__init__(log)
        self.src = Path(source)
        self.patt = pattern
        self._tx = None
        self.reload()

    def about(self, id) -> Mapping:
        try:
            return deepcopy(self._tx[id])
        except KeyError:
            return None

    def is_known(self, id) -> bool:
        return bool(self._tx[id])

    def count(self) -> int:
        return len(self._tx)

    def ids(self) -> Iterator[str]:
        return self._tx.keys()

    def load_taxonomy(self, id) -> Taxonomy:
        about = self.about(id)
        if not about:
            return None
        return load_taxonomy(about['location'])

    def reload(self, **kwargs):
        """
        reload the taxonomy metadata from the cache's source
        """
        self._tx = {}
        if self.src.is_dir():
            if self.patt:
                patt = re.compile(self.patt)
                tfiles = [self.src/f for f in os.listdir(self.src) if patt.search(f)]
                self._tx = self._load_from_file_scans(tfiles)
            else:
                locf = self.src/(self.LOCATION_FILE_BASE+".yml")
                if not locf.is_file():
                    locf = self.src/(self.LOCATION_FILE_BASE+".json")
                if locf.is_file():
                    self._tx = self._load_locations_from_file(locf)

        else:
            self._tx = self._load_locations_from_file(self.src)

    def count(self):
        return len(self._tx)

    def _load_from_file_scans(self, tfiles, out=None, basedir=None):
        if out is None:
            out = {}
        for f in tfiles:
            tax = self._scan_tax_file(f, basedir)
            if tax:
                out[tax['id']] = tax
        return out
    
    def _warn(self, message, *args):
        if self.log:
            self.log.warning(message, *args)

    def _scan_tax_file(self, tfile, basedir=None):
        if isinstance(tfile, str):
            tfile = Path(tfile)
        if not tfile.is_absolute():
            tfile = Path(basedir) / tfile
        if not tfile.is_file():
            return None

        try:
            about = summarize(tfile)
            if not about:
                self._warn("%s: no taxonomy info loaded; skipping.", str(locfile))
                return None
            
            about['location'] = str(tfile)
            return about
        except (IOError, ValueError) as ex:
            self._warn(str(ex))
            return None
        except Exception as ex:
            if self.log:
                log.exception(ex)
            raise

    def _load_locations_from_file(self, locfile, out=None, visitedfiles=[]):
        data = {}
        try: 
            data = _load_file(locfile, "taxonomy location")
        except (IOError, ValueError) as ex:
            self._warn(str(ex))
            return None
        except Exception as ex:
            if self.log:
                log.exception(ex)
            raise
        
        if not data:
            self._warn("%s: No taxonomy locations found", str(locfile))
            return None

        visitedfiles.append(str(locfile))  # prevents include loops

        basedir = data.get('baseDirectory')
        if not basedir:
            basedir = locfile.parents[0]

        if out is None:
            out = {}
        if data.get('taxonomy'):
            if not isinstance(data['taxonomy'], list):
                self._warn("%s: location file format error: taxonomy: not a list", str(tfile))
                return None

            for tax in data['taxonomy']:
                if not tax.get('location') or not isinstance(tax['location'], str) or \
                   not tax.get('id') or not isinstance(tax['id'], str):
                    continue
                if not os.path.isabs(tax['location']):
                    tax['location'] = os.path.join(basedir, tax['location'])
                out[tax['id']] = tax

        elif data.get('pattern'):
            patt = re.compile(data['pattern'])
            tfiles = [basedir/f for f in os.listdir(basedir) if patt.search(f)]
            self._load_from_file_scans(tfiles, out, basedir)

        if data.get('include'):
            if not isinstance(data['taxonomy'], list):
                _warn("%s: location file format error: include: not a list", str(tfile))
            else:
                basedir = data.get('baseDirectory')
                if not basedir:
                    basedir = locfile.parents[0]
                for inclloc in data.get('include'):
                    inclloc = basedir / Path(inclloc)
                    if str(inclloc) in visitedfiles:
                        continue
                    if inclloc.is_file():
                        self._load_locations_from_file(inclloc, out, visitedfiles)
                    elif inclloc.is_dir():
                        visitedfiles.append(inclloc)
                        tfiles = [inclloc/f for f in os.listdir(inclloc) if patt.search(f)]
                        self._load_from_file_scans(tfiles, out, inclloc)

        return out

    def export_locations(self, dest, format=None, basedir=None):
        """
        export the location information into a taxonomy location file.

        The file will comply with the schema 
        :py:class:`described in this class <FileTaxonomyCache>`.

        :param str|Path dest:  the path to the destination.  If the path points to an
                               existing directory, it will be written to a file with 
                               the standard name, `taxonomyLocations.`*fmt*, where *fmt*
                               corresponds to a supported format designated by the 
                               ``format`` argument.  Otherwise, it will be interpreted as 
                               the output file.  In either case, if the file exists, it 
                               will be overwritten.
        :param str    format:  the label indicating the desired format to write the file in.
                               Supported labels are "json" and "yaml".  If not provided and 
                               ``dest`` points to a destination file, then the format will
                               be inferred by the file's extension (where ".yml" is also 
                               recognized); if the destination file is not specified the 
                               format defaults to "yaml".  If ``format`` is provided and 
                               ``dest`` refers to a file, the extension will be ignored.
        :param str|Path|bool|None basedir:  if a str or Path, interpret it as a directory to set 
                               as the base directory for taxonomy file locations; all 
                               locations for taxonomy files in this cache under that path 
                               will be rewritten to be relative to it.  If True, the base 
                               directory will be set to the directory implied by ``dest``.  
                               If False, the base directory is not set, and all locations 
                               will written as absolute paths.  If None (default), the 
                               base directory will not be set, but the locations will made 
                               relative to the base directory implied by ``dest``.  
                               A value of True or False makes the location file more portable, 
                               but a value of None makes the whole directory more portable.  
        """
        if not dest:
            dest = self.src
        else:
            dest = Path(dest)

        if not format:
            format = dest.suffix.lstrip('.') if not dest.is_dir() else None
        if not format or format == "yaml":
            format = "yml"
        if format not in "json yml".split():
            raise ValueError("export_locations(): format not recognized: "+format)
        if dest.is_dir():
            dest = dest / f"taxonomyLocations.{format}"

        out = {}
        if basedir is True:
            out['baseDirectory'] = str(dest.parents[0])
            basedir = dest.parents[0]
        elif basedir:
            out['baseDirectory'] = str(basedir)
        elif basedir is None:
            basedir = dest.parents[0]

        taxlist = []
        for tax in self._tx.values():
            taxlist.append(deepcopy(tax))
            if basedir and Path(tax['location']).is_relative_to(basedir):
                taxlist[-1]['location'] = str(Path(tax['location']).relative_to(basedir))
        out['taxonomy'] = taxlist

        with open(dest, 'w') as fd:
            if format == "json":
                json.dump(out, fd, indent=2)
            else:
                yaml.dump(out, fd, indent=2, default_flow_style=False, sort_keys=False)
        

_taxon_parsers = {
    "https://data.nist.gov/od/dm/simple-taxonomy/v1.0": SimpleTaxonomy._from_content
}
def load_taxonomy(taxon_file, incl_depr: bool=False) -> Taxonomy:
    """
    return an Taxonomy instance for the definitions contained in a given file

    :param str|Path taxon_file:  the path to the file to read
    :param bool      incl_depr:  if True, include definitions of deprecated terms
    :raise IOError:   if the the file cannot be read for some reason, including because 
                      it doesn't exist or has an unrecognized format (based on its extension).
    :raise ValueEror: if the contents cannot be parsed
    """
    content = _load_file(taxon_file, "taxonomy definition")    # may raise exception
    
    if not content.get('_schema'):
        raise ValueError("Taxonomy definition schema (_schema) not specified")
    if content['_schema'] not in _summary_parsers:
        raise ValueError("Unrecognized taxonomy definition schema: "+str(data['schema']))

    return _taxon_parsers[content['_schema']](content)
                        
_summary_parsers = {
    "https://data.nist.gov/od/dm/simple-taxonomy/v1.0": SimpleTaxonomy._summary_from
}
def summarize(taxon_file):
    """
    return summary information about the contents of a taxonomy file for storing into
    a TaxonomyCache

    :param str|Path taxon_file:  the path to the file to read
    :raise IOError:   if the the file cannot be read for some reason, including because 
                      it doesn't exist or has an unrecognized format (based on its extension).
    :raise ValueEror: if the contents cannot be parsed
    """
    content = _load_file(taxon_file, "taxonomy definition")   # may raise exception
    
    if not content.get('_schema'):
        raise ValueError("Taxonomy definition schema (_schema) not specified")
    if content['_schema'] not in _summary_parsers:
        raise ValueError("Unrecognized taxonomy definition schema: "+str(content['_schema']))
    return _summary_parsers[content['_schema']](content)
            
            
        
