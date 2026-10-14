"""Gate de ruído e normalização de volume para as gravações.

Para que serve: uma gravação de guitarra tem zumbido de 60 Hz, chiado da
interface e ruído de sala entre as notas. O gate corta esse silêncio; o
normalizador deixa todas as-take com o mesmo volume, para comparar dois presets
sem o volume te enganando ("esse preset é melhor" quando na verdade só está
mais alto).

Por que `audioop` e não numpy: numpy não está no projeto e ia pesar ~15 MB
no requirements e no .exe gerado pelo PyInstaller. O `audioop` faz parte da
biblioteca padrão (deprecated, mas presente até o Python 3.12 — que é o que o
setup.bat instala) e resolve 90% do trabalho em C.

O gate é envelope-based com histerese e hold, como um compressor de lado: sem
isso o gate abre e fecha a cada nota e fica "engasgando", que é o defeito
clássico de gate mal ajustado.
"""
from __future__ import annotations

import array
import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

try:
    import audioop
except ImportError:  # pragma: no cover - só em Python >= 3.13
    audioop = None

SAMPLE_WIDTH = 2          # Int16
FULL_SCALE = 32768.0
WINDOW = 256              # ~5.8 ms a 44,1 kHz


def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def lin_to_db(v: float) -> float:
    return 20.0 * math.log10(v) if v > 1e-9 else -120.0


def peak_dbfs(pcm: bytes) -> float:
    """Pico do PCM em dBFS. -120 dB é o piso (silêncio)."""
    if not pcm or audioop is None:
        return -120.0
    return lin_to_db(audioop.max(pcm, SAMPLE_WIDTH) / FULL_SCALE)


def rms_dbfs(pcm: bytes) -> float:
    if not pcm or audioop is None:
        return -120.0
    return lin_to_db(audioop.rms(pcm, SAMPLE_WIDTH) / FULL_SCALE)


@dataclass
class GateResult:
    out: bytes
    closed_ms: int          # quanto tempo foi cortado
    total_ms: int
    events: int             # quantas vezes o gate abriu

    def pct_closed(self) -> float:
        return (self.closed_ms / self.total_ms * 100.0) if self.total_ms else 0.0


