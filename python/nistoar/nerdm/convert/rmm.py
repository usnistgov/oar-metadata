"""
Classes and functions for converting NERDm records to and from NERDm objects as stored in the RMM.

The RMM includes three relevant collections:
  * ``records``     -- contains the latest versions of NERDm records.  This used by default for searches 
                       via the Science Data Portal (SDP).  The ``releaseHistory`` property included in
                       each record is expected to be up to date.  The value of the ``@id`` property will 
                       be of the general ARK form without any qualifying extensions.
  * ``releasesets`` -- contains ``ReleaseCollection`` resource records corresponding to each resource in
                       ``records``.  The ``releaseHistory`` property included in each record must include
                       all known (released) versions.  The ``@id`` property with include the "/pdr:v" 
                       extension, qualifying it as a ReleaseCollection ID.
  * ``versions``    -- contains all of the different versions of the NERDm records in ``records``.  The 
                       ``releaseHistory`` property in each record is not expected to be up to date but 
                       rather reflect the history at the time the version was ingested.  The ``@id`` 
                       property with include the version extension of the form /pdr:v/M.N.P, qualifying it 
                       as a version-specific ID.
"""
import re
from collections import OrderedDict
from collections.abc import Mapping
from urllib.parse import urljoin
from copy import deepcopy

from .. import validate
from .. import utils
from ..constants import RLS_SCHEMA_URI
from .latest import NERDm2Latest, VERSION_EXTENSION_RE, RELHIST_EXTENSION, to_version_ext


