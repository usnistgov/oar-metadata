# jq conversion library:  doc JSON to HTML
#
# This formats the documentation into a particular HTML layout
#

# insert data into an (HTML) template.  The template, read as the input
# stream, should contain insert points of the form {name} where name
# corresponds to a property name from the data, provided as an argument
#
# Input: string, the HTML template containing {} insert points
# Output:  the realized HTML
# data:  object, the data to insert into
# 
def template(data): 
    . as $tmpl |
    reduce (capture("{(?<a>[^}]+)}"; "g") | .a) as $lab
           ($tmpl; gsub("\\{"+$lab+"}"; data[$lab]))
;
def wrap_template(tmpl; tag):
    . as $val | tmpl | sub("\\{"+tag+"}"; $val)
;
def wrap_template(tmpl):
    wrap_template(tmpl; "0")
;
def make_type_link(tname; title):
    (title | gsub("\""; "\\\"")) as $title | 
    { tn: tname, ti: $title } as $data |
    "<span class=\"Type reference\"><a href=\"#{tn}\"" | template($data) +
    (if ($title|length) > 0 then
       (" title=\"{ti}\"" | template($data))
     else "" end) +
    ">{tn}</a></span>" | template($data)
;
def make_prop_link(pname; tname; title):
    (title | gsub("\""; "\\\"")) as $title | 
    { pn: pname, tn: tname, ti: $title } as $data |
    "<span class=\"Property reference\"><a href=\"#{tn}.{pn}\""|template($data)+
    (if ($title|length) > 0 then
       (" title=\"{ti}\"" | template($data))
     else "" end) +
    ">{pn}</a></span>" | template($data)
;
def _make_links:
    if .type then
      .type as $type |
      (if .title then .title else "" end) as $title |
      (if .prop then
         (.prop as $prop | 
          .prop |= make_prop_link($prop; $type; $title))
       else . end |
       .type |= make_type_link($type; $title))
    else
      .
    end
;

def show_message:
    [((objects |
       if .template then
         if .data then
           ((.data|_make_links) as $data | .template | template($data))
         else
           .template
         end
       else
         empty
       end),
      strings, "")] | .[0]
;

def allowed_values:
    reduce
      (("  <dt> <strong>Allowed Values:</strong>\n  <dd>\n       <dl>\n"),

       (to_entries |
        map( . as $d |
            "         <dt> <code>{key}</code> </dt>\n"+
            "         <dd> {value} </dd>\n" |
            template($d) ) | .[]),

       ("       </dl></dd>\n"))
    as $ln (""; . + $ln)
;

def layout_prop_type:
  (if .type == "object" then .of
   else
     if .type == "array" then .each
     else null
     end
   end) as $type | .show |
  ((strings |
    if $type
    then
      sub($type; "<span class=\"Type reference\"><a href=\"#"+$type+"\">"+$type+"</a></span>")
    else
      .
    end),
   (objects | show_message)) 
;

def layout_property:
  . as $prop |
  reduce  
  (("<a name=\"{parent}.{name}\"></a>\n" +
    "<div class=\"md_entry md_prop\">\n<h5>\n" +
    "<span class=\"preheading\"><a href=\"#def:property\" title=\"definition: property\">Property</a> of the\n"+
    "<a href=\"#{parent}\">{parent}</a> type</span> <br />\n" +
    "<span class=\"Property heading\">{name}</span>\n</h5>\n<hr />\n\n" +
    "<dl>\n" + 
    "  <dt> <strong>What it represents:</strong> </dt>\n"
    | template($prop)),

   (.description | map( wrap_template("  <dd> {0} </dd>") )
                 | join(" <p>\n")+"\n"),
    
   ("  <dt> <strong>Value type:</strong> </dt>\n" +
    "  <dd> " + (.type|layout_prop_type) + " </dd>\n"),

   (if .allowed then
      (.allowed | allowed_values ) 
    else "" end),

   "</dl>\n\n",

   (if (.notes|length) > 0 then
      ("<div class=\"notes\">",
       "<strong>Notes:</strong>\n<ul>\n",
       (.notes[]|("  <li> "+.+" </li>\n")),
       "</ul>\n</div>\n")
    else "" end),
    
   (if (.examples|length) > 0 then
      "<dl>  <dt> <strong>Example Values:</strong>\n  <dd> " +
      (.examples | map( wrap_template("<code>{0}</code>") ) |
       join(", <br />\n       ") + "\n</dl>")
    else "" end),
    
   ("\n</div> <!-- end property description -->\n\n"))
   as $p (""; . + $p)
;

