# jq conversion library: converts JSON schema to wiki documenting markdown
#
# There several ways to run convert a NERDm JSON Schema to wiki markdown.
# To convert the entire schema:
#
#  jq -r -L $PWD/jq 'import "schema2wikimd" as s2w; s2w::describe_schema' \
#     SCHEMAFILE
#
# To convert a particular type definition:
#
#  jq -r -L $PWD/jq 'import "schema2wikimd" as s2w; s2w::describe_type("NAME")' \
#     SCHEMAFILE
#
# To convert a particular property definition:
#
#  jq -r -L $PWD/jq \
#     'import "schema2wikimd" as s2w; s2w::describe_prop("PROP", "NAME") \
#     SCHEMAFILE
#


# return true if the input is a string
def isstring: [strings or null, false][0];

def prefixes:
    { "https://www.nist.gov/od/dm/nerdm-schema/v0.1#": "nerdm",
      "https://www.nist.gov/od/dm/nerdm-schema/pub/v0.1#": "pubnerdm" }
;

def _add_prefix(url; prefix):
    .[url] = prefix
;

def _default_prefix(url; prefix):
    if .[url] then .
    else
       _add_prefix(url; prefix)
    end 
;

def prefixedref(url2pre; curschema):
    if (isstring|not) then error("$ref value not a string: " + (.|tostring)) 
       else . end | 
    . as $ref | sub(".*#/definitions/"; "") as $name |
    if startswith("#/definitions/") then
       (curschema | sub("#$"; "")) + .
    else .
    end |
    if startswith("http") then
       . as $ref | sub("#/definitions/.*"; "#") as $schemaid |
       url2pre | .[$schemaid] |
       if . then . else $schemaid end |
       . + ":" + $name
    else .
    end
;

def type2subclass(urlpre; curschema):
    if .allOf then
       .allOf | map( select(.["$ref"]) | .["$ref"] |
       prefixedref(urlpre; curschema) ) | join(", ")
    else
       ""
    end
;

def type2class(name; urlpre; curschema):
    "---+++ " + name + "\n\n" +
    "| *definition:*      | " + .description + "  | \n" +
    "| *subClassOf:*      | " + type2subclass(urlpre; curschema) + "  | \n" +
    "| *target version:*  | X.X  | \n\n" +
    if .notes then
        "Notes:\n" +
        (.notes | map("   * " + . + "\n") | join("")) + "\n"
    else
        ""
    end
;

def proptype(urlpre; curschema):
    if .["$ref"] then
       .["$ref"] | prefixedref(urlpre; curschema)
    elif .anyOf then
       .anyOf[0] | proptype(urlpre; curschema)
    elif .type == "array" then
       .items |
         (objects | .),
         (arrays  | .[0]) | proptype(urlpre; curschema)
    else
       .type | tostring
    end
;

def dcref:
    if .asOntology.referenceProperty then
      if (.asOntology.referenceProperty|startswith("dc:")) or
         (.asOntology.referenceProperty|startswith("dct:"))  then
          .asOntology.referenceProperty
      else ""
      end
    else ""
    end
;

def prop2prop(name; urlpre; curschema):
    "---+++++ " + name + "\n\n" +
    "| *reference property:*  | " + .asOntology.referenceProperty + "  | \n" +
    "| *definition:*          | " + .description + "  | \n" +
    "| *type:*                | " + proptype(urlpre; curschema) +"  | \n" +
    "| *POD correspondence:*  | | \n" + 
    "| *DC correspondence:*   | " + dcref + "  | \n" + 
    "| *target version:*      | X.X  | \n\n" +
    if .notes then
        "Notes:\n" +
        (.notes | map("   * " + . + "\n") | join(""))
    else
        ""
    end
;

def describe_prop(type; name):
    prefixes as $urlpre |
    .id as $curschema   |
    .definitions | .[type] | .properties | .[name] |
    prop2prop(name; $urlpre; $curschema)
;

def desc_properties(urlpre; curschema):
    if .allOf then
       (.allOf | [.[1]] | 
        map( select(.["$ref"]|not) | desc_properties(urlpre; curschema) ) |
        join("\n"))
    elif .properties then
       (.properties | to_entries | 
        map( .key as $key | .value | prop2prop($key; urlpre; curschema) ) |
        join("\n"))
    else ""
    end
;

def type2classwprops(name; urlpre; curschema):
    (type2class(name; urlpre; curschema)) +
       "---++++ Properties\n\n" +
    desc_properties(urlpre; curschema)
;

def describe_type(name):
    prefixes as $urlpre | .id as $curschema   |
    .definitions | .[name] | type2classwprops(name; $urlpre; $curschema)
;

def describe_schema:
    prefixes as $urlpre | .id as $curschema   |
    ("---+ " + .title + "\n\n" + .description + "\n\n---++ Classes\n\n") + 
    (.definitions | to_entries |
    map( .key as $key | .value | type2classwprops($key; $urlpre; $curschema) ) |
    join("\n"))
;

def junk:
    .
;
