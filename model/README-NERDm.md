# The NIST Extensible Resource Data Model (NERDm): JSON schemas for rich description of digital resources

## Overview

The NIST Extensible Resource Data Model (NERDm) is set of schemas for encoding in JSON format metadata
that describe digital resources.  The variety of digital resources it can describe includes not only
digital data sets and collections, but also software, digital services, web sites and portals, and
digital twins.  It was created to serve as the internal metadata format used by the NIST Public Data
Repository and Science Portal to drive rich presentations on the web and to enable discovery; however, it
was also designed to enable programmatic access to resources and their metadata by external users.
Interoperability was also a key design aim: the schemas are defined using the JSON Schema standard,
metadata are encoded as JSON-LD, and their semantics are tied to community ontologies, with an emphasis
on DCAT and the US federal Project Open Data (POD) models.  Finally, extensibility is also central to its
design: the schemas are composed of a central core schema and various extension schemas.  New extensions
to support richer metadata concepts can be added over time without breaking existing applications.

### About Validation

Validation is central to NERDm's extensibility model.  Consuming applications should be able to choose
which metadata extensions they care to support and ignore terms and extensions they don't support.
Furthermore, they should not fail when a NERDm document leverages extensions they don't recognize, even
when on-the-fly validation is required.  To support this flexibility, the NERDm framework allows
documents to declare what extensions are being used and where.  We have developed an optional extension
to the standard JSON Schema validation (see ejsonschema below) to support flexible validation: while a
standard JSON Schema validater can validate a NERDm document against the NERDm core schema, our extension
will validate a NERDm document against any recognized extensions and ignore those that are not
recognized.

### Data Model Summary

The NERDm data model is based around the concept of resource, semantically equivalent to a schema.org
Resource, and as in schema.org, there can be different types of resources, such as data sets and
software.  A NERDm document indicates what types the resource qualifies as via the JSON-LD "@type"
property.  All NERDm Resources are described by metadata terms from the core NERDm schema; however,
different resource types can by describe by additional metadata properties (often drawing on particular
NERDm extension schemas).  A Resource can contain Components of various types (including
DCAT-defined Distributions); these can include specifically downloadable data files, hierachical data
collecitons, links to web sites (like software repositories), software tools, or other NERDm Resources.
Through the NERDm extension system, domain-specific metadata can be included at either the resource or
component level.  The direct semantic and syntactic connections to the DCAT, POD, and schema.org schemas
is intended to ensure unambiguous conversion of NERDm documents into those schemas.

### Status and Future

As of this writing, the Core NERDm schema and its framework stands at version 0.7 and is compatible with
the "draft-04" version of JSON Schema.  Version 1.0 is projected to be released in 2023.  In that
release, the NERDm schemas will be updated to the "draft2020" version of JSON Schema.  Other improvements
will include stronger support for RDF and the Linked Data Platform through its support of JSON-LD.

## Key Links

<dl>
  <dt> The NERDm JSON Schema Files: <br/>
       <a href="https://github.com/usnistgov/oar-metadata/tree/integration/model">
       https://github.com/usnistgov/oar-metadata/tree/integration/model</a> </dt>
  <dd> This directory contains the latest (and previous) versions of the core NERDm Schema and various
       extensions. All files with names of the form, "*-schema*.json" are JSON Schema definition files; those
       that do not include a version in the file name represent the latest versions. The latest version of the
       core schema is called `nerdm-schema.json`, and schemas with names of the form,
       `nerdm-`_[ext]_`-schema.json`, contain extension schemas. All NERDm schemas here are documented
       internally, including semantic definitions of all terms. </dd>

  <dt> ejsonschema: Software for Validating JSON supporting extension schemas <br/>
       <a href="">
       </a> </dt>
  <dd> This software repository provides Python software that extends the community software library,
       python-jsonschema
       (<a href="https://github.com/python-jsonschema/jsonschema">https://github.com/python-jsonschema/jsonschema</a>)
       to support NERDm's extension framework. Use the scripts/validate script to validate NERDm
       documents on the command line. (Type `validate -h` for more information.) </dd>

  <dt> Example NERDm Documents <br/>
       <a href="">
       </a> </dt>
  <dd> This folder contains example NERDm documents that illustrate the NERDm data model and use of
       extension schemas. These all can be validated using the ejsonschema validate script. </dd>

  <dt> NERDm Support Software <br/>
       <a href="">
       </a> </dt>
  <dd> This software repository includes a Python package, `nistoar.nerdm`, that aids in creating and
       handling NERDm documents. In particular, it includes converters that convert NERDm instances into
       other formats (like POD, schema.org, and DCAT). It can also transform NERDm documents conforming
       to earlier versions of the schemas to that of the latest versions. </dd>
</dl>

## References

[1] JSON Schema Website, URL: https://json-schema.org/

[2] Galiegue, F., Zyp, K, and Court, G. (2013). JSON Schema: core definitions and terminology (draft04),
IETF Internet-Draft, URL: https://datatracker.ietf.org/doc/html/draft-zyp-json-schema-04

[3] Galiegue, F., Zyp, K, and Court, G. (2013). JSON Schema: interactive and no interactive validation
 (draft04), IETF Internet-Draft, URL: https://datatracker.ietf.org/doc/html/draft-fge-json-schema-00 

[4] JSON-LD Website, URL: https://json-ld.org/

[5] Sporny, M., Longley, D., Kellogg, G., Lanthaler, M., Champin, P., Lindstrom (2020) JSON-LD 1.1: A
 JSON-based Serialization for Linked Data, W3C Recommendation 16 July 2020, URL:
 https://www.w3.org/TR/json-ld/

[6] Albertoni, R., Browning, D., Cox, S., Gonzalez Beltran, A., Perego, A, Winstanley, P. (2020) Data
 Catalog Vocabulary (DCAT) - Version 2, W3C Recommendation 04 February 2020, URL:
 https://www.w3.org/TR/vocab-dcat-2/

[7] United States Government, DCAT-US Schema v1.1 (Project Open Data Metadata Schema), URL:
 https://resources.data.gov/resources/dcat-us/

[8] McBride, B. (2004). The Resource Description Framework (RDF) and its Vocabulary Description Language
 RDFS. Handbook on Ontologies, 51-65. https://doi.org/10.1007/978-3-540-24750-0_3

[9] Candan, K. S., Liu, H., & Suvarna, R. (2001). Resource description framework. ACM SIGKDD Explorations
Newsletter, 3(1), 6-19. https://doi.org/10.1145/507533.507536 