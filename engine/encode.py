"""MP4 encoding and probing for the short-film pipeline.

`encode` streams RGB frames (arrays or PNG paths) into H.264 High / yuv420p
with BT.709 colour tags, optionally muxes a 48 kHz stereo WAV as AAC-LC, and
puts the moov atom at the front. `probe` reads the result back as numbers.

The audio is interleaved with the video as it is written and trimmed to the
video's length, so the two tracks end together.

Run the self-test from the repository root:  python -m engine.selftest_av
"""

from __future__ import annotations

import struct
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Union

import av
import numpy as np
import soundfile as sf
from PIL import Image
from engine.files import fresh, write_text as save_text

FrameSource = Union[np.ndarray, str, Path]

AUDIO_RATE = 48000
AAC_FRAME = 1024
AUDIO_BIT_RATE = 192_000
MAX_KEYFRAME_INTERVAL = 60

# FFmpeg enum values for the colour tags, as PyAV exposes them.
_PRIMARIES = {1: "bt709", 5: "bt470bg", 6: "smpte170m"}
_TRANSFER = {1: "bt709", 6: "smpte170m", 13: "iec61966-2-1"}
_MATRIX = {1: "bt709", 5: "bt470bg", 6: "smpte170m"}
_RANGE = {1: "tv", 2: "pc"}


def _to_array(frame: FrameSource, size: tuple[int, int]) -> np.ndarray:
    """Return an (H, W, 3) uint8 RGB array of the expected size, or raise."""
    if isinstance(frame, (str, Path)):
        with Image.open(frame) as img:
            array = np.asarray(img.convert("RGB"))
    else:
        array = np.asarray(frame)
    width, height = size
    if array.dtype != np.uint8 or array.shape != (height, width, 3):
        raise ValueError(f"frame must be uint8 of shape {(height, width, 3)}, "
                         f"got {array.dtype} {array.shape}")
    return np.ascontiguousarray(array)


def _audio_blocks(audio_wav: str | Path):
    """Yield (samples, 2) float32 blocks of AAC_FRAME samples from a 48 kHz WAV."""
    with sf.SoundFile(audio_wav) as source:
        if source.samplerate != AUDIO_RATE:
            raise ValueError(f"audio must be {AUDIO_RATE} Hz, got {source.samplerate}")
        if source.channels not in (1, 2):
            raise ValueError("audio must be mono or stereo")
        while True:
            block = source.read(AAC_FRAME, dtype="float32", always_2d=True)
            if block.shape[0] == 0:
                return
            if block.shape[1] == 1:
                block = np.repeat(block, 2, axis=1)
            yield block


class _AudioFeeder:
    """Feeds AAC frames on demand up to a time limit, so audio interleaves with video."""

    def __init__(self, container, stream, audio_wav):
        self.container, self.stream = container, stream
        self.blocks = _audio_blocks(audio_wav)
        self.written = 0  # samples
        self.exhausted = False

    def feed_until(self, seconds: float, final: bool = False) -> None:
        """Write whole blocks until `seconds` is covered; on `final`, trim to exactly that."""
        limit = int(round(seconds * AUDIO_RATE))
        while not self.exhausted and self.written < limit:
            block = next(self.blocks, None)
            if block is None:
                self.exhausted = True
                return
            if final and self.written + block.shape[0] > limit:
                block = block[:limit - self.written]
                self.exhausted = True  # the rest of the audio is dropped
            self._write(block)

    def _write(self, block: np.ndarray) -> None:
        frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(block.T), format="fltp", layout="stereo")
        frame.sample_rate = AUDIO_RATE
        frame.pts = self.written
        frame.time_base = Fraction(1, AUDIO_RATE)
        self.written += block.shape[0]
        for packet in self.stream.encode(frame):
            self.container.mux(packet)

    def flush(self) -> None:
        for packet in self.stream.encode(None):
            self.container.mux(packet)


