"""
Utility functions and classes for interrogating and manipulating NERDm metadata objects
"""
import re
import jsonpath_ng as jp
from collections.abc import Mapping, Sequence
from typing import Union, List

from nistoar.base.config import hget

META_PREFIXES = "_$"

def meta_prop_ch(nerdmd, metaname="schema", prefixchs=META_PREFIXES):
    """
    return the apparent meta-property prefix character in use in the given NERDm metadata object.
    This is usually either '$' or '_' (the latter being compatible with MongoDB).  This is determined, 
    by default, by looking for the "_schema" or "$schema" property in the given object.
    :param str metaname:  a property name to search for by prepending "_" or "$"
    :param str prefixchs:  a list of allowed prefix characters to look for (in order)
    """
    for ch in prefixchs:
        if ch+metaname in nerdmd:
            return ch
    raise ValueError("No %s%s metatag found (is this a NERDm record?)" % (prefixchs[0],metaname))

def is_type(nerdm, typename):
    """
    return True if the given metadata object is declared as being of the type with a given name.
    This implementation looks at the elements in the "@type" property and looks for one matching
    the name (ignoring prefixes)
    :param dict-like nerdm:   the NERDm object to test
    :param str    typename:   the name of the type to look for in the @type property.  Prefixes 
                                do not need to match
    """
    tps = nerdm.get('@type')
    if not tps:
        return False
    if not isinstance(tps, list):
        tps = [tps]
    
    pfxre = re.compile(r'^.*:')
    typename = pfxre.sub('', typename)
    for t in tps:
        if typename == pfxre.sub('', t):
            return True
    return False

def is_any_type(nerdm, typenames):
    """
    return True if any of the given type names match one of the declared types of the given NERDm
    object.  The type names are searched for in order.
    :param dict-like nerdm:   the NERDm object to test
    :param list  typenames:   a list of typenames to look for
    """
    return which_type(nerdm, typenames) is not None

def which_type(nerdm, typenames):
    """
    return the first type name from a given set that matches a type declared by a given NERDm object,
    or None otherwise
    :param dict-like nerdm:   the NERDm object to test
    :param list  typenames:   a list of typenames to look for
    """
    if not isinstance(typenames, (list,tuple)):
        raise TypeError("Not a list: "+str(typenames))
    for name in typenames:
        if is_type(nerdm, name):
            return name
    return None

def _insert_before_val(vals, inval, *beforevals):
    p = -1
    for insertpt in beforevals:
        try: 
            p = vals.index(insertpt)
            vals.insert(p, inval)
            break
        except ValueError:
            continue
    if p < 0:
        vals.append(inval)
    return vals

def insert_type(nerdm, newtype, *beforetypes):
    """
    ensure that a given type is included among the values of the `@type` property.  
    :param Mapping nerdm:  the NERDm object that is expected to have an @type property
    :param str newtype:    the `@type` value to look for and insert if not found
    :param *List[str] beforetypes:  a list of `@type` values to look for if `newtype` is 
                           not found in the current `@type` property; the new value should 
                           be inserted before the first of these values found in the 
                           currently set list.  If none of these values are found, the `newtype`
                           will be appended to the list.
    """
    types = nerdm.setdefault('@type', [])
    _insert_before_val(types, newtype, *beforetypes)
    return nerdm

def get_schema(nerdm, prefixchs=META_PREFIXES):
    schemaprop = meta_prop_ch(nerdm, prefixchs=prefixchs) + "schema"
    return nerdm.get(schemaprop)

def nerdm_schema_version(uri):
    """
    return the schema version field from the given NERDm schema URI.  The returned label will have 
    any "v" prefix removed.
    """
    if '/' not in uri:
        raise ValueError("Not a NERDm schema URI: "+str(uri))
    return re.sub(r'^.*/','', re.sub(r'#.*$', '', uri)).lstrip('v')

def get_nerdm_schema_version(nerdm):
    """
    return the schema version field from the given NERDm schema URI.  The returned label will have 
    any "v" prefix removed.
    """
    uri = get_schema(nerdm)
    if not uri:
        return None
    return nerdm_schema_version(uri)

_ver_delim = re.compile(r"[\._]")
_proper_ver = re.compile(r"^\d+([\._]\d+)*$")

