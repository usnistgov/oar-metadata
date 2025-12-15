#! /usr/bin/env python
#
# Usage: ingest-patents.py [-M URL] [--no-drop] [-q] [-s]
#
import os, sys, json, logging
from argparse import ArgumentParser
from datetime import datetime
from pymongo import MongoClient

# Save the repo root BEFORE basedir gets overwritten by OAR_HOME
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

basedir = repo_root
oarpypath = os.path.join(basedir, "python")
if 'OAR_HOME' in os.environ:
    basedir = os.environ['OAR_HOME']
    oarpypath = os.path.join(basedir, "lib", "python") + ":" + \
                os.path.join(basedir, "python")
if 'OAR_PYTHONPATH' in os.environ:
    oarpypath = os.environ['OAR_PYTHONPATH']
sys.path.extend(oarpypath.split(os.pathsep))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ingest-patents")

def define_opts(progname=None):
    parser = ArgumentParser(progname, None,
        "ingest patents metadata into the RMM (reads patents.json from ../products/patents.json)", None)
    parser.add_argument('-M', '--mongodb-url', metavar='URL', type=str, dest='url',
                        action='store', default="mongodb://mongodb:3333/TestDB",
                        help="MongoDB URL (e.g., mongodb://HOST:PORT/DBNAME)")
    parser.add_argument('--no-drop', dest='drop', default=True,
                        action='store_false',
                        help="Do not drop the existing 'patents' collection before ingest")
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

    # Strictly look for products/patents.json in the repo root
    infile = os.path.join(repo_root, "products", "patents.json")
    
    if not os.path.exists(infile):
        if not opts.silent:
            print(
                f"{parser.prog}: patents.json not found at {infile}",
                file=sys.stderr
            )
        return 1

    if not opts.quiet:
        print(f"Using input file: {infile}")

    try:
        with open(infile) as fd:
            patents = json.load(fd)
    except Exception as ex:
        if not opts.silent:
            print(f"{parser.prog}: failed to read JSON: {ex}", file=sys.stderr)
        return 1

    if not isinstance(patents, list):
        if not opts.silent:
            print(f"{parser.prog}: expected a JSON array of patents", file=sys.stderr)
        return 1

    client = MongoClient(opts.url)
    db = client.get_database()
    try:
        if opts.drop:
            db.drop_collection("patents")
            if not opts.quiet:
                print("Dropped existing 'patents' collection")
        db.patents.create_index([("$**", "text")])
        db.patents.create_index([("Descriptive Title", 1)])
        db.patents.create_index([("Patent #", 1)])
        db.patents.create_index([("Laboratory 1", 1)])
        db.patents.create_index([("Status", 1)])
        db.patents.create_index([("File Date", 1)])
    except Exception as ex:
        if not opts.silent:
            print(f"{parser.prog}: failed initializing collection/index: {ex}", file=sys.stderr)
        client.close()
        return 1

    success = 0
    for rec in patents:
        try:
            rec = normalize_dates(rec)
            db.patents.insert_one(rec)
            success += 1
        except Exception as ex:
            log.error("Failed to ingest record: %s", ex)

    client.close()
    if not opts.quiet:
        print(f"Ingested {success} patents out of {len(patents)}")
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))