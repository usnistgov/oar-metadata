"""
a simulated uwsgi module
"""
opt = {}

import imp as _imp
import sys, os
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
    for arg in opts.ph:
        parts = arg.split('=', 1)
        if len(parts) < 2:
            raise RuntimeError("Bad placeholder argument: "+arg)
        wsgiopt[parts[0]] = parts[1].encode()

    if opts.oar_config_file:
        wsgiopt['oar_config_file'] = opts.oar_config_file.encode()
    if opts.oar_working_dir:
        wsgiopt['oar_working_dir'] = opts.oar_working_dir.encode()



