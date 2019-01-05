# Metadata Documentation

This folder contains files supporting on-line documentation of OAR-PDR
metadata.  In particular, it includes files that go into HTML
documentation of the NERDm schema.

Note that much of the content going into the NERDm docuementation is
extracted automatically from the JSON Schema definition documents (in
the ../../model directory).  See
["Building the NERDm Documentation"](#Building_the_NERDm_Documentation)
for details extracting documentation.

## Contents

```
README.md                 --> this file
helpview.css              --> default stylesheet for rendering the HTML 
                              version of the NERDm docuementation
nerdm-glossary-body.html  --> JSON-related glossary for the NERDm
                              reader's guide (manually composed)
nerdm-intro-body.html     --> Introduction to the NERDm reader's guide
                              (manually composed)
nerdm-reference-body.html --> the reference section of the NERDm
                              reader's guide.  This is initially
                              generated but may contain manual edits.
nerdm-view.json           --> A transformed version of NERDm schemas
                              optimized for documentation generation.
                              This is initially generated programatically 
                              (see nerdm-view-unedited.json); but contains
                              extensive manual edits.
nerdm-view.json           --> A transformed version of NERDm schemas
                              optimized for documentation generation.
                              This is the form originally generated from the
                              NERDM schemas; it contains no manual edits.
nerdm-readersguide.html   --> A default but complete HTML document
                              containing the NERDm Reader's Guide.  This
                              a concatonation of the nerdm-*-body.html files,
                              wrapped in a default HTML header and footer
                              for reviewing in a browser.
schema_viewhelp-proto.html--> A manually-created prototype of the Reader's 
                              Guide, used to guide development of the
                              extraction and conversion tools.  
```

