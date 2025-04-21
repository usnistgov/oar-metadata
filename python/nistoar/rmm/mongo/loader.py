"""
common code for validating and loading data into the MongoDB database
"""
import json, re, warnings
from abc import ABCMeta, abstractmethod
from pymongo import MongoClient

from ejsonschema import ExtValidator
from ejsonschema import ValidationError, SchemaError, RefResolutionError

from ..exceptions import RMMException, DatabaseStateError

_dburl_re = re.compile(r"^mongodb://(\w+(:\S+)?@)?\w+(\.\w+)*(:\d+)?/\w+$")

class Loader(object, metaclass=ABCMeta):
    """
    an abstract base class for loading data
    """

    def __init__(self, dburl, dburl_metrics, collname=None, schemadir=None, log=None):
        """
        create the loader.  Validation will always be skipped if a schemadir
        is not provided.

        :param dburl  str:    the URL of MongoDB database in the form,
                              'mongodb://HOST:PORT/DBNAME' 
        :param collname str:  the collection name within the database to load 
                              data into
        :param schemadir str: the path to a directory containing the JSON 
                              schemas needed to validate the input JSON data;
                              if None, validation will always be skipped.
        :param log logging.Logger:  a logging instance that messages can be 
                              sent to.  If not provided, warnings might be 
                              issued via the warnings module.  
        """
        if not _dburl_re.match(dburl):
            raise ValueError("Loader: Bad dburl format (need "+
                             "'mongodb://[USER:PASS@]HOST[:PORT]/DBNAME'): "+
                             dburl)
        self._dburl = dburl
        self._dburl_metrics = dburl_metrics
        self.coll = collname
        self.log = log

        if schemadir:
            self._val = ExtValidator.with_schema_dir(schemadir, ejsprefix='_')

        self._client = None
        self._db = None

        self._client_metrics = None
        self._db_metrics = None

    def validate(self, data, schemauri=None, strict=True):
        """
        validate the given JSON data, raising an exception if it does not 
        conform.

        :param data JSON-data:  JSON data to validate.  If it is not a 
                                dictionary, a schemauri must be provided.
        :param schemauri str:   a schema URI for the schema that the data should 
                                compliant against.
        :param strict bool:     fail if an extended schema cannot be found
        """
        return self._val.validate(data, schemauri=schemauri, strict=strict,
                                  raiseex=False)

    def connect(self):
        """
        establish a connection to the database.
        """
        self._client = MongoClient(self._dburl)

        # the proper method to use depends on pymongo version
        if not hasattr(self._client, 'get_database'):
            self._client.get_database = self._client.get_default_database

        self._db = self._client.get_database()

        if(self._dburl_metrics != None):
            self._client_metrics = MongoClient(self._dburl_metrics)

            # the proper method to use depends on pymongo version
            if not hasattr(self._client_metrics, 'get_database'):
                self._client_metrics.get_database = self._client_metrics.get_default_database
        
            self._db_metrics = self._client_metrics.get_database()

    def disconnect(self):
        """
        close the connection to the database.
        """
        if self._client:
            try:
                self._client.close()
                if(self._dburl_metrics != None):
                    self._client_metrics.close()
            finally:
                self._client = None
                self._db = None
                if(self._dburl_metrics != None):
                    self._client_metrics = None
                    self._db_metrics = None
        
    def load_data(self, data, key=None, onupdate='quiet') -> int:
        """
        load the given data document into the configured MongoDB collection.

        The key parameter can be used to enforce a uniqueness constraint on 
        the collection.  See parameter docuemntation below for details.

        Note that this function does not test validation.

        :param data dict:   the data document to load into the collection
        :param key  dict:   a MongoDB search query that should result in either
                            one or zero records from the collection and which 
                            should be run prior to insert.  If one record is
                            returned, loading the new data would be considered an
                            update that replaces the previous record; otherwise,
                            it is a simple insert.  If key is not provided, 
                            no uniqueness constraint 
        :param onupdate str or func:  an indication of what to do if the load
                            request appears to be an update.  A str value of 
                            'quiet' (default) will cause the matching record
                            to be removed before loading the new data.  If 
                            set to 'warn', the data will be replace, but a 
                            warning will be issued.  If set to 'fail', an 
                            exception will be raised.  If it is a function, it 
                            will be executed before loading the new data.  It 
                            should take data and key as arguments where data will
                            previously saved record and key will be the MongoDB 
                            that was used to select it; this function should 
                            return True if the new data should then be loaded
                            or False if it should not.  
        :return:  the number of database records added; 0 is returned if implementation
                  decides that it is not necessary to load any records
                  :rtype: int
        """
        try:
            if not self._client:
                self.connect()

            coll = self._db[self.coll]

            if key:
                count = coll.count_documents(key);
                if count > 1:
                    # key should have returned no more than 1 record
                    raise DatabaseStateError("unique key query returns "
                                             "multiple records")
                if count > 0:
                    # a previous record with matching key exists
                    if onupdate == 'fail':
                        raise RecordIngestError("Existing record with key "
                                                "value; updates not allowed")

                    doload = True
                    if hasattr(onupdate, '__call__'):
                        c = coll.find(key)
                        try:
                            doload = onupdate(c[0], key)
                        finally:
                            c.close()

                    if doload:
                        if isinstance(onupdate, str) and onupdate != 'quiet':
                            msg = "Updating previously loaded record into %s: %s" % \
                                  (self.coll, str(key))
                            if self.log:
                                self.log.warn(msg)
                            else:
                                warnings.warn(msg, UpdateWarning)

                        result = coll.delete_one(key)
                        if result.deleted_count == 0:
                            raise RecordIngestError("Failed to remove previous "
                                                   +"record with key="+key)
                        assert result.deleted_count == 1

                    else:
                        return 0    
                    
            result = coll.insert_one(data)
            return 1

        except RecordIngestError as ex:
            raise
        except Exception as ex:
            if self.log:
                self.log.exception("Unexpected loading error: "+str(ex))
                raise RuntimeError("Unexpected loading error: "+str(ex))
            raise RecordIngestError("Failed to load record: "+str(ex), ex)

    @abstractmethod
    def load(self, data, validate=True, results=None, id=None):
        """
        load the given data into the database
        :param data:  the data to load
        :param validate bool:   False if validation should be skipped before
                            loading; otherwise, loading will fail if the input
                            data is not valid.
        :param results ResultLog:  if provided, add the loading results to this 
                            ResultLog object.
        :param id:    a name to record results against in the returned LoadLog;
                      if not provided, the extracted key will be used as 
                      applicable.  
        :return LoadLog:  a log successes and failures
        """
        raise NotImplemented


