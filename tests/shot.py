"""Gera screenshots da UI em PNG, para conferir o visual sem abrir a janela.
Rode:  .venv\\Scripts\\python.exe tests\\shot.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cubebaby.ui import HelpDialog, build_window
from cubebaby.about import AboutDialog
from cubebaby.onboarding import GuitarPickerDialog, WelcomeDialog

OUT = os.environ.get("SHOT_DIR", r"C:\Users\ntende\Desktop\cubebaby-studio\shots")

# build_window() aplica o MESMO tema do programa real. Antes este script criava
# um QApplication cru e a janela saia com as cores do Qt, não as do programa —
# foi o que fez os screenshots divergirem da tela de verdade.
#
# Settings em pasta TEMPORARIA: sem isso o script abre com a preferencia real
# do usuario e a sobrescreve ao fechar (tamanho de janela, aba, guitarra).
import tempfile
from pathlib import Path
from cubebaby.settings import Settings

_TMP = tempfile.TemporaryDirectory()
app, win = build_window(Settings(Path(_TMP.name) / "p.json"))
win.resize(1180, 720)
app.processEvents()

os.makedirs(OUT, exist_ok=True)

# 1) aba do pedal com um preset REAL carregado.
# Com tudo zerado os sliders ficam sem preenchimento e a captura não mostra a
# paleta de verdade — que era exatamente o que enganava na revisão visual.
from cubebaby import presets_lib as PL

win.tabs.setCurrentIndex(1)
win.presets_tab.ed_search.setText("grunge")
win.presets_tab.load_selected()
win.tabs.setCurrentIndex(0)
app.processEvents()

# modo iniciante (padrao)
win.pedal_tab.sw_modo.setChecked(False)
app.processEvents()
win.grab().save(os.path.join(OUT, "1-pedal.png"))

# modo avancado: os 13 controles
win.pedal_tab.sw_modo.setChecked(True)
app.processEvents()
win.grab().save(os.path.join(OUT, "1b-pedal-avancado.png"))
win.pedal_tab.sw_modo.setChecked(False)
app.processEvents()

# 1b) a janela de dicas, na aba de roteiro
dlg = HelpDialog(win)
dlg.resize(660, 680)
dlg.tabs.setCurrentIndex(0)
dlg.show()
app.processEvents()
dlg.grab().save(os.path.join(OUT, "5-dicas.png"))
dlg.tabs.setCurrentIndex(1)
app.processEvents()
dlg.grab().save(os.path.join(OUT, "6-dicas-controles.png"))
dlg.close()

# 2) aba de presets curados, com o detalhe visível
win.tabs.setCurrentIndex(1)
win.presets_tab.ed_search.setText("")
app.processEvents()
win.grab().save(os.path.join(OUT, "2-presets.png"))

# 3) a mesma aba filtrada por gênero
win.presets_tab.cb_genre.setCurrentIndex(1)
app.processEvents()
win.grab().save(os.path.join(OUT, "3-presets-genero.png"))

# 4) biblioteca
win.tabs.setCurrentIndex(2)
app.processEvents()
win.grab().save(os.path.join(OUT, "4-biblioteca.png"))

# 5) áudio: monitor ligado, com um take real na lista
rec_dir = os.path.expanduser(r"~\CubeBabyStudio\gravacoes")
wavs = sorted([os.path.join(rec_dir, f) for f in os.listdir(rec_dir) if f.endswith(".wav")], reverse=True) \
    if os.path.isdir(rec_dir) else []
if wavs:
    win.audio_tab.reload_takes(wavs[0])
win.audio_tab.lbl_mon.setText("Monitor ligado — toque para ouvir.")
win.audio_tab.btn_mon.setChecked(True)
win.audio_tab.on_level(0.55)
win.audio_tab.lbl_time.setText("00:07")
win.audio_tab.lbl_state.setText("Gravado.")
win.tabs.setCurrentIndex(2)
app.processEvents()
win.grab().save(os.path.join(OUT, "7-audio.png"))
win.audio_tab.close_all()
win.audio_tab.btn_mon.setChecked(False)
win.audio_tab.lbl_mon.setText("Monitor desligado")
win.tabs.setCurrentIndex(3)
app.processEvents()
win.grab().save(os.path.join(OUT, "4-biblioteca.png"))

# 6) primeira execução: boas-vindas e escolha da guitarra
w = WelcomeDialog()
w.show(); app.processEvents()
w.grab().save(os.path.join(OUT, "8-bem-vindo.png")); w.close()

g = GuitarPickerDialog(current="stratocaster")
g.show(); app.processEvents()
g.grab().save(os.path.join(OUT, "9-guitarra.png")); g.close()

# 7) sobre
a = AboutDialog(win)
a.show(); app.processEvents()
a.grab().save(os.path.join(OUT, "10-sobre.png")); a.close()

print("ok:", OUT)
