"""
This module provides an ID minting and registry implementation that persists 
its IDs and related data to a file on disk.  This implementation provides 
locking to prevent two processes from acquiring the same ID.
"""
import os, logging, json
from collections import Mapping
from copy import deepcopy
from .minter import IDRegistry, IDMinter, NoidMinter, NIST_ARK_NAAN
import pynoid as noid, filelock

log = logging.getLogger(__name__)

class SimplePersistentIDRegistry(IDRegistry):
    """
    a registry that persists its information to disk.  

    The persisted file is JSON format containing an object whose properties
    are the currently issued IDs and the values are the data associated with
    them.  

    This class can take a configuration dictionary on construction; the 
    following parameters are supported:
    :param id_store_file  str:  the name to give to the file where IDs 
                                are persisted (default: 'issued-ids.json')
    :param cache_on register bool:  if True (default) each newly registered ID
                                is persisted immediately upon call to 
                                registerID(); if False, the IDs will only be
                                persisted with a call to cache_data().
    :param pretty_print bool:   if True, persisted ID file will be written out
                                in JSON with "pretty print" formatting for 
                                easier reading by a human.
    """

    def __init__(self, parentdir=None, config=None):
        if parentdir:
            assert os.path.isdir(parentdir)

        if config is None:
            config = {}
        if not isinstance(config, Mapping):
            raise TypeError("Configuration not a dictionary: " + str(config))
        self.cfg = deepcopy(config)

        self.data = {}
        self.cache_pending = False

        # set up the registry disk storage
        self.store = None
        self.lock = None
        if parentdir:
            self.store = os.path.join(parentdir,
                              self.cfg.get('id_store_file', 'issued-ids.json'))

        self.lock = self._mylock(self.store)
        if self.store:
            self.reload_data()
            if not self.data:
                log.info("IDRegistry: starting with an empty registry")

        if not self.store:
            self.cfg['cache_on_register'] = False


    def reload_data(self):
        if os.path.exists(self.store):
            with self.lock:
                with open(self.store) as fd:
                    data = json.load(fd)
                self.data = data

    def cache_data(self):
        if not self.store:
            raise RuntimeError("Can't cache: No caching storage configured")

        with self.lock:
            extra = {}
            if self.cfg.get('pretty_print', True):
                extra['separators'] = (',', ': ')
                extra['indent'] = 4
            with open(self.store, 'w') as fd:
                json.dump(self.data, fd, **extra)
            self.cache_pending = False

    def registerID(self, id, data=None):
        """
        register the given ID to reserve it from further use.  

        The data will be persisted with the id.

        :param id str:     the ID to be reserved
        :param data dict:  any data to store with the identifier.
        :raises ValueError:  if the id has already exists in storage.
        """
        with self.lock:
            if id in self.data:
                raise ValueError("id is already registered: " + id)
            self.data[id] = data
            self.cache_pending = True
            if self.cfg.get('cache_on_register', True):
                self.cache_data()

    def get_data(self, id):
        """
        return the data for a given ID or none if it is not registered
        """
        return self.data.get(id)

    def registered(self, id):
        """
        return true if the given ID has already been registered

        :param id str:  the identifier string to check
        """
        return id in self.data

    class _mylock(object):
        def __init__(self, storefile=None):
            self._lock = None
            if storefile:
                lockfile = os.path.splitext(storefile)[0]+".lock"
                self._lock = filelock.FileLock(lockfile)
        def __enter__(self):
            if self._lock:
                self._lock.acquire(timeout=30)
            return self
        def __exit__(self, exc_type, exc_value, traceback):
            if self._lock:
                self._lock.release()
            return None

