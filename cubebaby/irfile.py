"""O IR de usuário do CUBE Baby: onde fica, em que formato, e como ler.

FORMATO DESCOBERTO NO HARDWARE (SINCO-CubeBaby, firmware A 2022-07-06)
---------------------------------------------------------------------
O IR de usuário vive em **memory=0**, endereço **0x69000**, com 32768 bytes.

São **8 blocos de 4096 bytes** — e cada bloco é um **BANCO independente**:

    +0   int32 LE   marcador estrutural (0 no 1º e no último, 1 nos do meio)
    +4   1023 x float32 LE   amostras

Cada bloco guarda um IR completo, não um pedaço de um. A prova: entre duas
capturas (antes e depois de importar no CubeSuite), **7 blocos ficaram byte a
byte idênticos** e só o bloco 1 mudou — o bloco do banco ativo.

  bloco 1  -> mostra o banco ATIVO (é o que o pedal está usando agora)
  blocos 2-8 -> os outros bancos, estáveis

Um IR tem **1023 amostras = 21,3 ms a 48 kHz**. É curto de propósito: o pedal
guarda a parte inicial da resposta, que é o que define o timbre.

COMO ISTO FOI CONFIRMADO
------------------------
Não por dedução. O usuário importou `6 - Brohymn-Mesa-4x12-SM57-V30-5.wav`
pelo CubeSuite e o bloco do banco ativo deu **correlação +0,89** com esse
arquivo — a maior de longe entre os 8 candidatos da pasta (o segundo deu 0,18).

O pedal guarda em 48 kHz, float32, cortado. O CubeSuite reamostra e corta o
WAV na importação.

A ESCRITA FUNCIONA — VERIFIQUE PELA FORMA
-----------------------------------------
Gravando um IR novo no bloco do banco ativo e relendo:

    correlacao com o IR NOVO  : +0,9939
    correlacao com o ORIGINAL : -0,0606

Ou seja: gravou. E restaurar o original deu +0,94 de volta.

**Mas o hash dos bytes crus NÃO serve para verificar.** O bloco ativo se move
sozinho entre leituras (é o espelho do que o pedal está processando); os
blocos inativos são estáveis. Então:

  - para verificar uma gravação, compare a **forma** (as amostras), não o hash;
  - leia **o bloco do banco**, não os 32768 bytes de uma vez.

Um erro que custou tempo: comparar o hash dos 32768 bytes fazia parecer que a
região era toda volátil e que a escrita não funcionava. Não era nada disso —
era leitura de 8 bancos colados, verificada no lugar errado.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Onde e como
# ---------------------------------------------------------------------------

IR_MEMORY = 0                 # memory=0 (não é o 5, que é o banco de presets)
IR_BASE_ADDRESS = 0x69000     # confirmado: zerado antes do import, cheio depois
IR_TOTAL_BYTES = 32768
IR_BLOCK_BYTES = 4096
IR_BLOCKS = 8                 # = 8 BANCOS independentes
IR_HEADER_BYTES = 4           # o marcador no início de cada bloco
IR_SAMPLES_PER_BLOCK = (IR_BLOCK_BYTES - IR_HEADER_BYTES) // 4   # 1023
IR_SAMPLE_RATE = 48000
IR_BLOCK_DURATION_MS = IR_SAMPLES_PER_BLOCK / IR_SAMPLE_RATE * 1000   # 21,3 ms

# Quantos blocos o pedal tem (um por banco de IR)
IR_BANCOS = IR_BLOCKS

assert IR_BLOCKS * IR_BLOCK_BYTES == IR_TOTAL_BYTES
assert IR_SAMPLES_PER_BLOCK == 1023


def endereco_do_banco(banco: int) -> int:
    """Endereço inicial do bloco de um banco (1..8)."""
    if not 1 <= banco <= IR_BANCOS:
        raise ValueError(f"banco deve ser 1..{IR_BANCOS} (veio {banco})")
    return IR_BASE_ADDRESS + (banco - 1) * IR_BLOCK_BYTES


@dataclass
class UserIR:
    """Um IR de um banco do pedal (ou pronto para gravar)."""
    samples: list[float]
    marcador: int = 0
    banco: int = 1

    # ---- informações -------------------------------------------------------
    @property
    def duracao_ms(self) -> float:
        return len(self.samples) / IR_SAMPLE_RATE * 1000

    @property
    def pico(self) -> float:
        fin = [x for x in self.samples if math.isfinite(x)]
        return max((abs(x) for x in fin), default=0.0)

    def amostras_uteis(self, limiar: float = 1e-4) -> int:
        ult = 0
        for i, x in enumerate(self.samples):
            if math.isfinite(x) and abs(x) > limiar:
                ult = i
        return ult + 1

    def esta_vazio(self) -> bool:
        return all(x == 0.0 for x in self.samples)

    def resumo(self) -> str:
        if self.esta_vazio():
            return f"banco {self.banco}: vazio"
        return (f"banco {self.banco}: {self.duracao_ms:.1f} ms · "
                f"pico {self.pico:.4f} · útil "
                f"{self.amostras_uteis() / IR_SAMPLE_RATE * 1000:.1f} ms")


# ---------------------------------------------------------------------------
# Decodificação — um BLOCO (um banco)
# ---------------------------------------------------------------------------

def decode_bloco(raw: bytes, banco: int = 1) -> UserIR:
    """4096 bytes de UM bloco -> UserIR daquele banco."""
    if len(raw) != IR_BLOCK_BYTES:
        raise ValueError(
            f"um bloco tem {IR_BLOCK_BYTES} bytes (recebi {len(raw)}). "
            f"Para ler a área inteira, use `ler_todos`."
        )
    marcador = struct.unpack("<i", raw[:IR_HEADER_BYTES])[0]
    amostras = list(struct.unpack("<1023f", raw[IR_HEADER_BYTES:]))
    return UserIR(samples=amostras, marcador=marcador, banco=banco)


def encode_bloco(ir: UserIR) -> bytes:
    """UserIR -> 4096 bytes de um bloco, para gravar num banco."""
    n = len(ir.samples)
    if n > IR_SAMPLES_PER_BLOCK:
        raise ValueError(
            f"cada banco guarda {IR_SAMPLES_PER_BLOCK} amostras "
            f"({IR_BLOCK_DURATION_MS:.1f} ms); este tem {n}. Corte antes de gravar."
        )
    amostras = list(ir.samples) + [0.0] * (IR_SAMPLES_PER_BLOCK - n)
    return struct.pack("<i", ir.marcador) + struct.pack("<1023f", *amostras)


# Compatibilidade: a área inteira (8 bancos) como bytes
def decode(raw: bytes) -> list[UserIR]:
    """32768 bytes -> lista de 8 UserIR, um por banco."""
    if len(raw) != IR_TOTAL_BYTES:
        raise ValueError(f"a área de IR tem {IR_TOTAL_BYTES} bytes (recebi {len(raw)})")
    return [decode_bloco(raw[i * IR_BLOCK_BYTES:(i + 1) * IR_BLOCK_BYTES], i + 1)
            for i in range(IR_BLOCKS)]


def encode(irs: list[UserIR]) -> bytes:
    """Lista de 8 UserIR -> 32768 bytes."""
    if len(irs) != IR_BLOCKS:
        raise ValueError(f"preciso de {IR_BLOCKS} bancos (recebi {len(irs)})")
    return b"".join(encode_bloco(ir) for ir in irs)


# ---------------------------------------------------------------------------
# WAV
# ---------------------------------------------------------------------------

def _le_wav(caminho):
    """Lê um WAV e devolve (amostras_float, taxa, canais).

    Aceita PCM 16/24/32 bits **e IEEE float 32** (formato 3), que é comum em
    IRs. O módulo `wave` do Python recusa float com 'unknown format: 3', então
    esses arquivos são lidos aqui à mão — antes eles simplesmente davam erro.
    """
    import wave
    from pathlib import Path

    p = Path(caminho)
    try:
        with wave.open(str(p)) as w:
            sr, n, ch, sw = (w.getframerate(), w.getnframes(),
                             w.getnchannels(), w.getsampwidth())
            raw = w.readframes(n)
        formato = 1                     # PCM
    except wave.Error as e:
        if "unknown format" not in str(e):
            raise
        sr, n, ch, sw, raw, formato = _le_wav_float(p)

    if formato == 3 or sw == 4 and formato == 3:
        v = list(struct.unpack(f"<{n * ch}f", raw[:n * ch * 4]))
        escala = 1.0
    elif sw == 2:
        v = list(struct.unpack(f"<{n * ch}h", raw))
        escala = 32768.0
    elif sw == 3:
        # 24 bits: leitura ASSINADA. Tratar o byte alto como magnitude dava um
        # valor 256x maior — os WAVs de 24 bits do pack mediam pico 512 em vez
        # de ~1,0, e o IR saía saturado (a normalização no fim mascarava).
        v = []
        for i in range(n * ch):
            b = raw[i * 3:i * 3 + 3]
            if len(b) < 3:
                break
            x = b[0] | (b[1] << 8) | (b[2] << 16)
            if x & 0x800000:
                x -= 0x1000000
            v.append(x)
        escala = 8388608.0
    elif sw == 4:
        v = list(struct.unpack(f"<{n * ch}i", raw))
        escala = 2147483648.0
    else:
        raise ValueError(f"WAV de {sw * 8} bits não suportado (use 16, 24 ou 32)")

    if ch > 1:
        v = v[::ch]
    return [x / escala for x in v], sr


def _le_wav_float(p):
    """Lê um WAV IEEE float32 direto do arquivo (o `wave` não aceita)."""
    d = p.read_bytes()
    if d[:4] != b"RIFF" or d[8:12] != b"WAVE":
        raise ValueError(f"'{p.name}' não é um WAV válido")
    pos, sr, ch, bits, dados = 12, 44100, 1, 32, b""
    while pos + 8 <= len(d):
        cid = d[pos:pos + 4]
        tam = int.from_bytes(d[pos + 4:pos + 8], "little")
        corpo = d[pos + 8:pos + 8 + tam]
        if cid == b"fmt ":
            tag = int.from_bytes(corpo[0:2], "little")
            ch = int.from_bytes(corpo[2:4], "little")
            sr = int.from_bytes(corpo[4:8], "little")
            bits = int.from_bytes(corpo[14:16], "little")
            if tag != 3:
                raise ValueError(f"'{p.name}': formato {tag} não suportado")
        elif cid == b"data":
            dados = corpo
            break
        pos += 8 + tam + (tam & 1)
    if not dados:
        raise ValueError(f"'{p.name}': sem bloco de dados")
    n = len(dados) // 4
    return sr, n, ch, bits // 8, dados, 3


def de_wav(caminho, normalizar: bool = True) -> UserIR:
    """Lê um WAV (PCM 16/24/32 bits ou float32) e corta para um banco.

    Reamostra para 48 kHz e corta em 1023 amostras, que é o que um banco do
    pedal guarda. É o mesmo tratamento que o CubeSuite aplica na importação.
    """
    fl, sr = _le_wav(caminho)

    if sr != IR_SAMPLE_RATE:
        passo = sr / IR_SAMPLE_RATE
        out = []
        i = 0.0
        while int(i) < len(fl):
            out.append(fl[int(i)])
            i += passo
        fl = out

    fl = fl[:IR_SAMPLES_PER_BLOCK]
    if normalizar and fl:
        pico = max(abs(x) for x in fl) or 1.0
        fl = [x / pico * 0.95 for x in fl]
    return UserIR(samples=fl)


def para_wav(ir: UserIR, caminho, taxa: int = IR_SAMPLE_RATE) -> str:
    """Grava o IR num WAV mono 16 bits (para ouvir/arquivar).

    O pedal preenche com NaN o trecho depois do fim do IR. NaN não converte
    para int: vira zero (silêncio), que é o correto — não é sinal.
    """
    import wave
    from pathlib import Path

    fin = [x for x in ir.samples if math.isfinite(x)]
    pico = max((abs(x) for x in fin), default=0.0) or 1.0
    escala = 0.98 / pico

    def amostra(x: float) -> int:
        if not math.isfinite(x):
            return 0
        return max(-32768, min(32767, int(x * escala * 32767)))

    pcm = struct.pack(f"<{len(ir.samples)}h", *[amostra(x) for x in ir.samples])
    p = Path(caminho)
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(pcm)
    return str(p)


# ---------------------------------------------------------------------------
# Acesso ao pedal
# ---------------------------------------------------------------------------

def ler_banco(pedal, banco: int = 1) -> UserIR:
    """Lê o IR de UM banco do pedal (1..8). Só leitura — nunca escreve.

    Leia por banco, não a área inteira: o bloco do banco **ativo** muda entre
    leituras (é o espelho do que o pedal processa), mas os blocos dos outros
    bancos são estáveis byte a byte. Comparar o hash dos 32768 bytes faz
    parecer que tudo é volátil — não é.

    Lê em pedaços de `MAX_READ_BYTES`: pedidos maiores que 64 bytes já
    travaram o pedal nesta investigação (uma leitura de 512 bytes o deixou
    mudo até reconectar o USB).
    """
    from .client import MAX_READ_BYTES
    import time

    base = endereco_do_banco(banco)
    buf = bytearray()
    for off in range(0, IR_BLOCK_BYTES, MAX_READ_BYTES):
        n = min(MAX_READ_BYTES, IR_BLOCK_BYTES - off)
        buf += pedal.read_memory(IR_MEMORY, base + off, n)
        time.sleep(0.012)
    return decode_bloco(bytes(buf), banco)


def ler_todos(pedal) -> list[UserIR]:
    """Lê os 8 bancos. Para verificar uma gravação, prefira `ler_banco`."""
    return [ler_banco(pedal, b) for b in range(1, IR_BANCOS + 1)]


# Nome antigo: lê o banco ativo. Mantido para não quebrar quem já chamava.
def ler(pedal, timeout: float = 2.0) -> UserIR:
    """Lê o banco 1 (o ativo, na maioria dos casos)."""
    return ler_banco(pedal, 1)


def gravar_banco(pedal, ir: UserIR, progresso=None) -> None:
    """Grava um IR no banco indicado por `ir.banco`. VALIDADO no hardware.

    Medido: gravar e reler deu **correlação +0,9939** com o IR enviado (e
    −0,06 com o anterior) — a escrita funciona.

    Escreve só o bloco daquele banco (4096 bytes), nunca a área inteira.
    """
    from .client import MAX_READ_BYTES
    import time

    dados = encode_bloco(ir)
    base = endereco_do_banco(ir.banco)
    enviados = 0
    for off in range(0, len(dados), MAX_READ_BYTES):
        n = min(MAX_READ_BYTES, len(dados) - off)
        if not pedal.write_memory(IR_MEMORY, base + off, dados[off:off + n]):
            raise RuntimeError(
                f"o pedal recusou a escrita no offset {off:#x} do banco {ir.banco}"
            )
        enviados += n
        if progresso:
            progresso(int(enviados / len(dados) * 100))
        time.sleep(0.015)


def gravar(pedal, ir: UserIR, progresso=None) -> None:
    """Grava no banco de `ir.banco`. Atalho para `gravar_banco`."""
    gravar_banco(pedal, ir, progresso)


# ---------------------------------------------------------------------------
# Comparação (para verificar um IR lido contra um WAV de origem)
# ---------------------------------------------------------------------------

def correlacao(a: list[float], b: list[float], n: int = 300) -> float:
    """Correlação de Pearson entre os primeiros n valores.

    Serve para responder 'este IR veio daquele WAV?'. O IR do pedal é o WAV
    reamostrado e cortado, então a forma bate; a escala não, por isso a
    correlação normaliza.
    """
    a, b = a[:n], b[:n]
    m = min(len(a), len(b))
    if m < 16:
        return 0.0
    a, b = a[:m], b[:m]
    ma, mb = sum(a) / m, sum(b) / m
    na = math.sqrt(sum((x - ma) ** 2 for x in a))
    nb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (na * nb)
