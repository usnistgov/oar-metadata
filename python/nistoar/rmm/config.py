"""
Utilities for obtaining a configuration for a service
"""
import os, sys, logging, json, yaml, re
from urlparse import urlparse, urlunparse
import urllib

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
    if not isinstance(location, (str, unicode)):
        raise TypeError("resolve_configuration(): location is not a string")
    if not location:
        raise ValueError("resolve_configuration(): location not provided")

    locurl = urlparse(location)
    if not locurl.scheme:
        if baseurl:
            if not isinstance(baseurl, (str, unicode)):
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
            return yaml.load(fd)

def load_from_url(configurl):
    """
    read the configuration from the configuration server

    :param configurl str:  the URL for retrieving the configuration
    """
    try:
        resp = urllib.urlopen(configurl)
        ct = resp.headers.get('content-type','')
        if '/yaml' in ct:
            # it's in YAML format
            fmt = 'YAML'
            data = yaml.loads(resp.text)
        elif ct or '/json' in ct:
            # response is in JSON format by default
            fmt = 'JSON'
            data = resp.json()

        out = data
        if 'propertySources' in data:
            # this data is from the configuration server
            out = _extract_config_from_csdata(data)
            
        return out
            
    except ValueError, ex:
        raise ConfigurationException("Failed to parse %s data from URL".
                                     format(fmt), cause=ex)
    except requests.RequestException, ex:
        raise ConfigurationException("Failed to pull configuration from URL: " +
                                     str(ex), cause=ex)

def _extract_config_from_csdata(data):
    """
    return configuration data used by applications given a response from the
    configuration server.  See the configuration server documentation for 
    details regarding for format and interpretation of the config server 
    response.  
    """
    try:

        out = data['propertySources'][-1]['source']
        if len(data['propertySources']) > 1:
            out.update( data['propertySources'][0]['source'] )
        return out

    except (KeyError, IndexError), ex:
        raise ConfigurationException("Unexpected format from config server: ".
                                     format(fmt), cause=ex)


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
        

