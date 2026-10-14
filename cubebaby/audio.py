"""Captura e reprodução de áudio: ouvir e gravar a guitarra direto no programa.

Motivação: para conferir um preset do CUBE Baby não é preciso abrir o REAPER.
Com uma interface de áudio USB (qualquer Scarlett, Focusrite, Behringer, ou
até a onboard) a guitarra entra como entrada de linha e este módulo:

  - mostra o nível de entrada em tempo real (VU), para saber se a guitarra
    está clipando antes de gravar;
  - monitora o sinal ao vivo pela saída escolhida, com controle de volume
    (a latência é pequena, mas suficiente para conferir timbre);
  - grava a entrada num WAV PCM 16-bit e salva em ~/CUBEBabyUnleashed/gravacoes.

Por que QAudioSource/QAudioSink e não PyAudio/sounddevice: PySide6 já traz o
QtMultimedia, então não entra dependência nova no requirements — o mesmo
executável continua funcionando. O QtMultimedia fala WASAPI no Windows, que é
o caminho nativo e de menor latência do sistema.

Cuidado importante: gravar da entrada é mono por definição (uma guitarra). O
arquivo sai estéreo só para tocar em qualquer player; o canal direito é cópia
do esquerdo. O VU é calculado do PCM, não do Qt, para não depender do que o
backend decided PeakNormalize.
"""
from __future__ import annotations

import struct
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QObject, QTimer, Signal

from .settings import data_dir
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QAudioSource, QMediaDevices

SAMPLE_RATE = 44100   # usado so se o dispositivo nao anunciar taxa nenhuma
CHANNELS = 1          # captura: uma guitarra, um canal

# Tamanho de bloco, em amostras. O Reaper usa 512 e mostra ~10 ms; com 48 kHz
# isso da 10,7 ms, que e a meta. Menor = menos latencia e mais risco de
# estouro (underrun) se a maquina nao aguentar.
BLOCK_SIZES = (128, 256, 512, 1024, 2048)
DEFAULT_BLOCK = 512
PEAK_CEILING = 0.98   # acima disso, consideramos clipping

# Prioridade da thread de audio (espelha o Reaper).
# O Qt Multimedia nao expoe isso, entao usamos ctypes para chamar
# SetThreadPriority na thread onde o audio roda.
PRIORIDADES = {
    "normal":    ("Normal",    0),
    "alta":      ("Alta",      2),
    "critica":   ("Crítica",  15),   # THREAD_PRIORITY_TIME_CRITICAL
    "realtime":  ("Tempo real", 16),  # THREAD_PRIORITY_TIME_CRITICAL + 1
}

# Códigos de QAudio::State (Qt 6). Fixados aqui porque ler o enum pelo PySide6
# dentro de um slot reaciona a um bug de binding do próprio PySide6.
STOPPED = 0
IDLE = 1
ACTIVE = 3


def recordings_dir(base: Path | None = None) -> Path:
    d = data_dir(base) / "gravacoes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_inputs() -> list[str]:
    return [d.description() for d in QMediaDevices.audioInputs()]


def list_outputs() -> list[str]:
    return [d.description() for d in QMediaDevices.audioOutputs()]


def guess_input(devices: list[str]) -> int:
    """Heurística: prefere interface USB sobre microfone e sobre onboard."""
    hints = ("usb", "line", "interface", "scarlett", "focusrite", "behringer",
             "audio", "quaddrum")
    for i, name in enumerate(devices):
        low = name.lower()
        if any(h in low for h in hints) and "microfone" not in low and "headset" not in low:
            return i
    for i, name in enumerate(devices):
        if "microfone" not in name.lower():
            return i
    return 0 if devices else -1


def native_rate(device, fallback: int = SAMPLE_RATE) -> int:
    """A taxa que o dispositivo realmente usa, em vez de forcar 44100.

    Se a interface roda a 48 kHz e pedimos 44100, o Windows insere um
    resampler entre a placa e o programa — e o resampler segura buffer para
    poderconverter. Esse buffer extra É latencia, e nao aparece em lugar nenhum
    da interface. Usar a taxa nativa remove o stage inteiro.
    """
    try:
        pref = device.preferredFormat()
    except Exception:  # noqa: BLE001
        return fallback
    r = int(pref.sampleRate()) if pref is not None else 0
    return r if r > 0 else fallback


