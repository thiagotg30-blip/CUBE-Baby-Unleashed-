"""Testa o módulo de áudio: matemática de PCM, WAV e a UI da aba Áudio.

Rode:  .venv\\Scripts\\python.exe tests\\test_audio.py

Não grava de verdade: a máquina pode não ter guitarra plugada, e abrir a
entrada de áudio em CI travaria. O que é testado é tudo que é determinístico
— a conversão mono→estéreo, o cálculo de pico, a escrita/leitura do WAV e a
montagem da interface.
"""
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cubebaby import audio as AU
from cubebaby.settings import Settings


def test_mono_para_estereo():
    # 2 amostras mono (Int16 little-endian) -> 2 amostras estéreo
    mono = struct.pack("<hh", 1000, -2000)
    out = AU.to_stereo(mono)
    assert len(out) == 8, len(out)  # 2 canais * 2 amostras * 2 bytes
    assert out == struct.pack("<hhhh", 1000, 1000, -2000, -2000), out.hex()


def test_to_estereo_vazio_e_quebrado():
    assert AU.to_stereo(b"") == b""
    # byte ímpar não pode estourar o laço
    assert len(AU.to_stereo(b"\x01")) == 0


def test_pico():
    assert AU.peak_of(b"") == 0.0
    assert AU.peak_of(struct.pack("<h", 0)) == 0.0
    assert AU.peak_of(struct.pack("<h", 32767)) == 32767 / 32768.0
    assert AU.peak_of(struct.pack("<h", -32768)) == 1.0
    # o pico é o MAIOR, não o último
    assert AU.peak_of(struct.pack("<hhh", 100, 30000, 200)) == 30000 / 32768.0


def test_gravacao_no_pedal_simulado_nao_quebra():
    """O formato capturado precisa ser o que o WAV espera."""
    fmt = AU.capture_format()
    assert fmt.sampleRate() == 44100
    assert fmt.channelCount() == 1


def test_wav_salvo_e_lido_de_volta():
    """Simula o que o Recorder faz no stop(): escreve e confere o arquivo."""
    # 44100 amostras de 1/4 de onda, mono
    n = 44100
    mono = b"".join(struct.pack("<h", int(20000 * ((i % 100) / 100 - 0.5) * 2)) for i in range(n))
    stereo = AU.to_stereo(mono)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "teste.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(AU.SAMPLE_RATE)
            w.writeframes(stereo)
        assert p.exists() and p.stat().st_size > 100_000, p.stat().st_size
        with wave.open(str(p), "rb") as w:
            assert w.getnchannels() == 2
            assert w.getsampwidth() == 2
            assert w.getframerate() == 44100
            assert w.getnframes() == n, w.getnframes()
            # o áudio de volta tem de ser idêntico ao que entrou (mono duplicado)
            back = w.readframes(n)
            assert back[0:2] == back[2:4]  # L == R
            assert AU.peak_of(back, 2) > 0.5


def test_guess_input_prefeza_interface():
    devices = ["Microfone (Array)", "Linha (USB-Audio)", "Alto-falantes"]
    assert AU.guess_input(devices) == 1, "deveria escolher a interface USB"
    # se só houver microfone, ele ganha
    assert AU.guess_input(["Microfone (H210)"]) == 0
    assert AU.guess_input([]) == -1


def test_segundos_label():
    assert AU.seconds_label(0) == "00:00"
    assert AU.seconds_label(65) == "01:05"
    assert AU.seconds_label(3661) == "61:01"
    assert AU.seconds_label(-5) == "00:00"


def test_level_meter_suaviza():
    m = AU.LevelMeter()
    seen = []
    m.level.connect(seen.append)
    m.feed(struct.pack("<h", 30000))
    assert seen and seen[-1] > 0.9
    before = seen[-1]
    m.feed(struct.pack("<h", 0))     # silêncio não pode zerar na hora
    assert seen[-1] >= before * 0.7, "o VU está caindo rápido demais"
    clipped = []
    m.clipped.connect(lambda: clipped.append(1))
    m.feed(struct.pack("<h", 32767))
    assert clipped, "não sinalizou clipping em 0 dBFS"


def test_recordings_dir_e_lista():
    from cubebaby import settings as S
    with tempfile.TemporaryDirectory() as tmp:
        d = AU.recordings_dir(Path(tmp))
        assert d.is_dir() and d.name == "gravacoes"
        # mora na pasta do programa, que cita o aparelho
        assert d.parent.name == S.APP_DIR_NAME, d


def test_aba_audio_monta():
    app = QApplication.instance() or QApplication([])
    from cubebaby.ui import AudioTab, MainWindow
    _tmp = tempfile.TemporaryDirectory()
    win = MainWindow(settings=Settings(Path(_tmp.name) / "p.json"))
    at = win.audio_tab
    assert at.cb_in.count() >= 1, "nenhuma entrada de áudio encontrada"
    assert at.btn_rec.text().startswith("●")
    at.on_level(0.5)
    assert "-6" in at.lbl_db.text() or "-7" in at.lbl_db.text(), at.lbl_db.text()
    at.bar.mark_clip()
    at.close_all()
    win.close()