def layout_inherited_properties:
   if (.properties|length) > 0 then
     ({ type: .from, title: .brief } | _make_links) as $type |
     .properties as $props |
     reduce
       (("<div class=\"md_entry md_iprop\">\n" +
         "<dl>\n  <dt> Inherited from {type}: </dt>\n" +
         "  <dd> "
         | template($type)),

        (.properties |
         map({ type: .parent, prop: .name, title: .brief }| _make_links| .prop)|
         join(",\n       ")),

        "\n  </dd>\n</dl>\n</div>\n\n"
       )
     as $item (""; . + $item)
   else "" end
;

def layout_type:
  . as $type |
  (.show|show_message) as $show |
  reduce  
    (("<a name=\"{name}\"></a>\n" + 
      "<div class=\"md_entry md_type\">\n" +
      "<div class=\"type_body\">\n<h3>\n" +
      "<span class=\"preheading\"><a href=\"#def:named_type\" title=\"defintion: named type\">Named Type</a></span>" +
      "<br />\n<span class=\"Type heading\">{name}</span>\n"+
      "</h3>\n<hr />\n\n<dl>\n" +
      "  <dt> <strong>JSON type:</strong> </dt>\n" +
      "  <dd> "+$show+" </span>\n" +
      "  <dt> <strong>What it represents:</strong> </dt>\n" 
      | template($type)),

     (.description | map( wrap_template("  <dd> {0} </dd>") )
                   | join(" <p>\n")+"\n"),

     ("  <dt> <strong>Where it is used:</strong> </dt>\n" + 
      "  <dd> "),

     (select(.use) | .use | map( show_message )
           | join(" </dd>\n  <dd> ")),
         
     " </dd>\n</dl>",

     (if .properties or .inheritedProperties then
       (("<p>\n\n<h4>Properties:</h4>\n</div>\n\n" +
         "<div class=\"md_props\">\n\n"),

        (if .inheritedProperties then
          (.inheritedProperties | map( layout_inherited_properties ) | .[])
         else empty end),

        (if .properties then
          (.properties | map( layout_property ) | .[])
         else empty end))
      else empty end),

     ("</div> <!-- end properties section -->\n" +
      "</div> <!-- end type description -->\n\n<p>\n\n"))

   as $p (""; . + $p)
;

def layout_schema(title):
    "<a name=\"sec:namedtypes\"></a>\n<h2> "+title+" </h2>\n\n" +

    "<h3> Index </h3>\n<ul>\n"+
    "  <li> <a href=\"#sec:Resource\">Resource Types</a> </li>\n  <ul>\n"+
    (.types | map(select(.cat == "Resource") |
                  "    <li> " + make_type_link(.name; .brief) + " </li> ") |
     join("\n")) +

    "  </ul>  <li> <a href=\"#sec:Component\">Component Types</a> </li>\n  <ul>\n"+
    (.types | map(select(.cat == "Component") |
                  "    <li> " + make_type_link(.name; .brief) + " </li> ") |
     join("\n")) +

    "  </ul>  <li> <a href=\"#sec:Other\">Other Types</a> </li>\n  <ul>\n"+
    (.types | map(select(.cat != "Component" and .cat != "Resource") |
                  "    <li> " + make_type_link(.name; .brief) + " </li> ") |
     join("\n")) +

    "  </ul>\n</ul>\n\n" +

    reduce
       (.types[] | select(.cat == "Resource") | layout_type) as $t
       ("<a name=\"sec:Resource\"></a>\n<h3>Resource Types</h3>\n\n"; . + $t) +
    reduce
       (.types[] | select(.cat == "Component") | layout_type) as $t
       ("<a name=\"sec:Component\"></a>\n<h3>Component Types</h3>\n\n"; . +$t) +
    reduce
       (.types[] | select(.cat != "Component" and .cat != "Resource")
                 | layout_type) as $t
       ("<a name=\"sec:Other\"></a>\n<h3>Other Types</h3>\n\n"; . + $t)
;

def layout_schema:
    layout_schema("NERDm Reference: Named Types")
;

def view2html:
   { title: .title} as $title |
   
   ("<html> <head>\n" +
    (.title | wrap_template("<title>{0}</title>\n")) + 
    "<style>\nbody {\n   font-family: Helvetica Neue, Arial, sans-serif;\n}\n"+
    "</style>\n<link rel=\"stylesheet\" type=\"text/css\" " +
    "href=\"helpview.css\" />\n"+
    "</head>\n\n<body>\n" +
    (.title | wrap_template("<h1>{0}</h1>\n\n"))),

   (layout_schema),

   ("</body>\n</html>\n")
;




