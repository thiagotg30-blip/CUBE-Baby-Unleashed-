"""Os 9_IR_CAB do CUBE Baby: qual gabinete é cada número, e como fazer um parecido.

O pedal tem 9 posições no botão IR CAB: a primeira desliga a simulação, e as
outras 8 são caixas reais. O que é qual **depende do firmware**, e existem duas
listas diferentes em circulação — o manual antigo (M-VAVE) e o novo (CUVAVE).
Elas não são a mesma coisa na mesma ordem.

  M-VAVE (firmware antigo) — caixas vintage, com Fender no topo
  CUVAVE (firmware novo)   — caixas de high gain, 5150, Diezel, VHT

Como descobrir qual é o seu: os presets de fábrica contam. O preset B da
CUVAVE usa "Soldano 2×12 V30" e o preset C usa "Marshall 1960A T75"; na lista
antiga o Soldano é a posição 7 e na nova é a 6. Confira qual delle bate com
o preset que você reconhece.

A diferença não é besteira: 2×12 vintage e 4×12 de high gain soam em mundos
diferentes. Escolher a lista errada faz o preset inteiro soar errado, e o
usuário não tem como saber que o culpado foi o número.

Sobre os IRs: os de fábrica estão na ROM do pedal (0x71000, segundo a
documentação do cuvave-midi). Copiá-los exigiria implementar a leitura de IR via
SysEx, que é a mesma família de operação que escreve na flash — o item que o
README deixa de fora de propósito. `make_ir` aqui gera uma aproximação
SINTETIZADA, útil para experimentar e como ponto de partida, não é o IR de
fábrica e não substitui um capture medido.
"""
from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 44100
N_POSITIONS = 9          # 0 = bypass, 1..8 = gabinetes


@dataclass(frozen=True)
class Cabinet:
    pos: int              # valor do parâmetro (0..8)
    name: str             # como aparece na interface
    short: str            # nome curto, para a lista
    spec: str             # "4x12", "1x10"...
    character: str        # como soa, em uma frase
    # Parâmetros de síntese (usados por make_ir)
    low_hz: float         # corte de graves
    high_hz: float        # corte de agudos
    presence_hz: float    # pico de presença
    presence_db: float    # ganho desse pico
    low_mid_db: float     # corpo (200-800 Hz)
    decay_ms: float       # decaimento do reverb curto da caixa
    resonance_hz: float   # ressonância do woofer
    resonance_db: float


BYPASS = Cabinet(0, "Desligado (bypass)", "Desligado", "—",
                 "Sem simulação de caixa: o som vai direto, cru.", 20, 20000, 3000, 0, 0, 0, 40, 0)

# ---------------------------------------------------------------- M-VAVE -----
# Fonte: manual do CUBE BABY (versão M-VAVE) e a tabela do SCRIBD do produto.
M_VAVE = (
    BYPASS,
    Cabinet(1, "Fender Pro Princeton 1×12", "Princeton 1×12", "1×12",
            "Caixa pequena de Fender, som médio e macio. O fundo do twang limpo.",
            95, 5200, 2400, 3.0, 4.0, 26, 110, 2.0),
    Cabinet(2, "Fender Pro Princeton II 1×12", "Princeton II 1×12", "1×12",
            "A Princeton II, um pouco mais brilhante e presente que a I.",
            100, 5600, 2600, 3.5, 4.5, 24, 115, 2.5),
    Cabinet(3, "Fender Pro Junior 1×10", "Junior 1×10", "1×10",
            "Um 10 polegadas: mais grave e punch, o som do rockabilly.",
            85, 4200, 2100, 4.0, 6.0, 32, 95, 3.5),
    Cabinet(4, "GH Dual Rectifier 4×12", "Dual Rectifier 4×12", "4×12",
            "Quatro Speaker Greenback, som grande e com sustain. O classicão do rock.",
            92, 6000, 2800, 3.0, 5.0, 38, 105, 2.0),
    Cabinet(5, "Line 6 Vetta 1×10", "Vetta 1×10", "1×10",
            "Um 10 com voicing moderno: mais brilho e definição que as Fender.",
            88, 6500, 3200, 4.0, 4.0, 30, 100, 2.5),
    Cabinet(6, "Soldano 2×12", "Soldano 2×12", "2×12",
            "Duas 12 V30: grave firme e highs cantantes. O som do high gain.",
            90, 7200, 3400, 5.0, 5.0, 34, 108, 2.5),
    Cabinet(7, "Recabinet Mesa Boogie 4×12", "Mesa Standard 4×12", "4×12",
            "Recabinet Mesa: as quatro 12 V30 com o conjunto do Mesa. Som alto e fino.",
            95, 7800, 3800, 5.5, 3.5, 36, 112, 2.0),
    Cabinet(8, "Marshall 1960A & B 2×12", "Marshall 1960 2×12", "2×12",
            "Duas 12 Greenback: o som mais famoso do rock clásico.",
            90, 6000, 2900, 3.5, 5.5, 36, 106, 2.0),
)

