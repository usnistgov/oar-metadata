"""
methods for merging POD-sourced NERDm records with enhancing annotations.

By default, initial NERDm records are generated by converting a POD record
generated by the MIDAS system.  Users can use MIDAS to update the POD
metadata.  Through the PDR, they can enhance their default metadata
with additional metadata.  Updates made seperately by these different
systems must be integrated to create a single NERDm view of a
resource.  

The PDR handles this by storing enhanced metadata separately from the
default generated by MIDAS.  This module handles the merging of those
two source documents to create the final NERDm record.  

This module uses the jsonmerge package to handle these mergers.
Strategies for merging the source data are configured via special
mark-up added to the NERDm schemas.  This module allows for different
named configurations (with different sets of marked-up schemas); the
mergerFor() factory function allows one to choose the desired
configuration.  
"""
import os, logging, json
from abc import ABCMeta, abstractmethod

import ejsonschema.schemaloader as ejsl
from jsonmerge.strategies import Strategy
from jsonmerge import Merger

from .exceptions import MergeError

class KeepBase(Strategy):
    """
    a jsonmerge strategy that will retain the base value, ignoring the
    head.  If the base does not include a value, the value from the
    head will not be merged in.  This locks out certain values from
    being updated.  
    """

    def merge(self, walk, base, head, schema, meta, **kwargs):
        return base

    def get_schema(self, walk, schema, meta, **kwargs):
        return walk.resolve_refs(schema)

STRATEGIES = {
    "keepBase": KeepBase()
}

class MergerFactoryBase(object):
    """
    a class for creating Merger objects.  The factory is responsible
    for locating and loading the necessary schema as well as
    configuring the strategies available.  
    """
    __metaclass__ = ABCMeta

    def __init__(self, logger=None):
        """
        initialize the logger for the factory
        """
        if not logger:
            logger = logging.getLogger(__name__)
        self.logger = logger

    @abstractmethod
    def make_merger(self, stratname, typename):
        """
        return a Merger instance using a set of strategies having a name
        and a schema for a given type.  

        :param stratname str:  a name for the set of strategies to use.  This 
                               corresponds to a set of schemas that have merge 
                               strategies encoded into them.  
        :param typename  str:  a name for the particular type that the data
                               to be merged conform to.  
        """
        raise NotImplemented
    
class DirBasedMergerFactory(MergerFactoryBase):
    """
    This factory is based on a convention for storing the schemas in directories.
    Initialized with a root directory for schemas, it assumes that strategy 
    convention names correspond to the names of directories directly within
    the root.  Type names correspond to schema files (TYPE-schema.json) with 
    references to types potentially in on other schemas in the same directory.
    """

    def __init__(self, rootdir, strategies=(), logger=None):
        """
        create a factory that will look for schemas in subdirectories of a 
        root directory

        :param rootdir     str:  the path to the root directory containing the 
                                 schemas
        :param strategies dict:  a custom dictionary of strategy names to 
                                 Strategy instances.  
        :param logger   Logger:  a logger object to use capture messages
        """
        super(DirBasedMergerFactory, self).__init__(logger)
        if not rootdir:
            raise ValueError("DirBasedMergerFactory: rootdir not provided")
        if not isinstance(rootdir, (str, unicode)):
            raise TypeError("DirBasedMergerFactory: rootdir not a str: {0}".
                            format(str(rootdir)))
        if not os.path.exists(rootdir):
            raise IOError(2, "Directory not found: {0}".format(rootdir))
        if not os.path.isdir(rootdir):
            raise IOError(21,"rootdir not a directory path: {0}".format(rootdir))

        self.root = rootdir
        self.strategies = STRATEGIES.copy()
        if strategies:
            self.strategies.update(strategies)

    def make_merger(self, stratname, typename):
        """
        return a Merger instance using a set of strategies having a name
        and a schema for a given type.  

        :param stratname str:  a name for the set of strategies to use.  This 
                               corresponds to a set of schemas that have merge 
                               strategies encoded into them.  
        :param typename  str:  a name for the particular type that the data
                               to be merged conform to.  
        """
        stratdir = os.path.join(self.root, stratname)
        if stratname.startswith('.') or not os.path.exists(stratdir):
            raise MergeError("Strategy convention not recognized: "+stratname)

        cache = ejsl.DirectorySchemaCache(stratdir)
        
        schemafile = os.path.join(stratdir, "{0}-schema.json".format(typename))
        if not os.path.exists(schemafile):
            raise MergeError("Schema Type name not supported: "+typename)

        with open(schemafile) as fd:
            schema = json.load(fd)

        out = Merger(schema, self.strategies, def_objclass='OrderedDict')
        for schema in cache.schemas().values():
            out.cache_schema(schema)

        return out

    def strategy_conventions(self):
        """
        return a list of the supported strategy conventions.  Any name from 
        this list can be passed to the makeMerger() function.
        """
        return [d for d in os.listdir(self.root) if not d.startswith('.')]
        
    
MergerFactory = DirBasedMergerFactory