def block_bytes(frames: int, channels: int, sample_width: int = 2) -> int:
    """bytes de um bloco de `frames` amostras."""
    return max(64, int(frames) * int(channels) * int(sample_width))


def latency_ms(frames: int, rate: int) -> float:
    """Atraso de ida e volta de um bloco, em ms."""
    return (frames / max(1, rate)) * 1000.0


def capture_format() -> QAudioFormat:
    f = QAudioFormat()
    f.setSampleRate(SAMPLE_RATE)
    f.setChannelCount(CHANNELS)
    f.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    return f


def aplicar_prioridade(chave: str = "normal") -> None:
    """Ajusta a prioridade da thread atual (onde o áudio roda).

    O Qt Multimedia não expõe esse controle, então usamos ctypes para chamar
    SetThreadPriority. Isso espelha o "Audio Thread Priority: Time Critical"
    do Reaper — o Windows dá mais CPU para a thread de áudio, reduzindo
    dropouts e crackling.

    Chamado na thread onde o QAudioSink está rodando (a thread de áudio do Qt).
    """
    import ctypes
    if chave not in PRIORIDADES:
        chave = "normal"
    nome, valor = PRIORIDADES[chave]
    try:
        kernel32 = ctypes.windll.kernel32
        # THREAD_PRIORITY_TIME_CRITICAL = 15, THREAD_PRIORITY_HIGHEST = 2
        kernel32.SetThreadPriority(kernel32.GetCurrentThread(), valor)
    except Exception:
        pass  # se falhar, o áudio continua funcionando na prioridade normal


def to_stereo(pcm_mono: bytes) -> bytes:
    """Mono -> estéreo, duplicando o canal. Um ints16 por amostra."""
    out = bytearray()
    for i in range(0, len(pcm_mono) - 1, 2):
        out += pcm_mono[i:i + 2] * 2
    return bytes(out)


def peak_of(pcm: bytes, channels: int = CHANNELS) -> float:
    """Pico normalizado 0..1 a partir de PCM Int16."""
    if len(pcm) < 2:
        return 0.0
    count = len(pcm) // 2
    best = 0
    unpack = struct.Struct("<h")
    for i in range(0, len(pcm) - 1, 2):
        v = abs(unpack.unpack_from(pcm, i)[0])
        if v > best:
            best = v
    return min(1.0, best / 32768.0)


class LevelMeter(QObject):
    """Calcula o pico de um buffer de áudio e emite o nível, suavizado."""
    level = Signal(float)
    clipped = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._smooth = 0.0

    def feed(self, pcm: bytes) -> None:
        raw = peak_of(pcm)
        # ataque rápido, decaimento lento: parece um VU de verdade
        self._smooth = raw if raw > self._smooth else self._smooth * 0.8 + raw * 0.2
        if raw >= PEAK_CEILING:
            self.clipped.emit()
        self.level.emit(self._smooth)