# ----------------------------------------------------------------- CUVAVE ----
# Fonte: manual atual (ManualsLib) e o mesmo manual no SCRIBD. Reposiciona as
# caixas: some as Fender, entram as de high gain.
CUVAVE = (
    BYPASS,
    Cabinet(1, "Line 6 Vetta 2×12", "Vetta 2×12", "2×12",
            "Duas 12 com voicing moderno: brilho e definição.",
            90, 6800, 3300, 4.5, 4.5, 32, 102, 2.5),
    Cabinet(2, "Marshall 1960AV 4×12", "Marshall 1960AV 4×12", "4×12",
            "Quatro V30 com bright cap: presença agressiva, corte firme.",
            95, 8200, 4000, 6.0, 4.0, 36, 112, 2.0),
    Cabinet(3, "Marshall 1960A T75 LA610 4×12", "Marshall 1960A 4×12", "4×12",
            "Quatro T75 com greenback: o som redondo do rock clássico.",
            90, 6200, 2900, 3.5, 5.5, 38, 106, 2.0),
    Cabinet(4, "VHT Deliverance 2×12", "VHT Deliverance 2×12", "2×12",
            "Duas 12 de alta potência: som grosso, com sustain.",
            88, 7000, 3100, 4.5, 5.5, 34, 106, 2.5),
    Cabinet(5, "Soldano 2×12", "Soldano 2×12", "2×12",
            "Duas 12 V30: grave firme e highs cantantes.",
            90, 7200, 3400, 5.0, 5.0, 34, 108, 2.5),
    Cabinet(6, "Peavey 5150 + Mesa Oversized 4×12", "Peavey 5150 4×12", "4×12",
            "5150 com Oversized: som de metal dos anos 90, agressivo.",
            92, 8500, 4200, 6.5, 4.0, 34, 115, 2.0),
    Cabinet(7, "JSX KT77 + Mesa Stiletto AKG C1000 4×12", "JSX KT77 4×12", "4×12",
            "KT77 com Stiletto: som gráfico, quase valvulado.",
            92, 8000, 3900, 6.0, 4.5, 34, 113, 2.0),
    Cabinet(8, "Diezel V30 SM57 (Soldano HR) 4×12", "Diezel V30 4×12", "4×12",
            "V30 com microfone de borda: presença aberta, o som do crunch tungido.",
            90, 7600, 3600, 5.0, 5.0, 32, 110, 2.0),
)

FIRMWARES = {
    "cuvave": {"label": "CUVAVE (firmware novo)", "cabs": CUVAVE},
    "mvave": {"label": "M-VAVE (firmware antigo)", "cabs": M_VAVE},
}
DEFAULT_FIRMWARE = "cuvave"


def get(firmware: str = DEFAULT_FIRMWARE, pos: int = 0) -> Cabinet:
    table = FIRMWARES.get(firmware, FIRMWARES[DEFAULT_FIRMWARE])["cabs"]
    return table[max(0, min(N_POSITIONS - 1, int(pos)))]


def label(firmware: str = DEFAULT_FIRMWARE, pos: int = 0) -> str:
    c = get(firmware, pos)
    return "Desligado (bypass)" if c.pos == 0 else f"{c.pos} · {c.name}"


def short_label(firmware: str = DEFAULT_FIRMWARE, pos: int = 0) -> str:
    c = get(firmware, pos)
    return "Bypass" if c.pos == 0 else f"{c.pos} · {c.short} ({c.spec})"


def all_labels(firmware: str = DEFAULT_FIRMWARE) -> list[str]:
    return [short_label(firmware, i) for i in range(N_POSITIONS)]


# ---------------------------------------------------------------------------
# Geração de IR: aproximação SINTETIZADA, não o IR de fábrica
# ---------------------------------------------------------------------------

def _rbj(f0: float, Q: float = 0.707):
    """cos(w0) e alpha de um biquad RBJ (valores comuns a todos os tipos)."""
    w0 = 2.0 * math.pi * f0 / SAMPLE_RATE
    return math.cos(w0), math.sin(w0) / (2.0 * Q)


