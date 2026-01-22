#! /usr/bin/env python
#
# Usage: ingest-patents.py [-M URL] [--input FILE] [--no-drop] [-q] [-s]
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
log = logging.getLogger("ingest-patents")

def define_opts(progname=None):
    parser = ArgumentParser(progname, None,
        "ingest patents metadata into the RMM", None)
    parser.add_argument('--input', metavar='FILE', dest='infile',
                        required=True,
                        help="Path to patents JSON file (required)")
    parser.add_argument('-M', '--mongodb-url', metavar='URL', type=str, dest='url',
                        default="mongodb://mongodb:3333/TestDB",
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

NERDM_CONTEXT = "https://data.nist.gov/od/dm/nerdm-schema/v0.7#"
NIST_LICENSE = "https://www.nist.gov/open/license"
NIST_PUBLISHER = {"@type": "org:Organization", "name": "National Institute of Standards and Technology"}

def _split_list(val):
    if not val:
        return []
    if isinstance(val, list):
        return [v for v in val if v]
    if isinstance(val, str):
        return [v.strip() for v in val.split(";") if v.strip()]
    return []

def normalize_dates(doc):
    for field in DATE_FIELDS:
        if doc.get(field):
            try:
                if isinstance(doc[field], (int, float)):
                    ts = float(doc[field]) / 1000.0
                    doc[field] = datetime.fromtimestamp(ts).isoformat()
                else:
                    doc[field] = str(doc[field])
            except Exception:
                doc[field] = str(doc[field])
    return doc

def transform_patent(rec):
    title = (rec.get("Application Title") or rec.get("Descriptive Title") or "").strip()
    issued = (rec.get("Patent Issue Date") or rec.get("File Date") or "").strip()
    patent_no = (rec.get("Patent #") or "").strip()

    keywords = []
    keywords += _split_list(rec.get("Inventor"))
    keywords += _split_list(rec.get("Assignee 1"))
    if rec.get("Laboratory 1"):
        keywords.append(rec.get("Laboratory 1"))
    if rec.get("Division 1"):
        keywords.append(rec.get("Division 1"))

    return {
        "@context": [NERDM_CONTEXT],
        "@type": ["Patent"],
        "@id": f"patent:{patent_no}" if patent_no else f"patent:{rec.get('PATENTMASTERID')}",
        "title": title,
        "description": [rec.get("Description", "")] if rec.get("Description") else [],
        "contactPoint": {"fn": rec.get("NIST Contact", "")} if rec.get("NIST Contact") else {},
        "modified": issued,
        "status": rec.get("Status", ""),
        "ediid": str(rec.get("PATENTMASTERID", "")) if rec.get("PATENTMASTERID") is not None else "",
        "landingPage": rec.get("Link", ""),
        "accessLevel": "public",
        "license": NIST_LICENSE,
        "keyword": [k for k in keywords if k],
        "theme": [],
        "topic": [],
        "inventory": [],
        "components": [],
        "publisher": NIST_PUBLISHER,
        "language": ["en"],
        "bureauCode": [],
        "programCode": [],
        "dataHierarchy": [],
        "version": "1.0.0"
    }

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
        db.patents.create_index([("title", 1)])
        db.patents.create_index([("@id", 1)])
        db.patents.create_index([("keyword", 1)])
        db.patents.create_index([("status", 1)])
        db.patents.create_index([("modified", 1)])
    except Exception as ex:
        if not opts.silent:
            print(f"{parser.prog}: failed initializing collection/index: {ex}", file=sys.stderr)
        client.close()
        return 1

    success = 0
    for rec in patents:
        try:
            rec = normalize_dates(rec)
            doc = transform_patent(rec)
            db.patents.insert_one(doc)
            success += 1
        except Exception as ex:
            log.error("Failed to ingest record: %s", ex)

    client.close()
    if not opts.quiet:
        print(f"Ingested {success} patents out of {len(patents)}")
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))