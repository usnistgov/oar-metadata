"""
load NERDm records into the RMM's MongoDB database
"""
# import pandas as pd
import json, os, sys, warnings
from collections import OrderedDict
from collections.abc import Mapping

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
    def __init__(self, collection_name, dburl, metrics_dburl, schemadir, log=None, defschema=DEF_SCHEMA):
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
        :param str metrics_dburl the url for mongodb database for Metrics collections, 
                                it is optional

        """
        super(_NERDmRenditionLoader, self).__init__(dburl, metrics_dburl,collection_name, schemadir, log )
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
        def __init__(self, dburl,metrics_dburl, schemadir, log=None):
            super(NERDmLoader.LatestLoader, self).__init__(LATEST_COLLECTION_NAME, dburl, metrics_dburl, schemadir, log)

        def load_data(self, data, key=None, onupdate='quiet'):
            added = super().load_data(data, key, onupdate)
            if added:
                # initialize the metrics collections as needed
                try:
                    init_metrics_for(self._db_metrics, data)
                except Exception as ex:
                    msg = "Failure detected while initializing Metric data for %s: %s" % \
                        (data.get("@id", "unknown record"), str(ex))
                    if self.log:
                        self.log.warning(msg)
                    else:
                        warnings.warn(msg, UpdateWarning)
            return added

    class ReleaseSetLoader(_NERDmRenditionLoader):
        def __init__(self, dburl, metrics_dburl, schemadir, log=None):
            super(NERDmLoader.ReleaseSetLoader, self).__init__(RELEASES_COLLECTION_NAME, dburl, metrics_dburl,schemadir, log)


    def __init__(self, dburl, metrics_dburl, schemadir, onupdate='quiet', log=None, defschema=DEF_SCHEMA):
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
        super(NERDmLoader, self).__init__(VERSIONS_COLLECTION_NAME, dburl, metrics_dburl, schemadir, log, defschema)
        self.onupdate = onupdate

        self.lateloadr = self.LatestLoader(dburl,metrics_dburl, schemadir, log)
        self.relloadr  = self.ReleaseSetLoader(dburl, metrics_dburl,schemadir, log)
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

        self.lateloadr._client_metrics = self._client_metrics
        self.lateloadr._db_metrics = self._db_metrics

        

        
        
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
        errs = []

        # the input is a versioned Resource record; convert it into its three parts for the three
        # collections (record, versions, releaseSets)
        try:
            parts = self.tormm.convert(rec, validate=False)
        except (ValueError, ValidationError) as ex:
            return results.add(id or json.dumps({'@id': rec.get('@id','?')}), ex)

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
            return results.add(id, RecordIngestError("Data is missing input key value, @id"))

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
                ex = JSONEncodingError(ex)
                if not results:
                    raise ex
                results.add(filepath, ex)
                return results

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

def init_metrics_for(db_metrics, nerdm):
    """
    initialize the metrics-related collections for dataset described in the given NERDm record
    as needed.  

    This function assumes that the given NERDm record is the latest description of the dataset.
    It should not be called with NERDm records describing earlier versions of the dataset.  

    :param Database db:  the MongoDB Database instance the contains the metrics collections.  
                         This instance will have come from a MongoDB client that is already 
                         connected to a backend server.
    :param dict  nerdm:  the NERDm record to initialize for.
    """
    #Convert nderm dict to an array of dict
    #nerdm_use = [nerdm]
    
    record_collection_fields = { 
                                "pdrid": None,
                                "ediid":None, 
                                "first_time_logged": None, 
                                "last_time_logged": None,
                                "total_size_download":0,
                                "success_get":0,
                                "number_users":0,
                                "record_download":0, 
                                "ip_list":[]}
    
    #Record fields to be copied
    record_fields = ['pdrid', 'ediid']
    
    files_collection_fields = {
                         "pdrid": None,
                        "ediid":None, 
                        "filesize": 0,
                        "success_get" : 0, 
                        "failure_get" : 0, 
                        "datacart_or_client" : 0,
                        "total_size_download": 0,
                        "number_users" : 0,
                        "ip_list": [],
                        "first_time_logged" : None,
                        "last_time_logged" : None,
                        "downloadURL": None
                        }
    
    nerdm['pdrid'] = nerdm.pop('@id')
    records = {}
    #Copy fields
    for field in record_fields:
        records[field] = nerdm[field]
        
     #Initialize record fields
    for col in record_collection_fields.keys():
        if col not in records.keys():
            records[col] = record_collection_fields[col]
    
    if(db_metrics["recordMetrics"].find_one({"ediid": nerdm["ediid"]}) is None):
        db_metrics["recordMetrics"].insert_one(records)
    
    #Get files from record components
    files = flatten_records(nerdm, files_collection_fields)
    files_to_update = []
    
    current_files = db_metrics["fileMetrics"].find({"ediid": nerdm["ediid"]})
    current_files_filepaths = [x["filepath"] for x in current_files]
    for file_item in files:
        if 'filepath' in file_item.keys():
            if file_item['filepath'] not in current_files_filepaths:
                files_to_update.append(file_item)
                
    if len(files_to_update)>0:            
        db_metrics["fileMetrics"].insert_many(files_to_update)
    
# This takes a nerdm record and collect the files related data from components.
# Inputs are record=nerdm to be updated
# initialize fields=fileMetrics fields to be updated
def flatten_records(record, initialize_fields):
    files = []
    keys_to_keep = ['filepath', 'size', 'downloadURL', 'ediid', '@id']
    for component in record['components']:
        file_dict = {}
        #Initialize  fields
        for key in initialize_fields.keys():
            file_dict[key] = initialize_fields[key]
        #Get file information

        if 'filepath' in component.keys():            
            for key in keys_to_keep:
                if key in component.keys():
                    file_dict[key] = component[key]

        if 'size' in file_dict.keys():
            file_dict['filesize'] = file_dict.pop('size')
        else:
            file_dict['filesize'] = 0
            
        if 'downloadURL' not in component.keys():
                file_dict['downloadURL'] = ''

        file_dict['pdrid'] = record['pdrid']
        file_dict['ediid'] = record['ediid']
        
        files.append(file_dict)
    return files

