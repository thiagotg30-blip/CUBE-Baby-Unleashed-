"""Afinador: escuta a corda e diz a nota e o quanto está fora.

Como funciona, em uma frase: procura-se o período em que a onda "se repete"
(autocorrelação) e a frequência é o inverso dele.

Duas decisões que valem explicação:

**Por que autocorrelação e não FFT.** A guitarra tem harmônicos fortes — o
2º e o 3º podem ser mais altos que o fundamental. Uma FFT apontaria para o
harmônico e diria "afinado" uma oitava acima. A autocorrelação acha o período
real, então acerta a corda grave, que é justamente onde o iniciante erra.

**Por que decimar (reduzir a taxa).** Afinação de guitarra vive entre 80 e
400 Hz. Guardar 44 kHz para analisar isso é desperdício: reduz-se a ~8 kHz
somando grupos de amostras, o que também funciona como filtro passa-baixa
(tira o ruído agudo). Sem decimar, a autocorrelação em Python puro não caberia
no orçamento de uma thread de interface.

Nada aqui é específico do CUBE Baby: é a mesma matemática de qualquer afinador.
O que muda é o vocabulário, que fala a língua de quem está começando.
"""
from __future__ import annotations

import math
import struct
import threading
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

# ---------------------------------------------------------------------------
# Afinações
# ---------------------------------------------------------------------------
# As notas são declaradas por NOME e a frequência é CALCULADA. Escrever 82.41 à
# mão para cada corda de cada afinação é convite a erro de digitação — e um
# afinador que mostra a nota errada é pior que nenhum.
_NOTAS = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
          "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
          "A#": 10, "Bb": 10, "B": 11}


def freq_da_nota(nota: str) -> float:
    """Frequência de uma nota escrita como 'E2', 'F#3', 'Eb2'. A4 = 440 Hz."""
    i = 1 if len(nota) > 1 and nota[1] in "#b" else 0
    nome, oitava = nota[:i + 1], int(nota[i + 1:])
    midi = (oitava + 1) * 12 + _NOTAS[nome]
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def _cordas(notas: tuple[str, ...]) -> tuple[tuple[str, str, float], ...]:
    """(nota, rótulo da corda, freq) da mais grave para a mais aguda.

    O rótulo conta de trás para frente — a corda mais grave é a 6ª — porque é
    assim que todo guitarrista fala, mesmo em afinação aberta.
    """
    n = len(notas)
    rotulos = {6: "6ª corda (mais grave)", 5: "5ª corda", 4: "4ª corda",
               3: "3ª corda", 2: "2ª corda", 1: "1ª corda (mais aguda)"}
    out = []
    for i, nota in enumerate(notas):
        num = n - i
        out.append((nota, rotulos.get(num, f"corda {num}"), freq_da_nota(nota)))
    return tuple(out)


@dataclass(frozen=True)
class Afinacao:
    chave: str
    nome: str          # como aparece no seletor
    resumo: str        # para que serve, em uma linha
    cordas: tuple


AFINACOES: tuple[Afinacao, ...] = (
    Afinacao("padrao", "Padrão (E A D G B E)",
             "A afinação de fábrica. Se você não sabe qual usar, é esta.",
             _cordas(("E2", "A2", "D3", "G3", "B3", "E4"))),
    Afinacao("drop-d", "Drop D (D A D G B E)",
             "A 6ª corda desce para Ré: power chords com um dedo só.",
             _cordas(("D2", "A2", "D3", "G3", "B3", "E4"))),
    Afinacao("meio-tom", "Meio tom abaixo (Eb Ab Db Gb Bb Eb)",
             "Tudo meio tom abaixo. Corda mais macia e som mais grave — "
             "muito usado em blues e hard rock.",
             _cordas(("Eb2", "Ab2", "Db3", "Gb3", "Bb3", "Eb4"))),
    Afinacao("d-standard", "D Standard (D G C F A D)",
             "Tom inteiro abaixo. Pesado, mas ainda com a forma padrão.",
             _cordas(("D2", "G2", "C3", "F3", "A3", "D4"))),
    Afinacao("drop-c", "Drop C (C G C F A D)",
             "Metal moderno: grave apertado com a 6ª em Dó.",
             _cordas(("C2", "G2", "C3", "F3", "A3", "D4"))),
    Afinacao("drop-b", "Drop B (B F# B E G# C#)",
             "Grave pesado de metal. Cordas grossas são obrigatórias.",
             _cordas(("B1", "F#2", "B2", "E3", "G#3", "C#4"))),
    Afinacao("open-g", "Open G (D G D G B D)",
             "Com a guitarra solta já sai um acorde de Sol. O som do slide "
             "e do rock clássico.",
             _cordas(("D2", "G2", "D3", "G3", "B3", "D4"))),
    Afinacao("open-d", "Open D (D A D F# A D)",
             "Acorde de Ré com as cordas soltas. Slide e folk.",
             _cordas(("D2", "A2", "D3", "F#3", "A3", "D4"))),
    Afinacao("dadgad", "DADGAD",
             "Afinação celta: acordes que soam suspensos, sem terça. "
             "Muito usada em folk e fingerstyle.",
             _cordas(("D2", "A2", "D3", "G3", "A3", "D4"))),
)