class NERDmForRMM(object):
    """
    a transformation engine for turning a "latest" NERDm record into records to be loaded into the RMM.
    """
    _pfxre = re.compile("^[^:]+:")
    _verextre = VERSION_EXTENSION_RE

    def __init__(self, logger=None, schemadir=None, pubeps={}):
        """
        create the converter.

        The pubeps parameter sets public PDR endpoint URLs to assume: those used by this converter
        can be provided via these key names:
          *  portalBase -- the common base URL for all PDR/SDP endpoints.  This must be an absolute
               URL and will be combined with any other relative URLs in this dictionary. 
               (Default: https://data.nist.gov/).
          *  landingPageService -- the base URL that, when combined with an ID, resolves to a landing 
               page.  If relative, it will be combined with the value for "portalBase" (Default: "/od/id/")
          *  distributionService -- the base URL that, when combined with an ID and filepath, downloads a 
               dataset. If relative, it will be combined with the value for "portalBase" (Default: "/od/ds/")
        :param dict   config:  a dictionary with conversion configuration data
                               in it (see class documentation)
        :param Logger logger:  a logger object that can be used to write warning
                               messages 
        :param str schemadir:  path to the directory containing NERDm schemas; provide this to 
                               enable automatic validation
        :param dict   pubeps:  a dictionary of public PDR endpoints that should be assumed when filling 
                               out URL values into the converted record.
        """
        if pubeps is None:
            pubeps = {}
        self.cfg = pubeps
        self._log = logger

        self._valid8r = None
        if schemadir:
            self._valid8r = validate.create_validator(schemadir, "_")

        self._2latest = NERDm2Latest()

        self._lpsbase = urljoin(self.cfg.get("portalBase", "https://data.nist.gov/"),
                                self.cfg.get("landingPageService", "od/id/"))
        self._distbase = urljoin(self.cfg.get("portalBase", "https://data.nist.gov/"),
                                 self.cfg.get("distributionService", "od/ds/"))


    def to_rmm(self, nerdm, defver="1.0.0"):
        """
        convert the NERDm record to an RMM-ready record.  The input NERDm record is taken to be the 
        "latest" record (thus the ``@id`` identifier should not have a trailing /_v extension).
        The output record will be a dictionary with three properties:
          * ``record`` -- the input record massaged to serve as the "latest" record in the RMM database
          * ``releaseSet`` -- a ``ReleaseCollection`` record derived from the ``releaseHistory`` of 
                          the input record
          * ``version`` -- the input record massaged to serve as the versioned copied of the record; in
                          particular, the ``@id`` property will be appended with a /_v/M.N.P extension for 
                          version indicated by the ``version`` property.  If the ``version`` property 
                          is not present, the value of the defval parameter will be used. 

        :param dict nerdm:   the NERDm resource record to convert
        :param str defver:   the default version to assume if the record does not include a ``version``
                             property
        :param bool validate:  if True, validate the output before returning.  Not that the input is 
                             not validated.  
        :raises ValueError:  if the input NERDm record is not sufficiently NERDm-like or appears to be 
                             the wrong type of input.  
        """
        if '@id' not in nerdm or '@type' not in nerdm:
            raise ValueError("Input apparently not a NERDm record (must have @id and @type)")

        if utils.is_type(nerdm, "ReleaseCollection") or nerdm.get('version', '').endswith(RELHIST_EXTENSION):
            raise ValueError("Input NERDm must not be a ReleaseCollection resource")

        rec = self._2latest.convert(nerdm)
        if 'version' not in rec:
            rec['version'] = defver
        if 'releaseHistory' in rec:
            for vref in rec['releaseHistory'].get('hasRelease',[]):
                vext = to_version_ext(vref['version']) if vref.get('version') else None
                if not vref.get('@id') or not self._verextre.search(vref['@id']):
                    if vext:
                        vref['@id'] = nerdm['@id'] + to_version_ext(vref['version'])
                    elif 'refid' in vref:
                        vref['@id'] = vref['refid']
                    else:
                        vref['@id'] = rec.get('@id')
                if 'refid' in vref:
                    del vref['refid']
        
        out = {
            'record': rec,
            'version': deepcopy(rec)  # deep copy
        }

        # massage the identifiers to match the PDR convention for "latest" and "versioned"
        rec['@id'] = self._verextre.sub('', rec['@id'])
        if not self._verextre.search(out['version']['@id']):
            out['version']['@id'] += to_version_ext(rec['version'])

        # massage URLs to point to versioned copies
        # tweak the PDR landing page
        if out['version'].get('landingPage'):
            m = re.match(r'^https?://[^/]+/od/id/(ark:/\d+/)?([^/]+)',
                         out['version']['landingPage'])
            if m and not out['version']['landingPage'][m.end():].startswith(RELHIST_EXTENSION):
                out['version']['landingPage'] += to_version_ext(rec['version'])

        # tweak PDR download URLs
        dsre = re.compile(r'^https?://[^/]+/od/ds/(ark:/\d+/)?([^/]+)')
        for cmp in [c for c in out['version'].get('components', []) if c.get('downloadURL')]:
            m = dsre.match(cmp['downloadURL'])
            if m and not cmp['downloadURL'][m.end():].startswith("_v/"):
                cmp['downloadURL'] = m.group() + "/_v/" + rec['version'] + cmp['downloadURL'][m.end():]

        def fromkeys(fromdict, todict, keys):
            for key in keys:
                if key in fromdict:
                    todict[key] = fromdict[key]

        # construct the ReleaseCollection from the base record
        vc = OrderedDict([
            ('_schema', rec['_schema']),
            ('_extensionSchemas', [ RLS_SCHEMA_URI ]),
            ('@type', ['nrdr:ReleaseCollection', 'dcat:Catalog'])
        ])
        vc['@id'] = rec['@id'] + RELHIST_EXTENSION
        fromkeys(rec, vc, "ediid title description keyword firstIssued publisher contactPoint theme".split())
        fromkeys(rec, vc, "abbrev version".split())

        if 'releaseHistory' in rec:
            vc['hasRelease'] = rec['releaseHistory'].get('hasRelease', [])
        else:
            vc['hasRelease'] = []

        if len(vc['hasRelease']) == 0:
            vc['hasRelease'] = [ self._2latest.create_release_ref(out['version']) ]

        # make sure the location property in release history points to the version specific value.
        # do this for all three renditions.
        for rel in vc['hasRelease'] + out['version'].get('releaseHistory',{}).get('hasRelease',[]):
            rel['location'] = self._lpsbase + rel['@id']

        out['releaseSet'] = vc

        return out

    def validate_rmm(self, rmmmd):
        """
        validate each of the objects under the "record", "version", and "releaseSet" are valid.  In 
        particular, this ensures that a NERDm record of the proper type appears under each property.  
        :param dict rmmmd:  the RMM-format record, as is returned by to_rmm().  
        :raise ValidationError: if there any of the objects under the three properties are invalid.
        """
        if not self._valid8r:
            raise RuntimeError("NERDmForRMM: not configured for validation")
        if 'record' in rmmmd:
            if not isinstance(rmmmd['version'], Mapping):
                raise validate.ValidationError("'record' property does not contain a NERDm record (type: "+
                                               str(type(rmmmd['record'])))
            if not utils.is_any_type(rmmmd['record'], ["Resource", "PublicDataResource", "DataPublication"]):
                raise validate.ValidationError("Unexpected @type for 'record': "+str(rmmmd['record']['@type']))
            self._valid8r.validate(rmmmd['record'])
        if 'version' in rmmmd:
            if not isinstance(rmmmd['version'], Mapping):
                raise validate.ValidationError("'version' property does not contain a NERDm record (type: "+
                                               str(type(rmmmd['version'])))
            if not utils.is_any_type(rmmmd['version'], ["Resource", "PublicDataResource", "DataPublication"]):
                raise validate.ValidationError("Unexpected @type for 'version': "
                                               +str(rmmmd['version']['@type']))
            self._valid8r.validate(rmmmd['version'])
        if 'releaseSet' in rmmmd:
            if not isinstance(rmmmd['releaseSet'], Mapping):
                raise validate.ValidationError("'releaseSet' property does not contain a NERDm record (type: "+
                                               str(type(rmmmd['releaseSet'])))
            if not utils.is_type(rmmmd['releaseSet'], "ReleaseCollection"):
                raise validate.ValidationError("'releaseSet' not a 'ReleaseCollection': "
                                               +str(rmmmd['releaseSet']['@type']))
            self._valid8r.validate(rmmmd['releaseSet'])
        

    def convert(self, nerdm, validate=False, defver="1.0.0"):
        out = self.to_rmm(nerdm, defver)
        if validate:
            self.validate_rmm(out)  # may raise an exception
        return out

    
