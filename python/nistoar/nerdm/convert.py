"""
Classes and functions for converting from and to the NERDm schema
"""
import os, json, re
from collections import OrderedDict

from .. import jq
from ..doi import resolve, is_DOI
from ..doi.resolving import Resolver
from .constants import CORE_SCHEMA_URI, PUB_SCHEMA_URI

class PODds2Res(object):
    """
    a transformation engine for converting POD Dataset records to NERDm
    resource records.

    This convert supports optional configuration parameters that affect the 
    transformation.  These are:
    :prop fetch_authors bool:  True if the converter should attempt to resolve
                               the DOI for the data to obtain author information.
                               This is ignored if there is no DOI in the POD 
                               record.  (default: False)
    :prop enrich_refs   bool:  True if references given as DOIs in the POD 
                               should be enriched with metadata retrieved by 
                               resolving the DOI.  (default: False)
    :prop doi_resolver  dict:  a dictionary for configuring the DOI resolver
                               used to retrieve additional information.  The
                               supported sub-parameters are documented as part 
                               of DOIResolver.from_config().  If enrich_refs 
                               is True, then it is recommended that 
                               doi_resolver.client_info be set.  
    """

    def __init__(self, jqlibdir, config=None, logger=None):
        """
        create the converter

        :param jqlibdir str:   path to the directory containing the nerdm jq
                               modules
        :param config  dict:   a dictionary with conversion configuration data
                               in it (see class documentation)
        :param logger Logger:  a logger object that can be used to write warning
                               messages 
        """
        self.jqt = jq.Jq('nerdm::podds2resource', jqlibdir, ["pod2nerdm:nerdm"])
        if config is None:
            config = {}
        self.cfg = config
        self._log = logger
        self._doires = DOIResolver.from_config(self.cfg.get('doi_resolver', {}))

    def convert(self, podds, id):
        """
        convert JSON-encoded data to a resource object

        :param podds str:   a string containing the JSON-formatted input POD 
                            Dataset record
        :param id str:      The identifier to assign to the output NERDm resource
        """
        out = self.jqt.transform(podds, {"id": id})
        if self.should_massage:
            self.massage(out)
        return out

    def convert_data(self, podds, id):
        """
        convert parsed POD record data to a resource object

        :param podds str:   a string containing the JSON-formatted input POD 
                            Dataset record
        :param id str:      The identifier to assign to the output NERDm resource
        """
        out = self.jqt.transform(json.dumps(podds), {"id": id})
        if self.should_massage:
            self.massage(out)
        return out

    def convert_file(self, poddsfile, id):
        """
        convert parsed POD record data to a resource object

        :param podds str:   a string containing the JSON-formatted input POD 
                            Dataset record
        :param id str:      The identifier to assign to the output NERDm resource
        """
        out = self.jqt.transform_file(poddsfile, {"id": id})
        if self.should_massage:
            self.massage(out)
        return out

    @property
    def should_massage(self):
        """
        True if either enrich_refs or fetch_authors is set to True
        """
        return self.cfg.get('enrich_refs', False) or \
               self.cfg.get('fetch_authors', False)

    @property
    def enrich_refs(self):
        """
        True if references given as DOIs in the POD should be enriched with 
        metadata retrieved by resolving the DOI.  
        """
        return self.cfg.get('enrich_refs', False)

    @enrich_refs.setter
    def enrich_refs(self, tf):
        self.cfg['enrich_refs'] = bool(tf)

    @enrich_refs.deleter
    def enrich_refs(self):
        del self.cfg['enrich_refs']

    @property
    def fetch_authors(self):
        """
        True if the converter should attempt to resolve the DOI for the 
        data to obtain author information when a POD includes a DOI for 
        the record.  
        """
        return self.cfg.get('fetch_authors', False)

    @fetch_authors.setter
    def fetch_authors(self, tf):
        self.cfg['fetch_authors'] = bool(tf)

    @fetch_authors.deleter
    def fetch_authors(self):
        del self.cfg['fetch_authors']

    def massage(self, nerd):
        """
        make further enriching updates to the given NERDm record based the 
        data already there, according to the configuration of this coverter 
        instance.  If fetch_authors is True, massage_authors() will be called.
        If enrich_refs is True, massage_refs will be called.  The given NERDm
        record will be updated in-situ

        @param nerd   the NERDm record to update
        """
        if self.fetch_authors:
            self.massage_authors(nerd)
        if self.enrich_refs:
            self.massage_refs(nerd)
        return nerd

    def massage_authors(self, nerd):
        """
        update the authors on the given NERDm record by resolving the associated
        DOI for the record.  If no DOI has been set, the record will be 
        unchanged.  This function ignores the value of the fetch_authors
        property, always updating as long as there is a DOI present.  Any
        previous author data will be overwritten.
        """
        if nerd.get('doi'):
            nerd['authors'] = self._doires.to_authors(nerd.get('doi'))
        return nerd
            
    def massage_refs(self, nerd):
        """
        update all of the reference identified with a DOI in the given NERDm 
        record with metadata retrieved by resolving the DOI.  Retrieved 
        metadata properties will overwrite those already in the reference 
        entry.  This function ignores the value of the enrich_refs
        property, always updating a reference as long as there is a DOI present.
        """
        if 'references' in nerd and isinstance(nerd['references'], list):
            refs = nerd['references']
            for i in range(len(nerd['references'])):
                if 'location' in refs[i] and is_DOI(refs[i]['location']):
                    newref = self._doires.to_reference(refs[i]['location'])
                    refs[i].update(newref)

        return nerd
            