POR_CHAVE = {a.chave: a for a in AFINACOES}
AFINACAO_PADRAO = "padrao"

# Compatibilidade: o resto do código e os testes usam STANDARD.
STANDARD = POR_CHAVE[AFINACAO_PADRAO].cordas

# Nomes de nota em cifra (o que aparece em qualquer música).
NOMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
NOMES_PT = ("Dó", "Dó#", "Ré", "Ré#", "Mi", "Fá", "Fá#", "Sol", "Sol#", "Lá", "Lá#", "Si")

TARGET_RATE = 8000.0     # taxa depois de decimar
MIN_HZ = 55.0            # cobre Drop B (B1 = 61,7 Hz) com folga
MAX_HZ = 420.0           # acima disso não é corda solta de guitarra
CLARITY_MIN = 0.55       # abaixo disso o sinal é ruído, não nota


def nome_da_freq(freq: float) -> tuple[str, int, float]:
    """(nome da nota, oitava, desvio em cents) para uma frequência.

    Cents: 100 cents = um semitom. ±5 cents já é audível; ±15 está claramente
    fora. É a unidade que qualquer afinador usa, então vale ensiná-la.
    """
    if freq <= 0:
        return "—", 0, 0.0
    # A4 = 440 Hz, MIDI 69. Cada semitom é um fator 2**(1/12).
    midi = 69 + 12 * math.log2(freq / 440.0)
    arred = int(round(midi))
    cents = (midi - arred) * 100.0
    nome = NOMES[arred % 12]
    oitava = arred // 12 - 1
    return nome, oitava, cents