def gate(
    pcm: bytes,
    threshold_db: float = -45.0,
    hysteresis_db: float = 6.0,
    hold_ms: float = 120.0,
    release_ms: float = 80.0,
    fade_ms: float = 4.0,
    sample_rate: int = 44100,
) -> GateResult:
    """Corta o que estiver abaixo do limiar, com histerese e hold.

    threshold_db   abaixo disso o gate fecha (ex.: -45 dB)
    hysteresis_db  o gate só reabre acima de threshold + hysteresis, o que evita
                   abrir e fechar no meio de uma nota fraca
    hold_ms        tempo que o gate fica aberto depois do sinal cair
    release_ms     suavização ao fechar, para não estalar
    fade_ms        fade in/out de borda, também para não estalar
    """
    n = len(pcm)
    if n < WINDOW * 4 or audioop is None:
        return GateResult(pcm, 0, max(0, n * 1000 // (sample_rate * SAMPLE_WIDTH)), 0)

    nbytes = n
    nsamples = n // SAMPLE_WIDTH
    rate = sample_rate
    fade_n = max(1, int(rate * fade_ms / 1000))
    hold_n = max(0, int(rate * hold_ms / 1000))
    release_n = max(0, int(rate * release_ms / 1000))
    open_db = threshold_db + hysteresis_db

    # 1) envelope: pico em dB por janela (rápido, em C, via audioop.max).
    #    Os deslocamentos são em BYTES, porque é o que o audioop consome.
    env: list[tuple[int, float]] = []
    for off in range(0, nbytes - WINDOW, WINDOW):
        lin = audioop.max(pcm[off:off + WINDOW], SAMPLE_WIDTH) / FULL_SCALE
        env.append((off, lin_to_db(lin)))

    # 2) histerese + hold -> máscara por AMOSTRA (o array é por amostra)
    open_flags = [False] * nsamples
    is_open = False
    hold_left = 0
    events = 0
    release_left = 0

    for off, db in env:
        if not is_open:
            if db >= open_db:
                is_open = True
                events += 1
                hold_left = hold_n
                release_left = release_n
        else:
            if db >= threshold_db:
                hold_left = hold_n
                release_left = release_n
            elif hold_left > 0:
                hold_left -= WINDOW // SAMPLE_WIDTH
            else:
                release_left -= WINDOW // SAMPLE_WIDTH
                if release_left <= 0:
                    is_open = False
        if is_open or release_left > 0:
            s0 = off // SAMPLE_WIDTH
            s1 = min(nsamples, s0 + WINDOW // SAMPLE_WIDTH)
            for i in range(s0, s1):
                open_flags[i] = True

    # 3) aplica: zera o que está fechado, com fade para não estalar
    data = array.array("h")
    data.frombytes(pcm)
    if sys_is_big_endian():
        data.byteswap()
    for i, keep in enumerate(open_flags):
        if not keep:
            data[i] = 0

    _smooth_edges(data, open_flags, fade_n)

    if sys_is_big_endian():
        data.byteswap()
    out = data.tobytes()
    closed = open_flags.count(False)
    closed_ms = closed * 1000 // rate
    total_ms = nsamples * 1000 // rate
    return GateResult(out, closed_ms, total_ms, events)


def _smooth_edges(data: array.array, flags: list[bool], fade_n: int) -> None:
    """Aplica fade in/out nas bordas do gate, para não estalar."""
    n = len(data)
    i = 0
    while i < n:
        if flags[i]:
            j = i
            while j < n and flags[j]:
                j += 1
            # fade-in
            for k in range(i, min(j, i + fade_n)):
                data[k] = int(data[k] * ((k - i) / fade_n))
            # fade-out
            for k in range(max(i, j - fade_n), j):
                data[k] = int(data[k] * ((j - k) / fade_n))
            i = j
        else:
            i += 1


def sys_is_big_endian() -> bool:
    return __import__("sys").byteorder == "big"


def normalize(pcm: bytes, target_db: float = -1.0, limit_db: float = -0.5,
              mode: str = "pico") -> tuple[bytes, float]:
    """Ajusta o volume. mode='pico' alinha o pico; mode='rms' alinha o volume
    percebido (melhor para comparar takes).

    Devolve (pcm, ganho_em_db_aplicado).
    """
    if not pcm or audioop is None:
        return pcm, 0.0
    peak = peak_dbfs(pcm)
    if mode == "rms":
        cur = rms_dbfs(pcm)
        if cur <= -119.0:
            return pcm, 0.0        # silêncio: normalizar amplificaria só o ruído
        gain_db = target_db - cur
    else:
        cur = peak
        if cur <= -119.0:
            return pcm, 0.0
        gain_db = target_db - cur

    # O limite é sobre o PICO, sempre. No modo rms o ganho é muito maior, e
    # comparar o rms resultante contra o limite deixa o pico estourar em 0 dBFS
    # — que é exatamente o clipping que o limitador existe para evitar.
    if peak > -119.0 and peak + gain_db > limit_db:
        gain_db = limit_db - peak
    return audioop.mul(pcm, SAMPLE_WIDTH, db_to_lin(gain_db)), gain_db


def process_file(
    path: str | Path,
    out_path: str | Path | None = None,
    do_gate: bool = True,
    do_norm: bool = True,
    threshold_db: float = -45.0,
    target_db: float = -1.0,
    mode: str = "pico",
) -> dict:
    """Processa um WAV. Nunca sobrescreve o original: grava em arquivo novo
    com sufixo, a menos que out_path seja explicitamente o mesmo caminho."""
    src = Path(path)
    with wave.open(str(src), "rb") as w:
        ch, sw, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(frames)

    if sw != SAMPLE_WIDTH:
        raise ValueError(f"Este arquivo é de {sw * 8}-bit; só 16-bit é suportado.")
    if ch != 1:
        # o programa sempre grava estéreo duplicando o mono; compacta para 1
        mono = bytearray()
        step = ch * SAMPLE_WIDTH
        for off in range(0, len(raw), step):
            mono += raw[off:off + SAMPLE_WIDTH]
        raw = bytes(mono)

    before_peak = peak_dbfs(raw)
    info = {"arquivo": src.name, "antes_db": round(before_peak, 1), "duracao_s": round(frames / rate, 1)}

    if do_gate:
        g = gate(raw, threshold_db=threshold_db, sample_rate=rate)
        raw = g.out
        info["gate_cortou_pct"] = round(g.pct_closed(), 1)
        info["gate_eventos"] = g.events

    if do_norm:
        raw, gain_db = normalize(raw, target_db=target_db, mode=mode)
        info["normalizou_db"] = round(gain_db, 1)

    info["depois_db"] = round(peak_dbfs(raw), 1)

    dest = Path(out_path) if out_path else src.with_name(f"{src.stem}-processado.wav")
    if dest == src:
        raise ValueError("Recusando sobrescrever o original; use um nome diferente.")
    out_stereo = b"".join(raw[i:i + 2] * 2 for i in range(0, len(raw), 2))
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(rate)
        w.writeframes(out_stereo)
    info["saida"] = dest.name
    return info


def describe_chain(threshold_db: float, target_db: float, mode: str) -> str:
    """Texto curto do que será feito, para a UI."""
    tipo = "pico" if mode == "pico" else "volume percebido (RMS)"
    return f"Gate em {threshold_db:.0f} dB · normaliza {tipo} para {target_db:.1f} dBFS"