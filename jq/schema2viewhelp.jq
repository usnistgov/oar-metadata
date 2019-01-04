# jq conversion library:  ejsonschema to doc JSON
#
# This library collects pertinent information for building
# human-readable documentation.
#

def stripref:
    gsub(".*#/definitions/"; "")
;

def iteminfo:
    if .["$ref"] then
        (.["$ref"] | stripref)
    else
        .type
    end
;

def show_type:
    if .anyOf then
      .anyOf | map(select(.type!="null") | show_type) | join(" or ")
    else
      if .["$ref"] then
        (.["$ref"] | stripref) + " object"
      else
        if .type then
          if .type == "string" then
              "text" +
              if .format == "uri" then
                  " (URL)"
              else
                  if .format then " ("+.format+")" else "" end
              end
          else
              if .type == "array" then
                  if .items.type == "string" then
                      "list of text values"
                  else
                    if .items["$ref"] then
                      {
                         template: "list of {type} objects",
                         data: { type: (.items["$ref"]|stripref) }
                      }
                    else
                      "list of " + (.items | show_type) + "s"
                    end
                  end
              else
                  if .type == "int" then "integer"
                  else
                     if .type == "float" then "decimal"
                     else .type end
                  end
              end
          end
        else
          if .enum then
             if (.enum|length) > 1 then
                "fixed value, one of: \"" + (.enum | join("\", \"")) + "\""
             else
                "fixed value: \"" + .enum[0] + "\""
             end
          else
             "(see JSON schema)"
          end
        end
      end
    end
;

def typeinfo:
    if .anyOf then
      if (.anyOf|length) > 1 then
        (.anyOf |
         { type: (map(select(.type!="null") | typeinfo) +
                  (map(select(.type="null")) | .[0] | [{ type: "null" }])) })
      else
        (.anyOf[0] | typeinfo)
      end
    else
      if .["$ref"] then
        { type: "object", of: .["$ref"] | stripref }
      else
        if .type then
          if .type == "array" then
            { type, each: .items | iteminfo } 
          else
            { type }
          end
        else
          if .enum then
            { type: "fixed" }
          else
            { type: "unknown" }
          end
        end
      end
    end +
    if .format then { format } else {} end +
    { show: show_type }
;

def index_refs:
    .
;

def upd_index_for(key; val):
   if .[key]
   then 
     .[key] |= .[key] + [val]
   else
     .[key] |= [val]
   end
;

def select_ref:
    .[] | select(.["$ref"])
;

def merge_in_index(updidx):
    reduce (updidx|keys_unsorted)[] as $key
      (.; if .[$key]
          then
            .[$key] += updidx[$key]
          else
            .[$key] |= updidx[$key]
          end)
;

def extract_use_from_proptype(name; tp):
    if .of then
      (.of as $type | {} |
       .[$type] |=
         { "template":
              "as a value type for the {prop} property in the {type} type",
           "data": { "prop": name, "type": tp }, id: "value-type"} )
    else
      if .each then
        (.each as $type | {} |
         .[$type] |=
           { "template":
              "as a value type for the {prop} list property of the {type} type",
              "data": { "prop": name, "type": tp }, id: "list-type"} )
      else
        empty
      end
    end
;

def extract_use_from_prop_post(name; tp):
    .type |
    (arrays |  
       map( extract_use_from_prop_type(name; tp) ) |
       reduce .[] as $item ({}; .|merge_in_index($item)),
     objects |
       extract_use_from_prop_type(name; tp)
    )
;

def extract_use_from_prop(name; tp):
    if .["$ref"]
    then
      ({"template":
             "as a value type for the {prop} property in the {type} type",
        "data": { "prop": name, "type": tp }, id: "value-type"} as $val |
       (.["$ref"] | stripref) as $ref |
       ({}|.[$ref] |= [$val]))
    else
      if .items["$ref"]
      then
        ({"template":
              "as a value type for the {prop} list property of the {type} type",
          "data": { "prop": name, "type": tp }, id: "list-type"} as $val |
         (.items["$ref"] | stripref) as $ref |
         ({}|.[$ref] |= [$val]))
      else
        if (.allOf and (.allOf | select_ref))
        then
          ({"template":
             "as a part of the value type for the {prop} property of the {type} type",
            "data": { "prop": name, "type": tp }, id: "value-part"}  as $val |
           [.allOf | select_ref | (.["$ref"] | stripref) as $ref |
            ({}|.[$ref] |= [$val])] |
           reduce .[] as $item ({}; .|merge_in_index($item)))
        else
          empty
        end
      end
    end
;

def extract_use_in_allOf(name):
    select(.allOf) | .allOf |
    ((select_ref | .["$ref"] | stripref as $ref |
      {template: "as the basis for extension type, {type}",
        data: { type: name }, id: "base-type" }      as $val |
      ({}|.[$ref] |= [$val])
     ),
     (.[] | select(.properties) | .properties | to_entries |
      (.[] | .key as $pname | .value |
       extract_use_from_prop($pname; name))
     )
    )
;

def extract_use_from_type_post(tpname):
    [((select(.inheritsFrom) | .inheritsFrom as $type |
       {}| .[$type] |= 
         { template: "as the basis for extension type, {type}",
           data: { "type": name }, id: "base-type" } ),
      (select(.properties) |
       .properties | to_entries | .[] | .key as $pname | .value |
       extract_use_from_prop($pname; tpname)))] |
    reduce .[] as $item ({}; .|merge_in_index($item))
