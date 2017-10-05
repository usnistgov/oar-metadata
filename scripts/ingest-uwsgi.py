"""
The uWSGI script for launching the preservation service
"""
from __future__ import print_function
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
from nistoar.rmm.exceptions import ConfigurationException
from nistoar.rmm.ingest import wsgi

# get configuration
confserv = uwsgi.opt.get('oar_config_baseurl',
                         os.environ.get('OAR_CONFIGSERVER'))
confenv = uwsgi.opt.get('oar_config_env',
                         os.environ.get('OAR_CONFIG_ENV'))
confsrc = uwsgi.opt.get("oar_config_file")
if confsrc:
    confsrc = "file:" + confsrc
else:
    confsrc = uwsgi.opt.get('oar_config_loc', 'rmm-ingest-service')
    if confenv:
        confsrc += '/'+confenv
if not confsrc:
    raise RuntimeError("ingester: nist-oar configuration not provided")
cfg = config.resolve_configuration(confsrc, confserv)

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
        rmmconfsrc = acfg.get('rmm_config_loc', 'oar-rmm')
        if confenv:
            rmmconfsrc += '/'+confenv
        rmmcfg = config.resolve_configuration(rmmconfsrc, confserv)
        acfg['user'] = rmmcfg['oar.mongodb.readwrite.user'],
        acfg['pass'] = rmmcfg['oar.mongodb.readwrite.password'],

    except Exception, ex:
        raise ConfigurationException("Failed to retrieve Mongo authentication "+
                                     "info: "+str(ex), cause=ex)

application = wsgi.app(cfg)

