#! /usr/bin/env python
#
# Usage: ingest-papers.py [-M URL] [--input FILE] [--no-drop] [-q] [-s]
#
import os, sys, json, logging
from argparse import ArgumentParser
from datetime import datetime
from pymongo import MongoClient

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
oarpypath = os.path.join(basedir, "python")
if 'OAR_HOME' in os.environ:
    basedir = os.environ['OAR_HOME']
    oarpypath = os.path.join(basedir, "lib", "python") +":"+ \
                os.path.join(basedir, "python")
if 'OAR_PYTHONPATH' in os.environ:
    oarpypath = os.environ['OAR_PYTHONPATH']
sys.path.extend(oarpypath.split(os.pathsep))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ingest-papers")

DEF_INPUT = os.path.join(basedir, "etc", "data", "papers.json")

def define_opts(progname=None):
    parser = ArgumentParser(progname, None,
        "ingest papers metadata into the RMM", None)
    parser.add_argument('--input', metavar='FILE', dest='infile',
                        default=DEF_INPUT,
                        help="Path to patents/papers JSON (default: etc/samples/papers.json)")
    parser.add_argument('-M', '--mongodb-url', metavar='URL', type=str, dest='url',
                        default="mongodb://mongodb:3333/TestDB",
                        help="MongoDB URL (e.g., mongodb://HOST:PORT/DBNAME)")
    parser.add_argument('--no-drop', dest='drop', default=True,
                        action='store_false',
                        help="Do not drop the existing 'papers' collection before ingest")
    parser.add_argument('-q', '--quiet', dest='quiet', default=False,
                        action="store_true",
                        help="suppress non-fatal status messages")
    parser.add_argument('-s', '--silent', dest='silent', default=False,
                        action="store_true", help="print no messages at all")
    return parser

DATE_FIELDS = ["File Date", "Patent Issue Date", "Expiration Date", "Publication Date"]

def normalize_dates(doc):
    for field in DATE_FIELDS:
        if doc.get(field):
            try:
                ts = int(doc[field]) / 1000.0
                doc[field] = datetime.fromtimestamp(ts).isoformat()
            except Exception:
                doc[field] = None
    return doc

def main(args):
    parser = define_opts()
    opts = parser.parse_args(args)
    if opts.silent:
        opts.quiet = True

    if not os.path.isfile(opts.infile):
        if not opts.silent:
            print(f"{parser.prog}: input file not found: {opts.infile}", file=sys.stderr)
        return 1

    try:
        with open(opts.infile) as fd:
            papers = json.load(fd)
    except Exception as ex:
        if not opts.silent:
            print(f"{parser.prog}: failed to read JSON: {ex}", file=sys.stderr)
        return 1

    if not isinstance(papers, list):
        if not opts.silent:
            print(f"{parser.prog}: expected a JSON array of papers", file=sys.stderr)
        return 1

    client = MongoClient(opts.url)
    db = client.get_database()
    try:
        if opts.drop:
            db.drop_collection("papers")
            if not opts.quiet:
                print("Dropped existing 'papers' collection")
        db.papers.create_index([("$**", "text")])
        db.papers.create_index([("Descriptive Title", 1)])
        db.papers.create_index([("Patent #", 1)])
        db.papers.create_index([("Laboratory 1", 1)])
        db.papers.create_index([("Status", 1)])
        db.papers.create_index([("File Date", 1)])
    except Exception as ex:
        if not opts.silent:
            print(f"{parser.prog}: failed initializing collection/index: {ex}", file=sys.stderr)
        client.close()
        return 1

    success = 0
    for rec in papers:
        try:
            rec = normalize_dates(rec)
            db.papers.insert_one(rec)
            success += 1
        except Exception as ex:
            log.error("Failed to ingest record: %s", ex)

    client.close()
    if not opts.quiet:
        print(f"Ingested {success} papers out of {len(papers)}")
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))