;

def extract_use_from_type(tpname):
    [(
      (extract_use_in_allOf(tpname)),   # select types with allOf
      (select(.properties) |            # select object types
       .properties | to_entries | .[] | .key as $pname | .value |
       extract_use_from_prop($pname; tpname))
      )] |
    reduce .[] as $item ({}; .|merge_in_index($item))
;

# Input:  viewhelp types element node
def find_properties_of_type(tname):
    select(.properties) | .properties |
    [ .[] | (select(.type.of == tname), select(.type.each == tname)) | .name ]
;
# Input:  viewhelp types node
def find_typeproperties_of_type(tname):
    [ .[] | 
      select( (find_properties_of_type(tname) | length) > 0 ) |
      .name as $name | find_properties_of_type(tname) |
      .[] | { "type": $name, "prop": . }
    ]
;

def property2valuedoc:
    if .valueDocumentation then
      ((if .enum then "allowed" else "recognized" end) as $tag |
       [{ key: $tag, value: (.valueDocumentation | map_values(.description)) }] |
       from_entries)
    else
      {}
    end
;

def property2view:
    {
      type: typeinfo,
      description: [ .description ],
      brief: .description,
      label: .title,
      schema_notes: .notes,
      notes: [],
      examples: []
    } +
    property2valuedoc 
;
def property2view(name; parenttype):
    { name: name, parent: parenttype } +
    property2view 
;

def ensure_title(deftitle):
    if .value.title then . else (.value.title = deftitle) end
;

def ensure_titles:
    to_entries | map( ensure_title(.key) ) | from_entries
;

def type2view(name):
    { name: name, description: [.description], brief: .description } +
    (if .allOf then
       (
         .allOf |
         {
           jtype: "object", show: "object",
           inheritsFrom: map(select(.["$ref"]) | .["$ref"] | stripref),
           properties: (map(select(.properties) | .properties) |
                        reduce .[] as $itm ({}; . + $itm) ) 
         } |
         if (.properties|length) > 0 then . else
           del(.properties)
         end
       )
     else
       if .items then
         { jtype: "array", each: .items.type, show: show_type }
       else
         (if .type then
            { jtype: .type, show: show_type }
          else
            { jtype: "object", show: "object" }
          end +
          if .properties then {properties} else {} end)
       end
     end) |
    if .properties then
      .properties |= (ensure_titles | to_entries |
                      map( .key as $key | .value | property2view($key; name) ))
    else . end
;

def extract_polymorph_use_for_type(parent):
   (find_typeproperties_of_type(parent) | .[] |
    {
      template: "as an allowed value type in the {prop} property in the {type} type",
      data: .,
      id: "polymorph-type"
    }),
    (. as $tps |
     map(select(.name==parent) | select(.inheritsFrom) | .inheritsFrom |.[]) |
     (.[] | . as $gp | ($tps | extract_polymorph_use_for_type($gp)))
    )
;

# In: .definitions
def extract_polymorph_use:
    to_entries | map(.key as $tn | .value | type2view($tn)) | . as $tps |
    map(select(.inheritsFrom) | .name as $tn | .inheritsFrom as $parents | {} |
        .[$tn] = [$parents | .[] | . as $parent |
                  ($tps | extract_polymorph_use_for_type($parent))
                 ] |
        if (.[$tn]|length) < 1 then del(.[$tn]) else . end 
       ) |
    reduce .[] as $item ({}; .|merge_in_index($item))
;

def build_use_index:
    extract_polymorph_use as $initidx |
    to_entries |
    reduce .[] as $type ($initidx;
       .|merge_in_index($type| .value | extract_use_from_type($type["key"])))
;

def build_prop_index:
    to_entries | map(.key as $nm|.value|type2view($nm)) |
    reduce .[] as $type ({}; .[($type|.name)] |= $type)
;

def inherited_from(parent; propidx):
    if (propidx[parent]) then
       parent as $prnt |
       propidx[parent] | [
         (select(.inheritsFrom) | .inheritsFrom |
          map(inherited_from(.; propidx) |.[]) | .[]),
         {
           from: $prnt,
           brief: .brief,
         } +
         if .properties then
            { properties: .properties }
         else {} end
       ]
    else [] end
;

def type2view(name; useidx; propidx):
    type2view(name) |
    if (useidx[name]) then
       (.use |= useidx[name])
    else
       .
    end |
    if .inheritsFrom then
       .inheritedProperties |= [] |
       reduce (.inheritsFrom|.[]) as $p
              (.; .inheritedProperties += inherited_from($p; propidx))
    else . end
;
   
def schema2view: 
    (.definitions | build_use_index) as $useidx |
    (.definitions | build_prop_index) as $propidx |
    {
      title,
      description: (.description | [
         (strings),
         (arrays | .[])
      ]),
      types: (.definitions | to_entries |
              map( .key as $key | .value | type2view($key; $useidx; $propidx) ))
    }
;

# this function was intended to join the outputs of multiple files.
# It doesn't work. 
def all_schema2view:
    [schema2view] |
    if (length > 1) then
        reduce .[1:length] as $s (.[0]; .types += $s.types)
    else .[0] end
;

def combine_schemas:
    [.,inputs] | (.[0] | .definitions = {} | .description = []) as $head | 
    reduce .[] as $schema ($head; .["definitions"] += ($schema|.definitions) |
                                  .["description"] += ($schema|[.description]))
;

def schemasuite2view:
    combine_schemas | schema2view
;

      
