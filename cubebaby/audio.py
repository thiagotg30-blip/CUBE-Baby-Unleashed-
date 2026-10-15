"""Áudio: captura, monitor ao vivo, gravação e reprodução.

WASAPI é o backend (padrão no Windows). O monitor ao vivo é o que a
maioria chama de "ouvir a guitarra": você toca e ouve na hora, para
conferir o timbre do pedal antes de gravar qualquer coisa.

Atenção ao microfone: se a guitarra estiver na frente de um microfone
ligado, o monitor amplificado faz microfonia e o som satura. Com
guitarra (entrada de linha) isso não acontece.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QAudioSource, QMediaDevices

from .settings import data_dir

SAMPLE_RATE = 44100   # usado so se o dispositivo nao anunciar taxa nenhuma
CHANNELS = 1          # captura: uma guitarra, um canal

# Tamanho de bloco, em amostras. O Reaper usa 512 e mostra ~10 ms; com 48 kHz
# isso da 10,7 ms, que e a meta. Menor = menos latencia e mais risco de
# estouro (underrun) se a maquina nao aguentar.
BLOCK_SIZES = (128, 256, 512, 1024, 2048)
DEFAULT_BLOCK = 512
PEAK_CEILING = 0.98   # acima disso, consideramos clipping

# Códigos de QAudio::State (Qt 6). Fixados aqui porque ler o enum pelo PySide6
# dentro de um slot reaciona a um bug de binding do próprio PySide6.
STOPPED = 0
IDLE = 1
ACTIVE = 3
SUSPENDED = 3


def recordings_dir(base: Path | None = None) -> Path:
    d = data_dir(base) / "gravacoes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_inputs() -> list[str]:
    return [d.description() for d in QMediaDevices.audioInputs()]


def list_outputs() -> list[str]:
    return [d.description() for d in QMediaDevices.audioOutputs()]


def guess_input(devices: list[str]) -> int:
    """Escolhe a entrada de áudio, evitando sintetizadores virtuais."""
    if not devices:
        return -1
    deny = ("microsoft gs wavetable", "wavetable", "sintetizador",
            "what u hear", "cable output", "blackhole", "stereo mix")
    # 1) prefere entrada de linha/interface USB
    for i, n in enumerate(devices):
        low = n.lower()
        if any(t in low for t in ("usb", "line", "interface", "linha")) and \
                "microfone" not in low and "alto-falante" not in low:
            return i
    # 2) prefere qualquer coisa que nao seja microfone/sintetizador
    for i, n in enumerate(devices):
        if not any(t in n.lower() for t in deny) and "microfone" not in n.lower():
            return i
    return 0


def native_rate(device, fallback: int = SAMPLE_RATE) -> int:
    """Taxa nativa do dispositivo, se ela for um valor razoável.

    Usa preferredFormat() primeiro: minimumSampleRate() pode retornar
    valores muito baixos (ex: 8000 Hz) que não representam a taxa real
    de operação, causando cálculo errado de buffer e latência.
    """
    try:
        fmt = device.preferredFormat()
        if fmt is not None:
            sr = int(fmt.sampleRate())
            if sr > 0:
                return sr
    except Exception:  # noqa: BLE001
        pass
    try:
        sr = int(device.maximumSampleRate())
        if sr > 0:
            return sr
    except Exception:  # noqa: BLE001
        pass
    return fallback


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


def to_stereo(pcm_mono: bytes) -> bytes:
    """Mono -> estéreo, duplicando o canal. Um ints16 por amostra."""
    out = bytearray()
    for i in range(0, len(pcm_mono) - 1, 2):
        s = pcm_mono[i:i + 2]
        out += s + s
    return bytes(out)


def peak_of(pcm: bytes, channels: int = 1) -> float:
    """Pico de amplitude de um bloco PCM 16-bit, normalizado para 0..1.

    Usado para o VU e para detectar clipping antes de gravar.
    """
    if not pcm:
        return 0.0
    pico = 0.0
    # Amostras de 2 bytes, little-endian, com sinal
    for i in range(0, len(pcm) - 1, 2 * channels):
        v = abs(int.from_bytes(pcm[i:i + 2], "little", signed=True)) / 32768.0
        if v > pico:
            pico = v
    return pico


class Recorder(QObject):
    """Grava a entrada num WAV PCM 16-bit, em arquivo escolhido pelo usuário.

    A gravação é feita em blocos: a cada `block` amostras o arquivo é
    atualizado. Assim o usuário pode parar e o arquivo já está válido.
    """

    started = Signal()
    stopped = Signal()
    finished = Signal(str)        # caminho do WAV gravado
    failed = Signal(str)
    progress = Signal(int, int)   # frames gravados, frames esperados
    level = Signal(float)         # 0..1, o que a gravação está capturando
    elapsed = Signal(float)       # segundos gravados até agora

    def __init__(self) -> None:
        super().__init__()
        self._src = None
        self._dev = None
        self._frames: list[bytes] = []
        self._recording = False
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._flush)
        self._path: Path | None = None

    @property
    def recording(self) -> bool:
        return self._recording



    def start(self, in_index: int, path: Path, duration: float = 0.0) -> None:
        if self.recording:
            return
        devices = QMediaDevices.audioInputs()
        if not devices or not 0 <= in_index < len(devices):
            self.failed.emit("Nenhuma entrada de áudio encontrada. Plugue a interface da guitarra.")
            return
        self._path = path
        self._frames = []
        self._recording = True
        self._timer.start()
        self.started.emit()

    def _flush(self) -> None:
        """Escreve o que foi capturado até agora (a cada 100 ms)."""
        if not self._recording:
            return
        if self._dev is None:
            return
        try:
            pcm = bytes(self._dev.readAll())
        except Exception:  # noqa: BLE001
            return
        if pcm:
            self._frames.append(pcm)
            self.level.emit(peak_of(pcm))
            total = sum(len(f) for f in self._frames)
            self.elapsed.emit(total / 2.0 / SAMPLE_RATE)

    def stop(self) -> Path | None:
        if not self.recording:
            return None
        self._recording = False
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
            return None
        stereo = to_stereo(data)
        try:
            import wave
            with wave.open(str(self._path), "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(stereo)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return None
        self.stopped.emit()
        if self._path:
            self.finished.emit(str(self._path))
        return self._path


class Monitor(QObject):
    """Monitor ao vivo: o que entra na interface sai nos fones, sem gravar.

    É o que a maioria chama de "ouvir a guitarra": você toca e ouve na hora,
    para conferir o timbre do pedal antes de gravar qualquer coisa.

    Latência: entra uma cadeia WASAPI (captura -> mixagem -> saída), então
    ficam ~20-60 ms entre tocar e ouvir. Para tocar junto isso incomoda; para
    conferir timbre, não. Tocar junto de verdade só com monitor direto da
    interface, que é zero latência e não passa por programa nenhum.

    Atenção ao microfone: se a guitarra estiver na frente de um microfone
    ligado, o monitor amplificado faz microfonia e o som satura. Com guitarra
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
        # latência estimada e mudar o bloco antes de monitorar.
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
              block: int = DEFAULT_BLOCK) -> None:
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
        self._pump = self._Pump(self._dev, self._meter, on_data=self._on_data)
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
        if err and err != 0:
            self.stop()
            self.failed.emit(
                f"Não consegui abrir a saída de áudio ({err}). "
                "Ela pode estar em uso por outro programa.")

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

    def set_volume(self, v: float) -> None:
        if self._sink:
            self._sink.setVolume(max(0.0, min(1.0, v)))

    # ---- bomba: QIODevice que alimenta o sink ---------------------------------
    class _Pump(QBuffer):
        """Converte o fluxo da entrada no formato que o sink espera.

        O sink é estéreo; a entrada é mono. Este objeto lê os bytes que
        chegam da entrada, duplica o canal e devolve ao sink.
        """

        def __init__(self, dev, meter, on_data=None):
            super().__init__()
            self._dev = dev
            self._meter = meter
            # Callback chamado com uma CÓPIA do PCM capturado. Usado para
            # alimentar o afinador sem que ele precise abrir um segundo
            # QAudioSource na mesma entrada.
            self._on_data = on_data
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

            Devolve bytes e NAO limpa: quem chama e so leitura.
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
            # Nunca "fim": é um fluxo ao vivo, não um arquivo. Se dissese True
            # o sink pararia sozinho e o monitor desligaria.
            return False

    def _medir_vu(self) -> None:
        """Mede o nivel a partir do que a bomba ja separou.

        Roda na thread da GUI, nao na de audio: medir o pico ali dentro
        emitiria sinais do Qt na thread de audio e atrapalharia o som.
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


class LevelMeter(QObject):
    """Medidor de nivel: pega um bloco de áudio e devolve o pico."""

    level = Signal(float)     # 0..1
    clipped = Signal(bool)    # True quando o pico passou do teto

    def __init__(self) -> None:
        super().__init__()
        self._nivel = 0.0
        self._decaimento = 0.92

    def feed(self, pcm: bytes) -> None:
        """Atualiza o nivel a partir de um bloco de PCM estéreo 16-bit."""
        if not pcm:
            return
        # Amostras pares (canal esquerdo) bastam para o pico.
        pico = 0.0
        for i in range(0, len(pcm) - 1, 4):
            v = abs(int.from_bytes(pcm[i:i + 2], "little", signed=True)) / 32768.0
            if v > pico:
                pico = v
        # Decaimento suave: o medidor cai devagar, como um VU de verdade.
        self._nivel = max(pico, self._nivel * self._decaimento)
        self.level.emit(min(1.0, self._nivel))
        self.clipped.emit(self._nivel >= PEAK_CEILING)


class Player(QObject):
    """Reproduz um WAV pelo mesmo caminho do monitor.

    Serve para ouvir uma gravação sem sair do programa.
    """

    started = Signal()
    stopped = Signal()
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._sink = None
        self._src = None
        self._path: Path | None = None

    @property
    def playing(self) -> bool:
        return self._sink is not None

    def play(self, path: Path, out_index: int, volume: float = 0.8) -> None:
        if self.playing:
            self.stop()
        outs = QMediaDevices.audioOutputs()
        if not outs or not 0 <= out_index < len(outs):
            return
        ofmt = QAudioFormat()
        ofmt.setSampleRate(SAMPLE_RATE)
        ofmt.setChannelCount(2)
        ofmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._sink = QAudioSink(outs[out_index], ofmt, self)
        self._sink.setVolume(max(0.0, min(1.0, volume)))
        try:
            self._src = open(path, "rb")
        except Exception as e:  # noqa: BLE001
            self._sink = None
            self.failed.emit(str(e))
            return
        self._path = path
        self._sink.start(self._src)
        self.started.emit()

    def stop(self) -> None:
        if self._sink:
            try:
                self._sink.stop()
            except Exception:  # noqa: BLE001
                pass
        if self._src:
            try:
                self._src.close()
            except Exception:  # noqa: BLE001
                pass
        self._sink = None
        self._src = None


def guess_input_name() -> str:
    """Nome da entrada de áudio escolhida, para mostrar na interface."""
    try:
        devices = QMediaDevices.audioInputs()
        if devices:
            i = guess_input([d.description() for d in devices])
            return devices[i].description()
    except Exception:  # noqa: BLE001
        pass
    return ""


def seconds_label(s: float) -> str:
    """Formata segundos como MM:SS."""
    s = max(0, int(s))
    return f"{s // 60:02d}:{s % 60:02d}"
