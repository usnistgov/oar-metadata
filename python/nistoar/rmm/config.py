"""
Utilities for obtaining a configuration for RMM services
"""
import os, sys, logging, json, yaml, re, collections, time
from urllib.parse import urlparse, urlunparse
import requests

from .exceptions import ConfigurationException

oar_home = None
try:
    import uwsgi
    oar_home = uwsgi.opt.get('oar_home')
except ImportError:
    pass

if not oar_home:
    oar_home = os.environ.get('OAR_HOME', '/app/oar')

urlre = re.compile(r'\w+:')

def resolve_configuration(location, baseurl=None):
    """
    return a dictionary for configuring a system component.  The absolute 
    location of the configuration will depend on the combination of the 
    two input parameters, location and baseurl:
      :*: if location is in the form of a full URL (including starting with
          file:), location is considered solely as the location of the 
          configuration data; baseurl is ignored.
      :*: if location is in the form of a path (absolute or relative) and 
          baseurl is not given, location is interpreted as a file path on 
          the local filesystem.  
      :*: if both location and baseurl are given, they are combined according
          to the rules for combining base URLs and relative URLs:  if location
          is an absolute path, any path component provided with baseurl will 
          be dropped before they are combined.
      :*: baseurl can be set to "file:" to force the interpretation of location
          as a filesystem path.  baseurl cannot contain a server name.  

    :param location str:  the location of the configuration data, either as a
                          relative path, an absolute path, or a URL. 
    :param baseurl  str:  a base URL to combine with location to form the 
                          absolute location of the configuration data.  
    """
    if not isinstance(location, str):
        raise TypeError("resolve_configuration(): location is not a string")
    if not location:
        raise ValueError("resolve_configuration(): location not provided")

    locurl = urlparse(location)
    if not locurl.scheme:
        if baseurl:
            if not isinstance(baseurl, str):
              raise TypeError("resolve_configuration(): baseurl is not a string")
            baseurl = list(urlparse(baseurl))
        else:
            # default location of config files: "$OAR_HOME/etc/config/"
            baseurl=list(urlparse("file:"+os.path.join(oar_home,"etc","config")))

        # combine baseurl and location
        if locurl.path.startswith('/'):
            baseurl[2] = locurl.path
        else:
            baseurl[2] = '/'.join([ baseurl[2].rstrip('/'), locurl.path ])
        baseurl[3] = locurl.query
        baseurl[4] = locurl.fragment
        locurl = urlparse(urlunparse(baseurl))

    if locurl.scheme == 'file':
        if locurl.netloc:
            raise ValueError("resolve_configuration(): server name not allowed "+
                             "in file URL: " + locurl.netloc)
        return load_from_file(locurl.path)
    
    elif locurl.scheme in "http https":
        return load_from_url(urlunparse(locurl))

    else:
        raise ValueError("resolve_configuration(): unsupported URL scheme:" +
                         locurl.scheme)

def load_from_file(configfile):
    """
    read the configuration from the given file and return it as a dictionary.
    The file name extension is used to determine its format (with YAML as the
    default).
    """
    with open(configfile) as fd:
        if configfile.endswith('.json'):
            return json.load(fd)
        else:
            # YAML format
            return yaml.safe_load(fd)

def load_from_url(configurl):
    """
    read the configuration from the configuration server

    :param configurl str:  the URL for retrieving the configuration
    """
    try:
        resp = requests.get(configurl)
        if resp.status_code >= 400:
            raise ConfigurationException(
                "Server returned erroneous response: {0} {1}"
                .format(resp.status_code, resp.reason))
                                         
        ct = resp.headers.get('content-type','')
        if '/yaml' in ct:
            # it's in YAML format
            fmt = 'YAML'
            data = yaml.safe_loads(resp.text)
        elif ct or '/json' in ct:
            # response is in JSON format by default
            fmt = 'JSON'
            data = resp.json()

        out = data
        if 'propertySources' in data:
            # this data is from the configuration server
            out = ConfigService.extract(data, flat=True)
            
        return out
            
    except ValueError as ex:
        raise ConfigurationException("Failed to parse %s data from URL".
                                     format(fmt), cause=ex)
    except requests.RequestException as ex:
        raise ConfigurationException("Failed to pull configuration from URL: " +
                                     str(ex), cause=ex)


LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s: %(message)s"
_log_handler = None

