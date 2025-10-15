"""
Class and functions for converting a DOI into a NERDm data like a Reference or a 
list of authors
"""
import re
from collections import OrderedDict
from collections.abc import Mapping

from ...doi import resolve
from ...doi.resolving import Resolver
from ..constants import CORE_SCHEMA_URI, PUB_SCHEMA_URI, BIB_SCHEMA_URI
                         
class DOIResolver(object):
    """
    a class that given represents a service that returns a NERDm reference
    object given a DOI for the reference.   

    A reference is a citation to (typically) a journal article or data 
    publication.  A reference MAY be referenceable via a DOI.  This class 
    can resolve a DOI to a set of metadata provided by the DOI minter and 
    use it to fill out NERDm metadata.
    """

    def __init__(self, client_info=None, resolver=None):
        """
        create the resolver
        """
        if resolver is None:
            resolver = "https://doi.org/"
        self.resolver = Resolver(client_info, resolver)

    def to_reference(self, doi):
        """
        convert the given DOI to a NERDm reference description
        """
        return _doiinfo2reference( self.resolver.resolve(doi),
                                   self.resolver._resolver )
    
    def to_authors(self, doi):
        """
        convert the given DOI to an array of NERDm Person descriptions 
        representing an ordered list of authors
        """
        info = self.resolver.resolve(doi)
        out = []

        if info.source == "Crosscite" or info.source == "Datacite":
            out = datacite_creators2nerdm_authors(info.native.get('creators'))
        elif info.source == "Crossref":
            out = crossref_authors2nerdm_authors(info.native.get('author'))
        else:
            out = citeproc_authors2nerdm_authors(info.data.get('author'))
        
        return out

    @classmethod
    def from_config(cls, cfg):
        """
        construct a DOIResolver from a configuration dictionary.  The following
        properties are supported:

        :prop resolver_url str:  the base URL for the resolver service to use
        :prop client_info dict:  a configuration of info identifying the 
                                   client application using the resolver.
        
        The client_info property provides remote DOI resolving services 
        (namely Crossref) with information about the client for their 
        auditing and logging purposes.  The property accepts the following 
        subproperties:
        :prop app_name str:     a name for the client applicaiton
        :prop app_version str:  a version string for the application
        :prop app_url str:     a URL for learning more about the application
        :prop email str:        a contact email address for the client
        """
        resolver = cfg.get('resolver_url')
        ci = (
            cfg.get('app_name', "unspecified OAR-metadata client"),
            cfg.get('app_version', "unknown"),
            cfg.get('app_url', "https://github.com/usnistgov/oar-metadata"),
            cfg.get('email', "datasupport@nist.gov")
        )
        return DOIResolver(ci, resolver)

def _doiinfo2reference(info, resolver):
    out = OrderedDict( [('@id', "doi:"+info.id)] )

    # what type of reference
    tp = info.data.get('type')
    if not tp:
        if info.source == "Datacite":
            tp = 'dataset'
        elif info.source == "Crossref":
            tp = 'article'
        else:
            tp = 'document'

    if tp == 'dataset':
        out['@type'] = ['schema:Dataset']
        out['refType'] = "References"
    elif tp == 'journal-article' or tp.startswith('article'):
        out['@type'] = ['schema:Article']
        out['refType'] = "IsCitedBy"
    elif tp == 'book':
        out['@type'] = ['schema:Book']
        out['refType'] = "References"
    elif tp == 'thesis':
        out['@type'] = ['schema:Thesis']
        out['refType'] = "References"
    else:
        out['@type'] = ['npg:Document']
        out['refType'] = "References"

    if info.data.get('title'):
        out['title'] = info.data['title']

    if info.data.get('issued') and 'date-parts' in info.data['issued'] and \
       len(info.data['issued']['date-parts']) > 0:
        issued = _date_parts2date(info.data['issued']['date-parts'][0])
        if issued:
            out['issued'] = issued
            
    if 'location' not in out:
        out['location'] = resolver + info.id

    # citation text
    if info.citation_text:
        out['citation'] = info.citation_text

    out['_extensionSchemas'] = [ BIB_SCHEMA_URI+"#/definitions/DCiteReference" ]
    return out

def _date_parts2date(parts):
    if not parts:
        return None
    
    if not isinstance(parts[0], int) or parts[0] < 1000 or parts[0] > 3000:
        return None
    out = str(parts[0])

    if len(parts) > 1:
        if not isinstance(parts[1], int) or parts[1] < 1 or parts[1] > 12:
            return out
        out += "-{0:0>2}".format(parts[1])

    if len(parts) > 2 and \
       isinstance(parts[2], int) and parts[2] > 0 and parts[2] < 32:
        out += "-{0:0>2}".format(parts[2])

    return out

