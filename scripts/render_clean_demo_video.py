from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080
FPS = 24
DURATION = 26
TOTAL_FRAMES = FPS * DURATION
OUT = Path("outputs/raven-evidence-graph-clean-demo.mp4")

BG = (5, 6, 10)
PANEL = (14, 18, 29)
PANEL_2 = (20, 25, 38)
CRIMSON = (200, 16, 46)
CYAN = (69, 214, 255)
VIOLET = (139, 92, 246)
GREEN = (42, 196, 122)
AMBER = (245, 180, 48)
TEXT = (242, 245, 250)
TEXT_2 = (190, 198, 214)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"/System/Library/Fonts/Supplemental/Arial {'Bold' if bold else ''}.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


F12 = font(24)
F14 = font(28)
F18 = font(36)
F22 = font(44)
F28 = font(56, True)
F36 = font(72, True)
F52 = font(104, True)


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill, outline=None, width=2, r=24) -> None:
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def write(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fnt, fill=TEXT, anchor=None) -> None:
    draw.text(xy, value, font=fnt, fill=fill, anchor=anchor)


def pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], label: str, fill) -> None:
    rect(draw, xy, fill=fill, outline=None, r=18)
    write(draw, (xy[0] + 20, xy[1] + 9), label, F12, (5, 6, 10))


def node(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, color, t: float, radius: int = 34) -> None:
    pulse = int(4 * math.sin(t * math.pi * 2))
    draw.ellipse((x - radius - pulse, y - radius - pulse, x + radius + pulse, y + radius + pulse), fill=color)
    draw.ellipse((x - radius + 8, y - radius + 8, x + radius - 8, y + radius - 8), fill=(10, 13, 22))
    write(draw, (x, y + 70), label, F12, TEXT_2, anchor="mm")


def title_bar(draw: ImageDraw.ImageDraw) -> None:
    rect(draw, (56, 44, 1864, 126), fill=(9, 12, 21), outline=(35, 42, 60), r=28)
    draw.ellipse((86, 68, 132, 114), fill=CRIMSON)
    write(draw, (154, 68), "Raven Evidence Graph", F22, TEXT)
    write(draw, (154, 104), "local-first provenance for scientific AI", F12, TEXT_2)
    pill(draw, (1320, 70, 1605, 112), "raven.evidence_graph.v1", CYAN)
    pill(draw, (1630, 70, 1818, 112), "clean video", GREEN)


def scene_intro(draw: ImageDraw.ImageDraw, p: float) -> None:
    title_bar(draw)
    a = ease(p)
    write(draw, (140, int(mix(455, 395, a))), "Trace every claim.", F52, TEXT)
    write(draw, (144, int(mix(575, 525, a))), "Sources, claims, confidence, risk, and portable answer traces.", F22, TEXT_2)
    rect(draw, (1170, 260, 1760, 780), fill=PANEL, outline=(42, 48, 68), r=34)
    for i, (label, color, detail) in enumerate([
        ("Source", CYAN, "paper, dataset, note"),
        ("Claim", VIOLET, "scored factual statement"),
        ("Trace", GREEN, "answer + provenance JSON"),
    ]):
        y = 355 + i * 130
        node(draw, 1290, y, "", color, p + i)
        write(draw, (1380, y - 22), label, F22, TEXT)
        write(draw, (1380, y + 22), detail, F14, TEXT_2)


def scene_sources(draw: ImageDraw.ImageDraw, p: float) -> None:
    title_bar(draw)
    write(draw, (96, 186), "1. Add evidence sources", F36, TEXT)
    write(draw, (98, 266), "Papers, datasets, internal notes, expert review, or tool outputs.", F18, TEXT_2)
    rows = [("PAPER", "Clinical protocol review", CYAN), ("DATASET", "Validated benchmark record", GREEN), ("EXPERT", "Reviewer note", AMBER)]
    for i, (kind, title, color) in enumerate(rows):
        y = 350 + i * 150
        x = int(mix(2200, 118, ease(max(0, p - i * 0.12) / 0.55)))
        rect(draw, (x, y, x + 820, y + 112), fill=PANEL, outline=(42, 48, 68), r=24)
        pill(draw, (x + 28, y + 28, x + 150, y + 68), kind, color)
        write(draw, (x + 190, y + 25), title, F22, TEXT)
        write(draw, (x + 190, y + 70), "stable source_id, private content stays local", F12, TEXT_2)


def scene_graph(draw: ImageDraw.ImageDraw, p: float) -> None:
    title_bar(draw)
    write(draw, (96, 186), "2. Link claims to sources", F36, TEXT)
    write(draw, (98, 266), "The graph makes evidence flow inspectable before an answer ships.", F18, TEXT_2)
    points = {
        "trace": (1510, 515, GREEN),
        "claim A": (1160, 350, VIOLET),
        "claim B": (1160, 690, VIOLET),
        "source 1": (760, 280, CYAN),
        "source 2": (720, 540, CYAN),
        "source 3": (760, 800, CYAN),
    }
    edges = [("source 1", "claim A"), ("source 2", "claim A"), ("source 2", "claim B"), ("source 3", "claim B"), ("claim A", "trace"), ("claim B", "trace")]
    for idx, (a, b) in enumerate(edges):
        t = ease(max(0, p - idx * 0.06) / 0.5)
        ax, ay, _ = points[a]
        bx, by, _ = points[b]
        draw.line([(ax, ay), (int(mix(ax, bx, t)), int(mix(ay, by, t)))], fill=(58, 74, 107), width=5)
    for idx, (label, (x, y, color)) in enumerate(points.items()):
        node(draw, x, y, label, color, p + idx * 0.3)


