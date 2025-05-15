"""
Compatibility functions.
"""

from typing import Iterator, List

from playa.content import PathObject, PathSegment


def subpaths(path: PathObject) -> Iterator[PathObject]:
    """Iterate over "subpaths".

    Note: subpaths inherit the values of `fill` and `evenodd` from
    the parent path, but these values are no longer meaningful
    since the winding rules must be applied to the composite path
    as a whole (this is not a bug, just don't rely on them to know
    which regions are filled or not).

    """
    # FIXME: Is there an itertool or a more_itertool for this?
    segs: List[PathSegment] = []
    for seg in path.raw_segments:
        if seg.operator == "m" and segs:
            yield PathObject(
                _pageref=path._pageref,
                gstate=path.gstate,
                ctm=path.ctm,
                mcstack=path.mcstack,
                raw_segments=segs,
                stroke=path.stroke,
                fill=path.fill,
                evenodd=path.evenodd,
            )
            segs = []
        segs.append(seg)
    if segs:
        yield PathObject(
            _pageref=path._pageref,
            gstate=path.gstate,
            ctm=path.ctm,
            mcstack=path.mcstack,
            raw_segments=segs,
            stroke=path.stroke,
            fill=path.fill,
            evenodd=path.evenodd,
        )