def _fft(a: list[complex]) -> list[complex]:
    """FFT iterativa (Cooley-Tukey). n tem de ser potencia de 2.

    Implementada a mao porque o projeto nao usa numpy: puxar numpy so por causa
    do afinador somaria ~15 MB ao executavel. Esta versao faz 2048 pontos em
    ~3 ms, o que cabe folgado no timer de 120 ms.
    """
    n = len(a)
    a = list(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        wl = complex(math.cos(ang), math.sin(ang))
        half = length >> 1
        for i in range(0, n, length):
            w = complex(1.0, 0.0)
            for k in range(i, i + half):
                u = a[k]
                v = a[k + half] * w
                a[k] = u + v
                a[k + half] = u - v
                w *= wl
        length <<= 1
    return a


def _ifft(a: list[complex]) -> list[complex]:
    """Inversa, pelo truque do conjugado."""
    n = len(a)
    conj = [x.conjugate() for x in a]
    r = _fft(conj)
    return [x.conjugate() / n for x in r]


def _autocorr(buf: list[float], n_fft: int) -> list[float]:
    """Autocorrelacao por FFT: ACF = IFFT(|FFT(x)|^2).

    Direto seria O(n^2) — 2048 amostras x 660 lags = 1,3 milhao de
    multiplicacoes em Python puro, que travava a interface por segundos.
    Pela FFT fica O(n log n).
    """
    espectro = _fft([complex(x, 0.0) for x in buf] + [complex(0.0, 0.0)] * (n_fft - len(buf)))
    potencia = [abs(c) ** 2 for c in espectro]
    acf = _ifft(potencia)
    return [c.real for c in acf]


def detectar(pcm: bytes, rate: float, decimar: int = 6) -> tuple[float, float]:
    """(frequência em Hz, clareza 0..1) do buffer PCM Int16 mono.

    Devolve (0.0, 0.0) quando não há nota — silêncio, ruído ou acorde.
    """
    n_amostras = len(pcm) // 2
    if n_amostras < 512:
        return 0.0, 0.0
    amostras = struct.unpack("<%dh" % n_amostras, pcm[:n_amostras * 2])

    # Decima: media de grupos -> menos amostras E menos ruido agudo.
    if decimar > 1:
        buf = []
        for i in range(0, n_amostras - decimar, decimar):
            buf.append(sum(amostras[i:i + decimar]) / decimar)
        amostras = buf
        rate = rate / decimar
    if len(amostras) < 256:
        return 0.0, 0.0

    # Janela de 2048 amostras @8k = 256 ms (uns 20 ciclos de Mi grave).
    janela = list(amostras[-2048:]) if len(amostras) > 2048 else list(amostras)
    if len(janela) < 256:
        return 0.0, 0.0

    # Tira a media (DC): a autocorrelacao nao pode carregar offset.
    media = sum(janela) / len(janela)
    janela = [x - media for x in janela]
    if sum(x * x for x in janela) < 1.0:      # silencio
        return 0.0, 0.0

    # Aplica janela de Hann: sem ela, o corte abrupto nas bordas cria um pico
    # falso em lags grandes (vazamento espectral).
    n = len(janela)
    janela = [janela[i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)))
              for i in range(n)]

    n_fft = 1
    while n_fft < 2 * n:
        n_fft <<= 1
    acf = _autocorr(janela, n_fft)

    lag_min = max(2, int(rate / MAX_HZ))
    lag_max = min(n // 2, int(rate / MIN_HZ))
    if lag_max <= lag_min or lag_max >= len(acf):
        return 0.0, 0.0

    # Normalizacao tipo NSDF: divide pela energia das duas metades somadas.
    # Sem isto, o valor da autocorrelacao cai com o lag e todo pico distante
    # parece fraco.
    def norm(lag: int) -> float:
        m = acf[lag]
        e1 = sum(x * x for x in janela[:n - lag])
        e2 = sum(x * x for x in janela[lag:n])
        d = math.sqrt(e1 * e2)
        return (m / d) if d > 1e-9 else 0.0

    valores = {lag: norm(lag) for lag in range(lag_min, lag_max + 1)}
    if not valores:
        return 0.0, 0.0
    pico_global = max(valores.values())
    if pico_global < CLARITY_MIN:
        return 0.0, 0.0

    # O PONTO CRITICO: nao basta o pico global. O periodo DOBRADO tambem
    # correlaciona alto, e pegar o global lia D3 (146 Hz) como D2 (73 Hz).
    # O metodo correto aceita o PRIMEIRO pico que chegue perto do global.
    limiar = pico_global * 0.88
    melhor_lag = 0
    lags = sorted(valores)
    k = 0
    while k < len(lags):
        lag = lags[k]
        # sobe ate um pico local
        while k + 1 < len(lags) and valores[lags[k + 1]] > valores[lag]:
            k += 1
            lag = lags[k]
        if valores[lag] >= limiar:
            melhor_lag = lag
            break
        # desce ate cruzar zero e tenta o proximo lobe
        while k < len(lags) and valores[lags[k]] > 0:
            k += 1
        k += 1
    if melhor_lag == 0:
        melhor_lag = max(valores, key=valores.get)

    def corr(lag: int) -> float:
        return valores.get(lag, 0.0)

    # Refina com parabola nos tres pontos do pico: sem isso o erro fica em
    # ~1/8 de semitom, o que ja e' audivel.
    y0, y1, y2 = corr(melhor_lag - 1), corr(melhor_lag), corr(melhor_lag + 1)
    denom = (y0 - 2 * y1 + y2)
    ajuste = (y0 - y2) / (2 * denom) if abs(denom) > 1e-9 else 0.0
    lag_fino = melhor_lag + max(-0.5, min(0.5, ajuste))

    freq = rate / lag_fino if lag_fino > 0 else 0.0
    if not (MIN_HZ <= freq <= MAX_HZ):
        return 0.0, 0.0
    return freq, pico_global


@dataclass
class Leitura:
    freq: float = 0.0
    nota: str = "—"
    oitava: int = 0
    cents: float = 0.0
    clarity: float = 0.0
    corda: str = ""          # "6ª corda" quando bate com uma corda solta
    alvo: str = ""           # a nota-alvo escrita na afinação escolhida (Eb2)
    afinacao: str = ""       # nome da afinação em uso

    @property
    def afinado(self) -> bool:
        return self.freq > 0 and abs(self.cents) <= 5.0

    @property
    def texto(self) -> str:
        if self.freq <= 0:
            return "—"
        sinal = "+" if self.cents >= 0 else ""
        return f"{self.nota}{self.oitava}  {sinal}{self.cents:.0f} cents"


def mesma_nota(a: str, b: str) -> bool:
    """Duas notas escritas de forma diferente mas iguais no som.

    Eb2 e D#2 são a MESMA corda. Sem isto, o afinador em meio-tom abaixo
    mostrava a nota certa e dizia que estava errada — porque comparava o
    texto, e o motor sempre escreve com sustenido.
    """
    if a == b:
        return True
    try:
        return abs(freq_da_nota(a) - freq_da_nota(b)) < 0.5
    except (KeyError, ValueError, IndexError):
        return False


def nome_da_corda(cordas, freq: float) -> str:
    """A nota da afinação escolhida que corresponde a esta frequência.

    Devolve a escrita do USUÁRIO (Eb, não D#) — é a que ele vê no seletor.
    """
    if freq <= 0:
        return ""
    for nome, _rot, alvo in cordas:
        if abs(1200 * math.log2(freq / alvo)) < 60:   # dentro de meio tom
            return nome
    return ""


def corda_mais_proxima(freq: float, cordas=None) -> str:
    """Qual corda solta está mais perto — o atalho que o iniciante precisa."""
    if freq <= 0:
        return ""
    melhor, dist = "", 1e9
    for _nome, rotulo, alvo in (cordas or STANDARD):
        d = abs(1200 * math.log2(freq / alvo))
        if d < dist:
            dist, melhor = d, rotulo
    return melhor if dist < 300 else ""


class Tuner(QObject):
    """Escuta a entrada e emite leituras de afinação.

    Abre a PRÓPRIA entrada de áudio: assim o afinador não depende do monitor
    estar ligado, e desligar um não derruba o outro.
    """

    leitura = Signal(object)      # Leitura
    failed = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._src = None
        self._dev = None
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._timer = QTimer(self)
        self._timer.setInterval(120)     # ~8 leituras/s: rápido sem piscar
        self._timer.timeout.connect(self._analisar)
        self.rate = 0.0
        self.active = False
        self.afinacao = AFINACAO_PADRAO
        # True quando os dados vêm do Monitor (não abrimos um segundo
        # QAudioSource). Nesse caso o stop() não pode parar o src do Monitor.
        self._compartilhada = False

    def definir_afinacao(self, chave: str) -> None:
        if chave in POR_CHAVE:
            self.afinacao = chave

    @property
    def cordas(self):
        return POR_CHAVE[self.afinacao].cordas

    # ---- ciclo de vida ---------------------------------------------------
    def start(self, device_index: int, compartilhada=None) -> None:
        """Liga o afinador.

        `compartilhada` é o QIODevice de um Monitor já aberto. Passar o device
        do Monitor é importante: abrir DOIS QAudioSource na mesma entrada
        WASAPI faz o Windows dividir o buffer entre os dois consumidores, e
        um deles fica mal alimentado — era o "pipoca" do afinador com ouvir
        ao vivo. Compartilhando, os dois leem o mesmo fluxo e o som é limpo.
        """
        from .audio import capture_format, native_rate
        from PySide6.QtMultimedia import QAudioSource, QMediaDevices

        if self.active:
            return

        # Caminho preferido: o Monitor já abriu a entrada. O afinador NÃO
        # conecta no readyRead desse device — se o fizesse, o readAll() dele
        # roubaria os dados do Monitor (os dois slots rodam no mesmo sinal,
        # quem chega primeiro leva o resto). Em vez disso, o Monitor chama
        # alimentar() com uma CÓPIA do que capturou.
        if compartilhada is not None:
            self._src = None
            self._dev = None
            self._compartilhada = True
            self.rate = 48000
            try:
                self.rate = int(getattr(compartilhada, "rate", 48000))
            except Exception:  # noqa: BLE001
                pass
            self._buf = bytearray()
            self.active = True
            self._timer.start()
            self.started.emit()
            return

        # Caminho próprio: abrir o QAudioSource (afinador sozinho).
        devices = QMediaDevices.audioInputs()
        if not devices or not 0 <= device_index < len(devices):
            self.failed.emit("Nenhuma entrada de áudio encontrada. "
                             "Plugue a interface da guitarra.")
            return
        self.rate = native_rate(devices[device_index])
        fmt = capture_format()
        fmt.setSampleRate(self.rate)
        if not devices[device_index].isFormatSupported(fmt):
            self.rate = 44100
            fmt.setSampleRate(self.rate)
            if not devices[device_index].isFormatSupported(fmt):
                self.failed.emit(f"'{devices[device_index].description()}' "
                                 f"não aceita {self.rate} Hz mono 16-bit.")
                return

        self._buf = bytearray()
        self._src = QAudioSource(devices[device_index], fmt, self)
        self._src.setBufferSize(int(self.rate * 0.05) * 2)   # 50 ms
        self._dev = self._src.start()
        if self._dev is None:
            self._src = None
            self.failed.emit("Não consegui abrir a entrada para afinar. "
                             "Ela pode estar em uso por outro programa.")
            return
        self._dev.readyRead.connect(self._on_ready)
        self.active = True
        self._timer.start()
        self.started.emit()

    def _on_ready(self) -> None:
        """Slot do readyRead — só usado quando o afinador abre o próprio device.

        No caminho compartilhado este slot NÃO é conectado: o Monitor chama
        alimentar() com uma cópia. Se fosse conectado aqui, o readAll() do
        afinador roubaria os dados do Monitor (os dois slots rodam no mesmo
        sinal e quem chega primeiro leva o resto) — era o crackling.
        """
        if not self.active or self._dev is None:
            return
        try:
            pcm = bytes(self._dev.readAll())
        except Exception:  # noqa: BLE001
            return
        if not pcm:
            return
        # Guarda só o que interessa: ~2 s. Mais que isso é memória parada.
        with self._lock:
            self._buf += pcm
            limite = int(self.rate * 2)
            if len(self._buf) > limite:
                del self._buf[:len(self._buf) - limite]

    def _analisar(self) -> None:
        with self._lock:
            dados = bytes(self._buf)
        if not dados:
            self.leitura.emit(Leitura())
            return
        freq, clareza = detectar(dados, self.rate)
        if freq <= 0:
            self.leitura.emit(Leitura(clarity=clareza))
            return
        nome, oitava, cents = nome_da_freq(freq)
        cordas = self.cordas
        af = POR_CHAVE[self.afinacao]
        # Mostra a escrita da AFINAÇÃO (Eb) e não a do motor (D#): o usuário
        # escolheu "meio tom abaixo", então é Eb que ele espera ler.
        alvo = nome_da_corda(cordas, freq) or f"{nome}{oitava}"
        self.leitura.emit(Leitura(freq=freq, nota=nome, oitava=oitava,
                                  cents=cents, clarity=clareza,
                                  corda=corda_mais_proxima(freq, cordas),
                                  alvo=alvo, afinacao=af.nome))

    def alimentar(self, pcm) -> None:
        """Recebe uma CÓPIA do PCM capturado pelo Monitor.

        O afinador compartilha o device do Monitor, então não pode fazer
        readAll() por conta própria — roubaria os dados do monitor. O
        Monitor chama este método com uma cópia do que capturou.
        """
        if not self.active or not pcm:
            return
        with self._lock:
            self._buf += pcm
            limite = int(self.rate * 2)
            if len(self._buf) > limite:
                del self._buf[:len(self._buf) - limite]

    def stop(self) -> None:
        self._timer.stop()
        if not self.active:
            return
        # No caminho compartilhado, o src pertence ao Monitor — não o pare.
        if self._src is not None:
            try:
                self._src.stop()
            except Exception:  # noqa: BLE001
                pass
        self._src = self._dev = None
        self._compartilhada = False
        self.active = False
        self.stopped.emit()

# ---------------------------------------------------------------------------
# O mostrador: agulha, nota grande e as seis cordas
# ---------------------------------------------------------------------------

from PySide6.QtCore import QPointF, QRectF, Qt          # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,  # noqa: E402
                           QPen, QRadialGradient)