class ComponentCounter(object):
    """
    a class for calculating inventories using the jq conversion macros
    """

    def __init__(self, jqlibdir):
        """
        create the counter

        :param jqlibdir str:   path to the directory containing the nerdm jq
                               modules
        """
        self._modules = ["pod2nerdm:nerdm"]
        self._jqlibdir = jqlibdir

        self._inv_jqt = self._make_jqt('nerdm::inventory_components')
                              
    def _make_jqt(self, macro):
        return jq.Jq(macro, self._jqlibdir, self._modules)

    def inventory(self, components):
        """
        return an inventory NERDm property value that reflects the make-up of 
        the given array of component data.
        """
        datastr = json.dumps(components)
        return self._inv_jqt.transform(datastr)

    def inventory_collection(self, components, collpath):
        """
        return an inventory for components within a given subcollection.

        :param components list:  a list of components that includes those within
                                 the requested subcollection
        :param collpath    str:  the filepath for the desired subcollection to 
                                 inventory
        """
        macro = 'nerdm::inventory_collection("{0}")'.format(collpath)
        jqt = self._make_jqt(macro)
        datastr = json.dumps(components)
        return jqt.transform(datastr)

    def inventory_by_type(self, components, collpath):
        """
        return an inventory broken down by type within a given subcollection.

        :param components list:  a list of components that includes those within
                                 the requested subcollection
        :param collpath    str:  the filepath for the desired subcollection to 
                                 inventory
        """
        macro = 'nerdm::inventory_by_type("{0}")'.format(collpath)
        jqt = self._make_jqt(macro)
        datastr = json.dumps(components)
        return jqt.transform(datastr)

class HierarchyBuilder(object):
    """
    a class for calculating data hierarchies using the jq conversion macros
    """

    def __init__(self, jqlibdir):
        """
        create the builder.

        :param jqlibdir str:   path to the directory containing the nerdm jq
                               modules
        """
        self._modules = ["pod2nerdm:nerdm"]
        self._jqlibdir = jqlibdir

        self._hier_jqt = self._make_jqt('nerdm::hierarchy("")')
                              
    def _make_jqt(self, macro):
        return jq.Jq(macro, self._jqlibdir, self._modules)

    def build_hierarchy(self, components):
        """
        return an array representing the data hierarchy for a given set of 
        components.

        This is implemented via the appropriate jq translation macros.  
        """
        datastr = json.dumps(components)
        return self._hier_jqt.transform(datastr)

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

        if info.source == "Datacite":
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
    if info.source == "Datacite":
        out['@type'] = ['npg:Dataset']
        out['refType'] = "References"
    elif info.source == "Crossref":
        out['@type'] = ['npg:Article']
        out['refType'] = "IsCitedBy"
    else:
        out['@type'] = ['npg:Document']
        out['refType'] = "References"

    if info.data.get('title'):
        out['title'] = info.data['title']
    if info.data.get('issued') and 'date-parts' in info.data['issued']:
        parts = info.data['issued']['date-parts'][0]
        if len(parts) > 0: out['issued'] = str(parts[0])
        if len(parts) > 1: out['issued'] += "-{0:0>2}".format(parts[1])
        if len(parts) > 2: out['issued'] += "-{0:0>2}".format(parts[2])

    if 'location' not in out:
        out['location'] = resolver + info.id

    # citation text
    if info.citation_text:
        out['citation'] = info.citation_text

    out['_extensionSchemas'] = [ CORE_SCHEMA_URI+"#/definitions/DCiteReference" ]
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
        out['affiliation'] = [ OrderedDict( [("@type", "schema:affiliation")] ) ]
        out['affiliation'][0]['title'] = creator['affiliation']

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
    

        
                                
    
