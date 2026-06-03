from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass

from PIL import ImageFont
from apilmoji.core import get_font_height

Color = tuple[int, int, int]


@dataclass(eq=False, frozen=True, slots=True)
class FontMetrics:
    """字体度量（换行、估高）"""

    font: ImageFont.FreeTypeFont
    line_height: int
    cjk_width: int

    def __hash__(self) -> int:
        return hash((id(self.font), self.line_height, self.cjk_width))

    @lru_cache(maxsize=500)
    def get_char_width(self, char: str) -> int:
        bbox = self.font.getbbox(char)
        return int(bbox[2] - bbox[0])

    def get_char_width_fast(self, char: str) -> int:
        if "\u4e00" <= char <= "\u9fff":
            return self.cjk_width
        return self.get_char_width(char)

    def get_text_width(self, text: str) -> int:
        if not text:
            return 0
        return sum(self.get_char_width_fast(char) for char in text)


@dataclass(frozen=True, slots=True)
class CardTheme:
    """卡片颜色"""

    name: Color
    title: Color
    body: Color
    muted: Color


@dataclass(frozen=True, slots=True)
class StyledFont:
    """度量 + 颜色"""

    metrics: FontMetrics
    fill: Color


def _load_styled(font_path: Path, size: int, fill: Color) -> StyledFont:
    font = ImageFont.truetype(font_path, size)
    return StyledFont(
        metrics=FontMetrics(
            font=font,
            line_height=get_font_height(font),
            cjk_width=size,
        ),
        fill=fill,
    )


@dataclass(frozen=True, slots=True)
class CardFonts:
    """卡片各区块字体（加载时组合 theme)"""

    name: StyledFont
    title: StyledFont
    body: StyledFont
    muted: StyledFont

    @classmethod
    def load(cls, font_path: Path, theme: CardTheme) -> CardFonts:
        return cls(
            name=_load_styled(font_path, 28, theme.name),
            title=_load_styled(font_path, 30, theme.title),
            body=_load_styled(font_path, 24, theme.body),
            muted=_load_styled(font_path, 24, theme.muted),
        )