def encode(frames: Iterable[FrameSource], audio_wav: str | Path | None, out_mp4: str | Path, *,
           fps: int = 30, size: tuple[int, int] = (1080, 1920), crf: int = 16,
           preset: str = "slow") -> dict:
    """Encode `frames` (and `audio_wav`, if given) to out_mp4 and return probe(out_mp4).

    `size` is (width, height). Audio longer than the video is trimmed to it; audio
    shorter than the video is left short and shows up in the probe numbers.
    The returned dict also carries audio_samples_written and video_frames_written.
    """
    out_path = Path(out_mp4)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    container = av.open(str(fresh(out_path)), mode="w", options={"movflags": "+faststart"})
    try:
        video = container.add_stream("libx264", rate=fps)
        video.width, video.height = width, height
        video.pix_fmt = "yuv420p"
        video.time_base = Fraction(1, fps)
        video.codec_context.time_base = Fraction(1, fps)
        video.codec_context.color_primaries = 1
        video.codec_context.color_trc = 1
        video.codec_context.colorspace = 1
        video.codec_context.color_range = 1
        video.options = {"crf": str(crf), "preset": preset, "profile": "high",
                         "g": str(MAX_KEYFRAME_INTERVAL)}
        feeder = None
        if audio_wav is not None:
            audio = container.add_stream("aac", rate=AUDIO_RATE, layout="stereo")
            audio.bit_rate = AUDIO_BIT_RATE
            feeder = _AudioFeeder(container, audio, audio_wav)

        count = 0
        for source in frames:
            rgb = av.VideoFrame.from_ndarray(_to_array(source, size), format="rgb24")
            yuv = rgb.reformat(format="yuv420p", dst_colorspace="ITU709", dst_color_range="MPEG")
            yuv.pts = count
            yuv.time_base = Fraction(1, fps)
            for packet in video.encode(yuv):
                container.mux(packet)
            count += 1
            if feeder is not None:
                feeder.feed_until(count / fps)
        for packet in video.encode(None):
            container.mux(packet)
        if feeder is not None:
            feeder.feed_until(count / fps, final=True)
            feeder.flush()
    finally:
        container.close()

    report = probe(out_path)
    report["video_frames_written"] = count
    if audio_wav is not None:
        report["audio_samples_written"] = feeder.written
    return report


def _top_level_atoms(path: Path) -> list[str]:
    """Names of the top-level MP4 boxes in file order."""
    names = []
    size_total = path.stat().st_size
    with open(path, "rb") as handle:
        position = 0
        while position + 8 <= size_total:
            handle.seek(position)
            size, name = struct.unpack(">I4s", handle.read(8))
            if size == 1:
                size = struct.unpack(">Q", handle.read(8))[0]
            elif size == 0:
                size = size_total - position
            names.append(name.decode("latin-1"))
            if size < 8:
                break
            position += size
    return names


def _name(table: dict[int, str], value) -> str | None:
    if value is None:
        return None
    return table.get(int(value), f"unknown({int(value)})")


def probe(mp4_path: str | Path) -> dict:
    """Read back the properties of an MP4 as plain numbers and strings."""
    path = Path(mp4_path)
    atoms = _top_level_atoms(path)
    result: dict = {
        "path": str(path),
        "file_size": path.stat().st_size,
        "top_level_atoms": atoms,
        "faststart": "moov" in atoms and "mdat" in atoms and atoms.index("moov") < atoms.index("mdat"),
    }
    with av.open(str(path)) as container:
        result["duration_s"] = container.duration / av.time_base if container.duration else None
        result["container_bit_rate"] = container.bit_rate
        video = next((s for s in container.streams if s.type == "video"), None)
        audio = next((s for s in container.streams if s.type == "audio"), None)
        if video is not None:
            ctx = video.codec_context
            stamps, key_positions, packet_count = [], [], 0
            for packet in container.demux(video):
                if packet.dts is None:
                    continue
                if packet.is_keyframe:
                    key_positions.append(packet_count)
                packet_count += 1
                stamps.append(packet.pts)
            stamps.sort()
            deltas = {b - a for a, b in zip(stamps, stamps[1:])}
            gaps = [b - a for a, b in zip(key_positions, key_positions[1:])]
            if key_positions:
                gaps.append(packet_count - key_positions[-1])
            result["video"] = {
                "codec": ctx.name,
                "profile": ctx.profile,
                "pix_fmt": ctx.pix_fmt,
                "width": ctx.width,
                "height": ctx.height,
                "fps": float(video.average_rate) if video.average_rate else None,
                "frames": packet_count,
                "duration_s": float(video.duration * video.time_base) if video.duration else None,
                "bit_rate": video.bit_rate or ctx.bit_rate,
                "constant_frame_rate": len(deltas) <= 1,
                "max_keyframe_interval": max(gaps) if gaps else None,
                "color_primaries": _name(_PRIMARIES, ctx.color_primaries),
                "color_trc": _name(_TRANSFER, ctx.color_trc),
                "colorspace": _name(_MATRIX, ctx.colorspace),
                "color_range": _name(_RANGE, ctx.color_range),
            }
        if audio is not None:
            ctx = audio.codec_context
            result["audio"] = {
                "codec": ctx.name,
                "profile": ctx.profile,
                "sample_rate": ctx.sample_rate,
                "channels": ctx.channels,
                "duration_s": float(audio.duration * audio.time_base) if audio.duration else None,
                "bit_rate": audio.bit_rate or ctx.bit_rate,
            }
    return result