def configure_log(logfile=None, level=None, format=None, config=None,
                  addstderr=False):
    """
    configure the log file, setting the output file, threshold, and format
    as necessary.  These can be provided explicitly or provided via the 
    configuration; the former takes precedence.  

    :param logfile str:  the path to the output logfile.  If given as a relative
                         path, it will be assumed that it is relative to a 
                         configured log directory.
    :param level int:    the logging threshold to set for sending messages to 
                         the logfile.  
    :param format str:   the formatting string to configure the logfile with
    :param config dict:  a configuration dictionary to draw logging configuration
                         values from.  
    :param addstderr bool:  If True, send ERROR and more severe messages to 
                         the standard error stream (default: False).
    """
    if not config:
        config = {}
    if not logfile:
        logfile = config.get('logfile', 'rmm.log')

    if not os.path.isabs(logfile):
        # The log directory can be set either from the configuration or via
        # the OAR_LOG_DIR environment variable; the former takes precedence
        deflogdir = os.path.join(oar_home,'var','logs')
        logdir = config.get('logdir', os.environ.get('OAR_LOG_DIR', deflogdir))
        if not os.path.exists(logdir):
            logdir = "/tmp"
        logfile = os.path.join(logdir, logfile)
    
    if level is None:
        level = logging.DEBUG
    if not format:
        format = LOG_FORMAT
    frmtr = logging.Formatter(format)

    global _log_handler
    _log_handler = logging.FileHandler(logfile)
    _log_handler.setLevel(level)
    _log_handler.setFormatter(frmtr)
    rootlogger = logging.getLogger()
    rootlogger.addHandler(_log_handler)
    rootlogger.setLevel(logging.DEBUG)

    if addstderr:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.ERROR)
        handler.setFormatter(logging.Formatter(format))
        rootlogger.addHandler(handler)
        rootlogger.error("FYI: Writing log messages to %s",logfile)
        

