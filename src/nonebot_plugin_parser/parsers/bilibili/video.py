from msgspec import Struct


class Owner(Struct):
    name: str
    face: str


class Stat(Struct):
    view: int
    danmaku: int
    reply: int
    favorite: int
    coin: int
    share: int
    like: int


class Page(Struct):
    part: str
    duration: int
    first_frame: str | None = None


class VideoInfo(Struct):
    title: str
    desc: str
    duration: int
    owner: Owner
    stat: Stat
    pic: str | None = None
    pages: list[Page] | None = None

    @property
    def title_with_part(self) -> str:
        if self.pages and len(self.pages) > 1:
            return f"{self.title} - {self.pages[0].part}"
        return self.title

    @property
    def formatted_stats_info(self) -> str:
        """
        格式化视频信息
        """
        # 定义需要展示的数据及其显示名称
        stats_mapping = [
            ("👍", self.stat.like),
            ("🪙", self.stat.coin),
            ("⭐", self.stat.favorite),
            ("↩️", self.stat.share),
            ("💬", self.stat.reply),
            ("👀", self.stat.view),
            ("💭", self.stat.danmaku),
        ]

        # 构建结果字符串
        result_parts = []
        for display_name, value in stats_mapping:
            # 数值超过10000时转换为万为单位
            formatted_value = f"{value / 10000:.1f}万" if value > 10000 else str(value)
            result_parts.append(f"{display_name} {formatted_value}")

        return " ".join(result_parts)

    def extract_info_with_page(self, page_num: int = 1) -> tuple[int, str, int, str | None]:
        """获取视频信息，包含页索引、标题、时长、封面
        Args:
            page_num (int, optional): 页索引. Defaults to 1.

        Returns:
            tuple[int, str, int, str | None]: 页索引、标题、时长、封面
        """
        page_idx = page_num - 1
        title = self.title
        duration = self.duration
        cover = self.pic

        if self.pages and len(self.pages) > 1:
            page_idx = page_idx % len(self.pages)
            page = self.pages[page_idx]
            title += f" | 分集 - {page.part}"
            duration = page.duration
            cover = page.first_frame
        return page_idx, title, duration, cover


class ModelResult(Struct):
    summary: str


class AIConclusion(Struct):
    model_result: ModelResult | None = None

    @property
    def summary(self) -> str:
        if self.model_result and self.model_result.summary:
            return f"AI总结: {self.model_result.summary}"
        return "该视频暂不支持AI总结"
