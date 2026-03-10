"""
Support for taxonomies defined using the OAR-internal "simple" schema/format
"""
from copy import deepcopy
from typing import Iterator, Mapping, NewType
from urllib.parse import quote as urlquote

from .base import Taxonomy, _load_file

# forward declaration
SimpleTaxonomy = NewType("SimpleTaxonomy", object)

class SimpleTaxonomy(Taxonomy):
    """
    a taxonomy that conforms to the simple taxonomy definition file.  

    This format is optimized for use with topic taxonomies used in NERDm records
    """
    SCHEMA_URI = "https://data.nist.gov/od/dm/simple-taxonomy/v1.0"

    @classmethod
    def from_file(cls, tfile, incl_depr: bool=False) -> SimpleTaxonomy:
        """
        return a SimpleTaxonomy instance read in from a simple taxonomy file

        :raise IOError:   if the the file cannot be read for some reason, including because 
                          it doesn't exist or has an unrecognized format (based on its extension).
        :raise ValueEror: if the contents cannot be parsed
        """
        content = _load_file(tfile, "taxonomy definition")   # may raise exception
        return cls._from_content(content, incl_depr)

    @classmethod
    def _from_content(cls, content, incl_depr=False):
        return cls(cls._parse_content(content), incl_depr)

    @classmethod
    def _parse_content(cls, content) -> Mapping:

        if not content.get("@id"):
            raise ValueError(f"{tfile}: Missing taxonomy identifier (@id)")
        content['id'] = content['@id']
        del content['@id']

        if not content.get('_schema'):
            content['_schema'] = cls.SCHEMA_URI
        content['schema'] = content['_schema']
        del content['_schema']

        return content

    @classmethod
    def _summary_from(cls, content: Mapping) -> Mapping:
        content = cls._parse_content(content)
        del content['vocab']
        return content

    def __init__(self, taxdata: Mapping, incl_depr: bool=False):
        """
        create an instance from the given taxonomy data.  Normally, this constructor is not 
        called directly; rather, :py:meth:`from_file` should be called.  
        """
        if not taxdata.get('id'):
            raise ValueError("Missing required property: id")
        super(SimpleTaxonomy, self).__init__(taxdata['id'])

        vocab = taxdata.get('vocab', [])
        if taxdata.get('vocab'):
            del taxdata['vocab']
        self._meta = taxdata
        idsansver = self.id.rsplit('/', 1)[0]

        self._bylabel = {}
        self._byid = {}

        def labelfor(term):
            out = ''
            if term.get('parent'):
                out = term['parent'] + ": "
            return out + term['term']
        def label2idfrag(label):
            return '#' + urlquote(label)
            
        for term in vocab:
            if not term.get('term'):
                continue
            if not term.get('label'):
                term['label'] = labelfor(term)

            if not term.get('id'):
                frag = label2idfrag(term['label'])
                term['id'] = self.id + frag

            if term.get('deprecatedSince'):
                # this is a deprecated term
                if incl_depr and term.get('lastSupported'):
                    # include it, but make sure we get the ID right
                    term['id'] = f"{idsansver}/v{term['lastSupported']}{term.get['id']}"
                else:
                    # skipping deprecated terms
                    continue
                
            self._byid[frag] = term
            self._bylabel[term['label']] = term

    def count(self) -> int:
        return len(self._byid)

    def about(self) -> Mapping:
        return deepcopy(self._meta)

    def get(self, termid: str) -> Mapping:
        if termid.startswith(self.id):
            termid = termid[len(self.id):]
        return self._byid.get(termid)

    def match_label(self, label: str) -> Mapping:
        return self._bylabel.get(label)

    def terms(self) -> Iterator[Mapping]:
        return self._byid.values()

    def compare_meaning(self, term1: Mapping, term2: Mapping) -> int:
        if not self.contains(term1['id']):
            raise ValueError(f"term not known ({term1['label']})")
        if not self.contains(term2['id']):
            raise ValueError(f"term not known ({term2['label']})")

        try:
            if term1['id'] == term2['id'] or term1['label'] == term2['label']:
                return 0
            elif term2['label'].startswith(term1['label']+':'):
                return -1
            elif term1['label'].startswith(term2['label']+':'):
                return 1
        except KeyError:
            pass

        # the terms are disjoint or one is ill-formed
        return None

