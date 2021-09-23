"""
load NERDm records into the RMM's MongoDB database
"""
import json, os, sys
from collections import Mapping

from .loader import (Loader, RecordIngestError, JSONEncodingError,
                     UpdateWarning, LoadLog)
from .loader import ValidationError, SchemaError, RefResolutionError
from nistoar.nerdm import utils
from nistoar.nerdm.convert.rmm import NERDmForRMM

DEF_BASE_SCHEMA = "https://data.nist.gov/od/dm/nerdm-schema/v0.5#"
DEF_SCHEMA = DEF_BASE_SCHEMA + "/definitions/Resource"

LATEST_COLLECTION_NAME="record"
VERSIONS_COLLECTION_NAME="versions"
RELEASES_COLLECTION_NAME="releasesets"

class _NERDmRenditionLoader(Loader):
    """
    a base class for loading a rendition of a NERDm record into one of the data collections holding 
    NERDm metadata (record, versions, releaseSets)
    """
    def __init__(self, collection_name, dburl, schemadir, log=None, defschema=DEF_SCHEMA):
        """
        create the loader.  

        :param str collection_name
        :param str dburl:      the URL of MongoDB database in the form,
                               'mongodb://HOST:PORT/DBNAME' 
        :param str schemadir:  the path to a directory containing the JSON 
                               schemas needed to validate the input JSON data.
        :param logging.Logger log:  a logging instance that messages can be 
                               sent to.  If not provided, warnings might be 
                               issued via the warnings module.  
        :param str defschema:  the URI for the schema to validated new records 
                               against by default. 
        """
        super(_NERDmRenditionLoader, self).__init__(dburl, collection_name, schemadir, log)
        self._schema = defschema

    def _get_upd_key(self, nerdm):
        return { "@id": nerdm['@id'] }

    def _get_onupdate(self, nerdm):
        newver = nerdm.get('version', "1.0.0")
        # replace previous record if the version of new rec is newer or same as previous
        return lambda data, key: utils.cmp_versions(newver, data.get('version', '1.0.0')) >= 0

    def load(self, rec, validate=True, results=None, id=None):
        """
        load a NERDm resource record into the database
        :param rec dict:     the NERDm JSON record to load
        :param validate bool:   False if validation should be skipped before
                            loading; otherwise, loading will fail if the input
                            data is not valid.
        """
        if not results:
            results = self._mkloadlog()

        try:
            key = self._get_upd_key(rec)
        except KeyError as ex:
            if id is None:
                id = str({'@id': '?'})
            return results.add(id, RecordIngestError("Data is missing input key value, @id"))
        if id is None:
            id = key

        errs = None
        if validate:
            schemauri = rec.get("_schema")
            if not schemauri:
                schemauri = self._schema

            errs = self.validate(rec, schemauri)
            if errs:
                return results.add(id, errs)

        try:
            if self.load_data(rec, key, self._get_onupdate(rec)):
                results.add(key, None)
        except Exception as ex:
            results.add(key, [ex])
        return results

    def _mkloadlog(self):
        return LoadLog("NERDm resources")

    