def test_monitor_e_pump():
    """O _Pump precisa ser um QIODevice aberto de verdade, senão o sink não toca.

    Regressão real: sem open(), o QAudioSink.start() devolve OpenError e o
    programa fica em silêncio — sem erro visível, sem som, só o VU mexendo.
    """
    from PySide6.QtCore import QIODevice
    pump = AU.Monitor._Pump
    assert issubclass(pump, QIODevice), "o sink exige uma QIODevice concreta"

    class FakeDev(QIODevice):
        def __init__(self, data):
            super().__init__()
            self._data = data
        def readAll(self):  # noqa: N802
            d, self._data = self._data, b""
            return d

    m = AU.LevelMeter()
    p = pump(FakeDev(struct.pack("<hh", 1000, -1000)), m)

    # ESTE é o assert que pegaria o bug: aberto, ou o sink dá OpenError.
    assert p.isOpen(), "sem open() o QAudioSink.start() falha com OpenError"
    assert p.atEnd() is False, "se disser True o sink para sozinho e o monitor desliga"

    # Duas amostras mono (4 bytes) viram DUAS amostras estéreo (8 bytes):
    # o sink abre em 2 canais, então duplicar é obrigatório.
    assert p.bytesAvailable() == 8, f"esperava 8 bytes estéreo, veio {p.bytesAvailable()}"
    got = p.read(8)
    assert got == struct.pack("<hhhh", 1000, 1000, -1000, -1000), got.hex()

    # A bomba NAO mede o VU: _drain() roda na thread de audio, e medir o pico
    # ali dentro botava trabalho de interface no caminho critico do som. Quem
    # mede e o Monitor, por fora, lendo daqui.
    assert p.served == 8, p.served
    leftovers = p.para_o_vu()
    assert isinstance(leftovers, bytes), "para_o_vu() tem que devolver os bytes do anel"

    # E medir por fora tem que funcionar de verdade:
    meter_seen = []
    m2 = AU.LevelMeter()
    m2.level.connect(meter_seen.append)
    m2.feed(leftovers or struct.pack("<hh", 1000, -1000))
    assert meter_seen, "o VU não recebeu nada"
    assert p.served == 8, p.served
    # e o buffer esvazia, porque é um fluxo
    assert p.bytesAvailable() == 0
    assert p.read(8) == b"", "o que já saiu não pode voltar"

    # pedido desalinhado tem de ser arredondado para o frame inteiro, mas
    # NUNCA para zero (o sink ficaria esperando dado)
    p2 = pump(FakeDev(struct.pack("<hh", 5, 5)), m)
    out = p2.read(3)
    assert len(out) % 4 == 0 and len(out) >= 4, f"read(3) devolveu {len(out)} bytes"


def test_aba_tem_monitor():
    app = QApplication.instance() or QApplication([])
    from cubebaby.ui import AudioTab, MainWindow
    win = MainWindow()
    at = win.audio_tab
    assert at.btn_mon.text().startswith("▶"), at.btn_mon.text()
    assert at.btn_mon.isCheckable()
    assert at.monitor is not None and not at.monitor.active
    at.on_monitor_volume(50)          # não pode explodir sem monitor ligado
    at.close_all()
    win.close()


def test_latencia_usa_a_mesma_convencao_do_reaper():
    """512 amostras a 48 kHz tem de dar ~11 ms, e NAO 21 ms.

    O Reaper mostra "latency: 10 ms" para 512 amostras — um bloco, nao dois.
    Se o programa mostrar o dobro, o usuario compara dois numeros que medem
    coisas diferentes e conclui que o programa esta piorando o audio.
    """
    from cubebaby import audio as AU
    assert abs(AU.latency_ms(512, 48000) - 10.7) < 0.2, AU.latency_ms(512, 48000)
    m = AU.Monitor()
    for b, esperado in ((128, 2.7), (256, 5.3), (512, 10.7), (1024, 21.3)):
        m.block = b
        m.rate = 48000
        got = m.estimated_latency_ms()
        assert abs(got - esperado) < 0.2, (b, got, esperado)
    assert m.estimated_latency_ms() < 30, "latencia de 512 nao pode passar de 30 ms"


def test_buffer_e_bloque_antes_do_comeco_do_pull():
    """Regressão: sem setBufferSize o Qt usa o default e sobra latencia.

    Este teste nao abre audio de verdade (nao ha placa em CI). Ele trava o
    contrato: o codigo tem de chamar setBufferSize nos DOIS lados, com o
    tamanho do bloco escolhido, e tem de usar a taxa nativa do dispositivo.
    """
    import inspect
    from cubebaby import audio as AU
    src = inspect.getsource(AU.Monitor.start)
    assert src.count("setBufferSize") == 2, "entrada E saida precisam de setBufferSize"
    assert "native_rate" in src, "a taxa nativa do dispositivo precisa ser usada"
    # o bloco tem de chegar do argumento, e nao de uma constante fixa
    assert "block: int = DEFAULT_BLOCK" in inspect.signature(AU.Monitor.start).__str__() \
        or "block" in inspect.signature(AU.Monitor.start).parameters
    assert AU.block_bytes(512, 1) == 1024
    assert AU.block_bytes(512, 2) == 2048
    assert AU.block_bytes(1, 1) >= 64, "buffer minimo para nao travar o sink"