class Recorder(QObject):
    """Grava a entrada num WAV. A escrita do cabeçalho acontece no stop()."""

    finished = Signal(str)      # caminho do wav
    failed = Signal(str)
    level = Signal(float)       # 0..1
    elapsed = Signal(float)      # segundos

    def __init__(self) -> None:
        super().__init__()
        self._src: QAudioSource | None = None
        self._dev: QIODevice | None = None
        self._path: Path | None = None
        self._frames: list[bytes] = []
        self._start = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._tick)
        self.recording = False

    def start(self, device_index: int) -> None:
        if self.recording:
            return
        devices = QMediaDevices.audioInputs()
        if not devices or not 0 <= device_index < len(devices):
            self.failed.emit("Nenhuma entrada de áudio encontrada. Plugue a interface da guitarra.")
            return
        fmt = capture_format()
        if not devices[device_index].isFormatSupported(fmt):
            self.failed.emit(
                f"'{devices[device_index].description()}' não aceita "
                f"{SAMPLE_RATE} Hz mono 16-bit. Escolha outra entrada."
            )
            return

        self._frames = []
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._path = recordings_dir() / f"cuba-{stamp}.wav"

        # Qt6 (e PySide6) usa o modelo PULL: start() devolve um QIODevice e nós
        # puxamos os bytes em readyRead. Não existe sinal de buffer por amostra.
        self._src = QAudioSource(devices[device_index], fmt, self)
        self._dev = self._src.start()
        if self._dev is None:
            self._src = None
            self.failed.emit("Não consegui abrir a entrada de áudio. Ela pode estar em uso por outro programa.")
            return
        self._dev.readyRead.connect(self._on_ready)
        # NÃO usamos stateChanged: o PySide6 declara o sinal como QAudio::State
        # e recusa a conversão na entrega, levantando TypeError antes do corpo do
        # slot rodar. Sondar a propriedade state() no _tick é equivalente e não
        # passa pelo binding quebrado.
        self.recording = True
        self._start = datetime.now().timestamp()
        self._timer.start()
        self._meter = LevelMeter()
        self._meter.level.connect(self.level.emit)
        self._meter.clipped.connect(lambda: None)  # a UI mostra o alerta

    def _on_ready(self) -> None:
        """Puxa tudo que chegou na entrada. Int16 mono, 2 bytes por amostra."""
        if not self.recording or self._dev is None:
            return
        pcm = bytes(self._dev.readAll())
        if not pcm:
            return
        self._frames.append(pcm)
        self._meter.feed(pcm)

    def _state_stopped(self) -> bool:
        """True se a captura foi interrompida (leitura numérica, pelo motivo
        explicado em STOPPED/IDLE)."""
        if self._src is None:
            return True
        try:
            return int(self._src.state()) == STOPPED
        except (TypeError, ValueError):
            return False

    def _tick(self) -> None:
        self.elapsed.emit(max(0.0, datetime.now().timestamp() - self._start))
        # Sondagem do estado: substitui o sinal stateChanged, quebrado no PySide6.
        if self.recording and self._state_stopped():
            self.failed.emit(
                "A entrada de áudio parou. Ela pode ter sido desconectada, "
                "ou outro programa passou a usá-la."
            )

    def stop(self) -> None:
        if not self.recording:
            return
        self.recording = False
        self._timer.stop()
        try:
            if self._src:
                self._src.stop()
        except Exception:
            pass
        self._src = None
        self._dev = None

        data = b"".join(self._frames)
        if not data or self._path is None:
            self.failed.emit("Nada foi capturado — a entrada estava muda ou no volume zero.")
            return
        stereo = to_stereo(data)
        try:
            with wave.open(str(self._path), "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(stereo)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Não consegui salvar o WAV: {exc}")
            return
        self.finished.emit(str(self._path))
        self._frames = []


