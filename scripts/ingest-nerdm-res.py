#! /usr/bin/env python
#
# Usage: ingest-nerdm-res.py [-VqsU] [-M URL] NERD_FILE_OR_DIR [...]
# See help details via: ingest-nerdm-res.py -h
#
# Load NERDm JSON files into the RMM
#
import os, sys, errno, json, re, warnings
from argparse import ArgumentParser

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
oarpypath = os.path.join(basedir, "python")
if 'OAR_HOME' in os.environ:
    basedir = os.environ['OAR_HOME']
    oarpypath = os.path.join(basedir, "lib", "python") +":"+ \
                os.path.join(basedir, "python")
schemadir = os.path.join(basedir, "etc", "schemas")
if not os.path.exists(schemadir):
    sdir = os.path.join(basedir, "model")
    if os.path.exists(sdir):
        schemadir = sdir
    
if 'OAR_PYTHONPATH' in os.environ:
    oarpypath = os.environ['OAR_PYTHONPATH']

sys.path.extend(oarpypath.split(os.pathsep))
try:
    import nistoar
except ImportError as e:
    nistoardir = os.path.join(basedir, "python")
    sys.path.append(nistoardir)
    import nistoar

from nistoar.rmm.mongo.nerdm import (NERDmLoader, LoadLog, RecordIngestError,
                                     JSONEncodingError)

description = \
"""ingest NERDm resource data into the RMM.

Files or directories can be listed on the command-line.  When a directory is
listed, this script will search the directory (and its subdirectories) for files
with the '.json' extension and attempt to load them as NERDm files.  
"""

epilog = None

def define_opts(progname=None):
    parser = ArgumentParser(progname, None, description, epilog)
    parser.add_argument('nerdfile', metavar='NERDFILEDIR', type=str, nargs='+',
                        help="a file or directory containing the resource data")
    parser.add_argument('-V', '--skip-validate', dest='validate', default=True,
                        action="store_false",
                        help="do not attempt to validate the records before "+
                             "ingesting them")
    parser.add_argument('-A', '--archive-records', dest='archdir', metavar="DIR",
                        action='store', default=None,
                        help="after successfully loading each record, save a copy "+
                             "of it in the directory DIR")
    parser.add_argument('-q', '--quiet', dest='quiet', default=False,
                        action="store_true",
                        help="do not print non-fatal status messages")
    parser.add_argument('-s', '--silent', dest='silent', default=False,
                        action="store_true", help="print no messages at all")
    parser.add_argument('-U', '--warn-update', dest='warn', default=False,
                        action="store_true", help="print a warning message if "+
                               "one or more records overwrite/update previous "+
                               "existing records")
    parser.add_argument('-M', '--mongodb-url', metavar='URL',type=str,dest='url',
                        action='store', default="mongodb://mongodb:3333/TestDB",
                        help="the URL to the MongoDB database to load into (in "+
                             "the form 'mongodb://HOST:PORT/DBNAME')")

    return parser

def main(args):
    parser = define_opts()
    opts = parser.parse_args(args)
    if opts.silent:
        opts.quiet = True
    if opts.archdir and (not os.path.isdir(opts.archdir) or not os.access(opts.archdir, os.W_OK)):
        print("{0}: {1}: not a directory with write permission".format(parser.prog, opts.archdir),
              file=sys.stderr)
        return 3

    stat = 0
    loader = NERDmLoader(opts.url, schemadir)
    if opts.warn and not opts.quiet:
        loader.onupdate = 'warn'
        warnings.simplefilter("once")
    totres = LoadLog()

    for nerdpath in opts.nerdfile:
        validate = opts.validate

        if os.path.isdir(nerdpath):
            res = load_from_dir(nerdpath, loader, validate, opts.archdir)
        elif os.path.isfile(nerdpath):
            res = load_from_file(nerdpath, loader, validate, opts.archdir)
        elif not os.path.exists(nerdpath):
            res = LoadLog().add(nerdpath, [ "File not found." ])
        else:
            res = LoadLog().add(nerdpath, [ "Filepath not loadable." ])

        totres.merge(res)

        if not opts.silent and res.failure_count > 0:
            if not opts.quiet:
                print("{0}: The following records failed to load:"
                      .format(parser.prog), file=sys.stderr)
                for f in res.failures():
                    why = (isinstance(f.errs[0], RecordIngestError) and \
                               "Ingest error") or "Validation errors"
                    why += ": "+fmterrs(f.errs)
                    print("\t{0}: \t{1}".format(str(f.key), why))
            else:
                print("{0}: {1}: {2} out of {3} records failed to load"
                      .format(parser.prog, fldfile, res.failure_count,
                              res.attempt_count))

    if not opts.quiet:
        print("Ingested {0} out of {1} records".format(totres.success_count,
                                                       totres.attempt_count))

    if totres.failure_count > 0:
        stat = 2
    return stat

def load_from_dir(dirpath, loader, validate=True, archdir=None):
    results = LoadLog()

    for root, dirs, files in os.walk(dirpath):
        # don't look in .directorys
        for i in range(len(dirs)-1, -1, -1):
            if dirs[i].startswith('.'):
                del dirs[i]

        for f in files:
            if f.startswith('.') or not f.endswith('.json'):
                continue
            f = os.path.join(root, f) 
            load_from_file(f, loader, validate, archdir, results)
                                                  
    return results

def load_from_file(filepath, loader, validate=True, archdir=None, results=None):
    with open(filepath) as fd:
        try:
            data = json.load(fd)
        except ValueError as ex:
            ex = JSONEncodingError(ex)
            return LoadLog().add(filepath, ex)

    out = loader.load(data, validate=validate, results=results, id=filepath)

    if archdir and out.failure_count == 0:
        recid = re.sub(r'/.*$', '', re.sub(r'ark:/\d+/', '', data.get('@id','')))
        if not recid:
            # should not happen
            recid = filepath
        ver = data.get('version', '1.0.0').replace('.', '_')
        outfile = os.path.join(archdir, "%s-v%s.json" % (os.path.basename(recid), ver))

        # this should not raise errors, but if it does, let it bubble up
        with open(outfile, 'w') as fd:
            json.dump(data, fd, indent=2)
            
    return out



def fmterrs(errs):
    msgs = str(errs[0]).split("\n")
    out = msgs[0]
    if len(errs) > 1 or len(msgs) > 1:
        out += "..."
    return out
    
    
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
