# CC Legal Tools Technical Spec

June 17, 2020 - Preliminary - Dan Poirier, Caktus Group

## Formatting licenses

If we continue with our current plan to store the licenses as
plain text files and convert them automatically to HTML
for the web site, then we can use
[Pandoc markdown](https://pandoc.org/MANUAL.html#pandocs-markdown)
with some custom extensions to process the licenses.

Pandoc markdown supports many features needed to format licenses
already:

* Bold and italic text
* Section heads
* Intra-document links
* Deeply nested enumerated lists with different numbering formats
* [Storing metadata](https://pandoc.org/MANUAL.html#metadata-blocks)
  inside a document using a YAML section
  (extension is called "yaml_metadata_block")

We'll add a few more features by customization.
Pandoc supports running filters to modify the
internal abstract syntax tree of a document between
parsing the input format and generating the output format.

We'll use this to add:

* Underline (using the strikeout syntax, `~~text~~`)
* Putting link targets anywhere in the document
  (using the syntax `{#targetname}` anywhere we need a target)

## Translating licenses

### As whole documents

In the simple case we could just have a separate plain
text file for each license translation, and format them separately
into web pages.

### Piece-wise

Given the existence of the
[Creative Commons 4.0 Translation Worksheet](https://docs.google.com/document/d/1Vq6b89z6HWP1KZ66FNvx9E1GTeyAguPKk_zb4jXg4u8/edit#heading=h.sjnug5hrqruo),
it appears to be valid to translate licenses in smaller chunks of text rather
than all at once, which opens up some other possibilities.

#### Piece-wise by way of Django template translation tools

The Django template system works with any text files (not just HTML)
and has a translation system that allows marking chunks of text for
translation, optionally including notes for translators, extracting
all that text in a batch to a .po file for translation, and later
using the translated .po file to replace the original text with
the translated text during rendering.  (.po files are a standard way
of storing messages for translation that can easily be integrated
with Transifex.)

So we could just markup our input text files with the Django translation
tags and run them through Django for translation first, giving us translated
markdown files that we can then format with pandoc to any other format we
want.

As we'll be manually specifying each chunk of text to be translated,
we should be able to mark common chunks across the different licenses,
enabling those chunks to be translated only once and re-used in all
the licenses where that text shows up.

#### Piece-wise by automated extraction of text

Another possibility might be to use
the intermediate AST from Pandoc to extract each header, paragraph,
and list item from the input license, then submit each chunk of text
to Transifex for translation. Then we could translate by substituting
each chunk with its translation.

That might also help with re-using translations across licenses.