class Version(object):
    """
    a version class that can facilitate comparisons
    """

    def _toint(self, field):
        try:
            return int(field)
        except ValueError:
            return field

    def __init__(self, vers):
        """
        convert a version string to a Version instance
        """
        self._vs = vers
        self.fields = [self._toint(n) for n in _ver_delim.split(self._vs)]

    def __str__(self):
        return self._vs

    def __eq__(self, other):
        if not isinstance(other, Version):
            other = Version(other)
        return self.fields == other.fields

    def __lt__(self, other):
        if not isinstance(other, Version):
            other = Version(other)
        return self.fields < other.fields

    def __le__(self, other):
        if not isinstance(other, Version):
            other = Version(other)
        return self < other or self == other

    def __ge__(self, other):
        return not (self < other)
    def __gt__(self, other):
        return not self.__le__(other)
    def __ne__(self, other):
        return not (self == other)

    @classmethod
    def is_proper_version(cls, vers):
        """
        return true if the given version string is of the form M.M.M... where
        each M is any non-negative number.   
        """
        return _proper_ver.match(vers) is not None

def cmp_versions(ver1, ver2):
    """
    compare two version strings for their order.
    :return int:  -1 if v1 < v2, 0 if v1 = v2, and +1 if v1 > v2
    """
    a = Version(ver1)
    b = Version(ver2)
    if a < b:
        return -1
    elif a == b:
        return 0
    return +1

_doc_properties = "title description asOntology notes comments valueDocumentation equivalentTo".split()
def declutter_schema(schema: Mapping, post2020: bool=False):
    """
    remove documentation nodes from a JSON Schema object in situ
    """
    for prop in _doc_properties:
        if prop in schema:
            del schema[prop]

    if "properties" in schema:
        for prop in schema['properties']:
            declutter_schema(schema['properties'][prop])

    deftag = "definitions" if not post2020 else "$defs"
    if deftag in schema:
        for defname in schema[deftag]:
            declutter_schema(schema[deftag][defname])

    for seq in "allOf anyOf oneOf".split():
        if seq in schema:
            for itm in schema[seq]:
                declutter_schema(itm)


def unrequire_props_in(schema: Mapping, locations: Union[str, List[str]], post2020: bool=False):
    """
    remove ``"required"`` fields at the specified locations from within the given JSON Schema.

    The provided locations should point to schema definitions within the given schema dictionary.
    This function will remove the ``"required"`` property within the located schema (if it exists) 
    as well as any found within ``"allOf"``, ``"anyOf"``, or ``"oneOf"`` properties.  
    
    :param dict        schema:  a dictionary representing a JSON Schema 
    :param str|list locations:  slash-delimited paths to an internal schema that contains a required.  
                                An example might be "definitions/Resource".  An empty string indicates 
                                 the top-level processa 
    """
    if isinstance(locations, str):
        locations = [ locations ]

    for loc in locations:
        subsch = hget(schema, loc)
        if subsch and isinstance(subsch, Mapping):
            if "required" in subsch:
                del subsch["required"]
            for seq in "allOf anyOf oneOf".split():
                if seq in subsch and isinstance(subsch[seq], Sequence):
                    for itm in subsch[seq]:
                        unrequire_props_in(itm, "$", post2020)
                    

def loosen_schema(schema: Mapping, directives: Mapping, opts=None):
    """
    apply the given loosening directive to the given JSON Schema.  The directives is a 
    dictionary describes what to do with the following properties (the directives) supported:

    ``derequire``
         a list of type definitions within the schema from which the required property 
         should be removed (via :py:func:`~nistoar.nerdm.utils.unrequire_props_in`).  Each
         type name listed will be assumed to be an item under the "definitions" node in the 
         schema this directive is applied to.
    ``dedocument``
         a boolean indicating whether the documentation annotations should be removed from 
         the schema.  If not set, the default is determined by opts.dedoc if opts is given or
         True, otherwise.  

    :param dict schema:      the schema document as a JSON Schema schema dictionary
    :param dict directives:  the dictionary of directives to apply
    :param opt:              an options object (containing scripts command-line options)
    """
    if directives.get("dedocument", True):
        declutter_schema(schema)

    p2020 = directives.get("post2020")
    deftag = "$defs" if p2020 else "definitions"

    dereqtps = [ deftag+'.'+t for t in directives.get("derequire", []) ]
    unrequire_props_in(schema, dereqtps, p2020)

