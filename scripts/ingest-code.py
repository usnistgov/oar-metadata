#! /usr/bin/env python
#
# Usage: ingest-code.py [-M URL] [--source-url URL] [--no-drop] [-q] [-s]
#
# Load code releases from the NIST code API into the MongoDB 'code' collection.
#

import os, sys, json, logging, warnings
from argparse import ArgumentParser
import requests
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
log = logging.getLogger("ingest-code")

CODE_API_URL = "https://code.nist.gov/explore/code.json"

def define_opts(progname=None):
    parser = ArgumentParser(progname, None,
        "ingest code metadata into the RMM", None)
    parser.add_argument('-M', '--mongodb-url', metavar='URL', type=str, dest='url',
                        action='store', default="mongodb://mongodb:3333/TestDB",
                        help="MongoDB URL to load into (e.g., mongodb://HOST:PORT/DBNAME)")
    parser.add_argument('--source-url', metavar='URL', type=str, dest='srcurl',
                        default=CODE_API_URL,
                        help="Override the source URL for code JSON")
    parser.add_argument('--no-drop', dest='drop', default=True,
                        action='store_false',
                        help="Do not drop the existing 'code' collection before ingest")
    parser.add_argument('-q', '--quiet', dest='quiet', default=False,
                        action="store_true",
                        help="suppress non-fatal status messages")
    parser.add_argument('-s', '--silent', dest='silent', default=False,
                        action="store_true", help="print no messages at all")
    return parser

def fetch_code_data(srcurl):
    resp = requests.get(srcurl, timeout=30)
    resp.raise_for_status()
    return resp.json()

def transform_release(release):
    return {
        "name": release.get("name", ""),
        "organization": release.get("organization", ""),
        "description": release.get("description", ""),
        "repositoryURL": release.get("repositoryURL", ""),
        "homepageURL": release.get("homepageURL", ""),
        "downloadURL": release.get("downloadURL", ""),
        "languages": release.get("languages", []),
        "contact": {
            "email": release.get("contact", {}).get("email", ""),
            "url": release.get("contact", {}).get("URL", "")
        },
        "dates": {
            "created": release.get("date", {}).get("created", ""),
            "lastModified": release.get("date", {}).get("lastModified", "")
        },
        "permissions": {
            "usageType": release.get("permissions", {}).get("usageType", ""),
            "licenses": release.get("permissions", {}).get("licenses", [])
        },
        "status": release.get("status", ""),
        "laborHours": release.get("laborHours", 0),
        "tags": release.get("tags", []),
        "vcs": release.get("vcs", ""),
        "@type": "CodeRepository"
    }

def main(args):
    parser = define_opts()
    opts = parser.parse_args(args)
    if opts.silent:
        opts.quiet = True

    try:
        data = fetch_code_data(opts.srcurl)
    except Exception as ex:
        if not opts.silent:
            print(f"{parser.prog}: failed to fetch code data: {ex}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        if not opts.silent:
            print(f"{parser.prog}: invalid JSON format from source", file=sys.stderr)
        return 1

    releases = data.get("releases", [])
    if not isinstance(releases, list):
        if not opts.silent:
            print(f"{parser.prog}: 'releases' not found or not a list", file=sys.stderr)
        return 1

    client = MongoClient(opts.url)
    db = client.get_database()
    try:
        if opts.drop:
            db.drop_collection("code")
            if not opts.quiet:
                print("Dropped existing 'code' collection")
        db.code.create_index([("$**", "text")])
    except Exception as ex:
        if not opts.silent:
            print(f"{parser.prog}: failed initializing collection/index: {ex}", file=sys.stderr)
        client.close()
        return 1

    success = 0
    for rel in releases:
        try:
            if rel.get("name"):
                doc = transform_release(rel)
                db.code.insert_one(doc)
                success += 1
        except Exception as ex:
            log.error("Failed to ingest release %s: %s", rel.get("name","<unnamed>"), ex)

    client.close()
    if not opts.quiet:
        print(f"Ingested {success} code records out of {len(releases)}")
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))