from PySide6.QtWidgets import QWidget                    # noqa: E402

FUNDO = QColor("#191819")
COR_OK = QColor("#5cc98c")       # afinado
COR_PERTO = QColor("#e8b84b")    # quase
COR_LONGE = QColor("#e05a5a")    # fora
COR_NEUTRO = QColor("#8f8b83")

# Faixa mostrada na agulha: +-50 cents. Um semitom e 100, entao mostrar 50 de
# cada lado ja cobre "meio caminho ate a nota vizinha" — mais que isso confunde.
FAIXA_CENTS = 50.0


class TunerGauge(QWidget):
    """Agulha de afinacao, com a nota grande e as seis cordas.

    Mostra em cents, nao em Hz: o iniciante nao sabe que 82.4 Hz e o Mi grave,
    mas entende "esta 20 cents baixo, aperte a corda".
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(230)
        self._leitura = Leitura()
        self._suavizada = 0.0    # cents com suavizacao, para a agulha nao tremer
        self._cordas = STANDARD

    def definir_cordas(self, cordas) -> None:
        self._cordas = cordas
        self.update()

    def atualizar(self, leitura: Leitura) -> None:
        # Suaviza a agulha: sem isso ela pula a cada leitura e fica ilegivel.
        # Ataque rapido, retorno lento — igual a um VU.
        if leitura.freq > 0:
            if self._leitura.freq <= 0:
                self._suavizada = leitura.cents
            else:
                self._suavizada = self._suavizada * 0.6 + leitura.cents * 0.4
        else:
            self._suavizada *= 0.5
        self._leitura = leitura
        self.update()

    def _cor(self) -> QColor:
        l = self._leitura
        if l.freq <= 0:
            return COR_NEUTRO
        d = abs(l.cents)
        if d <= 5:
            return COR_OK
        if d <= 15:
            return COR_PERTO
        return COR_LONGE

    def paintEvent(self, e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, FUNDO)
        l = self._leitura
        cor = self._cor()

        # ---- geometria ----
        # Convencao: 0 graus = 12 horas (para cima), positivo = para a direita.
        #   x = cx + sin(0) * r   y = cy - cos(0) * r
        # A versao anterior somava -90 graus a mais e a agulha apontava para
        # baixo-esquerda com o arco desenhado na metade de baixo da tela.
        cx, cy = w / 2.0, h * 0.66
        raio = min(w * 0.32, h * 0.52)

        def ponto(cents: float, r: float) -> QPointF:
            """Posicao no arco para um desvio em cents."""
            th = math.radians(max(-1.0, min(1.0, cents / FAIXA_CENTS)) * 90.0)
            return QPointF(cx + math.sin(th) * r, cy - math.cos(th) * r)

        # arco: metade de CIMA. No Qt o angulo cresce anti-horario a partir das
        # 3 horas, entao 0 -> +180 graus desenha exatamente o semicirculo de cima.
        p.setPen(QPen(QColor("#2a2a30"), 9, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - raio, cy - raio, raio * 2, raio * 2),
                  0, int(180 * 16))

        # faixa verde central (zona afinada, +-5 cents)
        p.setPen(QPen(QColor(92, 201, 140, 120), 9, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        a0 = 90.0 - 5 / FAIXA_CENTS * 90.0     # angulo Qt do -5 cents
        a1 = 90.0 + 5 / FAIXA_CENTS * 90.0
        p.drawArc(QRectF(cx - raio, cy - raio, raio * 2, raio * 2),
                  int(a0 * 16), int((a1 - a0) * 16))

        # marcas: verde no centro, ambar aos 15, vermelho nas pontas
        for cents_marca, c in ((0, COR_OK), (-15, COR_PERTO), (15, COR_PERTO),
                               (-FAIXA_CENTS, COR_LONGE), (FAIXA_CENTS, COR_LONGE)):
            pt0 = ponto(cents_marca, raio - 8)
            pt1 = ponto(cents_marca, raio + 7)
            p.setPen(QPen(c, 2))
            p.drawLine(pt0, pt1)

        # ---- agulha ----
        if l.freq > 0:
            cents = max(-FAIXA_CENTS, min(FAIXA_CENTS, self._suavizada))
            px, py = ponto(cents, raio - 14).x(), ponto(cents, raio - 14).y()
            # halo
            halo = QRadialGradient(QPointF(px, py), 14)
            halo.setColorAt(0.0, QColor(cor.red(), cor.green(), cor.blue(), 120))
            halo.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(halo)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px, py), 14, 14)
            p.setPen(QPen(cor, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx, cy), QPointF(px, py))
        # eixo
        p.setBrush(QColor("#2a2a30")); p.setPen(QPen(QColor("#0d0d0f"), 1))
        p.drawEllipse(QPointF(cx, cy), 6, 6)

        # ---- nota grande no centro ----
        p.setPen(cor if l.freq > 0 else COR_NEUTRO)
        f = QFont(); f.setPointSize(30); f.setBold(True)
        p.setFont(f)
        texto = (l.alvo or f"{l.nota}{l.oitava}") if l.freq > 0 else "—"
        p.drawText(QRectF(0, cy - raio * 0.52, w, 44),
                   Qt.AlignmentFlag.AlignCenter, texto)

        # ---- cents / instrucao ----
        if l.freq > 0:
            if abs(l.cents) <= 5:
                msg, c2 = "AFINADO", COR_OK
            elif l.cents < 0:
                msg, c2 = "ESTICANDO A CORDA", COR_PERTO
            else:
                msg, c2 = "AFROUXANDO A CORDA", COR_PERTO
            if abs(l.cents) > 15:
                c2 = COR_LONGE
            p.setPen(c2)
            f2 = QFont(); f2.setPointSize(11); f2.setBold(True)
            p.setFont(f2)
            sinal = "+" if l.cents >= 0 else ""
            p.drawText(QRectF(0, cy - raio * 0.10, w, 20), Qt.AlignmentFlag.AlignCenter,
                       f"{sinal}{l.cents:.0f} cents")
            f3 = QFont(); f3.setPointSize(9)
            p.setFont(f3)
            p.setPen(QColor("#a5a199"))
            p.drawText(QRectF(0, cy - raio * 0.10 + 20, w, 18), Qt.AlignmentFlag.AlignCenter, msg)
            if l.corda:
                p.drawText(QRectF(0, cy - raio * 0.10 + 38, w, 18),
                           Qt.AlignmentFlag.AlignCenter, f"mais perto da {l.corda}")
        else:
            p.setPen(QColor("#8f8b83"))
            f2 = QFont(); f2.setPointSize(10)
            p.setFont(f2)
            p.drawText(QRectF(0, cy - raio * 0.10, w, 20),
                       Qt.AlignmentFlag.AlignCenter, "Toque uma corda solta e deixe soar")

        # ---- as seis cordas ----
        y = h - 26
        cordas = self._cordas or STANDARD
        n = len(cordas)
        largura = min(w - 40, 420)
        x0 = (w - largura) / 2
        passo = largura / (n - 1) if n > 1 else 0
        for i, (nome, _rot, alvo) in enumerate(cordas):
            x = x0 + i * passo
            # qual esta mais perto?
            perto = l.freq > 0 and l.corda == _rot
            ativo = perto
            p.setBrush(cor if ativo else QColor("#2a2a30"))
            p.setPen(QPen(cor if ativo else QColor("#43434b"), 1.2))
            p.drawEllipse(QPointF(x, y), 5 if ativo else 4, 5 if ativo else 4)
            p.setPen(cor if ativo else QColor("#6f6b64"))
            f4 = QFont(); f4.setPointSize(8); f4.setBold(ativo)
            p.setFont(f4)
            p.drawText(QRectF(x - 22, y + 8, 44, 14), Qt.AlignmentFlag.AlignCenter, nome)
        p.end()


class TunerPanel(QWidget):
    """A aba do afinador: botao, mostrador e a explicacao para iniciante."""

    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.tuner = Tuner()
        from . import i18n as I18N
        self.tuner.leitura.connect(self._on_leitura)
        self.tuner.failed.connect(self._on_falha)
        self.tuner.started.connect(self._on_ligado)
        self.tuner.stopped.connect(self._on_desligado)

        from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton,
                                       QVBoxLayout)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        topo = QHBoxLayout()
        titulo = QLabel(I18N.tr("aba_afinador", I18N.get_idioma()))
        titulo.setStyleSheet("font-size:19px; font-weight:700; color:#f0812a;")
        topo.addWidget(titulo)
        topo.addSpacing(14)

        # ---- seletor de afinacao ----
        # Fica SEMPRE visivel, mesmo desligado: a escolha muda o alvo das
        # cordas, entao o usuario precisa vê-la antes de tocar.
        from PySide6.QtWidgets import QComboBox
        topo.addWidget(QLabel(I18N.tr("afinacao", I18N.get_idioma())))
        self.cb_afinacao = QComboBox()
        self.cb_afinacao.setMinimumWidth(250)
        for a in AFINACOES:
            self.cb_afinacao.addItem(a.nome, a.chave)
        self.cb_afinacao.setToolTip("Qual afinação a guitarra está. "
                                    "Muda as notas que o mostrador espera.")
        self.cb_afinacao.currentIndexChanged.connect(self._trocar_afinacao)
        topo.addWidget(self.cb_afinacao)
        self.lbl_resumo = QLabel("")
        self.lbl_resumo.setObjectName("sig")
        topo.addWidget(self.lbl_resumo, 1)

        self.btn = QPushButton(I18N.tr("ligar_afinador", I18N.get_idioma()))
        self.btn.setObjectName("primary")
        self.btn.setCheckable(True)
        self.btn.setMinimumWidth(190)
        self.btn.clicked.connect(self._toggle)
        topo.addWidget(self.btn)
        root.addLayout(topo)

        self.gauge = TunerGauge()
        root.addWidget(self.gauge, 1)

        dica = QLabel(
            "Toque UMA corda solta e deixe soar — não abafe com a mão. "
            "A agulha vai para a esquerda se a corda está frouxa (aperte) e "
            "para a direita se está esticada (afrouxe). No centro, está afinado.")
        dica.setWordWrap(True)
        dica.setObjectName("sig")
        root.addWidget(dica)

        self.lbl_estado = QLabel(I18N.tr("desligado", I18N.get_idioma()))
        self.lbl_estado.setObjectName("muted")
        root.addWidget(self.lbl_estado)

        # restaura a afinação que o usuário escolheu da última vez
        chave = AFINACAO_PADRAO
        try:
            chave = (self.win.settings.get("afinacao") or AFINACAO_PADRAO)
        except Exception:  # noqa: BLE001
            pass
        if chave not in POR_CHAVE:
            chave = AFINACAO_PADRAO
        self.cb_afinacao.setCurrentIndex(
            [a.chave for a in AFINACOES].index(chave))
        self._aplicar_afinacao(chave)

    def _trocar_afinacao(self) -> None:
        chave = self.cb_afinacao.currentData()
        self._aplicar_afinacao(chave)
        try:
            self.win.settings.set("afinacao", chave)
            self.win.settings.save()
        except Exception:  # noqa: BLE001
            pass

    def _aplicar_afinacao(self, chave: str) -> None:
        """Muda o alvo das cordas no motor e no mostrador."""
        af = POR_CHAVE.get(chave, POR_CHAVE[AFINACAO_PADRAO])
        self.tuner.definir_afinacao(af.chave)
        self.gauge.definir_cordas(af.cordas)
        self.lbl_resumo.setText(af.resumo)
        self.lbl_resumo.setToolTip(af.resumo)
        # a leitura atual deixa de valer: a corda que era a 6ª pode não ser
        self.gauge.atualizar(Leitura())

    @property
    def monitor(self):
        """O Monitor da aba Áudio, se já estiver ligado."""
        return getattr(self, "_monitor", None)

    @monitor.setter
    def monitor(self, m) -> None:
        """Registra/remove o afinador como consumidor do Monitor.

        Quando o Monitor captura um bloco, ele chama `tuner.alimentar()` com
        uma cópia. Assim o afinador não precisa abrir um segundo QAudioSource
        na mesma entrada — o que causava o pipoca.
        """
        if getattr(self, "_monitor", None) is m:
            return
        if getattr(self, "_monitor", None) is not None:
            try:
                self._monitor.set_on_data(None)
            except Exception:  # noqa: BLE001
                pass
        self._monitor = m
        if m is not None:
            m.set_on_data(self.tuner.alimentar)

    def _toggle(self, on: bool) -> None:
        if on:
            # Se o Monitor já está ligado, o afinador usa o device que ele
            # já abriu. Abrir um segundo QAudioSource na mesma entrada WASAPI
            # fazia o Windows dividir o buffer entre os dois consumidores —
            # e o som pipocava.
            compartilhada = None
            try:
                if self.monitor is not None and self.monitor.active:
                    compartilhada = self.monitor.dev
            except Exception:  # noqa: BLE001
                compartilhada = None
            idx = 0
            try:
                idx = self.win.audio_tab.cb_in.currentIndex()
            except Exception:  # noqa: BLE001
                pass
            self.tuner.start(idx, compartilhada=compartilhada)
            if not self.tuner.active:
                self.btn.setChecked(False)
        else:
            self.tuner.stop()

    def _on_ligado(self) -> None:
        self.btn.setText(I18N.tr("desligar_afinador", I18N.get_idioma()))
        self.lbl_estado.setText(
            f"Ouvindo a entrada ({self.tuner.rate / 1000:.0f} kHz). "
            "Toque uma corda solta.")

    def _on_desligado(self) -> None:
        self.btn.setText("▶ Ligar o afinador")
        self.lbl_estado.setText("Desligado.")
        self.gauge.atualizar(Leitura())

    def _on_falha(self, msg: str) -> None:
        self.btn.setChecked(False)
        self.btn.setText("▶ Ligar o afinador")
        self.lbl_estado.setText(msg)

    def _on_leitura(self, leitura: Leitura) -> None:
        self.gauge.atualizar(leitura)

    def close_all(self) -> None:
        # Remove o afinador como consumidor do Monitor para não deixar
        # callback pendente quando a janela fecha.
        self.monitor = None
        self.tuner.stop()