class NERDmLoader(_NERDmRenditionLoader):
    """
    a class for validating and loading NERDm records into the Mongo database.
    """

    class LatestLoader(_NERDmRenditionLoader):
        def __init__(self, dburl, schemadir, log=None):
            super(NERDmLoader.LatestLoader, self).__init__(LATEST_COLLECTION_NAME, dburl, schemadir, log)

    class ReleaseSetLoader(_NERDmRenditionLoader):
        def __init__(self, dburl, schemadir, log=None):
            super(NERDmLoader.ReleaseSetLoader, self).__init__(RELEASES_COLLECTION_NAME, dburl, schemadir, log)


    def __init__(self, dburl, schemadir, onupdate='quiet', log=None, defschema=DEF_SCHEMA):
        """
        create the loader.  

        :param dburl  str:    the URL of MongoDB database in the form,
                              'mongodb://HOST:PORT/DBNAME' 
        :param schemadir str:  the path to a directory containing the JSON 
                            schemas needed to validate the input JSON data.
        :param onupdate:    a string or function that controls reactions to 
                            the need to update an existing record; see 
                            documentation for load_data().
        :param log logging.Logger:  a logging instance that messages can be 
                              sent to.  If not provided, warnings might be 
                              issued via the warnings module.  
        :param defschema str:  the URI for the schema to validated new records 
                               against by default. 
        """
        super(NERDmLoader, self).__init__(VERSIONS_COLLECTION_NAME, dburl, schemadir, log, defschema)
        self.onupdate = onupdate

        self.lateloadr = self.LatestLoader(dburl, schemadir, log)
        self.relloadr  = self.ReleaseSetLoader(dburl, schemadir, log)
        self.tormm = NERDmForRMM(log, schemadir)

    def connect(self):
        """
        establish a connection to the database.
        """
        super(NERDmLoader, self).connect()
        self.lateloadr._client = self._client
        self.lateloadr._db = self._db
        self.relloadr._client = self._client
        self.relloadr._db = self._db
        
    def disconnect(self):
        """
        close the connection to the database.
        """
        try:
            super(NERDmLoader, self).disconnect()
        finally:
            self.lateloadr._client = None
            self.relloadr._db = None

    def _get_upd_key(self, nerdm):
        return { "@id": nerdm['@id'], "version": nerdm.get('version', '1.0.0') }

    def _get_onupdate(self, nerdm):
        return self.onupdate

    def load(self, rec, validate=True, results=None, id=None):
        """
        load a NERDm resource record into the database
        :param dict rec:     the NERDm JSON record to load
        :param bool validate:   False if validation should be skipped before
                            loading; otherwise, loading will fail if the input
                            data is not valid.
        :param LoadLog results:  the results object to add loading result error messages to.  Provide
                            this when chaining loaders together
        :param str|dict id:  an identifier for the record being loaded that messages should be associated
                            with.  
        """
        if not results:
            results = self._mkloadlog()

        # the input is a versioned Resource record; convert it into its three parts for the three
        # collections (record, versions, releaseSets)
        parts = self.tormm.convert(rec, validate=False)
        errs = []
        for prop in "record version releaseSet".split():
            if prop not in parts or not isinstance(parts[prop], Mapping):
                errs.append(
                    ValidationError("Failed to extract %s record from input NERDm Resource" % prop)
                )
        if errs:
            if id is None:
                id = json.dumps({'@id': rec.get('@id','?')})
            return results.add(id, errs)
            
        # now load the versioned record first; if that's successful, we'll load the others

        # determine the versions udpate key
        try:
            key = self._get_upd_key(parts['version'])
            id = json.dumps(key)
        except KeyError as ex:
            if id is None:
                id = json.dumps({'@id': '?'})
            return results.add(id,
                     RecordIngestError("Data is missing input key value, @id"))
        if id is None:
            id = key

        # validate the versions record (if requested)
        errs = None
        if validate:
            schemauri = parts['version'].get("_schema")
            if not schemauri:
                schemauri = self._schema

            errs = self.validate(parts['version'], schemauri)
            if errs:
                return results.add(id, errs)

        # load the version record
        try:
            if self.load_data(parts['version'], key, self._get_onupdate(parts['version'])):
                results.add(id, None)
        except Exception as ex:
            errs = [ex]
            return results.add(id, errs)
        

        # now (conditionally) load the other parts.  (These will not get loaded if the version is not
        # new enough)
        self.lateloadr.load(parts['record'], validate, results, key)
        self.relloadr.load(parts['releaseSet'], validate, results, key)
        return results
    

    def load_from_file(self, filepath, validate=True, results=None):
        """
        load a NERDm resource record from a file (containing one resource)
        """
        with open(filepath) as fd:
            try:
                data = json.load(fd)
            except ValueError as ex:
                raise JSONEncodingError(ex)
        return self.load(data, validate=validate, results=results, id=filepath)

    def load_from_dir(self, dirpath, validate=True, results=None):
        """
        load all the records found in a directory.  This will attempt to load
        all files in the given directory with the extension, '.json'
        """
        for root, dirs, files in os.walk(dirpath):
            # don't look in .directorys
            for i in range(len(dirs)-1, -1, -1):
                if dirs[i].startswith('.'):
                    del dirs[i]

            for f in files:
                if f.startswith('.') or not f.endswith('.json'):
                    continue
                f = os.path.join(root, f) 
                results = self.load_from_file(f, validate, results)
                                                  
        if not results:
            results = self._mkloadlog()
            
        return results

