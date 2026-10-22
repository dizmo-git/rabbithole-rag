"""
YouTube video ingestor: the video's subtitles become the source text.

Only subtitles are read (what the CC button shows), no video or audio is downloaded, and
no API key is needed (youtube-transcript-api talks to the same endpoints the player
uses). A video without any subtitles can't be ingested; transcribing the audio locally
(Whisper) would be the fallback, not implemented.

Which subtitle track:
  1. uploaded by the creator, in the video's spoken language (clean, punctuated)
  2. YouTube's auto-generated one in the spoken language (no punctuation, some misheard
     words, but most videos have it)
  3. any uploaded track, then any auto-generated one
The spoken language matters because of auto-dubbing: a dubbed video (Karpathy's GPT
video has 12) lists one auto-generated track per audio language, alphabetically, so
"the first auto track" can be a machine-dubbed language. The watch page says which audio
track is the default one (= the original, id like "en-US.4"; dubs are "<lang>.10").
Undubbed videos have no track id there, but then they have exactly one auto track, and
that is the spoken language.

Chunking: subtitles arrive as a few words each with a start time. They are glued in
order into windows of about MAX_CHUNK_CHARS (same size and overlap as files), so every
chunk knows exactly which seconds it covers. Each chunk gets a
"[title · channel · 12:01–13:47]" header and links to watch?v=<id>&t=<start>s, so a
citation opens the video right where the passage is spoken.

The video title is also put on the Source (BaseIngestor.title), so the sidebar shows it
instead of the URL.
"""

import asyncio
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import requests
from youtube_transcript_api import (
    AgeRestricted,
    CouldNotRetrieveTranscript,
    InvalidVideoId,
    NoTranscriptFound,
    RequestBlocked,
    Transcript,
    TranscriptList,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
)

from backend.ingestors.base import BaseIngestor, IngestError
from backend.ingestors.generic_url import REQUEST_TIMEOUT, USER_AGENT, with_scheme
from backend.models import Chunk, Platform, PostOrigin, SourceType

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "youtu.be",
}
# /shorts/<id>, /live/<id>, /embed/<id>, /v/<id> carry the id in the path
PATH_ID_PREFIXES = ("shorts", "live", "embed", "v")
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

WATCH_URL = "https://www.youtube.com/watch?v={}"

MAX_CHUNK_CHARS = 1800  # same as the file splitter, header included
CHUNK_OVERLAP = 250  # roughly, the overlap is made of whole subtitle lines
# Sound cues like "[Music]", "[Applause]", "[laughs]" and lyric notes carry nothing to embed
CUE_RE = re.compile(r"\[[^\]]{1,40}\]|[♪♫]")


@dataclass
class VideoInfo:
    title: str
    channel: str | None = None
    published: datetime | None = None
    spoken_language: str | None = None  # from the default audio track, dubbed videos only


@dataclass
class Line:
    start: float
    end: float
    text: str


def is_youtube_url(url: str) -> bool:
    return (urlparse(with_scheme(url)).hostname or "").lower() in YOUTUBE_HOSTS


def parse_video_id(url: str) -> str:
    """The 11-char video id of a single-video link, else ValueError (shown to the user)."""
    parsed = urlparse(with_scheme(url))
    host = (parsed.hostname or "").lower()
    parts = [p for p in parsed.path.split("/") if p]
    query = parse_qs(parsed.query)

    candidate = None
    if host == "youtu.be":
        candidate = parts[0] if parts else None
    elif parts[:1] == ["watch"]:
        candidate = query.get("v", [None])[0]
    elif len(parts) >= 2 and parts[0] in PATH_ID_PREFIXES:
        candidate = parts[1]

    if candidate and VIDEO_ID_RE.match(candidate):
        return candidate
    if "list" in query or parts[:1] == ["playlist"]:
        raise ValueError("Only single YouTube videos are supported, not playlists")
    if parts and (parts[0].startswith("@") or parts[0] in ("channel", "c", "user")):
        raise ValueError("Only single YouTube videos are supported, not channels")
    raise ValueError(f"Not a YouTube video link: {url}")


def format_time(seconds: float) -> str:
    s = int(seconds)
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def base_language(code: str) -> str:
    return code.split("-")[0].lower()  # "en-US" -> "en"


