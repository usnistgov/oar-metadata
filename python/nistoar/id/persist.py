"""
This module provides an ID minting and registry implementation that persists 
its IDs and related data to a file on disk.
"""
import os, logging, json
from collections import Mapping
from .minter import IDRegistry, IDMinter, NoidMinter, NIST_ARK_NAAN
import pynoid as noid

log = logging.getLogger(__name__)

class SimplePersistentIDRegistry(IDRegistry):
    """
    a registry that persists its information to disk
    """

    def __init__(self, parentdir, config=None):
        assert os.path.isdir(parentdir)

        if config is None:
            config = {}
        if not isinstance(config, Mapping):
            raise TypeError("Configuration not a dictionary: " + str(config))
        self.cfg = config
        self.store = os.path.join(parentdir,
                              self.cfg.get('id_store_file', 'issued-ids.json'))
        self.data = {}
        self.reload_data()
        if not self.data:
            log.info("IDRegistry: starting with an empty registry")
        self.cache_pending = False

    def reload_data(self):
        if os.path.exists(self.store):
            with open(self.store) as fd:
                data = json.load(fd)
            self.data = data

    def cache_data(self):
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

class EDIBasedMinter(IDMinter):
    """
    An IDMinter that creates NOID-compliant identifiers based on an 
    EDIID seed.  

    This minter accepts a dictionary of data when minting an ID.  If that 
    data contains a key 'ediid', the ID will be computed based on the key's
    value (and the configured template).  If the key is not present, the 
    issued ID is based on a sequence (via NoidMinter).  
    """

    def __init__(self, edishoulder, seqshoulder, regdir, count=1, hashorder=6,
                 seedkey='ediid'):
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
        self.seedkey = seedkey
        self.registry = SimplePersistentIDRegistry(regdir)

        self._prefix = 'ark:/{0}/'.format(NIST_ARK_NAAN)
        self._seededmask = self._prefix + edishoulder + '.zeeeeeek'
        self.seqminter = NoidMinter(self._prefix+seqshoulder+'.zeeek',
                                    count=count)
        self._div = 10 ** hashorder
        self._annotn = 1

    def _hash(self, hexid):
        s = 0
        d = int(hexid, 16)
        while d > 0:
            s ^= d % self._div
            d /= self._div
        return s

    def mint(self, data=None):
        """
        return an available identifier string.  
        """
        out = None
        if isinstance(data, Mapping) and self.seedkey in data:
            n = self._hash(data[self.seedkey])

            out = self._seededmint(self._seededmask, n)

        else:
            out = self.seqminter.mint(data)

        self.registry.registerID(out, data)
        return out

    def _seededmint(self, mask, n):
        out = noid.mint(self._seededmask, n)
        if self.issued(out):
            mask = out[:-1]+"0.zek"
            while self.issued(out):
                out = noid.mint(mask, self._annotn)
                self._annotn += 1
        return out
    
    def issued(self, id):
        return self.registry.registered(id)

    def datafor(self, id):
        return self.registry.get_data(id)

