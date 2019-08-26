"""
tools for validating NERDm metadata
"""
from collections import Mapping

import ejsonschema as ejs

def get_mdval_flavor(data):
    """
    return the prefix used to identify meta-properties used for validation 
    in the given NERDm record, or None if no meta-properties are found.
    """
    for prop in "schema extensionSchemas".split():
        mpfxs = [k[0] for k in data.keys() if k[1:] == prop and k[0] in "_$"]
        if len(mpfxs) > 0:
            return mpfxs[0]
    return None

def validate(nerdm, schemadir, typeuri=None, strict=True):
    """
    validate the NERDm record data, return a list of errors.  

    This implementation is not actually NERDm specific: if the schema URIs 
    either specified by typeuri or found in the record data can be found in 
    the schema directory, the validation should be successful.  

    :param Mapping nerdm:  the NERDm data to validate
    :param str schemadir:  the directory where the NERDm schemas are cached
    :param str typeuri:    the URI identifying the type of the base object 
                             provided in nerdm.  If not provided, the _schema
                             property will be used.  
    """
    valid8r = create_validator(schemadir, nerdm)
    return valid8r.validate(nerdm, schemauri=typeuri, strict=strict,
                            raiseex=False)

def create_validator(schemadir, forprefix="_"):
    """
    return a validator instance (ejsonschema.ExtValidator) that can validate
    NERDm records.

    The Validator assumes a particular prefix (usually "_" or "$") for 
    identifying the so-called "metaproperties" that are used for validation.
    This can be set by the forprefix parameter.  

    :param str schemadir:  the directory where the NERDm schemas are cached
    :param forprefix:      Either a single character ("_" or "$") or a NERDm 
                           data record used to determine the metaproperty 
                           convention.  If the value is a Mapping, it is 
                           assumed to be a NERDm record that contains 
                           metaproperties beginning either with "_" or "$";
                           which ever convention this record appears to be 
                           using will be the prefix assumed.  
    """
    if isinstance(forprefix, Mapping):
        forprefix = get_mdval_flavor(forprefix) or "_"
    if not isinstance(forprefix, (str, unicode)):
        raise TypeError("create_validator: forprefix: not a str or dict")

    return ejs.ExtValidator.with_schema_dir(schemadir, forprefix)