class LoadResult(object):
    """
    a summary of an attempt to load a record
    """

    def __init__(self, key, errs= None):
        self.key = key
        self.errs = errs

    @property
    def successful(self):
        """
        True if the attempt was successful
        """
        return not self.errs

    def __repr__(self):
        nm = str(type(self))[len("<class '"):-2]
        return "{0}(key={1}, errs={2})".format(nm, str(self.key), str(self.errs))
    

class LoadLog(object):
    """
    a class for keeping track of the results of record loading, including 
    failures.
    """
    
    def __init__(self, desc=None):
        self.description = desc
        self._results = []

    @property
    def attempt_count(self):
        """
        return the number of record loadings attempted (successful or failed)
        """
        return len(self._results)

    @property
    def failure_count(self):
        """
        return the number of record loadings attempted (successful or failed)
        """
        return len([r for r in self._results if not r.successful])

    @property
    def success_count(self):
        """
        return the number of record loadings attempted (successful or failed)
        """
        return len([r for r in self._results if r.successful])

    def succeeded(self, key):
        """
        return True if the record with the given key was successfully loaded
        """
        for r in self._results:
            if r.key == key and r.successful:
                return True
        return False

    def failed(self, key):
        """
        return True if the record with the given key was attempted but failed 
        to load.  Note that it is possible that a key can appear as both failed
        and succeeded if it was attempted more than once.
        """
        for r in self._results:
            if r.key == key and not r.successful:
                return True
        return False

    def failures(self, key=None):
        """
        return an array of the failed results loading records with the given 
        key.  
        """
        if key:
            return [r for r in self._results if r.key == key and
                                                not r.successful]
        else:
            return [r for r in self._results if not r.successful]

    def add(self, key, errs=None):
        """
        add a new result with a given key.  If errors are provided, the result
        will be registered as failed.

        :return self:
        """
        if errs is not None and not isinstance(errs, list):
            errs = [errs]
        self._results.append(LoadResult(key, errs))
        return self

    def merge(self, otherlog):
        """
        merge the results from another LoadLog into this one

        :return self:
        """
        if otherlog:
            for res in otherlog._results:
                self._results.append(res)
        return self

class RecordIngestError(RMMException):
    """
    an exception indicating a failure to load a record into the RMM
    """

    def __init__(self, msg=None, cause=None):
        if not msg and not cause:
            msg = "Unknown RMM Ingest Error"
        super(RecordIngestError, self).__init__(msg, cause)

class JSONEncodingError(RecordIngestError):
    """
    An exception indicating that a record was improperly encoded in JSON.  
    This typically captures errors eminating from the json module.  
    """
    def __init__(self, *args):
        """
        create the exception either from another exception or a message.

        If the first argument is a str, then it is assumed to be an error 
        message, and the second optional argument is treated as the underlying
        cause (as in, an exception).  If the first argument is not a str,
        it is taken to be the underlying cause (i.e. an exception), and the 
        message is its string representation.
        """
        if len(args) > 0:
            if isinstance(args[0], str):
                msg = args[0]
                cause = (len(args) > 1 and args[1]) or None
            else:
                cause = args[0]
                msg = "Error reading JSON data: " + str(cause)
        else:
            msg = "Unknown error reading JSON data"
            cause = None
        super(JSONEncodingError, self).__init__(msg, cause)

class ValidationError(RecordIngestError):
    """
    An error indicating that a record failed to be ingested due to a validation
    error
    """
    def __init__(self, *args):
        """
        create the exception either from another exception or a message.

        If the first argument is a str, then it is assumed to be an error 
        message, and the second optional argument is treated as the underlying
        cause (as in, an exception).  If the first argument is not a str,
        it is taken to be the underlying cause (i.e. an exception), and the 
        message is its string representation.
        """
        if len(args) > 0:
            if isinstance(args[0], str):
                msg = args[0]
                cause = (len(args) > 1 and args[1]) or None
            else:
                cause = args[0]
                msg = "Record validation error: " + str(cause)
        else:
            msg = "Unknown record validation error"
            cause = None
        super(ValidationError, self).__init__(msg, cause)
    
class UpdateWarning(Warning):
    """
    a warning indicating that a loaded record replaced a previous version
    """
    pass

