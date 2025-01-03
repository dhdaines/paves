# PAVÉS: Bajo los adoquines, la PLAYA 🏖️

The goal with **PLAYA** is just to get objects out of PDF, with no
dependencies or further analysis.  So, over top of **PLAYA** there is
**PAVÉS**: "**P**DF, **A**nalyse et **V**isualisation ... plus
**É**laborée**s**", I guess?

Anything that deviates from the core mission of "getting objects out
of PDF" goes here, so, hopefully, more interesting analysis and
extraction that may be useful for all of you AI Bros doing
"Partitioning" and "Retrieval-Assisted-Generation" and suchlike
things.  But specifically, visualization stuff inspired by the "visual
debugging" features of `pdfplumber` but not specifically tied to its
data structures and algorithms.

There will be dependencies.  Oh, there will be dependencies.

## Installation

```console
pip install paves
```

## Workin' in a PDF mine

`pdfminer.six` is widely used for text extraction and layout analysis
due to its liberal licensing terms.  Unfortunately it is quite slow
and contains many bugs.  Now you can use PAVÉS instead:

```python
from paves.miner import extract, LAParams

laparams = LAParams()
for page in extract(path, laparams):
    # do something
```

By default this will use all of your CPUs to go fast on large
documents and somewhat slower on small ones.  You can make it not do
that by passing `max_workers=1`, or you can only use some CPUs by
passing some other value.

Even with a single CPU, it is often faster than `pdfminer.six`.

There are a few differences with `pdfminer.six` (some might call them
bug fixes):

- By default, if you do not pass the `laparams` argument to `extract`,
  no layout analysis at all is done.  This is different from
  `extract_pages` in `pdfminer.six` which will set some default
  parameters for you.  If you don't see any `LTTextBox` items in your
  `LTPage` then this is why!
- Rectangles are recognized correctly in some cases where
  `pdfminer.six` thought they were "curves".
- Colours and colour spaces are the PLAYA versions, which do not
  correspond to what `pdfminer.six` gives you, because what
  `pdfminer.six` gives you is not useful and often wrong.
- You have access to the marked content section ID and tag in every
  `LTComponent`, as the `mcs` attribute (but this is often `None` in
  the case where there is no MCS, or there are multiple MCSes)
- Bounding boxes of rotated glyphs are the actual bounding box.

Probably more... but you didn't use any of that stuff anyway, you just
wanted to get `LTTextBoxes` to feed to your hallucination factories.

There is also a bug:

- The `size` of rotated glyphs is incorrect (this will get fixed in
  PLAYA soon hopefully).

## PLAYA Bears

[PLAYA](https://github.com/dhdaines/playa) has a nice "lazy" API which
is efficient but does take a bit of work to use.  If, on the other
hand, **you** are lazy, then you can use `paves.bears`, which will
flatten everything for you into a friendly dictionary representation
(but it is a
[`TypedDict`](https://typing.readthedocs.io/en/latest/spec/typeddict.html#typeddict))
which, um, looks a lot like what `pdfplumber` gives you, except
possibly in a different coordinate space, as defined [in the PLAYA
documentation](https://github.com/dhdaines/playa#an-important-note-about-coordinate-spaces).

```python
from paves.bears import extract

for dic in extract(path):
    print("it is a {dic['object_type']} at ({dic['x0']}", {dic['y0']}))
    print("    the color is {dic['stroking_color']}")
    print("    the text is {dic['text']}")
    print("    it is in MCS {dic['mcid']} which is a {dic['tag']}")
    print("    it is also in Form XObject {dic['xobjid']}")
```

This can be used to do machine learning of various sorts.  For
instance, you can write `page.layout` to a CSV file:

```python
from paves.bears import FIELDNAMES

writer = DictWriter(outfh, fieldnames=FIELDNAMES)
writer.writeheader()
for dic in extract(path):
    writer.writerow(dic)
```

you can also create a Pandas DataFrame:

```python
df = pandas.DataFrame.from_records(extract(path))
```

or a Polars DataFrame or LazyFrame:

```python
from paves.bears import SCHEMA

df = polars.DataFrame(extract(path), schema=SCHEMA)
```

As above, this will use all of your CPUs and return a possibly quite
large object.

## License

`PAVÉS` is distributed under the terms of the
[MIT](https://spdx.org/licenses/MIT.html) license.
