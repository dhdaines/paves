# PAVÉS: Bajo los adoquines, la PLAYA 🏖️

[**PLAYA**](https://github.com/dhdaines/playa) is intended
to get objects out of PDF, with no
dependencies or further analysis.  So, over top of **PLAYA** there is
**PAVÉS**: "**P**DF, **A**nalyse et **V**isualisation ... plus
avancé**ES**", I guess?

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

## Looking at Stuff in a PDF

When poking around in a PDF, it is useful not simply to read
descriptions of objects (text, images, etc) but also to visualise them
in the rendered document.  `pdfplumber` is quite nice for this, though
it is oriented towards the particular set of objects that it can
extract from the PDF.

The primary goal of [PLAYA-PDF](https://dhdaines.github.io/playa)
is to give access to all the objects and
particularly the metadata in a PDF.  One goal of PAVÉS (because there
are a few) is to give an easy way to visualise these objects and
metadata.

First, maybe you want to just look at a page in your Jupyter notebook.
Okay!

```python
import playa, paves.image as pi
pdf = playa.open("my_awesome.pdf")
page = pdf.pages[3]
pi.show(page)
```

Something quite interesting to do is, if your PDF contains a logical
structure tree, to look at the bounding boxes of the contents of those
structure elements for a given page:

```python
pi.box(pdf.structure.find_all(lambda el: el.page is page))
```

![Structure Elements](./docs/page3-elements.png)

You can also look at the marked content sections, which are the
leaf-nodes of the structure tree:

```python
pi.box(page.structure)
```

Alternately, if you have annotations (such as links), you can look at
those too:

```python
pi.box(page.annotations)
```

![Annotations](./docs/page2-annotations.png)

You can of course draw boxes around individual PDF objects, or
one particular sort of object, or filter them with a generator
expression:

```python
pi.box(page)  # outlines everything
pi.box(page.texts)
pi.box(page.images)
pi.box(t for t in page.texts if "spam" in t.chars)
```

Alternately you can "highlight" objects by overlaying them with a
semi-transparent colour, which otherwise works the same way:

```python
pi.mark(page.images)
```

![Annotations](./docs/page298-images.png)

If you wish you can give each type of object a different colour:

```python
pi.mark(page, color={"text": "red", "image": "blue", "path": "green"})
```

![Annotations](./docs/page298-colors.png)

You can also add outlines and labels around the highlighting:

```python
pi.mark(page, outline=True, label=True,
        color={"text": "red", "image": "blue", "path": "green"})
```

![Annotations](./docs/page298-outlines.png)

By default, PAVÉS will assign a new colour to each distinct label based
on a colour cycle [borrowed from
Matplotlib](https://matplotlib.org/stable/gallery/color/color_cycle_default.html)
(no actual Matplotlib was harmed in the making of this library).  You
can use Matplotlib's colour cycles if you like:

```
import matplotlib
pi.box(page, color=matplotlib.color_sequences["Dark2"])
```

![Color Cycles](./docs/page2-color-cycles.png)

Or just any list (it must be a `list`) of color specifications (which
are either strings, 3-tuples of integers in the range `[0, 255]`, or
3-tuples of floats in the range `[0.0, 1.0]`):

```
pi.mark(page, color=["blue", "magenta", (0.0, 0.5, 0.32), (233, 222, 111)], labelfunc=repr)
```

![Cycle Harder](./docs/page298-color-cycles.png)

(yes, that just cycles through the colors for each new object)

## Working in the PDF mine

`pdfminer.six` is widely used for text extraction and layout analysis
due to its liberal licensing terms.  Unfortunately it is quite slow
and contains many bugs.  Now you can use PAVÉS instead:

```python
from paves.miner import extract, LAParams

laparams = LAParams()
for page in extract(path, laparams):
    # do something
```

This is generally faster than `pdfminer.six`.  You can often make it
even faster on large documents by running in parallel with the
`max_workers` argument, which is the same as the one you will find in
`concurrent.futures.ProcessPoolExecutor`.  If you pass `None` it will
use all your CPUs, but due to some unavoidable overhead, it usually
doesn't help to use more than 2-4:

```
for page in extract(path, laparams, max_workers=2):
    # do something
```

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
- You have access to the list of enclosing marked content sections in
  every `LTComponent`, as the `mcstack` attribute.
- Bounding boxes of rotated glyphs are the actual bounding box.

Probably more... but you didn't use any of that stuff anyway, you just
wanted to get `LTTextBoxes` to feed to your hallucination factories.

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

As above, you can use multiple CPUs with `max_workers`, and this will
scale considerably better than `paves.miner`.

## License

`PAVÉS` is distributed under the terms of the
[MIT](https://spdx.org/licenses/MIT.html) license.
