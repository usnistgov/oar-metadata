"""
This module sets important constants (like schema URIs) for handling NERDm 
data to make them available from Python.
"""
core_schema_base = "https://data.nist.gov/od/dm/nerdm-schema/"

schema_versions = ["v0.2", "v0.1"]

def core_schema_uri_for(version):
    """
    return the schema URI for the requested version of the Core NERDm schema
    @raises ValueError   if the given version is not a recognized version
    """
    return schema_uri_for(core_schema_base, version)

def pub_schema_uri_for(version):
    """
    return the schema URI for the requested version of the Core NERDm schema
    @raises ValueError   if the given version is not a recognized version
    """
    return schema_uri_for(core_schema_base+"pub/", version)

def schema_uri_for(schema_base, version):
    """
    return the schema URI for the requested version of the Core NERDm schema
    @raises ValueError   if the given version is not a recognized version
    """
    if version in schema_versions:
        return schema_base+version
    vers = "v" + version
    if vers in schema_versions:
        return schema_base+vers

    raise ValueError("Not an recognized NERDm version: " + version)

CORE_SCHEMA_URI = core_schema_uri_for(schema_versions[0])
PUB_SCHEMA_URI = pub_schema_uri_for(schema_versions[0])

TAXONOMY_VOCAB_BASE_URI = "https://data.nist.gov/od/dm/nist-themes/"
TAXONOMY_VOCAB_INIT_URI = "https://www.nist.gov/od/dm/nist-themes/v1.0"

taxon_versions = ["v1.1", "v1.0"]

def taxon_uri_for(taxon_base, version):
    """
    return the schema URI for the requested version of the Core NERDm schema
    @raises ValueError   if the given version is not a recognized version
    """
    if version in taxon_versions:
        return taxon_base+version
    vers = "v" + version
    if vers in taxon_versions:
        return taxon_base+vers

    raise ValueError("Not an recognized NERDm version: " + version)

TAXONOMY_VOCAB_URI = taxon_uri_for(TAXONOMY_VOCAB_BASE_URI, taxon_versions[0])