class Monitor(QObject):
    """Monitor ao vivo: o que entra na interface sai nos fones, sem gravar.

    É o que a maioria chama de "ouvir a guitarra": você toca e ouve na hora,
    para conferir o timbre do pedal antes de gravar qualquer coisa.

    Latência: entra uma cadeia WASAPI (captura -> mixagem -> saída), então
    ficam ~20-60 ms entre tocar e ouvir. Para tocar junto isso incomoda; para
    conferir timbre, não. Tocar junto de verdade só com monitor direto da
    interface, que é zero latência e não passa por programa nenhum.

    Atenção ao microfone: se a guitarra estiver na frente de um microfone
    ligado, o monitor amplified faz microfonia e o som satura. Com guitarra
    (entrada de linha) isso não acontece.
    """

    started = Signal()
    stopped = Signal()
    failed = Signal(str)
    level = Signal(float)   # 0..1, do que está entrando

    def __init__(self) -> None:
        super().__init__()
        self._src = None
        self._dev = None
        self._sink = None
        self._pump = None
        # Preenchidos em start(); existem aqui para que a interface possa ler a
        # latencia estimada e mudar o bloco antes de monitorar.
        self.rate = SAMPLE_RATE
        self.block = DEFAULT_BLOCK
        self._vu_timer = None
        self._meter = LevelMeter()
        self._meter.level.connect(self.level.emit)
        self.active = False
        # Callback chamado com uma cópia do PCM capturado. O afinador usa isso
        # para não abrir um segundo QAudioSource na mesma entrada (o que
        # causava o pipoca).
        self._on_data = None

    @property
    def dev(self):
        """O QIODevice de captura, se o monitor estiver ativo."""
        return self._dev if self.active else None

    def set_on_data(self, fn) -> None:
        """Registra o callback que recebe uma cópia do PCM capturado.

        Usado pelo afinador para compartilhar a entrada com o monitor sem
        abrir um segundo QAudioSource na mesma entrada WASAPI.
        """
        self._on_data = fn

    def start(self, in_index: int, out_index: int, volume: float = 0.8,
              block: int = DEFAULT_BLOCK, prioridade: str = "normal") -> None:
        if self.active:
            return
        ins, outs = QMediaDevices.audioInputs(), QMediaDevices.audioOutputs()
        if not ins or not 0 <= in_index < len(ins):
            self.failed.emit("Nenhuma entrada de áudio encontrada. Plugue a interface da guitarra.")
            return
        if not outs or not 0 <= out_index < len(outs):
            self.failed.emit("Nenhuma saída de áudio encontrada.")
            return

        # A taxa nativa do dispositivo. Forcar 44100 numa placa de 48 kHz
        # obriga o Windows a resamplear, e o resampler enfileira buffer.
        self.rate = native_rate(ins[in_index])
        self.block = max(64, int(block))

        fmt = capture_format()
        fmt.setSampleRate(self.rate)
        if not ins[in_index].isFormatSupported(fmt):
            # Cai para 44100 se a placa nao aceitar a taxa anunciada.
            self.rate = SAMPLE_RATE
            fmt.setSampleRate(self.rate)
            if not ins[in_index].isFormatSupported(fmt):
                self.failed.emit(
                    f"'{ins[in_index].description()}' não aceita "
                    f"{self.rate} Hz mono 16-bit.")
                return

        # Saída: pedem-se 2 canais para tocar igual à maioria das interfaces.
        ofmt = QAudioFormat()
        ofmt.setSampleRate(self.rate)
        ofmt.setChannelCount(2)
        ofmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        self._src = QAudioSource(ins[in_index], fmt, self)
        # O buffer da FONTE e o da SAIDA entram na conta da latencia. Sem isto
        # o Qt usa o default (dezenas de amostras) e sobra atraso.
        self._src.setBufferSize(block_bytes(self.block, 1))
        self._dev = self._src.start()
        if self._dev is None:
            self._src = None
            self.failed.emit("Não consegui abrir a entrada de áudio para monitorar.")
            return

        self._sink = QAudioSink(outs[out_index], ofmt, self)
        if self._sink is None:
            self._src.stop(); self._src = None; self._dev = None
            self.failed.emit("Não consegui abrir a saída de áudio para monitorar.")
            return
        self._sink.setBufferSize(block_bytes(self.block, 2))
        self._sink.setVolume(max(0.0, min(1.0, volume)))

        # O VU lê da entrada; o sink consome os mesmos bytes (a cópia é feita
        # dentro do _Pump). Sem connect em stateChanged: o PySide6 recusa a
        # conversão de QAudio::State na entrega do sinal e levanta TypeError.
        self._pump = self._Pump(self._dev, self._meter, on_data=self._on_data,
                                prioridade=prioridade)
        self._sink.start(self._pump)
        # Se o sink não entrou em ActiveState, ele não vai tocar — e isso
        # aparece como OpenError no start(), não como exceção. Sem esta checagem
        # o programa fica em silêncio com o VU mexendo e nenhum aviso.
        self._check_sink()
        self.active = True
        # VU medido fora da thread de audio (ver _medir_vu).
        self._vu_timer = QTimer(self)
        self._vu_timer.timeout.connect(self._medir_vu)
        self._vu_timer.start(30)
        self.started.emit()

    def _check_sink(self) -> None:
        """Se o sink não abriu, derruba tudo e explica o motivo."""
        try:
            err = self._sink.error() if self._sink else None
        except Exception:  # noqa: BLE001
            err = None
        try:
            ok = int(self._sink.state()) == ACTIVE
        except (TypeError, ValueError, AttributeError):
            ok = self._sink is not None
        if ok:
            return
        self.stop()
        msg = (
            "Não consegui abrir a saída de áudio para monitorar.\n\n"
            "Causa comum: entrada e saída são o MESMO dispositivo de áudio. "
            "O Windows não deixa um aparelho abrir entrada e saída ao mesmo tempo.\n\n"
            "Tente: Saída = um par de fones ou alto-falante diferente do que a "
            "guitarra usa (por exemplo, fones no notebook)."
            if err is not None else
            "Não consegui abrir a saída de áudio para monitorar."
        )
        self.failed.emit(msg)

    class _Pump(QBuffer):
        """Adapta o pull da entrada para o push que o QAudioSink espera.

        O Qt6 é pull na entrada (readyRead) e push na saída (QIODevice): o
        sink pede bytes e não sabe puxar. Esta classe faz a ponte.

        Três coisas que quebram se você não souber — todas descobertas na
        máquina, com um QIODevice puro que silenciosamente não tocava nada:

        1. Precisa herdar de QBuffer (uma QIODevice concreta). Um QIODevice
           "puro" faz `sink.start()` falhar com OpenError em TODO formato e
           TODO dispositivo — o sink exige a implementação real.
        2. Precisa sobrescrever `read()`, não só `readData()`: o QAudioSink
           consome pelo QIODevice::read, e o armazenamento interno do QBuffer
           devolve vazio, então o sink nunca puxa (0 bytes, silêncio).
        3. A entrada é mono (1 canal) e o sink é estéreo. Sem converter, o
           sink lê 4 bytes por frame e casa a esquerda com a direita da
           amostra seguinte: chiado ou silêncio, dependendo do driver.
        """

        def __init__(self, dev, meter, on_data=None, prioridade="normal"):
            super().__init__()
            self._dev = dev
            self._meter = meter
            # Callback chamado com uma CÓPIA do PCM capturado. Usado para
            # alimentar o afinador sem que ele precise abrir um segundo
            # QAudioSource na mesma entrada.
            self._on_data = on_data
            # Prioridade da thread de audio. Aplicada no primeiro _drain,
            # que roda na thread do Qt Multimedia (não na thread da GUI).
            self._prioridade = prioridade
            self._prioridade_aplicada = False
            self._hold = b""
            self._primed = False
            self._stopped = False
            # Espera maxima por dados, em ms. Acima disso desiste e devolve o
            # que tem: melhor um estalo honesto do que travar a thread de audio.
            self._wait_ms = 40
            self._chegou = threading.Event()
            # Quantos vezes o sink pediu e nao havia nada. Deve ficar em 0 numa
            # maquina saudavel; se cresce, o bloco esta pequeno demais.
            self.underruns = 0
            # Quantos bytes o sink já consumiu. Serve para provar que ele está
            # realmente puxando dado (isto é, tocando) e não parado.
            self.served = 0
            dev.readyRead.connect(self._drain)
            # O open() é obrigatório: sem ele o QAudioSink.start() devolve
            # OpenError e fica em StoppedState, em silêncio. Confirmado na
            # máquina: com open() -> ActiveState; sem -> OpenError.
            self.open(QIODevice.OpenModeFlag.ReadOnly)

        def _drain(self) -> None:
            """Puxa o que chegou da entrada e converte mono -> estéreo."""
            # Aplica a prioridade na primeira chamada, que roda na thread de
            # áudio do Qt Multimedia (não na thread da GUI).
            if not self._prioridade_aplicada:
                self._prioridade_aplicada = True
                aplicar_prioridade(self._prioridade)
            try:
                pcm = bytes(self._dev.readAll())
            except Exception:  # noqa: BLE001
                return
            if not pcm:
                return
            # NAO medimos o VU aqui. _drain() roda na thread de audio, e
            # medir o pico + emitir um sinal Qt a cada buffer coloca trabalho
            # de interface no caminho critico do som. Quem mede e o LevelTimer,
            # na thread da GUI, lendo daqui com uma pitada de lock.
            self._hold += to_stereo(pcm)
            self._primed = True
            # Acorda quem esta esperando no read(): dado chegou, pode servir.
            self._chegou.set()
            # Envia uma CÓPIA para o consumidor (ex.: afinador). Ele não pode
            # fazer readAll() por conta própria — roubaria os dados do monitor.
            # A cópia é feita aqui, uma vez, na thread de audio.
            if self._on_data is not None:
                try:
                    self._on_data(bytes(pcm))
                except Exception:  # noqa: BLE001
                    pass

        def para_o_vu(self) -> bytes:
            """Ultimo trecho recebido, para o VU medir fora da thread de audio.

            devolve bytes e NAO limpa: quem chama e so leitura.
            """
            self._drain()
            return self._hold

        def bytesAvailable(self) -> int:  # noqa: N802
            self._drain()
            return len(self._hold)

        def read(self, maxSize: int) -> bytes:  # noqa: N802
            # O sink pede múltiplos do bytes-per-frame (4). Cortar no meio de
            # um frame desalinha os canais, então arredonda — mas nunca para
            # zero: um pedido menor que um frame ainda entrega um frame inteiro,
            # senão o sink recebe vazio e trava esperando.
            if maxSize > 0:
                maxSize = max(4, maxSize - maxSize % 4)
            self._drain()

            # UNDERRUN: o sink pediu e o anel estava seco. Antes devolvia vazio
            # e o driver tocava um buraco — era o "estalo". Aqui espera-se o
            # próximo readyRead por um instante curto. Sem isso, buffer pequeno
            # estala sem parar; com isso, o anel só esvazia se a maquina real
            # nao acompanhar, e ai o erro e honesto.
            # Espera so pelo que FALTA. Se ja ha parte do pedido no anel,
            # espera-la inteira atrasa o audio sem motivo.
            if len(self._hold) < maxSize:
                self._wait(maxSize)

            chunk, self._hold = self._hold[:maxSize], self._hold[maxSize:]
            # Sobra sempre em frame inteiro: meio frame no fim desalinha.
            corte = len(self._hold) - (len(self._hold) % 4)
            self._hold = self._hold[:corte]
            self.served += len(chunk)
            if chunk:
                self.underruns = 0
            else:
                self.underruns += 1
            return chunk

        def _wait(self, need: int) -> None:
            """Espera (no máximo _wait_ms) a entrada encher o necessario.

            O wait() PRECISA do lock adquirido — chamar sem levanta
            "cannot wait on un-acquired lock", e isso acontecia DENTRO da
            thread de audio do Qt, derrubando o som. Da para usar um Evento
            simples, que nao exige lock nenhum.
            """
            t0 = time.monotonic()
            while len(self._hold) < need:
                if self._stopped:
                    return
                # Espera curta e progressiva. Uma espera fixa de 2 ms
                # acrescentava latencia media de ate 2 ms POR VEZ que o
                # anel ficava abaixo do pedido — e num bloco de 512 isso
                # acontece varias vezes por buffer.
                decorrido = (time.monotonic() - t0) * 1000.0
                if decorrido >= self._wait_ms:
                    return
                self._chegou.wait(min(0.0005, max(0.0001, (self._wait_ms - decorrido) / 1000.0)))
                self._chegou.clear()
                self._drain()

        def readData(self, maxSize: int) -> bytes:  # noqa: N802
            return self.read(maxSize)

        def writeData(self, data) -> int:  # noqa: N802
            # Aberto como ReadOnly: qualquer escrita é do QBuffer interno, e
            # ignorá-la impede que ele consuma o que o sink deveria receber.
            return 0

        def atEnd(self) -> bool:  # noqa: N802
            # Nunca "fim": é um fluxo ao vivo, não um arquivo. Se dissesse True
            # o sink pararia sozinho e o monitor desligaria.
            return False

    def set_volume(self, v: float) -> None:
        if self._sink:
            self._sink.setVolume(max(0.0, min(1.0, v)))

    def _medir_vu(self) -> None:
        """Mede o nivel a partir do que a bomba ja separou.

        Roda na thread da GUI, nao na de audio: medir o pico ali dentro
        acrescentava latencia ao caminho critico do som.
        """
        if self._pump is None:
            return
        try:
            dados = self._pump.para_o_vu()
        except Exception:  # noqa: BLE001
            return
        # Le a cauda e devolve: para_o_vu() nao consome, so le.
        if dados:
            # Usa um recorte recente: o anel inteiro pode ter segundos.
            self._meter.feed(dados[-8192:])

    def estimated_latency_ms(self) -> float:
        """Atraso estimado, na MESMA convencao que o Reaper usa.

        O Reaper mostra "latency: 10 ms" para 512 amostras a 48 kHz — isto e,
        o numero dele tambem e UM bloco, nao dois. Contar entrada e saida
        daria 21 ms e nao bateria com a referencia que voce esta comparando.

        Cuidado ao ler: este e so o piso que o programa controla. O Windows
        WASAPI em modo compartilhado ainda junta o seu proprio buffer, e o Qt
        nao deixa ver quanto. Se o Reaper marca 10 ms e o programa parece
        maior, a diferenca esta no motor do Windows, nao no bloco.
        """
        return latency_ms(self.block, self.rate)

    def _on_sink_state(self, _s) -> None:
        # Só para diagnóstico: o sinal é quebrado no PySide6 e não é conectado
        # em lugar nenhum. O estado real é lido por sondagem, se necessário.
        pass

    def stop(self) -> None:
        # Acorda a espera da bomba ANTES de derrubar os objetos: se o read()
        # estiver bloqueado, derrubar o device embaixo dele deixa a thread de
        # audio presa no meio de um wait e o programa nao fecha.
        if self._pump is not None:
            self._pump._stopped = True
            self._pump._chegou.set()
        if self._vu_timer is not None:
            self._vu_timer.stop()
            self._vu_timer = None
        if not self.active:
            return
        for obj, meth in ((self._sink, "stop"), (self._src, "stop")):
            try:
                if obj is not None:
                    getattr(obj, meth)()
            except Exception:
                pass
        self._sink = self._src = self._dev = self._pump = None
        self.active = False
        self.stopped.emit()

    def underruns(self) -> int:
        """Quantas vezes o sink pediu audio e o anel estava vazio."""
        return self._pump.underruns if self._pump is not None else 0