class EDIBasedMinter(IDMinter):
    """
    An IDMinter that creates NOID-compliant identifiers based on an 
    EDIID seed.  

    This minter accepts a dictionary of data when minting an ID.  If that 
    data contains a key 'ediid', the ID will be computed based on the key's
    value (and the configured template).  If the key is not present, the 
    issued ID is based on a sequence (via NoidMinter).  

    This class can take a configuration dictionary on construction; the 
    following parameters are supported:
    :param registry  dict:    configuration parameters for the ID registry 
                              that persists issued IDs; see the documentation
                              for SimplePersistentIDRegistry for the supported
                              parameters in this dictionary.
    :param ediid_data_key str:  the string key to use to extract the EDI ID 
                              from the data dictionary provided to mint()
                              (default: 'ediid')
    :param shoulder_for_edi str:  the ARK shoulder to use when minting 
                              IDs based on the EDI Identifier (default: 'mds0')
    :param shoulder_for_seq str:  the ARK shoulder to use when minting 
                              IDs based on a sequence number (default: 'pdr0')
    :param hashorder int:     a number that sets the length of the EDI ID hash
                              used for generating an ARK identifer
                              (default: 6).  This roughly sets the number 
                              IDs that can be issued without having to avoid 
                              collisions.
    :param seqstart int:      the starting sequence number to use for minting
                              IDs not based on an EDI ID (default: 1)
    """

    def __init__(self, regdir, config, seqstart=None):
        """
        Create the minter.

        Note that while the hashorder sets the capacity of the number of 
        non-colliding identifiers to expect, this minter does not fail on 
        an initial collision and guarantees uniqueness.  

        :param shoulder str:  the ARK shoulder to mint IDs under
        :param regdir   str:  path to the directory that will hold the 
                                ID registry data.
        :param count    int:  the initial sequence value to use when an EDIID
                                value is not available
        :param hashorder int: the number of hash digits to use in calculating
                                a hash of the EDI ID; the rough order of the
                                number of non-colliding IDs available.
        :param seedkey str:  the name of the key in data to look for the 
                                EDIID value under (default: 'ediid')
        """
        #        , edishoulder, seqshoulder, regdir, count=1, hashorder=6,
        #                 seedkey='ediid'):
        if config is None:
            config = {}
        if not isinstance(config, Mapping):
            raise TypeError("Configuration not a dictionary: " + str(config))
        self.cfg = config

        self.registry = SimplePersistentIDRegistry(regdir,
                                                   self.cfg.get('registry', {}))

        self.seedkey = self.cfg.get('ediid_data_key', 'ediid')
        edishldr = self.cfg.get('shoulder_for_edi', 'mds0')
        seqshldr = self.cfg.get('shoulder_for_seq', 'pdr0')
        prefix = 'ark:/{0}/'.format(NIST_ARK_NAAN)
        self._seededmask = prefix + edishldr + '.zeeeeek'
        self._div = 10 ** self.cfg.get('hashorder', 6)

        if not seqstart:
            seqstart = self.cfg.get('sequence_start', 1)
        if not isinstance(seqstart, int):
            raise TypeError("EDIBasedMinter: seqstart arg is not an int: "+
                            str(seqstart))

        self.seqminter = NoidMinter(prefix+seqshldr+'.zeeek', count=seqstart)

        self._annotn = 1
        self._collision_count = 0

    def _hash(self, hexid):
        s = 0
        d = int(hexid, 16)
        while d > 0:
            s ^= d % self._div
            d //= self._div
        return s

    def mint(self, data=None):
        """
        return an available identifier string.  
        """
        out = None
        with self.registry.lock:

            if isinstance(data, Mapping) and self.seedkey in data:
                # create an ID based on the EDI ID
                n = self._hash(data[self.seedkey])
                out = self._seededmint(self._seededmask, n)
            else:
                # create an ID based on a running sequence
                out = self.seqminter.mint(data)
                
            self.registry.registerID(out, data)

        return out

    def _seededmint(self, mask, n):
        out = noid.mint(self._seededmask, n)
        if self.issued(out):
            log.debug("apparent EDI-ARK id collision: %s", out)
            self._collision_count += 1
            mask = out[:-1]+"0.zek"
            while self.issued(out):
                out = noid.mint(mask, self._annotn)
                self._annotn += 1
        return out
    
    def issued(self, id):
        return self.registry.registered(id)

    def datafor(self, id):
        return self.registry.get_data(id)


PDRMinter = EDIBasedMinter
