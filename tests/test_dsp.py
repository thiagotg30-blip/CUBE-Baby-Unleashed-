"""Testa o DSP: gate de ruído e normalização.

Rode:  .venv\\Scripts\\python.exe tests\\test_dsp.py
"""
import math
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubebaby import dsp as DSP


def make_take(sr=44100, notes=((0.2, 1.0), (1.6, 2.4)), amp=12000, noise=120, dur=3.0):
    """Duas notas com zumbido de fundo, para o gate ter o que cortar."""
    n = int(sr * dur)
    out = bytearray()
    for i in range(n):
        t = i / sr
        on = any(a <= t < b for a, b in notes)
        v = (amp * math.sin(2 * math.pi * 440 * t) if on else 0)
        v += noise * math.sin(2 * math.pi * 60 * t)      # zumbido ~-49 dBFS
        out += struct.pack("<h", int(max(-32768, min(32767, v))))
    return bytes(out)


def test_db_e_conversoes():
    assert abs(DSP.db_to_lin(0.0) - 1.0) < 1e-9
    assert abs(DSP.db_to_lin(-6.0) - 0.5012) < 1e-3
    assert abs(DSP.lin_to_db(1.0)) < 1e-9
    assert DSP.lin_to_db(0.0) == -120.0
    # pico de -6 dBFS
    v = int(32768 * DSP.db_to_lin(-6.0))
    assert abs(DSP.peak_dbfs(struct.pack("<h", v)) + 6.0) < 0.2


def test_gate_corta_o_silencio():
    pcm = make_take()
    g = DSP.gate(pcm, threshold_db=-40)
    assert g.total_ms > 2500, g.total_ms
    assert g.events == 2, f"deveria abrir 2 vezes (2 notas), abriu {g.events}"
    assert g.pct_closed() > 25, f"cortou só {g.pct_closed():.1f}%"
    # o que sobrou é mais forte que o original: o zumbido de fundo foi junto
    assert DSP.peak_dbfs(g.out) >= DSP.peak_dbfs(pcm)


def test_gate_respeita_silencio_e_entradas_curtas():
    assert DSP.gate(b"\x00" * 40000).pct_closed() == 100.0
    # entrada curta demais não pode estourar
    curto = struct.pack("<h", 100) * 10
    assert DSP.gate(curto).out == curto


def test_gate_mais_agressivo_corta_mais():
    pcm = make_take()
    suave = DSP.gate(pcm, threshold_db=-55)
    forte = DSP.gate(pcm, threshold_db=-25)
    assert forte.pct_closed() >= suave.pct_closed(), (forte.pct_closed(), suave.pct_closed())


def test_normalize_pico():
    pcm = make_take(amp=6000)
    out, gain = DSP.normalize(pcm, target_db=-1.0)
    assert gain > 0
    assert abs(DSP.peak_dbfs(out) - (-1.0)) < 0.3, DSP.peak_dbfs(out)


def test_normalize_rms_respeita_o_limite_de_pico():
    """Regressão: no modo RMS o pico estourava em 0 dBFS (clipping)."""
    pcm = make_take(amp=20000)
    out, gain = DSP.normalize(pcm, target_db=-1.0, mode="rms")
    peak = DSP.peak_dbfs(out)
    assert peak <= -0.4, f"pico estourou: {peak:.1f} dBFS"
    # e o ganho alinhou o rms perto do alvo
    assert DSP.rms_dbfs(out) <= -1.0


def test_normalize_nao_amplifica_silencio():
    out, gain = DSP.normalize(b"\x00" * 8000, target_db=0.0)
    assert gain == 0.0, gain
    assert out == b"\x00" * 8000


def test_process_file_gera_copia_e_preserva_original():
    pcm = make_take()
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "take.wav"
        with wave.open(str(src), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
            w.writeframes(b"".join(pcm[i:i + 2] * 2 for i in range(0, len(pcm), 2)))
        antes = src.read_bytes()

        info = DSP.process_file(src, do_gate=True, do_norm=True, target_db=-1.0)
        assert src.read_bytes() == antes, "o original foi alterado!"
        dest = src.with_name(f"{src.stem}-processado.wav")
        assert dest.exists(), "não gerou a cópia"
        assert info["saida"] == dest.name
        assert info["depois_db"] <= -0.4
        assert "gate_cortou_pct" in info
        # o arquivo gerado é estéreo como o original
        with wave.open(str(dest), "rb") as w:
            assert w.getnchannels() == 2 and w.getframerate() == 44100


def test_process_file_recusa_sobrescrever():
    pcm = make_take(dur=1.0)
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "a.wav"
        with wave.open(str(src), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
            w.writeframes(b"".join(pcm[i:i + 2] * 2 for i in range(0, len(pcm), 2)))
        try:
            DSP.process_file(src, out_path=src)
        except ValueError:
            pass
        else:
            raise AssertionError("deveria recusar sobrescrever o original")


if __name__ == "__main__":
    for fn in (test_db_e_conversoes, test_gate_corta_o_silencio, test_gate_respeita_silencio_e_entradas_curtas,
               test_gate_mais_agressivo_corta_mais, test_normalize_pico,
               test_normalize_rms_respeita_o_limite_de_pico, test_normalize_nao_amplifica_silencio,
               test_process_file_gera_copia_e_preserva_original, test_process_file_recusa_sobrescrever):
        fn()
        print(f"  {fn.__name__}: ok")
    print("ok")