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
import jsonschema
from jsonmerge.strategies import Strategy
from jsonmerge.jsonvalue import JSONValue
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

class PreferBase(Strategy):
    """
    a jsonmerge strategy that will retain the base value unless it is 
    not set, in which the head value is taken.  The head effectively 
    serves as a default value.
    """

    def merge(self, walk, base, head, schema, meta, **kwargs):
        if (base is None or base.is_undef()) and \
           head is not None and not head.is_undef():
            return head

        return base

    def get_schema(self, walk, schema, meta, **kwargs):
        return walk.resolve_refs(schema)

class UniqueArray(Strategy):
    """
    merge arrays by only appending values not in the base, with caveats.

    The incompatible options is a list of lists where the inner lists represent
    mutually exclusive terms.  If one of those terms appear in the head and not 
    in the base but other terms from the mutually exclusive set do, then those
    other terms will be removed from the base before appending the new term. 
    """

    def merge(self, walk, base, head, schema, meta, incompatible=None, **kwargs):
        if incompatible is None:
            incompatible = []
        else:
            incompatible = [set(terms) for terms in incompatible]
            
        if head is None or head.is_undef():
            return base

        if not walk.is_type(head, "array"):
            head = JSONValue(val=[head.val], ref=head.ref)

        if base.is_undef():
            base = JSONValue({}, base.ref)
        elif not walk.is_type(base, "array"):
            base = JSONValue(val=[base.val], ref=base.ref)
        else:
            base = JSONValue(list(base.val), base.ref)

        def valInArray(val, ary):
            if isinstance(val, JSONValue):
                val = val.val
            return val in [(isinstance(v, JSONValue) and v.val) or v
                           for v in ary]

        def findIncompat(val):
            for _set in incompatible:
                if val in _set:
                    return _set
            return set()

        for newval in head.val:
            if valInArray(newval, base.val):
                continue
            choices = findIncompat(newval)
            for choice in choices:
                if newval == choice:
                    continue
                elif valInArray(choice, base):
                    base.val = [v for v in base.val if v != choice]
            base.val.append(newval)

        return base

    def get_schema(self, walk, schema, meta, **kwargs):
        subschema = schema.get('items')

        # Copied from jsonmerge.strategies.ArrayMergeById; see inline comment
        # there for note of concern
        walk.descend(subschema, meta)
        return schema

class ArrayMergeByMultiId(Strategy):
    """
    append object from the head array only if it does not appear in the base
    array based on a multi-property key.  

    The idRef options specifies the properties that represent the key.  If the 
    base array contains an object with the same set of values for those 
    properties as a head array item object, then the head object will be merged 
    with the matching head object; otherwise, the head object will be appended. 
    """
    def merge(self, walk, base, head, schema, meta, idRef=None,
              ignoreId=None, **kwargs):
        # implementation is base jsonmerge.strategies.ArrayMergeById
        if not walk.is_type(head, "array"):
            raise HeadInstanceError("Head for an 'arrayMergeByMultiId' merge "
                                    "strategy is not an array")

        if base.is_undef():
            base = JSONValue([], base.ref)
        else:
            if not walk.is_type(base, "array"):
                raise BaseInstanceError("Base for an 'arrayMergeByMultiId' "
                                        "merge strategy is not an array")
            base = JSONValue(list(base.val), base.ref)

        subschema = schema.get('items')

        if walk.is_type(subschema, "array"):
            raise SchemaError("'arrayMergeByMultiId' not supported when 'items' "
                              "is an array")

        if not idRef:
            idRef = [ "@id" ]

        def iter_index_key_item(jv):
            for i, item in enumerate(jv):
                key = {}
                for ref in idRef:
                    try:
                        key[ref] = walk.resolver.resolve_fragment(item.val, ref)
                    except jsonschema.RefResolutionError:
                        pass

                yield i, key, item

        # ensure that the items in the head array are unique based on
        # the key
        for i, key_1, item_1 in iter_index_key_item(head):
            for j, key_2, item_2 in iter_index_key_item(head):
                if j < i:
                    if key_1 == key_2:
                        raise HeadInstanceError("Id was not unique")
                else:
                    break

        for i, head_key, head_item in iter_index_key_item(head):

            if ignoreId and self.keys_match(head_key, ignoreId):
                continue

            key_count = 0
            for j, base_key, base_item in iter_index_key_item(base):

                if self.keys_match(base_key, head_key):
                    key_count += 1
                    # If there was a match, we replace with a merged item
                    base.val[j] = walk.descend(subschema, base_item,
                                               head_item, meta).val

            if key_count == 0:
                # If there wasn't a match, we append a new object
                base.val.append(walk.descend(subschema, JSONValue(undef=True),
                                             head_item, meta).val)
            if key_count > 1:
                raise BaseInstanceError("Id was not unique")

        return base

    def keys_match(self, basekey, headkey):
        """
        return True if the two given keys match.  

        A subclass can override this function to have more nuanced comparisons.
        """
        return basekey == headkey

    def get_schema(self, walk, schema, meta, **kwargs):
        subschema = schema.get('items')

        # Copied from jsonmerge.strategies.ArrayMergeById; see inline comment
        # there for note of concern
        walk.descend(subschema, meta)
        return schema

class TopicArray(ArrayMergeByMultiId):
    """
    This is a strategy for merging Topic arrays.  It allows for topics to be 
    typically identified either with an "@id" property or "scheme" and "tag"
    (though both is possible).  Two topic items refer to the topic if they 
    have matching "@id" values or matching "scheme"-"tag" combinations.  If 
    the two topics are idenfied differently, they are considered different.  
    Matching topic items from the head and base are merged via the 'objectMerge'
    strategy.

    This implementation is based on the ArrayMergeByMultiId.  The 'ignoreId'
    options is supported and behaves just like ArrayMergeByMultiId: items in 
    the head array that match this key will be ignored (i.e. not merged into 
    the output).  
    """

    def merge(self, walk, base, head, schema, meta, **kwargs):
        idRef = [ "@id", "scheme", "tag" ]
        if 'idRef' in kwargs:
            kwargs = dict(kwargs)
            del kwargs['idRef']

        return super(TopicArray, self).merge(walk, base, head, schema, meta,
                                             idRef=idRef, **kwargs)

    def _altkey(self, key):
        return { "scheme": key.get("scheme"), "tag": key.get("tag") }

    def keys_match(self, key1, key2):

        # if both have @id, use that solely
        if "@id" in key1 and "@id" in key2:
            return key1["@id"] == key2["@id"]

        # otherwise, use scheme and tag
        altkey1 = self._altkey(key1)
        altkey2 = self._altkey(key2)

        # if everything is None, respond with False
        if all([v is None for v in altkey1.values() + altkey2.values()]):
            return False
        
        if altkey1 == altkey2:
            return True

        return False

    
STRATEGIES = {
    "keepBase": KeepBase(),
    "preferBase": PreferBase(),
    "uniqueArray": UniqueArray(),
    "arrayMergeByMultiId": ArrayMergeByMultiId(),
    "topicArray": TopicArray()
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