class ConfigService(object):
    """
    an interface to the configuration service
    """

    def __init__(self, urlbase, envprof=None):
        """
        initialize the service.
        :param urlbase str:  the base URL for the service which must include 
                             the scheme (either http: or https:), the server,
                             and the base path.  It can also include a port
                             number.
        :param envprof str:  the label indicating the default environment 
                             profile (usually, one of 'local', 'dev', 'test',
                             or 'prod').
        """
        self._base = urlbase
        self._prof = envprof
        if not self._base.endswith('/'):
            self._base += '/'

        u = urlparse(self._base)
        msg = "Insufficient config service URL: "+self._base+" ({0})"
        if not u.scheme:
            raise ConfigurationException(msg.format("missing http/https"))
        if not u.netloc:
            raise ConfigurationException(msg.format("missing server name"))

    def url_for(self, component, envprof=None):
        """
        return the proper URL for access the configuration for a given 
        component.  
        :param component   the name for the service or component that 
                              configuration data is desired for
        :param envprof     the desired version of the configuration given 
                              its environment/profile name.  If not provided,
                              the profile set at construction time will 
                              be assumed.
        """
        if not envprof:
            envprof = self._prof
        if envprof:
            component = '/'.join([component, envprof])
        
        return self._base + component

    def is_up(self):
        """
        return true if the service appears to be up.  
        """
        try:
            resp = requests.get(self.url_for("ready"))
            return resp.status_code and resp.status_code < 500
        except requests.exceptions.RequestException:
            return False

    def wait_until_up(self, timeout=10, rais=True, verboseout=None):
        """
        poll the service until responds.  
        :param timeout int:  the maximum number of seconds to wait before 
                             timing out.
        :param rais bool:    if True, raise a ConfifigurationException if
                             the timeout period is reached without a response 
                             from the service.
        :param verboseout file:  a file stream to send message about waiting;
                             if None, no messages are printed.
        :return bool:  True if the service is detected as up; False, if the 
                       timeout period is exceeded (unless rais=True).
        :raises ConfifigurationException: if rais=True and the timeout period
                       is exceeded without getting a response from the service.
        """
        start = time.time()
        if self.is_up():
            if verboseout:
                print("RMM: configuration service is ready", file=verboseout)
            return True
        if verboseout:
            print("RMM: Waiting for configuration service...", file=verboseout)

        updated = start
        while time.time()-start < timeout:
            if verboseout and time.time()-updated > 10:
                print("RMM: ...waiting...")
                updated = time.time()
                
            time.sleep(2)
            
            if self.is_up():
                if verboseout:
                    print("RMM: ...ready", file=verboseout)
                return True

        if verboseout:
            print("RMM: ...timed out!")        
        if rais:
            raise ConfigurationException("Waiting for configuration service "+
                                         "timed out")
        return False
        

    def get(self, component, envprof=None, flat=False):
        """
        retrieve the configuration for the service or component with the 
        given name.  Internally, this will transform the raw output from 
        the service into a configuration ready to give to the PDR component
        (including combining the profile specializations with default values).

        :param component str: the name for the service or component that 
                              configuration data is desired for
        :param envprof   str: the desired version of the configuration given 
                              its environment/profile name.  If not provided,
                              the profile set at construction time will 
                              be assumed.
        :param flat     bool: if true, keep the flat structure provided directly
                              by the config server.
        :return dict:  the parsed configuration data 
        """
        try:
            resp = requests.get(self.url_for(component, envprof))
            resp.raise_for_status()
            return self._extract(resp.json(), component, flat)
        except ValueError as ex:
            raise ConfigurationException("Config service response: "+str(ex))
        except requests.exceptions.RequestException as ex:
            raise ConfigurationException("Failed to access configuration for "+
                                         component + ": " + str(ex))

    def _extract(self, rawdata, comp="unknown", flat=False):
        return self.__class__.extract(rawdata, comp, flat)

    @classmethod
    def _deep_update(cls, defdict, upddict):
        for k, v in upddict.items():
            if isinstance(v, collections.Mapping):
                defdict[k] = cls._deep_update(defdict.get(k, v.__class__()), v)
            else:
                defdict[k] = v
        return defdict

    _idxre = re.compile(r'\[(\d+)\]')
    @classmethod
    def _inflate(cls, flat):
        out = flat.__class__()
        for key in flat:
            levs = cls._idxre.sub(r'.\g<0>', key)
            levs = levs.split('.')
            pv = out
            while levs:
                lev = levs.pop(0)
                if len(levs) == 0: 
                    pv[lev] = flat[key]
                else:
                    if not isinstance(pv.get(lev), collections.Mapping):
                        pv[lev] = flat.__class__()
                    pv = pv[lev]

        return cls._cvtarrays(out)

    @classmethod
    def _cvtarrays(cls, md):
        if not isinstance(md, collections.Mapping):
            return md
        
        keys = list(md.keys())
        m = [cls._idxre.match(k) for k in keys]
        if all(m):
            ary = [( int(m[i].group(1)), md[keys[i]] ) for i in range(len(m))]
            ary.sort(lambda x,y: cmp(x[0], y[0]))
            return [ cls._cvtarrays(el[1]) for el in ary ]
        else:
            for k in keys:
                md[k] = cls._cvtarrays(md[k])
            return md

    @classmethod
    def extract(cls, rawdata, comp="unknown", flat=False):
        """
        extract component configuration from the config service response.
        This includes combining the environment/profile-specific data
        with the defaults.  
        """
        try:
            name = rawdata.get('name') or comp 
            vers = rawdata['propertySources']
        except KeyError as ex:
            raise ConfigurationException("Missing config param for label="+name+
                                         ": "+str(ex))
        if not isinstance(vers, list):
            raise ConfigurationException("Bad data schema for label="+name+
                                      ": wrong type for propertySources: "+
                                      str(type(vers)))
        if len(vers) == 0:
            raise ConfigurationException(name+": config data for app name not "+
                                         "found")

        try:
            out = vers[-1]['source']
            out.update(vers[0]['source'])
            if not flat:
                out = cls._inflate(out)
        except TypeError as ex:
            raise ConfigurationException("Bad data schema for label="+name+
                                         ": wrong type for propertySources "+
                                         "item: "+ str(type(vers)))
        except KeyError as ex:
            raise ConfigurationException("Bad data schema for label="+name+
                                         ": missing property: "+str(ex))

        return out

    @classmethod
    def from_env(cls):
        """
        return an instance of ConfigService based on environment variables
        or None if the proper environment is not set up.  To return an instance,
        the OAR_CONFIG_SERVICE environment variable needs to contain the 
        service's base URL.  If OAR_CONFIG_ENV is set, it will be taken as 
        the environment/platform label.  

        :raise ConfigurationException: if base URL in OAR_CONFIGSERVICE is 
                                       malformed.
        """
        if 'OAR_CONFIG_SERVICE' in os.environ:
            prof = os.environ.get('OAR_CONFIG_ENV')
            return ConfigService(os.environ['OAR_CONFIG_SERVICE'], prof)
        return None

service = None
try:
    service = ConfigService.from_env()
except:
    pass
        