def scene_trace(draw: ImageDraw.ImageDraw, p: float) -> None:
    title_bar(draw)
    write(draw, (96, 186), "3. Generate an answer trace", F36, TEXT)
    write(draw, (98, 266), "Confidence and risk travel with the output, not as an afterthought.", F18, TEXT_2)
    rect(draw, (118, 360, 890, 800), fill=PANEL, outline=(42, 48, 68), r=28)
    write(draw, (162, 420), "Answer", F22, TEXT)
    write(draw, (162, 492), "The workflow selected a local-first path with", F18, TEXT_2)
    write(draw, (162, 540), "traceable sources and reviewable claims.", F18, TEXT_2)
    pill(draw, (162, 625, 382, 668), "confidence 0.86", GREEN)
    pill(draw, (402, 625, 530, 668), "risk low", CYAN)
    pill(draw, (552, 625, 755, 668), "3 sources", VIOLET)
    rect(draw, (1010, 300, 1788, 855), fill=(8, 12, 19), outline=(42, 48, 68), r=28)
    rows = [
        '{',
        '  "schema": "raven.evidence_graph.v1",',
        '  "question": "What supports this answer?",',
        '  "claim_ids": ["claim:local-first"],',
        '  "source_ids": ["source:protocol"],',
        '  "confidence": 0.86,',
        '  "risk": "low"',
        '}',
    ]
    for i, row in enumerate(rows[: int(mix(1, len(rows), ease(p)))]):
        color = CYAN if '"schema"' in row else GREEN if '"risk"' in row else TEXT_2
        write(draw, (1060, 355 + i * 54), row, F14, color)


def scene_ecosystem(draw: ImageDraw.ImageDraw, p: float) -> None:
    title_bar(draw)
    write(draw, (96, 186), "4. One packet across the ecosystem", F36, TEXT)
    apps = [
        ("Raven AI", "core graph + scoring", VIOLET),
        ("OpenClinical AI", "clinical trace + audit", CYAN),
        ("Home for AI", "local run history", GREEN),
        ("Hermes Edge", "offline benchmark proof", AMBER),
    ]
    for i, (name, desc, color) in enumerate(apps):
        x = 130 + (i % 2) * 850
        y = 335 + (i // 2) * 245
        scale = ease(max(0, p - i * 0.1) / 0.5)
        x = int(mix(x - 50, x, scale))
        rect(draw, (x, y, x + 710, y + 168), fill=PANEL, outline=(42, 48, 68), r=28)
        draw.rectangle((x, y, x + int(710 * scale), y + 6), fill=color)
        write(draw, (x + 36, y + 42), name, F28, TEXT)
        write(draw, (x + 38, y + 106), desc, F18, TEXT_2)


def scene_outro(draw: ImageDraw.ImageDraw, p: float) -> None:
    title_bar(draw)
    write(draw, (WIDTH // 2, 415), "Raven Evidence Graph", F52, TEXT, anchor="mm")
    write(draw, (WIDTH // 2, 540), "local-first provenance for scientific AI", F28, TEXT_2, anchor="mm")
    write(draw, (WIDTH // 2, 660), "Trace every claim.", F36, CYAN, anchor="mm")
    rect(draw, (520, 760, 1400, 835), fill=PANEL_2, outline=(42, 48, 68), r=22)
    write(draw, (WIDTH // 2, 800), "github.com/simpliibarrii-crypto/raven-ai", F18, TEXT, anchor="mm")


def draw_frame(frame: int) -> Image.Image:
    t = frame / FPS
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    for x in range(0, WIDTH, 64):
        draw.line((x, 0, x, HEIGHT), fill=(10, 13, 22), width=1)
    for y in range(0, HEIGHT, 64):
        draw.line((0, y, WIDTH, y), fill=(10, 13, 22), width=1)
    if t < 4:
        scene_intro(draw, t / 4)
    elif t < 8:
        scene_sources(draw, (t - 4) / 4)
    elif t < 13:
        scene_graph(draw, (t - 8) / 5)
    elif t < 18:
        scene_trace(draw, (t - 13) / 5)
    elif t < 23:
        scene_ecosystem(draw, (t - 18) / 5)
    else:
        scene_outro(draw, (t - 23) / 3)
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-crf",
        "18",
        str(OUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for frame in range(TOTAL_FRAMES):
        proc.stdin.write(draw_frame(frame).tobytes())
    proc.stdin.close()
    code = proc.wait()
    if code:
        raise SystemExit(code)
    print(OUT)


if __name__ == "__main__":
    main()
