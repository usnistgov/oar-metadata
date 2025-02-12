"""
a simulated uwsgi module
"""
opt = {}

import imp as _imp
import sys, os, shutil
from argparse import ArgumentParser

def load_as_root_module():
    """
    This loads this module under the symbol uwsgi so that later attempts to import 
    uwsgi will get this simulated version.
    """
    srcf = __file__
    if srcf.endswith('.pyc'):
        srcf = srcf[:-1]
    with open(srcf) as fd:
        return _imp.load_module("uwsgi", fd, srcf, (".py", 'r', _imp.PY_SOURCE))

def load():
    """
    load a simulated uwsgi environment based on command line arguments
    """
    out = load_as_root_module()
    parser = create_parser(os.path.basename(sys.argv[0]))
    opts = parser.parse_args(sys.argv[1:])
    load_env(opts, out.opt)

    return out 

def create_parser(progname):
    usage = None
    desc = "Run the %s uWSGI service script in a simulated mode" % progname
    parser = ArgumentParser(progname, usage, desc)

    parser.add_argument("-c", "--config-file", type=str, dest="oar_config_file", metavar="FILE",
                        help="read service configuration file from FILE")
    parser.add_argument("-w", "--working-dir", type=str, dest="oar_working_dir", metavar="DIR",
                        help="set DIR as the working directory of the service")
    parser.add_argument("--set-ph", type=str, dest="ph", action="append", default=[], metavar="VAR=VAL",
                        help="set an arbitrary place-holder variable")

    return parser

def load_env(opts, wsgiopt):
    """
    load an WSGI environment dictionary with command-line option data.  This 
    is intended for use with :py:func:`create_parser`.  
    """
    for arg in opts.ph:
        parts = arg.split('=', 1)
        if len(parts) < 2:
            raise RuntimeError("Bad placeholder argument: "+arg)
        wsgiopt[parts[0]] = parts[1].encode()

    if opts.oar_config_file:
        wsgiopt['oar_config_file'] = opts.oar_config_file.encode()
    if opts.oar_working_dir:
        wsgiopt['oar_working_dir'] = opts.oar_working_dir.encode()

def get_ini_option(base=None, env=None, surmise=True):
    """
    return a string that should be added to a uwsgi command line providing options
    needed to run a Python-WSGI-implemented web service and which best match the 
    local installation of uwsgi.  

    How uwsgi was installed can affect what options must be included (if any, such 
    as ``--plugin``).  If the returned string is non-empty, it will usually start 
    with ``--ini ``, indicating a uwsgi configuration file to load.  An empty string 
    indicates that no generic options are needed.  

    This first checks if the ``OAR_UWSGI_OPTS`` environment variable is set; if so,
    it returns that.  The value should be one or more command-line options.  If not 
    set, it will look for a file called ``oar_uwsgi.ini`` in the following locations, 
    in order: _base_``/etc/uwsgi`` (where _base_ is the value of the ``base`` 
    argument), ``$OAR_HOME/etc/uwsgi``, and ``./etc/wsgi``.  

    Next, this function will look at where uwsgi is installed and then assume a 
    different name for ini file: if uwsgi is found in ``/usr/local/bin``, the ini 
    file name assumed is "pipinstalled.ini"; if it is in ``/usr/bin``, 
    "osinstalled.ini" is assumed.  The function then searches the same locations 
    for that filename.  

    If no such files are found, an empty string is returned.  

    :param str base:      a base directory where the PDR software is installed
    :param dict env:      the environment to use; if None, ``os.environ`` is used.  
    :param bool surmise:  if True (default), look for an ini file that depends on 
                          where uwsgi is installed; if False, skip this extra check.
    :return:  options to add to a uwsgi command line to run a python WSGI web service
              :rtype: str
    """
    if env is None:
        env = os.environ

    if env.get('OAR_UWSGI_OPTS') is not None:
        return env['OAR_UWSGI_OPTS']

    locs = []
    if base:
        locs.append(os.path.join(base, "etc", "uwsgi"))
    if env.get('OAR_HOME'):
        locs.append(os.path.join(env['OAR_HOME'], "etc", "uwsgi"))
    locs.append(os.path.join(".", "etc", "uwsgi"))

    def find_file_in(fname, dirs):
        for loc in dirs:
            fpath = os.path.join(loc, fname)
            if os.path.exists(fpath):
                return fpath
        return None

    out = find_file_in("oar_uwsgi.ini", locs)
    if not out and surmise:
        uwsgipath = shutil.which("uwsgi")
        if uwsgipath == "/usr/local/bin/uwsgi":
            out = find_file_in("pipinstalled.ini", locs)
        elif uwsgipath == "/usr/bin/uwsgi":
            out = find_file_in("osinstalled.ini", locs)
    if out:
        return "--ini "+out

    return ""
                    


