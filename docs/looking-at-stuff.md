# Looking at Stuff in a PDF

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
pi.box(page.structure)
```

![Structure Elements](./page3-elements.png)

Note however that this only gives you the elements associated with
*marked content sections*, which are the leaf nodes of the structure
tree.  So, you can also search up the structure tree to find things
like tables, figures, or list items:

```python
pi.box(page.structure.find_all("Table"))
pi.box(page.structure.find_all("Figure"))
pi.box(page.structure.find_all("LI"))
```

You can even search with regular expressions, to find headers for
instance:

```python
pi.box(page.structure.find_all(re.compile(r"H\d+")))
```

Alternately, if you have annotations (such as links), you can look at
those too:

```python
pi.box(page.annotations)
```

![Annotations](./page2-annotations.png)

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

![Annotations](./page298-images.png)

If you wish you can give each type of object a different colour:

```python
pi.mark(page, color={"text": "red", "image": "blue", "path": "green"})
```

![Annotations](./page298-colors.png)

You can also add outlines and labels around the highlighting:

```python
pi.mark(page, outline=True, label=True,
        color={"text": "red", "image": "blue", "path": "green"})
```

![Annotations](./page298-outlines.png)

By default, PAVÉS will assign a new colour to each distinct label based
on a colour cycle [borrowed from
Matplotlib](https://matplotlib.org/stable/gallery/color/color_cycle_default.html)
(no actual Matplotlib was harmed in the making of this library).  You
can use Matplotlib's colour cycles if you like:

```
import matplotlib
pi.box(page, color=matplotlib.color_sequences["Dark2"])
```

![Color Cycles](./page2-color-cycles.png)

Or just any list (it must be a `list`) of color specifications (which
are either strings, 3-tuples of integers in the range `[0, 255]`, or
3-tuples of floats in the range `[0.0, 1.0]`):

```
pi.mark(page, color=["blue", "magenta", (0.0, 0.5, 0.32), (233, 222, 111)], labelfunc=repr)
```

![Cycle Harder](./page298-color-cycles.png)

(yes, that just cycles through the colors for each new object)