class Player(QObject):
    """Toca um WAV mono/estéreo já gravado, com controle de volume."""

    started = Signal()
    finished = Signal()
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._sink = None
        self._dev = None
        self.playing = False
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(120)
        self._poll_timer.timeout.connect(self._poll)

    def set_volume(self, v: float) -> None:
        if self._sink:
            self._sink.setVolume(max(0.0, min(1.0, v)))

    def play(self, path: str) -> None:
        self.stop()
        p = Path(path)
        if not p.exists():
            self.failed.emit(f"Gravação não encontrada: {p.name}")
            return
        try:
            with wave.open(str(p), "rb") as w:
                ch, sw, rate, _ = (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes())
                raw = w.readframes(w.getnframes())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Não consegui ler o WAV: {exc}")
            return

        fmt = QAudioFormat()
        fmt.setSampleRate(rate)
        fmt.setChannelCount(ch)
        fmt.setSampleFormat(
            QAudioFormat.SampleFormat.Int16 if sw == 2 else QAudioFormat.SampleFormat.Float32)

        outputs = QMediaDevices.audioOutputs()
        if not outputs:
            self.failed.emit("Nenhuma saída de áudio encontrada.")
            return
        self._sink = QAudioSink(outputs[0], fmt, self)
        if self._sink is None:
            self.failed.emit("Não consegui abrir a saída de áudio.")
            return
        # Mesma razão do Recorder: stateChanged não é utilizável no PySide6,
        # então a conclusão da tocação é detectada por sonda (ver _poll).
        # QIODevice é abstrata em C++: quem carrega os bytes é o QBuffer.
        self._dev = QBuffer()
        self._dev.setData(raw)
        self._sink.start(self._dev)
        self.playing = True
        self._poll_timer.start()
        self.started.emit()

    def _poll(self) -> None:
        """Fim da tocação = o sink ficou Idle (esgotou o buffer).

        A comparação é por código numérico, não por str(enum): em PySide6
        converter o QAudio::State para str dentro de um slot reaciona ao mesmo
        bug de binding do sinal e trava o event loop.
        """
        if not self.playing or self._sink is None:
            return
        try:
            if int(self._sink.state()) == IDLE:
                self.playing = False
                self.finished.emit()
        except (TypeError, ValueError):
            # Se não der para ler o estado, cai no plano B: assume que terminou
            # quando o buffer de origem tiver sido todo consumido.
            if self._dev is not None and self._dev.atEnd():
                self.playing = False
                self.finished.emit()

    def stop(self) -> None:
        self._poll_timer.stop()
        if self._sink:
            try:
                self._sink.stop()
            except Exception:
                pass
        self._sink = None
        self._dev = None
        self.playing = False


def guess_input_name() -> str:
    """Nome de uma entrada provável, para pré-selecionar no seletor."""
    devices = QMediaDevices.audioInputs()
    if not devices:
        return ""
    return devices[guess_input(list_inputs())].description()


def seconds_label(s: float) -> str:
    s = max(0, int(s))
    return f"{s // 60:02d}:{s % 60:02d}"
