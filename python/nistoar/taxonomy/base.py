"""
Base classes and utility functions for 
:py:mod:`supporting taxonomies <nistoar.pdr.utils.taxonomy>`.
"""
import json, re, os
from pathlib import Path
from abc import ABC, abstractmethod
from logging import Logger
from copy import deepcopy
from typing import Iterator, Mapping

import yaml

class Taxonomy(ABC):
    """
    a container of terms defined in a taxonomy
    """
    def __init__(self, id):
        self._id = id

    @property 
    def id(self) -> str:
        """
        return the identifier for this taxonomy
        """
        return self._id

    @abstractmethod
    def count(self) -> int:
        """
        return the number of terms in this taxonomy
        """
        raise NotImplemented()

    @abstractmethod
    def about(self) -> Mapping:
        """
        returns a dictionary of information about a taxonomy as a whole
        """
        raise NotImplemented()

    @abstractmethod
    def match_label(self, label: str) -> Mapping:
        """
        returns the definition of term in this taxonomy given its given its prefered label
        :rtype: dict
        """
        raise NotImplemented()

    @abstractmethod
    def get(self, termid: str) -> Mapping:
        """
        returns the definition of term in this taxonomy given its URI identifier.  The 
        termid can either be the absolute, globally-unique ID or one relative to this 
        taxonomy's identifier.  
        :rtype: dict
        """
        raise NotImplemented()

    @abstractmethod
    def terms(self) -> Iterator[Mapping]:
        """
        iterate through all of the terms in this taxonomy, returning each term description
        as a dictionary (as in like from :py:meth:`get`)
        """
        raise NotImplemented()

    def contains(self, labelorid: str) -> bool:
        """
        return True if the given term identifier or label are defined in this taxonomy
        """
        if self._bylabel.get(labelorid):
            return True
        if labelorid.startswith(self.id):
            labelorid = labelorid[len(self.id):]
        return bool(self._byid.get(labelorid))

    @abstractmethod
    def compare_meaning(self, term1: Mapping, term2: Mapping) -> int:
        """
        return -1, 0, or +1, depending on whether term1 broader, equivalent, or narrower in 
        meaning, respectively, than term2, based on the relationships defined in this taxonomy.
        None is returned if the terms are disjoint--i.e., they have no relationships between 
        them.

        :param dict term1:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.
        :param dict term2:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.
        :raise ValueError:  if ``term1`` or ``term2`` is unknown to this taxonomy.
        """
        raise NotImplemented()

    def is_broader_than(self, term1: Mapping, term2: Mapping) -> bool:
        """
        return True if term1 is a more broad term than term2, based on the relationships 
        defined in this taxonomy.  False is returned if either term is not known to this 
        taxonomy.

        :param dict term1:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.
        :param dict term2:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.
        """
        try:
            diff = self.compare_meaning(term1, term2)
            return diff is not None and diff < 0
        except ValueError:
            return False

    def equivalent(self, term1, term2):
        """
        return True if the two given terms can be considered equivalent in meaning, based on 
        relationships given in this taxonomy.  The two terms need not have the same identifier.

        :param dict term1:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.
        :param dict term2:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.
        """
        try:
            diff = self.compare_meaning(term1, term2)
            return diff is not None and diff == 0
        except ValueError:
            return False

    def is_narrower_than_or_equiv(self, term1, term2):
        """
        return True if term1 either equivalent to term2 or is a more narrow term than term2, 
        based on the relationships defined in this taxonomy.  False is returned if either term 
        is not known to this taxonomy.

        :param dict term1:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.
        :param dict term2:  a term known to this taxonomy, given as a dictionary like that 
                            returned by :py:meth:`get`.        
        """
        try:
            diff = self.compare_meaning(term1, term2)
            return diff is not None and diff >= 0
        except ValueError:
            return False

class TaxonomyCache(ABC):
    """
    a class that manages access to taxonomy definitions.

    A cache has access to number of taxonomy definitions.  Creating an instance will typically
    load metadata for the taxonomies into memory to allow quick lookup and loading the definitions 
    from their sources.  
    """

    def __init__(self, log: Logger=None):
        self.log = log

    @abstractmethod
    def load_taxonomy(self, id) -> Taxonomy:
        """
        return a Taxonomy object with access to the terms in the taxonomy with the given 
        identifier

        :param str id:  the identifier for the taxonomy (which should include the version 
                        component, if applicable)
        :return:  the taxonomy with all its terms accessible
        """
        raise NotImplemented()

    @abstractmethod
    def about(self, id) -> Mapping:
        """
        return a small dictionary describing the taxonomy with the given identifier, or None
        if the identifier is not recognized
        """
        raise NotImplemented()

    @abstractmethod
    def count(self) -> int:
        """
        return the total number of taxonomies available
        """
        return 0

    @abstractmethod
    def ids(self) -> Iterator[str]:
        """
        return an iderator of the identifiers for the taxonomies available via this cache
        """
        raise NotImplemented()

    @abstractmethod
    def reload(self, **kwargs):
        """
        reload the taxonomy metadata from the cache's source
        """
        raise NotImplemented()

def _load_file(path, filetype:str="data") -> Mapping:
    """
    read a data file as either JSON or YAML (depending on the extension) and return 
    its contents as a dictionary.  Return None if it can't be read

    :param str      path:  the full path to the file to be read
    :param Logger errlog:  the Logger to send a warning message to if the file can't be read
    :param str  filetype:  a string to use in warning message indicating the type of file 
                           to be read.
    :raises IOError:  if the file cannot be read for some reason, including an unsupported 
                      format (as implied by its file extension)
    :raises ValueError:  if the content of the file cannot be parsed for syntactic reasons
    """
    path = Path(path)
    try:
        if path.suffix == ".json":
            with open(path) as fd:
                data = json.load(fd)
        elif path.suffix == ".yml" or path.suffix == ".yaml":
            with open(path) as fd:
                data = yaml.safe_load(fd)
        else:
            raise RuntimeError("unsupported file format")

        return data

    except (json.JSONDecodeError, yaml.YAMLError) as ex:
        raise ValueError("%s: Unable to parse %s file: %s" %
                         (str(path), filetype, str(ex)))  from ex
    except (IOError, RuntimeError) as ex:
        raise IOError("%s: Failed to read %s file: %s" %
                      (str(path), filetype, str(ex)))    from ex

        