def citeproc_author2nerdm_author(author):
    """
    convert a description of an author using the Citeproc schema into one 
    using the NERDm schema.
    """
    out = OrderedDict( [('@type', 'foaf:Person')] )

    if author.get('family'):
        out['familyName'] = author['family']
    if author.get('given'):
        out['givenName'] = author['given']
    if 'givenName' in out and 'familyName' in out:
        out['fn'] = "%s %s" % (out['givenName'], out['familyName'])

    # ORCID
    if author.get('ORCID'):
        out['orcid'] = re.sub(r'^https?://[^/\.]*orcid.org/', '',
                              author['ORCID'])

    # affiliation
    if isinstance(author.get('affiliation'), list) and \
       len(author['affiliation']) > 0:
        out['affiliation'] = []
        for affil in author['affiliation']:
            outa = OrderedDict()
            if isinstance(affil, str):
                outa['title'] = affil
            elif 'name' in affil:
                outa['title'] = affil['name']
            if outa:
                outa['@type'] = 'schema:affiliation'
                out['affiliation'].append(outa)

    return out

def citeproc_authors2nerdm_authors(authors):
    """
    convert a description of an author list using the Citeproc schema into one 
    using the NERDm schema.
    """
    out = []
    for auth in authors:
        out.append(citeproc_author2nerdm_author(auth))
    return out


def crossref_author2nerdm_author(author):
    """
    convert a description of an author using the Crossref schema into one 
    using the NERDm schema.
    """
    return citeproc_author2nerdm_author(author)

def crossref_authors2nerdm_authors(authors):
    """
    convert a description of an author list using the Crossref schema into one 
    using the NERDm schema.
    """
    out = []
    for auth in authors:
        out.append(crossref_author2nerdm_author(auth))
    return out


def datacite_creator2nerdm_author(creator):
    """
    convert a description of a dataset creator using the Datacite schema into 
    an publication author using the NERDm schema.
    """
    out = OrderedDict()

    if creator.get('nameType') == "Personal":
        if creator.get('familyName'):
            out['familyName'] = creator['familyName']
        if creator.get('givenName'):
            out['givenName'] = creator['givenName']

        if creator.get('name'):
            if ', ' in creator['name']:
                parts = creator['name'].split(', ', 1)
                if 'givenName' not in out and len(parts) > 1:
                    out['givenName'] = parts[1]
                if 'familyName' not in out:
                    out['familyName'] = parts[0]
                if 'givenName' in out and 'familyName' in out:
                    out['fn'] = "%s %s" % (parts[1], parts[0])

        if 'fn' not in out and 'givenName' in out and 'familyName' in out:
            out['fn'] = "%s %s" % (out['givenName'], out['familyName'])

    else:
        if 'name' in creator:
            out['fn'] = creator['name']

    # ORCID
    if 'nameIdentifiers' in creator:
        for nmid in creator['nameIdentifiers']:
          if nmid.get("nameIdentifierScheme") == 'ORCID' or \
             nmid.get("nameIdentifier","").startswith("https://orcid.org/"):
              out['orcid'] = re.sub(r'^https?://[^/\.]*orcid.org/', '',
                                    nmid['nameIdentifier'])
              break

    # affiliation
    if creator.get('affiliation'):
        out['affiliation'] = []
        if isinstance(creator.get('affiliation'), str):
            out['affiliation'].append(
                OrderedDict( [("@type", "schema:affiliation"),
                              ('title', creator.get('affiliation'))] )
            )
        else:
            for caffil in creator.get('affiliation',[]):
                affil = OrderedDict( [("@type", "schema:affiliation")] )
                if isinstance(caffil, Mapping):
                    affil['title'] = caffil.get('name','')
                else:
                    affil['title'] = caffil
                out['affiliation'].append(affil)

    return out

def datacite_creators2nerdm_authors(authors):
    """
    convert a description of an author list using the Crossref schema into one 
    using the NERDm schema.
    """
    out = []
    for auth in authors:
        out.append(datacite_creator2nerdm_author(auth))
    return out

def citeproc_ref2nerdm_ref(data):
    """
    convert a reference description in CiteProc format to a reference 
    description in NERDm format.
    """
    raise NotImplementedError()

