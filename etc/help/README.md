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

## Building the NERDm Documentation

The JSON Schema files that define the NERDm schema (found in
[../../model](../../model)) contain documentation that set the semantics for
the NERDm properties; however, the language of that documentation speaks
mainly to developers and metadata experts.  The audience of the Reader's
Guide--that is, non-experts--would benefit from a style that relies less on
jargon and formalism.  

We address this need with the following strategy for creating the Reader's
Guide from the documentation embedded in the schema files:

1. Transform the schema files to a JSON format optimized for creating
   documentation.  This is the _schema view_ format.

2. Manually edit and annotate the schema view file with documentation oriented
   to the intended audience.

3. Transform the schema view file to HTML to create reference documentation.

4. Combine the reference documentation with additional, manually-created
   material (in HTML) as well as desired header and footer material to
   create the complete HTML document.

We use the jq tool for transforming the schema and view files; its use is
explained in the next section.  This directory contains various files
resulting from the above steps, including: 
  * `nerdm-view-unedited.json` -- this is the result from step 1.
  * `nerdm-view.json` -- this is the result from step 2, edited for content.
  * `nerdm-reference-body.html` -- this is output of step 3.
  * `nerdm-intro-body.html` and `nerdm-glossary-body` -- these are manually
    created content intended to appear before and after the generated
    reference documentation and are input into step 4.
  * `nerdm-guide.html` -- this is a version of the completed documentation
    (with a simple header and footer, not included here).  
   
To view the `nerdm-guide.html`, be sure its stylesheet, `helpview.css` is in
the same directory when loading it the guide into a browser.  

### Using the jq tool

These instructions assume one has the jq tool installed and that the commands
below are executed from this repository's base directory.  In particular,
stylesheets from the `[jq](../../jq)` subdirectory are used to drive the
transformations.

To transform the schemas directly to HTML, execute the following:

```
jq -Ljq -r 'include "jq/schema2viewhelp"; include "jq/viewhelp2html"; schemasuite2view | view2html' \
   model/nerdm-schema.json model/nerdm-pub-schema.json > etc/help/ref.html
```

Note that we wrote the output, `ref.html`, to the `etc/help` directory so that
when we load the file into a web browser, the associated stylesheet
(`helpview.css`) will get loaded as well.

The above example combines the two transformation steps described in the
previous section into one step, but to apply the strategy described above, we
apply these steps separately.  To create the schema view document (to edit for
content), execute this instead:

```
jq -Ljq -r 'include "jq/schema2viewhelp"; schemasuite2view' \
   model/nerdm-schema.json model/nerdm-pub-schema.json > etc/help/view.json
```

After we have edited the output file, `view.json`, we can convert it to HTML:

```
jq -Ljq -r 'include "jq/viewhelp2html"; layout_schema' etc/help/view.json > etc/help/ref-body.html
```

The output from the above command will not include the HTML header and footer
markup; this allows it to be combined more easily with other content, as in:

```
cat myheader.html etc/help/nerdm-intro-body.html etc/help/ref-body.html \
    etc/help/nerdm-glossary-body.html myfooter.html > etc/help/ref.html
```

To create a complete HTML document containing just the reference material, one
can run the last jq example, substituting `view2html` for `layout_schema`:

```
jq -Ljq -r 'include "jq/viewhelp2html"; view2html' etc/help/view.json > etc/help/ref.html
```





