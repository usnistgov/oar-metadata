"""
The uWSGI script for launching the preservation service
"""

import os, sys, yaml, json, logging
try:
    import uwsgi
except ImportError:
    print("Warning: running ingest-uwsgi in simulate mode", file=sys.stderr)
    class uwsgi_mod(object):
        def __init__(self):
            self.opt={}
    uwsgi=uwsgi_mod()
            
try:
    import nistoar
except ImportError:
    oarpath = os.environ.get('OAR_PYTHONPATH')
    if not oarpath and 'OAR_HOME' in os.environ:
        oarpath = os.path.join(os.environ['OAR_HOME'], "lib", "python")
    if oarpath:
        sys.path.insert(0, oarpath)
    import nistoar

from nistoar.rmm import config
from nistoar.rmm.ingest import wsgi

def get_uwsgi_opt(key, default=None):
    out = uwsgi.opt.get(key)
    if out is None:
        return default
    elif isinstance(out, bytes):
        return out.decode('utf-8')
    return out

confsrvc = None
def get_confservice():
    cfgsrvc = None
    if 'oar_config_service' in uwsgi.opt:
        # this service is based on uwsgi command-line inputs
        cfgsrvc = config.ConfigService(get_uwsgi_opt('oar_config_service'),
                                        get_uwsgi_opt('oar_config_env'))
        timeout = int(get_uwsgi_opt('oar_config_timeout', 10))
                               
    else:
        # this service is based on environment variables
        cfgsrvc = config.service
        timeout = int(os.environ.get('OAR_CONFIG_TIMEOUT', 10))

    cfgsrvc.wait_until_up(timeout, True, sys.stderr)
    return cfgsrvc


# determine where the configuration is coming from.  Check first to see
# files were provided via the uwsgi command line.
cfg = None
confsrc = get_uwsgi_opt("oar_config_file")
if confsrc:
    cfg = config.resolve_configuration("file:" + confsrc)

if not cfg:
    # get the configuration from the config service
    confsrvc = get_confservice()
    if confsrvc:
        appname = get_uwsgi_opt('oar_config_appname',
                                os.environ.get('OAR_CONFIG_APP', 'rmm-ingest'))
        cfg = confsrvc.get(appname)

if not cfg:
    raise config.ConfigurationException("ingester: nist-oar configuration not "+
                                        "provided")

# set up logging
if 'logfile' not in cfg:
    cfg['logfile'] = 'rmm-ingest.log'
config.configure_log(config=cfg, addstderr=True)

# do we have db authentication info, or do we need to get it?
#
# if 'db_authn' does not exist in the configuration, then authenication info
# not needed.  If it does, but it is missing a username or password, we need
# to retrieve this info from the RMM's configuration
#
if cfg.get('db_authn') and \
   (not cfg['db_authn'].get('user') or not cfg['db_authn'].get('pass')):
    acfg = cfg['db_authn']
    try:
        rmmcfg = None
        rmmconfsrc = get_uwsgi_opt("oar_rmm_config_file",
                                   acfg.get("rmm_config_file"))
        if rmmconfsrc:
            rmmcfg = config.resolve_configuration(rmmconfsrc)

        if not rmmcfg:
            if not confsrvc:
                convsrvc = get_confservice()
            if not confsrvc:
                raise config.ConfigurationException("ingester: configuration not "+
                                                    "available; set db_authn.rmm_config_file")
            rmmcfg = confsrvc.get(acfg.get('rmm_config_loc', 'oar-rmm'),
                                  flat=True)

        acfg['user'] = rmmcfg['oar.mongodb.readwrite.user']
        acfg['pass'] = rmmcfg['oar.mongodb.readwrite.password']
        acfg['rouser'] = rmmcfg['oar.mongodb.read.user']
        acfg['ropass'] = rmmcfg['oar.mongodb.read.password']

    except Exception as ex:
        raise config.ConfigurationException("Failed to retrieve Mongo authentication info: "+str(ex), cause=ex)

application = wsgi.app(cfg)

