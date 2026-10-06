"""Musique originale de la vidéo de présentation (20 s), synthétisée note par note.

Composée pour IUC et calée sur l'animation (docs/video/presentation.html) : 150 battements
par minute, soit une phrase de 8 temps (3,2 s) par scène ; un impact à chaque changement de
scène, une montée juste avant, et de petits sons d'interface sur les clics, la frappe et les
apparitions. Aucun échantillon extérieur : la piste fait partie du projet (licence MIT).

    python scripts/presentation_music.py    # écrit build/presentation/musique.wav
"""

import wave
from collections.abc import Iterable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

Signal = NDArray[np.float64]

SR = 44_100
DURATION = 20.0
BEAT = 0.4  # 150 battements par minute
BAR = 4 * BEAT  # 1,6 s
EIGHTH = BEAT / 2
SIXTEENTH = BEAT / 4

# Un accord par mesure, en boucle : Fa maj7, Sol, La m7, Mi m7 (basse, puis notes MIDI).
CHORDS: list[tuple[int, tuple[int, ...]]] = [
    (41, (53, 57, 60, 64)),
    (43, (55, 59, 62, 67)),
    (45, (57, 60, 64, 67)),
    (40, (55, 59, 62, 64)),
]
FINAL_CHORD: tuple[int, tuple[int, ...]] = (36, (48, 55, 59, 62, 64, 71))  # Do maj9
FINAL_AT = 18.8  # conclusion de la vidéo
SCENES = (3.2, 6.4, 9.6, 12.8, 16.0)  # débuts de phrase, alignés sur les scènes
TARGET_RMS = 10 ** (-16 / 20)  # niveau moyen visé
CEILING = 10 ** (-1 / 20)  # crêtes sous -1 dBFS


def midi(note: float) -> float:
    return float(440.0 * 2 ** ((note - 69) / 12))


def timeline(seconds: float) -> Signal:
    return np.arange(int(seconds * SR)) / SR


def envelope(seconds: float, attack: float, release: float) -> Signal:
    """Montée linéaire puis descente en fin de note (sans clic)."""
    t = timeline(seconds)
    rise = np.clip(t / max(attack, 1e-4), 0, 1)
    fall = np.clip((seconds - t) / max(release, 1e-4), 0, 1)
    return rise * fall


def filtered(signal: Signal, low: float | None = None, high: float | None = None) -> Signal:
    """Filtre passe-haut (low) et passe-bas (high) du second ordre, appliqué par FFT."""
    spectrum = np.fft.rfft(signal)
    freq = np.fft.rfftfreq(len(signal), 1 / SR)
    gain = np.ones_like(freq)
    if high is not None:
        gain /= np.sqrt(1 + (freq / high) ** 4)
    if low is not None:
        gain /= np.sqrt(1 + (low / np.maximum(freq, 1e-3)) ** 4)
    out: Signal = np.fft.irfft(spectrum * gain, len(signal))
    return out


def tone(freq: float, seconds: float, harmonics: int, rolloff: float, cents: float = 0.0) -> Signal:
    """Onde riche en harmoniques (proche d'une dent de scie), adoucie par `rolloff`."""
    t = timeline(seconds)
    f = freq * 2 ** (cents / 1200)
    out = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        if f * k > 14_000:
            break
        out += np.sin(2 * np.pi * f * k * t) / k * np.exp(-(k - 1) / rolloff)
    return out


# --- Instruments ---------------------------------------------------------------------------


def pad(notes: Iterable[int], seconds: float, cents: float) -> Signal:
    out = sum(tone(midi(n), seconds, 16, 7.0, cents) for n in notes)
    return np.asarray(out) * envelope(seconds, 0.35, 0.7)


def pluck(note: int, bright: float = 2.5) -> Signal:
    seconds = 0.5
    t = timeline(seconds)
    return (
        tone(midi(note), seconds, 10, bright) * np.exp(-t / 0.13) * envelope(seconds, 0.003, 0.05)
    )


def bass(note: int, seconds: float) -> Signal:
    t = timeline(seconds)
    f = midi(note)
    raw = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.6 * raw) * np.exp(-t / 0.3) * envelope(seconds, 0.004, 0.04)


def kick() -> Signal:
    t = timeline(0.45)
    freq = 56 + 110 * np.exp(-t / 0.03)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.15)
    return np.tanh(1.5 * body)


def clap(rng: np.random.Generator) -> Signal:
    t = timeline(0.3)
    noise = rng.standard_normal(len(t))
    hits = sum(np.where(t >= b, np.exp(-(t - b) / 0.006), 0.0) for b in (0.0, 0.011, 0.022))
    shape = np.asarray(hits) + 0.6 * np.exp(-t / 0.09)
    return filtered(noise * shape, low=900, high=5000)


def hat(rng: np.random.Generator, decay: float = 0.03) -> Signal:
    t = timeline(0.15)
    return filtered(rng.standard_normal(len(t)) * np.exp(-t / decay), low=7500)


