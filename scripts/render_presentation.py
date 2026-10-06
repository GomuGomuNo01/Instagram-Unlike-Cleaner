"""Rend la vidéo de présentation d'IUC (20 s, 1920 × 1080, H.264) à partir de son animation.

    pip install -e ".[video]" -c constraints.txt
    python scripts/render_presentation.py                 # vidéo, musique et affiche
    python scripts/render_presentation.py --music-only    # remplace seulement la musique
    python scripts/render_presentation.py --still 2400    # une image à 2,4 s, pour vérifier

L'animation (docs/video/presentation.html) est figée à chaque instant avec window.seek(ms),
puis capturée par Playwright : chaque image est exacte, quelle que soit la vitesse du poste.
Les images sont envoyées à ffmpeg (fourni par imageio-ffmpeg) sans fichier intermédiaire,
puis la musique originale (scripts/presentation_music.py) est ajoutée en AAC.
Nécessite les dépendances du frontend (npm ci), qui fournissent la police Inter.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import Page, ViewportSize, sync_playwright
from presentation_music import compose, write_wav

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "video" / "presentation.html"
PUBLIC = ROOT / "frontend" / "public"
VIDEO = PUBLIC / "presentation.mp4"
POSTER = PUBLIC / "presentation-poster.jpg"
BUILD = ROOT / "build" / "presentation"
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


def add_music(video: Path) -> None:
    """Remplace la piste sonore de la vidéo par la musique, sans réencoder l'image."""
    music = write_wav(compose(), BUILD / "musique.wav")
    mixed = video.with_name(f"{video.stem}.tmp{video.suffix}")
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-i",
        str(music),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(mixed),
    ]
    if subprocess.run(command, check=False).returncode != 0:
        sys.exit("ffmpeg n'a pas pu ajouter la musique.")
    mixed.replace(video)
    print(f"Musique ajoutée : {video.relative_to(ROOT)} ({video.stat().st_size // 1024} Ko)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--still", type=float, nargs="+", help="Instants (ms) à capturer en PNG, sans vidéo."
    )
    parser.add_argument(
        "--music-only", action="store_true", help="Remplace la musique de la vidéo existante."
    )
    args = parser.parse_args()
    if args.music_only:
        add_music(VIDEO)
        return

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=SIZE)
        duration = open_animation(page)
        if args.still:
            for ms in args.still:
                seek(page, ms)
                path = BUILD / f"image-{int(ms):05d}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=path)
                print(path.relative_to(ROOT))
        else:
            render_video(page, duration, args.fps, VIDEO)
            add_music(VIDEO)
            seek(page, POSTER_AT_MS)
            page.screenshot(path=POSTER, type="jpeg", quality=88)
            print(f"Affiche : {POSTER.relative_to(ROOT)}")
        browser.close()


if __name__ == "__main__":
    main()
