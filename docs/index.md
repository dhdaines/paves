# PAVÉS: Bajo los adoquines, la PLAYA 🏖️

[**PLAYA**](https://github.com/dhdaines/playa) is intended to get
objects out of PDF, with no dependencies or further analysis.  So,
over top of **PLAYA**, this package provides **P**DF, **A**nalyse et
**V**isualisation simplifi**É**e**S**.

Or, if you prefer, **P**DF **A**nalysis and **V**isualization for
dummi**ES**.

The goal here is not to provide elaborate, enterprise-grade,
battle-tested, cloud and AI-native, completely configurable and
confoundingly complex classes for ETL.  It's to give you some helpful
functions that you can use to poke around in PDFs and get useful
things out of them, often but not exclusively in the context of a
Jupyter notebook.

## Installation

Install it from PyPI (as `paves`) with `pip` or `uv`, preferably in a
environment.  That's all.  If you want to play around in the source
code you can use `hatch` or `uv` (your choice).

## Quick start

To use it, I recommend importing `playa` and then abbreviating the
PAVÉS modules like this:

```python
import python
import paves.image as pi
import paves.tables as pt
import paves.text as px
```

The major use case (well, **my** major use case) for PAVÉS is [looking
at stuff in PDFs](./looking-at-stuff.md), generally in a
[Jupyter](https://jupyter.org) notebook.  Basically `pi.show` renders
pages to images, `pi.box` draws boxes around objects, and `pi.mark`
highlights objects with semi-transparent colour.  Images are
`PIL.Image.Image` objects everywhere so you can, for example, crop
them, save them, etc.

```python
pdf = playa.open("awesome-document.pdf")
page = pdf.pages[0]
image = pi.show(page)
image_with_text_objects = pi.box(page.texts)
image_with_marked_content = pi.box(page.structure)
image_with_highlighted_images = pi.mark(page.images)
```

Another use case is to extract words and lines of text, with
associated styling and graphics state.  So for instance you could look
at text with associated fonts:

```python
pi.show(px.words(page), label=px.textfont)
```

It can also detect tables.  Contrary to the current zeitgeist, PAVÉS
always tries to do everything the simplest and most efficient way,
taking advantage of explicit structure when possible (yes, PDFs can
have explicit structure).  This will fall back to *Deep Learning* if
there isn't any such structure, and if you have the necessary PyTorch
and HuggingFace junk installed.

Once you've found these tables you can... do stuff with them.  More on
this soon.

## License

`PAVÉS` is distributed under the terms of the
[MIT](https://spdx.org/licenses/MIT.html) license.