def impact(rng: np.random.Generator) -> Signal:
    t = timeline(1.8)
    sub = np.sin(2 * np.pi * np.cumsum(42 + 40 * np.exp(-t / 0.25)) / SR) * np.exp(-t / 0.6)
    crash = filtered(rng.standard_normal(len(t)), low=3500) * np.exp(-t / 0.8)
    return 0.7 * np.tanh(1.3 * sub) + 0.45 * crash


def riser(rng: np.random.Generator, seconds: float = 0.8) -> Signal:
    t = timeline(seconds)
    ramp = (t / seconds) ** 2
    noise = filtered(rng.standard_normal(len(t)), low=1800) * ramp
    sweep = np.sin(2 * np.pi * np.cumsum(300 * 6 ** (t / seconds)) / SR) * ramp
    return noise + 0.12 * sweep


def bell(note: int, seconds: float = 1.4) -> Signal:
    t = timeline(seconds)
    f = midi(note)
    partials = (
        np.sin(2 * np.pi * f * t) * np.exp(-t / 0.7)
        + 0.45 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.3)
        + 0.2 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / 0.15)
    )
    return partials * envelope(seconds, 0.002, 0.2)


def blip(note: int) -> Signal:
    t = timeline(0.2)
    f = midi(note)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.05)


def click(rng: np.random.Generator) -> Signal:
    t = timeline(0.03)
    noise = filtered(rng.standard_normal(len(t)), low=2500, high=9000) * np.exp(-t / 0.004)
    return noise + 0.4 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.006)


# --- Mixage ----------------------------------------------------------------------------------


class Mix:
    """Trois bus stéréo (batterie, musique, effets) et un départ de réverbération."""

    def __init__(self) -> None:
        size = int(DURATION * SR)
        self.buses = {name: np.zeros((2, size)) for name in ("drums", "music", "fx", "send")}

    def add(
        self, bus: str, sound: Signal, at: float, gain: float, pan: float = 0.0, verb: float = 0.0
    ) -> None:
        start = int(round(at * SR))
        size = self.buses[bus].shape[1]
        if start >= size or start < 0:
            return
        part = sound[: size - start] * gain
        angle = (pan + 1) * np.pi / 4
        stereo = np.vstack([part * np.cos(angle), part * np.sin(angle)]) * np.sqrt(2)
        end = start + len(part)
        self.buses[bus][:, start:end] += stereo
        if verb:
            self.buses["send"][:, start:end] += stereo * verb

    def render(self, kicks: list[float], rng: np.random.Generator) -> Signal:
        size = self.buses["music"].shape[1]
        # Effet de pompe : la musique s'efface brièvement sous chaque grosse caisse.
        duck = np.ones(size)
        shape = 1 - 0.5 * np.exp(-timeline(0.35) / 0.1)
        for at in kicks:
            start = int(at * SR)
            end = min(size, start + len(shape))
            duck[start:end] *= shape[: end - start]
        dry = self.buses["drums"] + self.buses["music"] * duck + self.buses["fx"]
        return dry + 0.35 * reverb(self.buses["send"], rng)


def reverb(signal: Signal, rng: np.random.Generator) -> Signal:
    """Réverbération de salle : convolution par un bruit à décroissance exponentielle."""
    t = timeline(1.8)
    out = np.zeros_like(signal)
    for channel in range(2):
        response = rng.standard_normal(len(t)) * np.exp(-t / 0.45)
        response = filtered(response, low=200, high=7000)
        response /= np.sqrt(np.sum(response**2))
        size = signal.shape[1] + len(response)
        wet = np.fft.irfft(np.fft.rfft(signal[channel], size) * np.fft.rfft(response, size), size)
        out[channel] = wet[: signal.shape[1]]
    return out


# --- Arrangement -----------------------------------------------------------------------------