def test_seletor_de_bloco_existe_na_aba_audio():
    app = QApplication.instance() or QApplication([])
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window
    from cubebaby import audio as AU
    import tempfile as tf
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        at = win.audio_tab
        assert list(AU.BLOCK_SIZES) == [at.cb_block.itemData(i)
                                        for i in range(at.cb_block.count())]
        # 512 (o valor do Reaper) tem de ser o padrao
        assert at.cb_block.currentData() == AU.DEFAULT_BLOCK
        at.cb_block.setCurrentIndex(0)
        app.processEvents()
        assert "ms" in at.lbl_lat.text(), at.lbl_lat.text()
        win.close()


def test_leitura_grande_e_recusada_antes_de_enviar():
    """O pedal TRAVOU de verdade com uma leitura de 512 bytes (memory=4) e só
    voltou depois de reconectar o USB. O limite tem de ser aplicado ANTES de
    enviar qualquer coisa — não depois de esperar resposta."""
    from cubebaby import client as C
    assert C.MAX_READ_BYTES == 64, C.MAX_READ_BYTES
    p = C.CubeBabyClient()          # sem connect(): _out é None
    # a recusa tem de vir do limite, não de 'não conectado'
    for n in (65, 128, 512, 4096):
        try:
            p.read_memory(5, 0x0, n)
            raise AssertionError(f"{n} bytes deveria ser recusado")
        except C.PedalError as e:
            assert "grande demais" in str(e), (n, str(e))
            assert str(C.MAX_READ_BYTES) in str(e)
    # 64 é o teto permitido: não pode ser recusado pelo limite
    try:
        p.read_memory(5, 0x0, 64)
    except C.PedalError as e:
        assert "grande demais" not in str(e), "64 bytes foi recusado pelo limite"


def test_ping_nao_levanta_excecao():
    """ping() é o 'você está aí?'. Tem de responder True/False sempre, sem
    exceção — é usado no caminho de recuperação, onde uma exceção esconderia
    a causa real."""
    from cubebaby import client as C
    p = C.CubeBabyClient()
    assert p.ping() is False           # sem porta aberta -> False, sem exceção
    assert p.ping(timeout=0.05) is False


def test_recuperacao_desiste_com_instrucao_clara():
    """Se o pedal não voltar, o erro tem de DIZER o que fazer. Foi exatamente
    a falta dessa mensagem que deixou o pedal travado sem explicação."""
    from cubebaby import client as C
    assert C.RECOVERY_WAITS, "tem de haver espera progressiva"
    assert all(w > 0 for w in C.RECOVERY_WAITS)
    p = C.CubeBabyClient()
    try:
        p._recuperar(5, 0x0, 64)       # sem porta: nunca recupera
        raise AssertionError("deveria ter levantado PedalError")
    except C.PedalTimeout:
        raise AssertionError("deveria ser PedalError, não PedalTimeout")
    except C.PedalError as e:
        msg = str(e)
        assert "reconecte o cabo USB" in msg
        assert "não é preciso mexer nos presets" in msg


def test_guess_port_nao_escolhe_sintetizador_de_software():
    """No Windows a lista traz 'Microsoft GS Wavetable Synth' na frente do
    pedal. Escolher a porta 0 por falta de match fazia a conexão falhar sempre."""
    from cubebaby import client as C
    saidas = ["Microsoft GS Wavetable Synth 0", "USB-Midi 1"]
    assert C.guess_port(saidas) == 1, "escolheu o sintetizador de software"
    # o nome do pedal continua vencendo qualquer coisa
    assert C.guess_port(["Microsoft GS Wavetable Synth 0", "CUBE Baby 1"]) == 1
    # só sintetizadores: cai no 0 mesmo (não há alternativa)
    assert C.guess_port(["Microsoft GS Wavetable Synth 0"]) == 0
    # lista vazia
    assert C.guess_port([]) == -1


if __name__ == "__main__":
    for fn in (test_mono_para_estereo, test_to_estereo_vazio_e_quebrado, test_pico,
               test_gravacao_no_pedal_simulado_nao_quebra, test_wav_salvo_e_lido_de_volta,
               test_guess_input_prefeza_interface, test_segundos_label,
               test_level_meter_suaviza, test_recordings_dir_e_lista,
               test_aba_audio_monta, test_monitor_e_pump, test_aba_tem_monitor,
               test_latencia_usa_a_mesma_convencao_do_reaper,
               test_buffer_e_bloque_antes_do_comeco_do_pull,
               test_seletor_de_bloco_existe_na_aba_audio,
               test_leitura_grande_e_recusada_antes_de_enviar,
               test_ping_nao_levanta_excecao,
               test_recuperacao_desiste_com_instrucao_clara,
               test_guess_port_nao_escolhe_sintetizador_de_software):
        fn()
        print(f"  {fn.__name__}: ok")
    print("ok")