class YouTubeIngestor(BaseIngestor):

    async def ingest(self, url: str, source_id: str) -> list[Chunk]:
        try:
            video_id = parse_video_id(url)
        except ValueError as e:  # upload_link validates already, this is a safety net
            raise IngestError(str(e))

        loop = asyncio.get_running_loop()  # blocking requests, keep off the event loop
        info = await loop.run_in_executor(None, self.fetch_info, video_id)
        transcript, lines = await loop.run_in_executor(
            None, self.fetch_transcript, video_id, info.spoken_language
        )
        if not lines:
            raise IngestError("The video's subtitles are empty")

        self.title = info.title
        chunks = self.build_chunks(lines, video_id, info, source_id)
        print(
            f"YouTubeIngestor: {video_id} {info.title!r} -> {len(lines)} lines, "
            f"{format_time(lines[-1].end)}, {len(chunks)} chunks | track "
            f"{transcript.language_code} "
            f"({'auto-generated' if transcript.is_generated else 'uploaded'}), "
            f"spoken {info.spoken_language}"
        )
        return chunks

    def fetch_info(self, video_id: str) -> VideoInfo:
        """Title, channel, upload date and spoken language from the watch page. Only
        nice-to-have: any failure gives a placeholder title and ingestion goes on."""
        fallback = VideoInfo(title=f"YouTube video {video_id}")
        try:
            resp = requests.get(
                WATCH_URL.format(video_id),
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            match = re.search(r"ytInitialPlayerResponse\s*=\s*", resp.text)
            if not match:
                return fallback
            player = json.JSONDecoder().raw_decode(resp.text, match.end())[0]
        except (requests.RequestException, ValueError) as e:
            print(f"YouTubeIngestor: no watch page info for {video_id}: {e}")
            return fallback

        details = player.get("videoDetails") or {}
        micro = (player.get("microformat") or {}).get("playerMicroformatRenderer") or {}
        published = None
        try:
            if micro.get("publishDate"):  # "2023-01-17T08:33:27-08:00"
                published = datetime.fromisoformat(micro["publishDate"])
        except ValueError:
            pass

        return VideoInfo(
            title=details.get("title") or fallback.title,
            channel=details.get("author"),
            published=published,
            spoken_language=self.default_audio_language(player),
        )

    def default_audio_language(self, player: dict) -> str | None:
        captions = (player.get("captions") or {}).get(
            "playerCaptionsTracklistRenderer"
        ) or {}
        tracks = captions.get("audioTracks") or []
        index = captions.get("defaultAudioTrackIndex")
        if index is None or not 0 <= index < len(tracks):
            return None
        track_id = tracks[index].get("audioTrackId")  # "en-US.4", absent if undubbed
        return base_language(track_id.split(".")[0]) if track_id else None

    def fetch_transcript(
        self, video_id: str, spoken_language: str | None
    ) -> tuple[Transcript, list[Line]]:
        try:
            transcripts = YouTubeTranscriptApi().list(video_id)
            transcript = self.pick_transcript(transcripts, spoken_language)
            fetched = transcript.fetch()
        except (TranscriptsDisabled, NoTranscriptFound):
            raise IngestError(
                "This video has no subtitles, so there is no transcript to ingest"
            )
        except AgeRestricted:
            raise IngestError("Age-restricted videos can't be ingested without signing in")
        except (VideoUnavailable, VideoUnplayable, InvalidVideoId):
            raise IngestError(
                "The video is unavailable (private, deleted or region-locked)"
            )
        except RequestBlocked:  # IpBlocked too
            raise IngestError(
                "YouTube is blocking transcript requests from this network right now, "
                "try again later"
            )
        except CouldNotRetrieveTranscript as e:
            # the library's messages are long multi-paragraph texts, keep the first line
            reason = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            raise IngestError(f"Could not get the transcript: {reason}")

        lines = []
        for snippet in fetched.snippets:
            text = CUE_RE.sub(" ", html.unescape(snippet.text))
            text = " ".join(text.split())
            if text:
                lines.append(
                    Line(snippet.start, snippet.start + snippet.duration, text)
                )
        return transcript, lines

    def pick_transcript(
        self, transcripts: TranscriptList, spoken_language: str | None
    ) -> Transcript:
        manual = [t for t in transcripts if not t.is_generated]
        generated = [t for t in transcripts if t.is_generated]
        if not manual and not generated:
            raise NoTranscriptFound("", [], transcripts)

        spoken = spoken_language
        if spoken is None and len(generated) == 1:
            # undubbed video: its only auto track is the speech recognised as spoken
            spoken = base_language(generated[0].language_code)

        if spoken:
            for group in (manual, generated):
                for t in group:
                    if base_language(t.language_code) == spoken:
                        return t
        return (manual or generated)[0]

    def build_chunks(
        self, lines: list[Line], video_id: str, info: VideoInfo, source_id: str
    ) -> list[Chunk]:
        meta = " · ".join(p for p in (info.title, info.channel) if p)
        # the time range is the only varying part of the header, budget its longest form
        target = MAX_CHUNK_CHARS - len(f"[{meta} · 0:00:00–0:00:00]") - 1
        origin_date = info.published or datetime.now(timezone.utc)

        chunks: list[Chunk] = []
        for window in self.windows(lines, target):
            start, end = window[0].start, window[-1].end
            header = f"[{meta} · {format_time(start)}–{format_time(end)}]"
            text = " ".join(line.text for line in window)
            chunks.append(
                Chunk(
                    id=str(uuid4()),
                    source_id=source_id,
                    source_type=SourceType.POST,
                    chunk_index=len(chunks),
                    content=f"{header}\n{text}",
                    origin=PostOrigin(
                        platform=Platform.YOUTUBE,
                        external_id=video_id,
                        author=info.channel,
                        origin_date=origin_date,  # upload date if known, else now
                        permalink=f"{WATCH_URL.format(video_id)}&t={int(start)}s",
                        ancestor_ids=[],  # a video is not a thread
                    ),
                )
            )
        return chunks

    def windows(self, lines: list[Line], target: int) -> list[list[Line]]:
        """Consecutive runs of lines of up to `target` chars, each starting with about
        CHUNK_OVERLAP chars of the previous one. Always advances by at least one line."""
        result = []
        i = 0
        while i < len(lines):
            j, size = i, 0
            while j < len(lines) and (j == i or size + 1 + len(lines[j].text) <= target):
                size += len(lines[j].text) + (1 if j > i else 0)
                j += 1
            result.append(lines[i:j])
            if j >= len(lines):
                break
            # step back over whole lines for the overlap, but never to i itself
            k, overlap = j, 0
            while k - 1 > i and overlap + len(lines[k - 1].text) <= CHUNK_OVERLAP:
                k -= 1
                overlap += len(lines[k].text) + 1
            i = k
        return result