def compose(seed: int = 2026) -> Signal:
    rng = np.random.default_rng(seed)
    mix = Mix()
    kicks: list[float] = []

    def drums(
        at: float, kick_beats: Iterable[float], clap_beats: Iterable[float], step: float
    ) -> None:
        for beat in kick_beats:
            kicks.append(at + beat * BEAT)
            mix.add("drums", kick(), at + beat * BEAT, 0.6)
        for beat in clap_beats:
            mix.add("drums", clap(rng), at + beat * BEAT, 0.42, pan=0.1, verb=0.25)
        position = 0.0
        while position < BAR - 1e-9:
            accent = 1.0 if round(position / EIGHTH) % 2 else 0.55
            mix.add("drums", hat(rng), at + position, 0.2 * accent, pan=0.35)
            position += step

    for bar in range(12):
        at = bar * BAR
        if at >= FINAL_AT:
            break
        root, notes = CHORDS[bar % len(CHORDS)]
        length = min(BAR + 0.5, FINAL_AT - at + 0.25)
        intro = at < 3.2
        # Nappe : deux voix légèrement désaccordées, à gauche et à droite.
        gain = 0.075 if intro else 0.1
        mix.add("music", pad(notes, length, +7), at, gain, pan=-0.6, verb=0.5)
        mix.add("music", pad(notes, length, -7), at, gain, pan=0.6, verb=0.5)

        # Arpège : noires dans l'introduction, croches ensuite, doubles croches à la fin.
        step = BEAT if intro else (SIXTEENTH if at >= 16.0 else EIGHTH)
        pattern = [
            notes[0] + 12,
            notes[1] + 12,
            notes[2] + 12,
            notes[3] + 12,
            notes[2] + 12,
            notes[1] + 12,
        ]
        position, index = (0.8 if bar == 0 else 0.0), 0
        while position < BAR - 1e-9 and at + position < FINAL_AT - 0.05:
            mix.add(
                "music",
                pluck(pattern[index % len(pattern)], 2.5 if intro else 4.5),
                at + position,
                0.07 if intro else 0.1,
                pan=-0.35 if index % 2 else 0.35,
                verb=0.4,
            )
            index += 1
            position += step

        if intro:
            continue
        # Basse : croches sur la fondamentale, octave sur les contretemps.
        position = 0.0
        while position < BAR - 1e-9 and at + position < FINAL_AT - 0.05:
            offbeat = round(position / EIGHTH) % 2 == 1
            mix.add("music", bass(root + (12 if offbeat else 0), EIGHTH * 0.95), at + position, 0.2)
            position += EIGHTH

        if at < 6.4:
            drums(at, (0, 2, 2.5), (2,), EIGHTH)  # demi-tempo pendant « le problème »
        elif at + BAR > FINAL_AT:
            drums(at, (0, 1, 2), (1,), SIXTEENTH)  # on retient le dernier temps avant la fin
        else:
            drums(at, (0, 1, 2, 3), (1, 3), SIXTEENTH if at >= 16.0 else EIGHTH)

    # Changements de scène : montée, puis impact.
    for at in (*SCENES, FINAL_AT):
        mix.add("fx", riser(rng), at - 0.8, 0.09, verb=0.2)
        mix.add("fx", impact(rng), at, 0.5, verb=0.3)

    # Conclusion : accord de Do maj9 tenu jusqu'à la fin.
    root, notes = FINAL_CHORD
    tail = DURATION - FINAL_AT
    mix.add("music", pad(notes, tail, +7), FINAL_AT, 0.11, pan=-0.6, verb=0.7)
    mix.add("music", pad(notes, tail, -7), FINAL_AT, 0.11, pan=0.6, verb=0.7)
    mix.add("music", bass(root, tail) * np.exp(-timeline(tail) / 0.6), FINAL_AT, 0.28)

    # Sons d'interface, synchronisés avec l'animation.
    for at, note, gain in (
        (0.15, 84, 0.12),
        (0.95, 88, 0.08),
        (1.4, 91, 0.07),
        (8.6, 88, 0.09),
        (18.2, 91, 0.1),
        (18.35, 96, 0.07),
        (19.25, 96, 0.06),
    ):
        mix.add("fx", bell(note), at, gain, pan=0.2, verb=0.5)
    for i in range(14):  # compteur de likes
        mix.add("fx", click(rng), 3.4 + i * 0.1, 0.05 + 0.004 * i, pan=-0.2)
    for at, steps, span in ((7.2, 14, 0.7), (7.7, 10, 0.6)):  # frappe au clavier
        for i in range(steps):
            mix.add("fx", click(rng), at + i * span / steps, 0.045, pan=0.3)
    for at, note in (
        (5.15, 79),
        (8.0, 72),
        (8.2, 76),
        (8.4, 79),
        (14.35, 79),
        (16.7, 67),
        (17.2, 67),
        (17.7, 72),
    ):
        mix.add("fx", blip(note), at, 0.07, pan=0.15, verb=0.3)
    for at in (10.95, 11.3, 11.6, 11.95, 14.2, 14.95):  # clics du curseur
        mix.add("fx", click(rng), at, 0.11, pan=0.25)

    out = mix.render(kicks, rng)
    out = np.vstack([filtered(channel, low=35) for channel in out])  # infrabasses inutiles
    # Fondus, niveau d'une musique d'accompagnement (RMS -16 dBFS), crêtes adoucies.
    fade = np.ones(out.shape[1])
    fade[: int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
    fade[-int(0.5 * SR) :] = np.linspace(1, 0, int(0.5 * SR))
    out = out * fade
    out *= TARGET_RMS / float(np.sqrt(np.mean(out**2)))
    out = np.tanh(out / CEILING) * CEILING
    return out


def write_wav(signal: Signal, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = (np.clip(signal.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(SR)
        file.writeframes(samples.tobytes())
    return path


def main() -> None:
    path = write_wav(
        compose(), Path(__file__).resolve().parents[1] / "build" / "presentation" / "musique.wav"
    )
    print(path)


if __name__ == "__main__":
    main()
