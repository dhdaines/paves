from typing import Callable, Iterator, Tuple, Union

from PIL import Image


class PdfBitmap:
    def to_pil(self) -> Image.Image: ...


class PdfColorScheme:
    pass


class PdfPage:
    def get_width(self) -> int: ...
    def get_height(self) -> int: ...

    def render(
        self,
        scale: float = ...,
        rotation: int = ...,
        crop: Tuple[float, float, float, float] = ...,
        may_draw_forms: bool = ...,
        bitmap_maker: Callable = ...,
        color_scheme: Union[PdfColorScheme, None] = ...,
        fill_to_stroke: bool = ...,
        **kwargs
    ) -> PdfBitmap: ...

    def close(self) -> None: ...


class PdfDocument:
    def __init__(self, input, password=None, autoclose=False) -> None: ...
    def __iter__(self) -> Iterator[PdfPage]: ...
    def __getitem__(self, idx: int) -> PdfPage: ...
    def close(self) -> None: ...
