"""Rend la vidéo de présentation d'IUC (20 s, 1920 × 1080, H.264) à partir de son animation.

    pip install -e ".[video]" -c constraints.txt
    python scripts/render_presentation.py                 # vidéo et affiche
    python scripts/render_presentation.py --still 2400    # une image à 2,4 s, pour vérifier

L'animation (docs/video/presentation.html) est figée à chaque instant avec window.seek(ms),
puis capturée par Playwright : chaque image est exacte, quelle que soit la vitesse du poste.
Les images sont envoyées à ffmpeg (fourni par imageio-ffmpeg) sans fichier intermédiaire.
Nécessite les dépendances du frontend (npm ci), qui fournissent la police Inter.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import Page, ViewportSize, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "video" / "presentation.html"
PUBLIC = ROOT / "frontend" / "public"
VIDEO = PUBLIC / "presentation.mp4"
POSTER = PUBLIC / "presentation-poster.jpg"
POSTER_AT_MS = 2400  # logo, titre et accroche affichés
SIZE: ViewportSize = {"width": 1920, "height": 1080}


def open_animation(page: Page) -> int:
    """Charge l'animation, attend la police, et renvoie sa durée en millisecondes."""
    page.goto(SOURCE.as_uri())
    page.evaluate("document.fonts.ready")
    duration: int = page.evaluate("window.DURATION")
    return duration


def seek(page: Page, ms: float) -> None:
    page.evaluate("(ms) => window.seek(ms)", ms)


def render_video(page: Page, duration: int, fps: int, output: Path) -> None:
    frames = round(duration / 1000 * fps)
    encoder = subprocess.Popen(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-loglevel",
            "error",
            "-f",
            "image2pipe",
            "-framerate",
            str(fps),
            "-c:v",
            "png",
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ],
        stdin=subprocess.PIPE,
    )
    assert encoder.stdin is not None
    for index in range(frames):
        seek(page, index * 1000 / fps)
        encoder.stdin.write(page.screenshot(type="png"))
        if index % fps == 0:
            print(f"\r  {index // fps} s / {duration // 1000} s", end="", flush=True)
    encoder.stdin.close()
    if encoder.wait() != 0:
        sys.exit("ffmpeg n'a pas pu encoder la vidéo.")
    size_kb = output.stat().st_size // 1024
    print(f"\rVidéo : {output.relative_to(ROOT)} ({size_kb} Ko, {frames} images)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--still", type=float, nargs="+", help="Instants (ms) à capturer en PNG, sans vidéo."
    )
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=SIZE)
        duration = open_animation(page)
        if args.still:
            for ms in args.still:
                seek(page, ms)
                path = ROOT / "build" / "presentation" / f"image-{int(ms):05d}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=path)
                print(path.relative_to(ROOT))
        else:
            render_video(page, duration, args.fps, VIDEO)
            seek(page, POSTER_AT_MS)
            page.screenshot(path=POSTER, type="jpeg", quality=88)
            print(f"Affiche : {POSTER.relative_to(ROOT)}")
        browser.close()


if __name__ == "__main__":
    main()
