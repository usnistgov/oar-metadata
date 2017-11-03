# jq conversion library:  doc JSON to HTML
#
# This formats the documentation into a particular HTML layout
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

def layout_property:
  . as $prop |
  reduce  
  (("<a name=\"{parent}.{name}\"></a>\n" +
    "<div class=\"md_entry md_prop\">\n<h5>\n" +
    "<span class=\"preheading\"><a href=\"#def_property\">Property</a> of the\n"+
    "<a href=\"#{parent}\">{parent}</a> type</span> <br />\n" +
    "<span class=\"Property heading\">{name}</span>\n</h5>\n<hr />\n\n" +
    "<dl>\n" + 
    "  <dt> <strong>What it represents:</strong> </dt>\n"
    | template($prop)),

   (.description | map( wrap_template("  <dd> {0} </dd>") )
                 | join(" <p>\n")+"\n"),
    
   ("  <dt> <strong>Value type:</strong> </dt>\n" +
    "  <dd> {show} </dd>\n" 
    | template($prop|.type)),

   (if .examples then
      "  <dt> <strong>Example Values:</strong>\n  <dd> " +
      (.examples | map( wrap_template("<code>{0}</code>") ) |
       join(", <br />\n       ") + "\n")
    else "" end),
    
   (if .allowed then
      (.allowed | allowed_values ) 
    else "" end),
    
   ("</dl>\n</div> <!-- end property description -->\n\n"))
   as $p (""; . + $p)
;

def layout_type:
  . as $type |
  reduce  
    (("<a name=\"{name}\"></a>\n" + 
      "<div class=\"md_entry md_type\">\n" +
      "<div class=\"type_body\">\n<h3>\n" +
      "<span class=\"preheading\"><a href=\"#def_type\">Named Type</a></span>" +
      "<br />\n<span class=\"Type heading\">{name}</span>\n"+
      "</h3>\n<hr />\n\n<dl>\n" +
      "  <dt> <strong>What it represents:</strong> </dt>\n" 
      | template($type)),

     (.description | map( wrap_template("  <dd> {0} </dd>") )
                   | join(" <p>\n")+"\n"),

     ("  <dt> <strong>How it is used:</strong> </dt>\n" + 
      "  <dd> <span class=\"Type reference\">\n"),

     (.use | map( wrap_template(" {0} \n") )
           | join("</dd> <p>\n  <dd> ")),

     ("       </dd>\n" +
      "</dl> <p>\n\n<h4>Properties:</h4>\n</div>\n\n" +
      "<div class=\"md_props\">\n\n"),

     (.properties | map( layout_property ) | .[]),

     ("</div> <!-- end properties section -->\n" +
      "</div> <!-- end type description -->\n\n"))

   as $p (""; . + $p)
;
