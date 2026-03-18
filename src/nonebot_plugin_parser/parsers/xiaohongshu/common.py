from msgspec import Struct


class StreamItem(Struct):
    masterUrl: str
    duration: int  # milliseconds
    backupUrl: list[str] | None = None


class Stream(Struct):
    h264: list[StreamItem] | None = None
    h265: list[StreamItem] | None = None
    av1: list[StreamItem] | None = None
    h266: list[StreamItem] | None = None


class Media(Struct):
    stream: Stream


class Video(Struct):
    media: Media

    @property
    def url_and_duration(self) -> tuple[str | None, float]:
        stream = self.media.stream

        # h264 有水印，h265 无水印
        if stream.h265:
            return stream.h265[0].masterUrl, stream.h265[0].duration / 1000
        elif stream.h264:
            return stream.h264[0].masterUrl, stream.h264[0].duration / 1000
        elif stream.av1:
            return stream.av1[0].masterUrl, stream.av1[0].duration / 1000
        elif stream.h266:
            return stream.h266[0].masterUrl, stream.h266[0].duration / 1000

        return None, 0.0