def _norm(b, a):
    """Divide os dois vetores por a[0].

    Obrigatório: a equação difference que _apply usa assume a[0] == 1.
    Sem normalizar, o passa-alta de 90 Hz fica numericamente instável e o IR
    explode (medido: pico de 7e67 em vez de ~0.9).
    """
    a0 = a[0]
    return [x / a0 for x in b], [x / a0 for x in a]


def _lowpass(f0: float, Q: float = 0.707):
    cos, alpha = _rbj(f0, Q)
    return _norm([(1 - cos) / 2, (1 - cos), (1 - cos) / 2],
                 [1 + alpha, -2 * cos, 1 - alpha])


def _highpass(f0: float, Q: float = 0.707):
    cos, alpha = _rbj(f0, Q)
    return _norm([(1 + cos) / 2, -(1 + cos), (1 + cos) / 2],
                 [1 + alpha, -2 * cos, 1 - alpha])


def _peaking(f0: float, gain_db: float, Q: float = 1.0):
    cos, alpha = _rbj(f0, Q)
    A = 10.0 ** (gain_db / 40.0)
    return _norm([1 + alpha * A, -2 * cos, 1 - alpha * A],
                 [1 + alpha / A, -2 * cos, 1 - alpha / A])


def _apply(x, coef):
    b, a = coef
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(x):
        yi = b[0] * xi + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        y[i] = yi
        x2, x1 = x1, xi
        y2, y1 = y1, yi
    return y


def make_ir(cab: Cabinet, length_ms: float = 180.0,
            seed: int = 0) -> bytes:
    """Sintetiza uma resposta de impulso para a caixa. PCM Int16 mono.

    O modelo é uma cadeia: impulso -> filtro passa-baixa -> passa-alta ->
    realces de presença e corpo -> ressonância do woofer -> decaimento. Não é
    uma medição; é uma aproximação com a resposta em frequência e a cauda
      cauda certas para o tipo de caixa.
    """
    n = int(SAMPLE_RATE * length_ms / 1000.0)
    if n < 8:
        n = 8
    # impulso: o "estalo" inicial, com um pouco de ruído (dentro da fase)
    imp = [0.0] * n
    imp[0] = 1.0
    # cauda: expoente, começa já no começo (o cone responde rápido)
    tau = max(1e-4, (cab.decay_ms / 1000.0) * 0.4)
    for i in range(1, n):
        env = math.exp(-(i / SAMPLE_RATE) / tau)
        # "ruído" determinístico (mesma seed = mesmo IR)
        r = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
        r -= math.floor(r)
        imp[i] += (r - 0.5) * 0.25 * env

    # resposta em frequência
    y = _apply(imp, _lowpass(cab.high_hz))
    y = _apply(y, _highpass(cab.low_hz))
    if cab.presence_db:
        y = _apply(y, _peaking(cab.presence_hz, cab.presence_db, 1.2))
    if cab.low_mid_db:
        y = _apply(y, _peaking(300.0, cab.low_mid_db, 0.9))
    if cab.resonance_db:
        y = _apply(y, _peaking(cab.resonance_hz, cab.resonance_db, 2.5))

    # normaliza
    peak = max(1e-9, max(abs(v) for v in y))
    scale = 0.89 / peak
    out = bytearray()
    for v in y:
        s = int(max(-32768, min(32767, v * scale * 32767)))
        out += struct.pack("<h", s)
    return bytes(out)


def save_ir(path: str | Path, cab: Cabinet, **kw) -> Path:
    """Grava o IR sintetizado num WAV estéreo (o que o CubeSuite espera)."""
    pcm = make_ir(cab, **kw)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    stereo = b"".join(pcm[i:i + 2] * 2 for i in range(0, len(pcm), 2))
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(stereo)
    return p


def ir_dir() -> Path:
    from .settings import data_dir
    d = data_dir() / "IRs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_all_irs(firmware: str = DEFAULT_FIRMWARE, dir: str | Path | None = None) -> list[Path]:
    """Gera os 8 IRs (o bypass não tem IR) e devolve os caminhos."""
    target = Path(dir) if dir else ir_dir()
    target.mkdir(parents=True, exist_ok=True)
    out = []
    for cab in FIRMWARES.get(firmware, FIRMWARES[DEFAULT_FIRMWARE])["cabs"]:
        if cab.pos == 0:
            continue
        nome = f"{cab.pos}-{cab.short.replace(' ', '_').replace('/', '-')}.wav"
        out.append(save_ir(target / nome, cab))
    return out