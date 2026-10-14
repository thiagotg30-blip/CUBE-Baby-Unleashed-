"""Interface desktop (Qt / PySide6) do Cube Baby Studio."""
from __future__ import annotations

import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QFrame, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QSpinBox, QStackedWidget, QTabWidget, QTextEdit, QPlainTextEdit,
    QVBoxLayout, QWidget,
)

from . import __version__
from . import i18n as I18N
from . import presetfile as PF
from . import protocol as P
from . import guides as GU
from . import guitars as GT
from . import presets_lib as PL
from . import audio as AU
from . import art as ART
from . import chain as CHN
from . import tuner as TUN
from . import somadas as SOM
from . import cabinets as CAB
from . import cabs_factory as CF
from .ui_ir import IrTab
from . import dsp as DSP
from . import theme as T
theme = T   # nome historico (STYLE = theme.STYLESHEET usa este)
from .about import AboutDialog
from .meter import LevelBar
from .onboarding import GuitarPickerDialog, WelcomeDialog
from .settings import Settings, data_dir
from .client import BasePedal, CubeBabyClient, PedalError, SimulatedPedal, guess_port, list_ports

STYLE = theme.STYLESHEET


# Ordem = fluxo de sinal (entrada -> saída), não ordem alfabética. Cada bloco
# tem uma cor que pinta os próprios sliders, para o olho agrupar.
# Cada bloco tem um acento. São funcionais (identificam o bloco de relance) mas
# foram escolhidos em cima da paleta quente do tema, para não brigar com o
# grafite. O primeiro bloco usa o âmbar da marca, como no AmpliTube.
BLOCKS = [
    ("Pré-amp", theme.ACCENT,
     [("type", "Tipo"), ("gain", "Ganho"), ("tone", "Tom")], ("toneSection", "EQ ligado")),
    ("Gabinete", theme.GOLD, [("cabinet", "Cabinet")], ("irSection", "IR ligada")),
    ("Modulação", theme.PURPLE, [("modulation", "Chorus / Phaser")], None),
    ("Delay", theme.BLUE,
     [("time", "Tempo"), ("feedback", "Retorno"), ("mix", "Mix")], ("delaySection", "Delay ligado")),
    ("Reverb", theme.OK, [("reverb", "Quantidade")], None),
    ("Saída", theme.FG_MUTED, [("volume", "Volume")], None),
]


def fmt_value(name: str, v: int) -> str:
    if name == "type":
        return next((f"{n}" for i, n, _ in P.PREAMP_TYPES if i == v), f"Tipo {v}")
    if name == "modulation":
        return P.modulation_label(v)
    if name == "cabinet":
        # O nome real do gabinete, não "Cabinet 3". O firmware define a lista.
        fw = fw_key()
        return CAB.short_label(fw, v)
    return f"{v} / {P.PARAM_MAX[name]}"


def fw_key() -> str:
    """Qual lista de gabinetes usar: a do firmware do pedal em uso.

    Listas diferentes entre M-VAVE e CUVAVE — ver cabinets.py. A escolha fica
    nas preferencias para nao ter que perguntar a cada abertura.
    """
    try:
        return Settings().get("firmware") or CAB.DEFAULT_FIRMWARE
    except Exception:  # noqa: BLE001
        return CAB.DEFAULT_FIRMWARE


class Runner(QObject):
    """Executa chamadas bloqueantes ao pedal numa thread única (mantém a ordem) e devolve na UI."""
    _result = Signal(object, object, object)
    progress = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._pool = ThreadPoolExecutor(max_workers=1)
        self._result.connect(lambda cb, res, err: cb(res, err) if cb else None)

    def submit(self, fn, cb=None) -> None:
        def run():
            try:
                res, err = fn(), None
            except Exception as exc:  # noqa: BLE001
                res, err = None, exc
            self._result.emit(cb, res, err)
        self._pool.submit(run)


class ParamRow(QWidget):
    changed = Signal(str, int)

    def __init__(self, name: str, label: str, accent: str = "#ff6b4a") -> None:
        super().__init__()
        self.name = name
        tip = GU.knob_tip(name)
        self.setToolTip(tip)
        # Aqui só se tinge o que depende da cor do bloco. O resto (trilho,
        # botão do slider, combobox) NÃO é redefinido de propósito: quem define
        # é theme.STYLESHEET. Redefinir aqui fazia o widget usar as cores do
        # tema antigo e divergir do resto da janela.
        self.setStyleSheet(
            f"QSlider::sub-page:horizontal {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"    stop:0 {accent}, stop:1 {theme.shade(accent, -22)}); }}"
            f"QSlider::handle:horizontal:hover {{ background: {accent}; }}"
            f"QSlider::handle:horizontal {{ border-color: {accent}; }}"
        )
        lay = QGridLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setHorizontalSpacing(8)
        self.title = QLabel(label)
        self.title.setStyleSheet(
            f"color:#b8bec9; font-size:12px; font-weight:600; letter-spacing:0.3px;")
        self.title.setToolTip(tip)
        self.value_lbl = QLabel()
        self.value_lbl.setAlignment(Qt.AlignRight)
        self.value_lbl.setStyleSheet(
            f"color:{accent}; font-size:12px; font-weight:700;")
        self.value_lbl.setToolTip(tip)
        # Largura FIXA. Sem isto, o rotulo com texto longo ("8 · Diezel V30 4×12")
        # espreme o slider da mesma linha e ele muda de tamanho a cada valor —
        # o "flicker" que se arrasta. O texto que não couber vira reticências.
        self._fixed_value_w = 168 if name == "cabinet" else 78
        self.value_lbl.setFixedWidth(self._fixed_value_w)
        lay.addWidget(self.title, 0, 0)
        lay.addWidget(self.value_lbl, 0, 1)
        if name == "type":
            self.combo = QComboBox()
            for i, n, cat in P.PREAMP_TYPES:
                self.combo.addItem(f"{n}  ({cat})", i)
            self.combo.setToolTip(tip)
            self.combo.currentIndexChanged.connect(self._on_type)
            lay.addWidget(self.combo, 1, 0, 1, 1)
            # Diagrama de caráter do pré-amp: brilho e sujeira de relance.
            self.art = ART.PreampArt(*ART.preamp_character(
                P.PREAMP_TYPES[0][1])[:2])
            self.art.setToolTip(
                "As barras mostram o caráter: T = brilho (tom), G = sujeira (gain).\n"
                "Os pré-amps da CUVAVE não têm imagem pública — este diagrama "
                "resume o som, não parece o amplificador.")
            lay.addWidget(self.art, 1, 1, Qt.AlignmentFlag.AlignRight)
            self.slider = None
            self.value_lbl.hide()
        else:
            self.combo = None
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(0, P.PARAM_MAX[name])
            self.slider.setToolTip(tip)
            self.slider.valueChanged.connect(self._on_slider)
            if name == "cabinet":
                # Planta da caixa: 1×10, 2×12, 4×12… muda com o valor.
                lay.addWidget(self.slider, 1, 0)
                self.cab_art = ART.CabinetArt()
                self.cab_art.setFixedWidth(88)
                # Desenha já com o valor atual. Sem isto o gabinete aparece em
                # branco até o usuário mexer no slider: setValue(0) não emite
                # sinal quando o slider já está em 0.
                self.cab_art.set_spec(CAB.get(fw_key(), 0).spec)
                self.cab_art.setToolTip(
                    "Desenho esquemático da caixa (tamanho e número de alto-falantes). "
                    "É uma ilustração feita a partir das especificações, não uma foto.")
                lay.addWidget(self.cab_art, 1, 1)
            else:
                lay.addWidget(self.slider, 1, 0, 1, 2)
            self.value_lbl.setText(fmt_value(name, 0))

    def _on_type(self, _i: int = 0) -> None:
        """Ao trocar o pré-amp, atualiza o diagrama de caráter."""
        if self.combo is not None:
            nome = self.combo.currentText().split("  (")[0]
            tom, sujeira, _cat = ART.preamp_character(nome)
            if getattr(self, "art", None):
                self.art.set_character(tom, sujeira)
        self.changed.emit(self.name, self.combo.currentData())

    def _set_value_text(self, v: int) -> None:
        """Escreve o valor no rótulo, cortando o que não couber na largura fixa."""
        txt = fmt_value(self.name, v)
        full = txt
        if txt != self.value_lbl.text():
            # fonte 12px ~= 6.4px por caractere; 5px de folga nas bordas
            max_ch = max(6, int((self._fixed_value_w - 8) / 6.4))
            if len(txt) > max_ch:
                txt = txt[:max_ch - 1].rstrip() + "…"
        self.value_lbl.setText(txt)
        self.value_lbl.setToolTip(full if txt != full else GU.knob_tip(self.name))

    def _on_slider(self, v: int) -> None:
        self._set_value_text(v)
        # O desenho da caixa tem de acompanhar o arrasto. Sem isto o gabinete
        # ficava sempre em branco enquanto o slider corria — o desenho só era
        # atualizado quando o valor vinha de fora (set_value), nunca pelo
        # próprio slider.
        if self.name == "cabinet" and getattr(self, "cab_art", None):
            self.cab_art.set_spec(CAB.get(fw_key(), v).spec)
        self.changed.emit(self.name, v)

    def set_value(self, v: int) -> None:
        w = self.combo or self.slider
        w.blockSignals(True)
        if self.combo:
            self.combo.setCurrentIndex(max(0, self.combo.findData(v)))
            nome = self.combo.currentText().split("  (")[0]
            tom, sujeira, _c = ART.preamp_character(nome)
            if getattr(self, "art", None):
                self.art.set_character(tom, sujeira)
        else:
            self.slider.setValue(v)
            self._set_value_text(v)
            if self.name == "cabinet" and getattr(self, "cab_art", None):
                self.cab_art.set_spec(CAB.get(fw_key(), v).spec)
        w.blockSignals(False)


class HelpDialog(QDialog):
    """Guia do programa, organizado pela pergunta do usuário, não pelo código.

    A ordem das abas segue o caminho de quem chega aqui perdido: "por onde
    começo?" -> "qual preset eu escolho?" -> "o que é cada controle?" ->
    "por que a guitarra muda as coisas?" -> "e o áudio?".

    Ter a lista dos 13 controles na primeira aba era inútil: ninguém que nunca
    usou um pedal quer saber o que é 'feedback' antes de saber o que tocar.
    """

    def __init__(self, win: "MainWindow") -> None:
        super().__init__(win)
        self.setWindowTitle(I18N.tr("ajuda_titulo", I18N.get_idioma()))
        self.resize(660, 680)
        lay = QVBoxLayout(self)

        self.tabs = QTabWidget()

        def _page(html: str) -> QScrollArea:
            w = QWidget()
            v = QVBoxLayout(w)
            lbl = QLabel(html)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl.setStyleSheet("font-size:13px; line-height:150%;")
            v.addWidget(lbl)
            v.addStretch()
            s = QScrollArea()
            s.setWidgetResizable(True)
            s.setWidget(w)
            return s

        # ---- 1. começar ----
        start = QWidget()
        sl = QVBoxLayout(start)
        head = QLabel(f"<b style='font-size:15px'>{I18N.tr("bem_vindo", I18N.get_idioma())}</b>")
        sl.addWidget(head)
        steps = QLabel(GU.first_steps_texto_com_audio())
        steps.setWordWrap(True)
        steps.setTextInteractionFlags(Qt.TextSelectableByMouse)
        steps.setStyleSheet("font-size:13px; line-height:150%;")
        sl.addWidget(steps)
        sl.addStretch()
        s0 = QScrollArea(); s0.setWidgetResizable(True); s0.setWidget(start)
        self.tabs.addTab(s0, I18N.tr("comeco", I18N.get_idioma()))

        # ---- 2. qual preset ----
        self.tabs.addTab(_page(GU.decisions_text()), I18N.tr("qual_preset", I18N.get_idioma()))

        # ---- 3. controles ----
        knobs = QWidget(); kl = QVBoxLayout(knobs)
        kl.addWidget(QLabel(
            "Os 13 parâmetros do pedal. Passe o mouse sobre qualquer controle "
            "(inclusive nos cartões e checkbox) para ver esta mesma explicação."))
        for name in P.PARAM_NAMES:
            box = QGroupBox(GU.FRIENDLY.get(name, name))
            v = QVBoxLayout(box)
            lbl = QLabel(GU.KNOB_TIPS.get(name, ""))
            lbl.setWordWrap(True); lbl.setObjectName("sig")
            v.addWidget(lbl)
            kl.addWidget(box)
        kl.addStretch()
        s2 = QScrollArea(); s2.setWidgetResizable(True); s2.setWidget(knobs)
        self.tabs.addTab(s2, I18N.tr("os_controles", I18N.get_idioma()))

        # ---- 4. guitarra ----
        guitars = QWidget(); gl = QVBoxLayout(guitars)
        gl.addWidget(QLabel(
            "<b>A guitarra muda o som final.</b> O CUBE Baby não sabe qual guitarra "
            "está plugada — ele só aplica os parâmetros. Por isso, ao escolher sua "
            "guitarra no topo da janela, o programa re-adapta os valores dos três "
            "slots de uma vez, sozinho.\n\n"
            "O que cada uma faz:"))
        for g in GT.GUITARS:
            box = QGroupBox(g.one_line())
            v = QVBoxLayout(box)
            lbl = QLabel(f"{g.character}<br><br><i>{g.tips}</i>")
            lbl.setWordWrap(True); lbl.setObjectName("sig")
            v.addWidget(lbl)
            gl.addWidget(box)
        gl.addStretch()
        s3 = QScrollArea(); s3.setWidgetResizable(True); s3.setWidget(guitars)
        self.tabs.addTab(s3, I18N.tr("sua_guitarra", I18N.get_idioma()))

        # ---- 5. áudio ----
        aud = QWidget(); al = QVBoxLayout(aud)
        al.addWidget(QLabel(
            "<b>Ouvir, gravar e limpar a gravação — sem REAPER.</b><br>"
            "Aba <b>Áudio</b> tem três coisas: ouvir a guitarra ao vivo, gravar em "
            "WAV, e limpar o chiado com gate + normalizador."))
        for k, title in (("monitor", "Ouvir ao vivo"), ("input", "Escolher a entrada"),
                         ("dsp", "Gate + Normalizar"), ("record", "Gravar"),
                         ("latency", "Atraso ao ouvir"), ("noise", "Se a gravação chiar")):
            box = QGroupBox(title)
            v = QVBoxLayout(box)
            lbl = QLabel(GU.audio_tip(k)); lbl.setWordWrap(True); lbl.setObjectName("sig")
            v.addWidget(lbl)
            al.addWidget(box)
        al.addStretch()
        s4 = QScrollArea(); s4.setWidgetResizable(True); s4.setWidget(aud)
        self.tabs.addTab(s4, I18N.tr("audio_tab", I18N.get_idioma()))

        # ---- 5. gabinetes de fábrica (lidos do CubeSuite oficial) ----
        cabs = QWidget(); cl = QVBoxLayout(cabs)
        cl.addWidget(QLabel(
            "<b>Os 32 gabinetes que vêm no CubeSuite.</b><br>"
            "Estes nomes foram lidos do arquivo <code>bin/BOR.bin</code> que "
            "acompanha o CubeSuite oficial — não são inventados. Servem para "
            "você reconhecer e procurar a caixa certa.<br><br>"
            "<b style='color:#e8a33d'>Atenção:</b> a ordem abaixo é a do "
            "<i>arquivo</i>. O pedal tem 8 posições no botão IR CAB e o arquivo "
            "tem 32 entradas; o CubeSuite não traz nenhum campo ligando uma à "
            "outra. Então este número <b>não é</b> a posição do pedal."))
        self.busca_cab = QLineEdit()
        self.busca_cab.setPlaceholderText(I18N.tr("filtrar_cab", I18N.get_idioma()))
        cl.addWidget(self.busca_cab)
        self.lista_cab = QVBoxLayout()
        cl.addLayout(self.lista_cab)

        def _redesenha(termo: str = "") -> None:
            while self.lista_cab.count():
                it = self.lista_cab.takeAt(0)
                w = it.widget()
                if w is not None:
                    w.deleteLater()
            achados = CF.procurar(termo)
            if not achados:
                self.lista_cab.addWidget(QLabel(I18N.tr("nada_encontrado", I18N.get_idioma())))
                return
            for c in achados:
                destaque = c.idx == CF.MONSTER_CAB.idx
                box = QGroupBox(f"{c.idx:2d} · {c.nome}   ({c.spec} · {c.familia})"
                                + ("   ← caixa do 'Monster'" if destaque else ""))
                v = QVBoxLayout(box)
                lbl = QLabel(c.nota); lbl.setWordWrap(True); lbl.setObjectName("sig")
                v.addWidget(lbl)
                self.lista_cab.addWidget(box)

        self.busca_cab.textChanged.connect(_redesenha)
        _redesenha("")
        cl.addStretch()
        s5 = QScrollArea(); s5.setWidgetResizable(True); s5.setWidget(cabs)
        self.tabs.addTab(s5, I18N.tr("gabinetes", I18N.get_idioma()))

        lay.addWidget(self.tabs, 1)

        row = QHBoxLayout(); row.addStretch()
        close = QPushButton(I18N.tr("fechar", I18N.get_idioma())); close.setObjectName("primary")
        close.clicked.connect(self.accept)
        row.addWidget(close); lay.addLayout(row)


class PedalTab(QWidget):
    def __init__(self, win: "MainWindow") -> None:
        super().__init__()
        self.win = win
        self.slot = "A"
        # Nome do timbre que foi carregado por ultimo neste editor. Serve para
        # dar um nome util a somada: e melhor que "Meu timbre".
        self.preset_atual: str | None = None
        self.params = {s: P.empty_params() for s in P.SLOT_IDS}
        self.rows: dict[str, ParamRow] = {}
        self.toggles: dict[str, QCheckBox] = {}
        self._timers: dict[str, QTimer] = {}

        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.slot_btns = {}
        for s in P.SLOT_IDS:
            b = QPushButton(f"Preset {s}"); b.setObjectName("slot"); b.setCheckable(True)
            b.clicked.connect(lambda _=False, s=s: self.select_slot(s))
            self.slot_btns[s] = b; bar.addWidget(b)
        self.slot_btns["A"].setChecked(True)
        bar.addStretch()

        self.lbl_modo = QLabel(I18N.tr("modo", I18N.get_idioma()))
        self.lbl_modo.setToolTip(
            I18N.tr("modo_desc", I18N.get_idioma()) + "\n"
            )
        self.sw_modo = QCheckBox(I18N.tr("avancado", I18N.get_idioma()))
        self.sw_modo.setToolTip(I18N.tr("marque_controles", I18N.get_idioma()))
        self.sw_modo.toggled.connect(self.toggle_mode)
        _lang = I18N.get_idioma()
        self.btn_read = QPushButton(I18N.tr("ler_do_pedal", I18N.get_idioma())); self.btn_read.clicked.connect(self.read_from_pedal)
        self.btn_import = QPushButton(I18N.tr("importar_arquivo", I18N.get_idioma())); self.btn_import.clicked.connect(self.import_file)
        self.btn_export = QPushButton(I18N.tr("exportar_slot", I18N.get_idioma())); self.btn_export.clicked.connect(self.export_slot)
        self.btn_lib = QPushButton(I18N.tr("salvar_biblioteca", I18N.get_idioma())); self.btn_lib.clicked.connect(self.save_to_library)
        for b in (self.btn_read, self.btn_import, self.btn_export, self.btn_lib):
            bar.addWidget(b)
        bar.addSpacing(theme.S4)
        bar.addWidget(self.lbl_modo)
        bar.addWidget(self.sw_modo)
        root.addLayout(bar)

        # painel de voicing: mostra o que a guitarra faz com o preset do slot
        self.lbl_voicing = QLabel(); self.lbl_voicing.setObjectName("sig")
        self.lbl_voicing.setWordWrap(True)
        root.addWidget(self.lbl_voicing)


        # ---- dois modos, um conjunto de controles ----
        # Os mesmos ParamRow são reorganizados entre as duas telas. Uma fonte de
        # verdade: o que muda é o arranjo, nunca o estado nem a lista de parâmetros.
        self.mode = (self.win.settings.get("modo") or "iniciante") \
            if hasattr(self.win, "settings") else "iniciante"
        self._adv_anchor: list[tuple] = []      # (layout, widgets) de cada bloco

        self._pages = QStackedWidget()
        self._page_adv = QWidget()
        self._page_beg = QWidget()
        self._pages.addWidget(self._page_beg)
        self._pages.addWidget(self._page_adv)
        root.addWidget(self._pages, 1)

        self._build_beginner(self._page_beg)
        self._build_advanced(self._page_adv)
        self._set_mode(self.mode)
        self.refresh_widgets()

    # ---- modo iniciante -------------------------------------------------------
    def _build_beginner(self, page: QWidget) -> None:
        v = QVBoxLayout(page)
        v.setContentsMargins(0, theme.S2, 0, 0)
        v.setSpacing(theme.S2)

        titulo = QLabel(I18N.tr("o_que_voce_quer", I18N.get_idioma()))
        titulo.setStyleSheet(f"font-size:{theme.FS_TITLE}; font-weight:600;")
        v.addWidget(titulo)

        sub = QLabel(I18N.tr("escolha_ponto", I18N.get_idioma()))
        sub.setStyleSheet(f"color:{theme.FG_MUTED}; font-size:{theme.FS_SMALL};")
        v.addWidget(sub)

        grade = QGridLayout()
        grade.setSpacing(theme.S2)
        self._intent_btns = {}
        for i, (key, label, desc, _params) in enumerate(GU.QUICK_INTENTS):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setToolTip(desc)
            b.setMinimumHeight(32)
            b.clicked.connect(lambda _=False, k=key: self.apply_intent(k))
            self._intent_btns[key] = b
            grade.addWidget(b, i // 3, i % 3)
        for c in range(3):
            grade.setColumnStretch(c, 1)
        v.addLayout(grade)

        self.lbl_intent = QLabel("")
        self.lbl_intent.setWordWrap(True)
        self.lbl_intent.setObjectName("sig")
        v.addWidget(self.lbl_intent)
        v.addSpacing(theme.S2)

        box = QGroupBox("Os controles que importam")
        bv = QVBoxLayout(box)
        bv.setSpacing(theme.S3)
        # Os widgets são adicionados depois, em _set_mode; guardamos a ordem.
        # Contêiner dedicado só para os controles. Assim trocar de modo é só
        # mover widgets entre dois layouts, sem depender de índice ou ordem.
        self._beg_rows_box = QWidget()
        self._beg_rows_layout = QVBoxLayout(self._beg_rows_box)
        self._beg_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._beg_rows_layout.setSpacing(theme.S3)
        bv.addWidget(self._beg_rows_box)
        self._beg_layout = bv
        self._beg_hint = QLabel(I18N.tr("controles_finos", I18N.get_idioma()))
        self._beg_hint.setStyleSheet(f"color:{theme.FG_MUTED}; font-size:{theme.FS_TINY};")
        bv.addWidget(self._beg_hint)
        v.addWidget(box)
        v.addStretch()

        # Contêineres vazios só para os controles que o iniciante não vê: eles
        # continuam existindo (o estado não se perde), só não estão visíveis.
        self._beg_hidden = QWidget()
        self._beg_hidden.setVisible(False)
        self._beg_hidden_layout = QVBoxLayout(self._beg_hidden)
        v.addWidget(self._beg_hidden)

    def apply_intent(self, key: str) -> None:
        """Aplica um atalho 'o que você quer' no slot atual."""
        item = next((q for q in GU.QUICK_INTENTS if q[0] == key), None)
        if not item:
            return
        _k, label, desc, params = item
        slot = self.slot
        novo = dict(self.params[slot])
        novo.update({k: P.clamp_param(k, val) for k, val in params.items()})
        # backup do que estava, como em qualquer gravação
        self.win.backup(slot, self.params[slot])
        self.params[slot] = novo
        self._preset_source_mark = None
        self.refresh_widgets()
        for k2, b in self._intent_btns.items():
            b.setChecked(k2 == key)
        self.lbl_intent.setText(f"<b>{label}</b> — {desc}")
        self.win.status(f"{label} aplicado no slot {slot}. Ajuste os controles abaixo como quiser.")

    # ---- modo avançado --------------------------------------------------------
    def _build_advanced(self, page: QWidget) -> None:
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        # Alinhar ao topo impede que as caixas estiquem até a altura da mais
        # cheia: o Gabinete (1 controle) não precisa da altura do Pré-amp.
        grid.setAlignment(Qt.AlignTop)
        self._adv_anchor = []
        for i, (title, color, knobs, toggle) in enumerate(BLOCKS):
            box = QGroupBox(title)
            box.setStyleSheet(
                f"QGroupBox::title {{ color: {color}; font-size:12px; "
                f"font-weight:700; letter-spacing:0.6px; }}"
            )
            btip = GU.block_tip(title)
            if btip:
                box.setToolTip(btip)
            v = QVBoxLayout(box)
            v.setSpacing(3)
            v.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)
            box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

            widgets = []
            for name, label in knobs:
                row = ParamRow(name, label, color)
                row.changed.connect(self.on_param)
                self.rows[name] = row
                v.addWidget(row)
                widgets.append(row)
            if toggle:
                cb = QCheckBox(toggle[1])
                cb.setToolTip(GU.knob_tip(toggle[0]))
                cb.setStyleSheet(
                    f"QCheckBox::indicator:checked {{"
                    f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                    f"    stop:0 {color}, stop:1 {theme.shade(color, -25)});"
                    f"  border-color: {theme.shade(color, -30)}; }}")
                cb.toggled.connect(lambda on, n=toggle[0]: self.on_param(n, int(on)))
                self.toggles[toggle[0]] = cb
                v.addWidget(cb)
                widgets.append(cb)
            if title == "Saída":
                self.bar_out = LevelBar(accent=color)
                self.bar_out.setToolTip(GU.audio_tip("level"))
                self.lbl_out = QLabel("—"); self.lbl_out.setObjectName("muted")
                h = QHBoxLayout()
                h.addWidget(self.bar_out, 1); h.addWidget(self.lbl_out)
                v.addSpacing(4); v.addLayout(h)
                widgets.append(self.lbl_out)

            grid.addWidget(box, i // 3, i % 3)
            # guarda (layout, widgets) para poder devolver tudo aqui depois
            # guarda o rótulo "de normalised" (usado no modo iniciante) e o
            # técnico (modo avançado): os mesmos widgets servem aos dois.
            for w in widgets:
                if isinstance(w, ParamRow) and w.name in GU.BEGINNER_LABELS:
                    w.adv_label = w.title.text()
                    w.beg_label, w.beg_tip = GU.BEGINNER_LABELS[w.name]
            self._adv_anchor.append((v, widgets))
        for c in range(3):
            grid.setColumnStretch(c, 1)

    # ---- troca de modo --------------------------------------------------------
    def _set_mode(self, mode: str) -> None:
        """Move os MESMOS widgets entre as duas telas. Nenhum é recriado, então
        nada se perde ao trocar de modo no meio de um ajuste.

        A regra é simples: em cada modo, todo widget vai para o layout de
        destino e os que não pertencem a ele são escondidos. addWidget() já
        re-pareia o widget, então não é preciso remover de lugar nenhum.
        """
        iniciante = mode != "avancado"

        # rótulos: o iniciante vê nome everyday, o avançado vê o nome do pedal
        for name, row in self.rows.items():
            if not hasattr(row, "adv_label"):
                continue
            if iniciante and name in GU.BEGINNER_PARAMS:
                row.title.setText(row.beg_label)
                row.setToolTip(row.beg_tip)
                row.title.setStyleSheet(
                    f"color:{theme.FG}; font-size:{theme.FS_HEAD}; font-weight:600;")
                row.value_lbl.setStyleSheet(
                    f"color:{theme.ACCENT}; font-size:{theme.FS_HEAD}; font-weight:700;")
            else:
                row.title.setText(row.adv_label)
                row.setToolTip(GU.knob_tip(name))
                row.title.setStyleSheet(
                    f"color:{theme.FG_DIM}; font-size:{theme.FS_SMALL}; font-weight:600;")
                row.value_lbl.setStyleSheet(
                    f"color:{theme.ACCENT}; font-size:{theme.FS_SMALL}; font-weight:700;")

        if iniciante:
            # 5 controles na página do iniciante, na ordem de BEGINNER_PARAMS
            for name in GU.BEGINNER_PARAMS:
                row = self.rows.get(name)
                if row:
                    self._beg_rows_layout.addWidget(row)
                    row.show()
            # todo o resto some
            for name, row in self.rows.items():
                if name not in GU.BEGINNER_PARAMS:
                    row.setParent(self._beg_hidden)
                    row.hide()
            for name, cb in self.toggles.items():
                cb.setParent(self._beg_hidden)
                cb.hide()
            self._pages.setCurrentWidget(self._page_beg)
        else:
            # tudo volta para o seu bloco original, na ordem original
            for v, widgets in self._adv_anchor:
                for w in widgets:
                    v.addWidget(w)
                    if hasattr(w, "setParent") and w is not self.bar_out:
                        w.show()
            self._pages.setCurrentWidget(self._page_adv)

        self.mode = mode
        if hasattr(self.win, "settings"):
            self.win.settings.set("modo", mode)
        self.refresh_voicing_note()

    def toggle_mode(self, avancado: bool) -> None:
        self._set_mode("avancado" if avancado else "iniciante")

    # ---- estado ------------------------------------------------------------------
    def select_slot(self, s: str) -> None:
        self.slot = s
        for k, b in self.slot_btns.items():
            b.setChecked(k == s)
        self.refresh_widgets()

    def refresh_widgets(self) -> None:
        p = self.params[self.slot]
        for n, row in self.rows.items():
            row.set_value(p[n])
        for n, cb in self.toggles.items():
            cb.blockSignals(True); cb.setChecked(bool(p[n])); cb.blockSignals(False)
        self.refresh_voicing_note()

    def set_enabled_pedal(self, on: bool) -> None:
        self.btn_read.setEnabled(on)

    def set_out_level(self, v: float) -> None:
        """VU ao vivo dentro do bloco Saída desta aba (ligado pelo monitor)."""
        if not hasattr(self, "bar_out"):
            return
        self.bar_out.set_level(v)
        if v <= 0.0002:
            self.lbl_out.setText("—")
        else:
            import math
            self.lbl_out.setText(f"{max(-60.0, 20 * math.log10(v)):+.0f} dB")

    # ---- voicing por guitarra -------------------------------------------------
    # A guitarra é um ajuste GLOBAL (na barra da janela), não um filtro. Aqui
    # só mostramos o efeito que ela tem no slot atual — a adaptação acontece
    # sozinha, em win.set_guitar(), para os 3 slots de uma vez.

    def refresh_voicing_note(self) -> None:
        """Descreve a guitarra escolhida e o que a adaptação faria no slot atual."""
        g = GT.get(self.win.guitarra_key)
        changes = g.preview(self.params[self.slot])
        head = f"<b>Sua guitarra: {g.label}</b> · {g.character} &nbsp;|&nbsp; "
        if changes:
            self.lbl_voicing.setText(
                head + "se trocar para outra guitarra, estes valores mudam: "
                + ", ".join(f"{n} {a}→{b}" for n, a, b in changes)
            )
        else:
            self.lbl_voicing.setText(head + "é a guitarra em que este preset foi pensado.")

    def on_param(self, name: str, value: int) -> None:
        self.params[self.slot][name] = int(value)
        self.refresh_voicing_note()
        if not self.win.pedal or not self.win.pedal.connected:
            return
        slot = self.slot
        key = f"{slot}:{name}"
        t = self._timers.get(key)
        if t is None:  # um timer por parâmetro, conectado uma vez só
            t = QTimer(self); t.setSingleShot(True)
            t.timeout.connect(lambda s=slot, n=name: self._flush(s, n))
            self._timers[key] = t
        t.start(60)  # debounce: não inunda o pedal enquanto o slider se mexe

    def _flush(self, slot: str, name: str) -> None:
        pedal = self.win.pedal
        if not pedal or not pedal.connected:
            return
        value = self.params[slot][name]
        self.win.runner.submit(
            lambda: pedal.write_live_param(slot, name, value),
            lambda ok, err: self.win.status(f"Falha ao gravar {name}: {err}") if err else (
                self.win.status(f"O pedal respondeu 'recusado' ao gravar {name} (resposta {pedal.last_ack}). Detalhes em pedal.log")
                if ok is False else None))

    # ---- ações -------------------------------------------------------------------
    def read_from_pedal(self) -> None:
        if not self.win.require_pedal():
            return
        self.win.busy("Lendo presets do pedal...")
        def done(bank, err):
            self.win.idle()
            if err:
                self.win.status(str(err)); return
            self.params = {s: P.clamp_params(bank[s]) for s in P.SLOT_IDS}
            self.refresh_widgets()
            self.win.status("Presets lidos do pedal.")
        self.win.runner.submit(self.win.pedal.read_bank, done)

    def apply_params(self, name: str, params: dict) -> None:
        """Coloca os parâmetros no editor do slot atual e, se conectado e confirmado, grava no pedal."""
        previous = dict(self.params[self.slot])
        self.params[self.slot] = P.clamp_params(params)
        self.preset_atual = name
        self.refresh_widgets()
        self.win.status(f'"{name}" carregado no editor do slot {self.slot}.')
        pedal = self.win.pedal
        if not pedal or not pedal.connected:
            return
        ask = QMessageBox.question(
            self, "Gravar no pedal?",
            f'Gravar "{name}" direto no slot {self.slot} do pedal agora?\n\n'
            "Um backup do que estava no editor é salvo automaticamente antes.")
        if ask != QMessageBox.Yes:
            return
        self.win.backup(self.slot, previous)
        slot, p = self.slot, dict(self.params[self.slot])
        self.win.busy(f"Gravando no slot {slot}...")
        def done(res, err):
            self.win.idle()
            if err:
                self.win.status(f"Falha ao gravar: {err}")
            else:
                extra = " (confirmado lendo de volta do pedal)" if res == "ok-readback" else ""
                self.win.status(f'"{name}" gravado no slot {slot} do pedal.{extra}')
        self.win.runner.submit(lambda: pedal.write_all_params(slot, p, self.win.runner.progress.emit), done)

    def import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importar preset", str(Path.home()), "Presets (*.json);;Todos (*)")
        if not path:
            return
        try:
            presets, warns = PF.load_file(path)
            if not presets:
                raise ValueError("O arquivo não tinha nenhum preset.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Importar", str(exc)); return
        for extra in presets[1:]:
            PF.library_add(extra["name"], extra["params"])
        if len(presets) > 1:
            self.win.library.reload()
            self.win.status(f"O arquivo tinha {len(presets)} presets; os outros foram para a biblioteca.")
        self.apply_params(presets[0]["name"], presets[0]["params"])
        if warns:
            self.win.status(self.win.statusBar().currentMessage() + " — " + " ".join(warns))

    def export_slot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exportar slot", str(Path.home() / f"cube-baby-slot-{self.slot}.json"), "Preset (*.json)")
        if path:
            PF.save_file(path, f"CUBE Baby - Slot {self.slot}", self.params[self.slot])
            self.win.status(f"Slot {self.slot} exportado.")

    def save_to_library(self) -> None:
        name, ok = QInputDialog.getText(self, "Biblioteca", "Nome do preset:", text=f"Slot {self.slot} - {datetime.now():%d/%m/%Y}")
        if ok and name.strip():
            PF.library_add(name.strip(), self.params[self.slot])
            self.win.library.reload()
            self.win.status(f'Preset "{name.strip()}" salvo na biblioteca.')


class PresetsTab(QWidget):
    """Biblioteca curada: assinatura sonora, gênero e guitarra de referência."""

    def __init__(self, win: "MainWindow") -> None:
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)

        # ---- filtros ----
        filt = QHBoxLayout()
        self.ed_search = QLineEdit(); self.ed_search.setPlaceholderText(I18N.tr("buscar_preset", I18N.get_idioma()))
        self.ed_search.setClearButtonEnabled(True)
        self.ed_search.textChanged.connect(self.reload)
        self.cb_genre = QComboBox(); self.cb_genre.setMinimumWidth(150)
        self.cb_genre.currentIndexChanged.connect(self.reload)
        for w in (QLabel(I18N.tr("genero_lbl", I18N.get_idioma())), self.cb_genre):
            filt.addWidget(w)
        filt.addWidget(self.ed_search, 1)
        # A guitarra NÃO é um filtro: é o ajuste global da janela. Aqui só
        # avisamos que a lista mostra todos os presets, adaptáveis à guitarra.
        self.lbl_note = QLabel(I18N.tr("presets_adaptam", I18N.get_idioma()).format(n=len(PL.PRESETS)))
        self.lbl_note.setObjectName("muted")
        filt.addWidget(self.lbl_note)
        lay.addLayout(filt)

        # ---- lista + detalhe ----
        split = QHBoxLayout()
        self.listw = QListWidget()
        self.listw.currentItemChanged.connect(self.on_select)
        self.listw.itemDoubleClicked.connect(lambda _: self.load_selected())
        split.addWidget(self.listw, 3)

        # Painel direito: o TEXTO de detalhe rola, os BOTOES ficam fixos.
        # Sem a rolagem, com a janela baixa o texto e os botões eram cortados
        # pela borda — o mesmo buraco que na aba Tocando.
        side = QVBoxLayout()
        det_scroll = QScrollArea()
        det_scroll.setWidgetResizable(True)
        det_scroll.setFrameShape(QFrame.Shape.NoFrame)
        det_scroll.setStyleSheet("QScrollArea { background: transparent; border: 0; }"
                                 "QScrollArea QWidget { background: transparent; }")
        det_body = QWidget()
        det_v = QVBoxLayout(det_body)
        det_v.setContentsMargins(0, 0, 4, 0)
        self.lbl_title = QLabel(); self.lbl_title.setStyleSheet("font-size:16px; font-weight:600;")
        self.lbl_sig = QLabel(); self.lbl_sig.setObjectName("sig"); self.lbl_sig.setWordWrap(True)
        self.lbl_meta = QLabel(); self.lbl_meta.setObjectName("muted"); self.lbl_meta.setWordWrap(True)
        self.lbl_diff = QLabel(); self.lbl_diff.setObjectName("sig"); self.lbl_diff.setWordWrap(True)
        for w in (self.lbl_title, self.lbl_sig, self.lbl_meta, self.lbl_diff):
            det_v.addWidget(w)
        det_v.addStretch()
        det_scroll.setWidget(det_body)
        side.addWidget(det_scroll, 1)

        row = QHBoxLayout()
        self.btn_load = QPushButton(I18N.tr("carregar_adaptado", I18N.get_idioma())); self.btn_load.setObjectName("primary")
        self.btn_load.setToolTip(I18N.tr("carregar_adaptado_tip", I18N.get_idioma()))
        self.btn_load.clicked.connect(self.load_selected)
        self.btn_raw = QPushButton(I18N.tr("carregar_original", I18N.get_idioma())); self.btn_raw.setObjectName("ghost")
        self.btn_raw.setToolTip(I18N.tr("carregar_original_tip", I18N.get_idioma()))
        self.btn_raw.clicked.connect(self.load_raw)
        self.btn_save = QPushButton(I18N.tr("salvar_biblioteca", I18N.get_idioma())); self.btn_save.clicked.connect(self.save_selected)
        row.addStretch()
        for b in (self.btn_load, self.btn_raw, self.btn_save):
            row.addWidget(b)
        side.addLayout(row)
        split.addLayout(side, 2)
        lay.addLayout(split, 1)

        # Só popula o filtro depois de existir a lista: addItem dispara
        # currentIndexChanged, e reload() depende de self.listw.
        self.cb_genre.addItem(I18N.tr("todos", I18N.get_idioma()), None)
        for g in PL.genres():
            self.cb_genre.addItem(g, g)

        self.reload()

    # ---- dados ----
    def current_preset(self) -> "PL.Preset | None":
        it = self.listw.currentItem()
        return it.data(Qt.UserRole) if it else None

    def reload(self) -> None:
        genre = self.cb_genre.currentData() or ""
        keep = self.current_preset()
        self.listw.blockSignals(True); self.listw.clear()
        found = PL.search(self.ed_search.text(), genre, "")
        for p in found:
            g = GT.get(p.guitar)
            it = QListWidgetItem(f"{p.name}\n{g.label} · {' / '.join(p.genres[:3])}")
            it.setData(Qt.UserRole, p)
            self.listw.addItem(it)
        self.listw.blockSignals(False)
        # Mantém a seleção se o preset continuar visível; senão, seleciona o primeiro.
        target = -1
        if keep:
            for i in range(self.listw.count()):
                if self.listw.item(i).data(Qt.UserRole).key == keep.key:
                    target = i
                    break
        if target < 0 and self.listw.count():
            target = 0
        if target >= 0:
            self.listw.setCurrentRow(target)
        else:
            self.on_select(None, None)
        self.win.status(f"{len(found)} preset(s) curado(s)." if found else "Nenhum preset com esses filtros.")

    def on_select(self, cur, _prev=None) -> None:
        p = cur.data(Qt.UserRole) if cur else None
        if not p:
            for w in (self.lbl_title, self.lbl_sig, self.lbl_meta, self.lbl_diff):
                w.setText("")
            for b in (self.btn_load, self.btn_raw, self.btn_save):
                b.setEnabled(False)
            return
        for b in (self.btn_load, self.btn_raw, self.btn_save):
            b.setEnabled(True)
        ref = GT.get(p.guitar)
        tgt = GT.get(self.win.guitarra_key)
        self.lbl_title.setText(p.name)
        self.lbl_sig.setText(p.signature)
        genres_line = " · ".join(p.genres)
        if p.notes:
            genres_line += f"<br><br>{p.notes}"
        # Aviso de afinacao: sem ele, o usuario carrega um preset de Drop C com
        # a guitarra em Mi padrao e conclui que o preset e' ruim — quando o
        # problema e' a corda, nao o timbre.
        aviso_af = ""
        if getattr(p, "afinacao", ""):
            try:
                from . import tuner as TU
                af = TU.POR_CHAVE.get(p.afinacao)
                if af:
                    atual = ""
                    try:
                        atual = self.win.settings.get("afinacao") or TU.AFINACAO_PADRAO
                    except Exception:  # noqa: BLE001
                        atual = TU.AFINACAO_PADRAO
                    if atual != p.afinacao:
                        aviso_af = (f"<br><b style='color:#e8b84b'>⚠ Precisa de "
                                    f"{af.nome}</b> — sua guitarra está em "
                                    f"{TU.POR_CHAVE.get(atual, af).nome}. "
                                    f"Troque no seletor da aba Afinador.")
                    else:
                        aviso_af = (f"<br><b style='color:#5cc98c'>✓ Sua afinação "
                                    f"({af.nome}) já é a certa.</b>")
            except Exception:  # noqa: BLE001
                aviso_af = ""

        # Sugestão de IR: ADICIONA informação, não muda o preset. O gabinete de
        # fábrica continua no lugar; isto é para quem tem um IR melhor e quer
        # saber qual usar.
        ir_txt = ""
        try:
            from . import irs as IRS
            sug = IRS.get(p.key)
            if sug:
                cor = {"alta": "#5cc98c", "media": "#e8b84b"}.get(
                    sug.confianca, "#9aa")
                rot = {"alta": "combina", "media": "combina",
                       "aproximacao": "aproximação"}.get(
                    sug.confianca, sug.confianca)
                ir_txt = (
                    f"<br><br><b>IR ideal para este som</b> "
                    f"<span style='color:{cor}'>({rot})</span><br>"
                    f"<b>{sug.arquivo}</b><br>"
                    f"<span style='color:#9aa'>{sug.pasta} · {sug.caixa}</span><br>"
                    f"{sug.porque}<br>"
                    f"<span style='color:#9aa'>Importe no CubeSuite (banco 8) — "
                    f"o gabinete de fábrica do preset continua valendo se você "
                    f"não usar IR.</span>")
        except Exception:  # noqa: BLE001
            ir_txt = ""

        self.lbl_meta.setText(
            f"<b>Assinatura original:</b> {ref.label} ({ref.family})<br>"
            f"<b>Gêneros:</b> {genres_line}<br>"
            f"<b>Sua guitarra ({tgt.label}):</b> {tgt.character}"
            f"{aviso_af}{ir_txt}")
        changes = tgt.preview(p.params)
        if tgt.key == p.guitar:
            self.lbl_diff.setText(
                f"Pensado na {ref.label}, que é a sua guitarra: entra sem alteração."
            )
        elif changes:
            self.lbl_diff.setText(
                f"<b>Adaptado para {tgt.label}</b> mudaria: "
                + ", ".join(f"{n} {a}→{b}" for n, a, b in changes)
            )
        else:
            self.lbl_diff.setText(f"Adaptar para {tgt.label} não mudaria nada neste preset.")

    # ---- ações ----
    def load_selected(self) -> None:
        """Carrega o preset JÁ ADAPTADO à guitarra global escolhida."""
        p = self.current_preset()
        if not p:
            return
        tgt = self.win.guitarra_key
        self._load(p, p.adapted_for(tgt), adapted=True)

    def load_raw(self) -> None:
        """Carrega os valores originais, sem adaptar."""
        p = self.current_preset()
        if not p:
            return
        self._load(p, dict(p.params), adapted=False)

    def _load(self, p, params, adapted=True) -> None:
        """Carrega no slot atual. adapted=False marca o slot como valor cru,
        para a troca de guitarra não mexer nele."""
        self.win.pedal_tab.apply_params(p.name, params)
        self.win._preset_source[self.win.pedal_tab.slot] = p.key if adapted else None
        self.win.pedal_tab.refresh_voicing_note()
        self.win.tabs.setCurrentIndex(0)

    def save_selected(self) -> None:
        p = self.current_preset()
        if not p:
            return
        tgt = self.win.guitarra_key
        name = p.name if tgt == p.guitar else f"{p.name} ({GT.get(tgt).label})"
        PF.library_add(name, p.adapted_for(tgt))
        self.win.library.reload()
        self.win.status(f'"{name}" salvo na biblioteca.')


class DspDialog(QDialog):
    """Gate de ruído + normalização, com prévia ao vivo da cadeia."""

    def __init__(self, win: "MainWindow", path: str) -> None:
        super().__init__(win)
        self.setWindowTitle("Gate + Normalizar")
        self.resize(480, 380)
        self.path = path
        lay = QVBoxLayout(self)

        head = QLabel(f"<b>{Path(path).name}</b>")
        head.setWordWrap(True)
        lay.addWidget(head)

        self.ck_gate = QCheckBox("Cortar silêncio e ruído (gate)")
        self.ck_gate.setChecked(True)
        self.ck_gate.toggled.connect(self._refresh)
        lay.addWidget(self.ck_gate)

        g = QHBoxLayout()
        g.addWidget(QLabel(I18N.tr("limiar", I18N.get_idioma())))
        self.sp_gate = QSlider(Qt.Horizontal); self.sp_gate.setRange(-70, -20)
        self.sp_gate.setValue(-45)
        self.sp_gate.valueChanged.connect(self._refresh)
        self.lb_gate = QLabel("-45 dB")
        g.addWidget(self.sp_gate, 1); g.addWidget(self.lb_gate)
        lay.addLayout(g)

        self.ck_norm = QCheckBox("Igualar volume")
        self.ck_norm.setChecked(True)
        self.ck_norm.toggled.connect(self._refresh)
        lay.addWidget(self.ck_norm)

        m = QHBoxLayout()
        m.addWidget(QLabel(I18N.tr("modo_gate", I18N.get_idioma())))
        self.cb_mode = QComboBox()
        self.cb_mode.addItem("Pico (o mais alto fica no alvo)", "pico")
        self.cb_mode.addItem("Volume percebido (mais natural)", "rms")
        self.cb_mode.currentIndexChanged.connect(self._refresh)
        m.addWidget(self.cb_mode, 1)
        lay.addLayout(m)

        t = QHBoxLayout()
        t.addWidget(QLabel(I18N.tr("alvo", I18N.get_idioma())))
        self.sp_target = QSlider(Qt.Horizontal); self.sp_target.setRange(-60, -10)
        self.sp_target.setValue(-14)
        self.sp_target.valueChanged.connect(self._refresh)
        self.lb_target = QLabel("-14 dB")
        t.addWidget(self.sp_target, 1); t.addWidget(self.lb_target)
        lay.addLayout(t)

        self.lbl_prev = QLabel(); self.lbl_prev.setObjectName("sig"); self.lbl_prev.setWordWrap(True)
        lay.addWidget(self.lbl_prev)

        btns = QHBoxLayout(); btns.addStretch()
        cancel = QPushButton(I18N.tr("cancelar", I18N.get_idioma())); cancel.clicked.connect(self.reject)
        ok = QPushButton(I18N.tr("processar", I18N.get_idioma())); ok.setObjectName("primary")
        ok.clicked.connect(self._run)
        self.ok_btn = ok
        btns.addWidget(cancel); btns.addWidget(ok)
        lay.addLayout(btns)

        # O dialogo e' aberto com str() (o wave.open exige texto); o resto do
        # codigo prefere Path. Normaliza uma vez, aqui, para nao ter dois
        # formatos brigando dentro do mesmo objeto.
        self.path = Path(self.path)
        self._src: bytes | None = None
        self._peak = None
        self.erro: str | None = None
        self.lbl_erro = QLabel(""); self.lbl_erro.setWordWrap(True)
        self.lbl_erro.setStyleSheet("color:#e8734a; font-size:11px;")
        self.lbl_erro.hide()
        lay.addWidget(self.lbl_erro)
        self._refresh()

    def _load(self) -> bytes:
        """Le o WAV do take. Nunca levanta: um arquivo ruim tem de virar aviso
        na janela, nao um crash que fecha o programa.

        Western ja responds "file is truncated" para WAV com cabecalho pela
        metade, e EOFError para arquivo de 5 bytes — os dois casos sao
        arquivos corrompidos ou gravacao interrompida, nao bug do programa.
        """
        if self._src is None:
            import wave
            try:
                with wave.open(str(self.path), "rb") as w:
                    raw = w.readframes(w.getnframes())
                    ch = w.getnchannels()
            except (EOFError, wave.Error, OSError) as e:
                self.erro = (
                    f"Não consegui ler este take:\n{self.path.name}\n\n"
                    f"O arquivo está corrompido ou a gravação foi interrompida. "
                    f"({type(e).__name__})\n\n"
                    f"Você pode apagar o arquivo e gravar de novo."
                )
                self._src = b""
                return self._src
            if not raw:
                self.erro = f"'{self.path.name}' está vazio — nada foi gravado."
                self._src = b""
                return self._src
            if ch > 1:  # o programa grava estéreo duplicando o mono
                mono = bytearray()
                for off in range(0, len(raw), ch * 2):
                    mono += raw[off:off + 2]
                raw = bytes(mono)
            self._src = raw
            self._peak = DSP.peak_dbfs(raw)
        return self._src

    def _refresh(self) -> None:
        self.lb_gate.setText(f"{self.sp_gate.value()} dB")
        self.lb_target.setText(f"{self.sp_target.value()} dB")

        # 1o: o arquivo e' valido? Sem isto o usuario clica em Processar e leva
        # um erro de WAV em vez de um aviso util.
        raw = self._load()
        if self.erro:
            self.lbl_erro.setText(self.erro)
            self.lbl_erro.show()
            self.lbl_prev.setText("")
            self.ok_btn.setEnabled(False)
            return
        self.lbl_erro.hide()
        self.ok_btn.setEnabled(True)

        if not self.ck_gate.isChecked() and not self.ck_norm.isChecked():
            self.lbl_prev.setText("Nada será feito.")
            return
        parts = [f"Original: pico {self._peak:.1f} dBFS · {len(raw)//2/44100:.1f}s"]
        if self.ck_gate.isChecked():
            parts.append(f"gate corta abaixo de {self.sp_gate.value()} dB")
        if self.ck_norm.isChecked():
            modo = "pico" if self.cb_mode.currentData() == "pico" else "RMS"
            parts.append(f"normaliza ({modo}) para {self.sp_target.value()} dB")
        self.lbl_prev.setText(" · ".join(parts) + ".<br>O original não é alterado.")

    def _run(self) -> None:
        # O erro ja esta escrito no lbl_erro e o botao desabilitado. Um
        # QMessageBox aqui seria redundante — e modal trava a suite de testes,
        # que nao tem como clicar em "OK".
        if self.erro:
            return
        try:
            info = DSP.process_file(
                self.path,
                do_gate=self.ck_gate.isChecked(),
                do_norm=self.ck_norm.isChecked(),
                threshold_db=float(self.sp_gate.value()),
                target_db=float(self.sp_target.value()),
                mode=self.cb_mode.currentData() or "pico",
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Processar", str(exc))
            return
        bits = [f"Pico {info['antes_db']} → {info['depois_db']} dBFS"]
        if "gate_cortou_pct" in info:
            bits.append(f"gate cortou {info['gate_cortou_pct']}% do silêncio")
        if "normalizou_db" in info:
            bits.append(f"ganho {info['normalizou_db']:+.1f} dB")
        self.accept()
        self.win.audio_tab.reload_takes()
        self.win.status(f"{info['saida']} — " + ", ".join(bits))


class AudioTab(QWidget):
    """Ouvir e gravar a guitarra sem sair do programa: entrada, VU, gravação, takes."""

    def __init__(self, win: "MainWindow") -> None:
        super().__init__()
        self.win = win
        self.recorder = AU.Recorder()
        self.player = AU.Player()
        self.monitor = AU.Monitor()
        self._takes: list[str] = []

        lay = QVBoxLayout(self)

        # ---- dispositivos ----
        devs = QHBoxLayout()
        self.cb_in = QComboBox(); self.cb_in.setMinimumWidth(240)
        self.cb_in.addItems(AU.list_inputs())
        self.cb_in.setToolTip(GU.audio_tip("input"))
        self.cb_out = QComboBox(); self.cb_out.setMinimumWidth(240)
        self.cb_out.addItems(AU.list_outputs())
        self.cb_out.setToolTip(GU.audio_tip("output"))
        self.btn_refresh = QPushButton(I18N.tr("atualizar_btn", I18N.get_idioma())); self.btn_refresh.setObjectName("ghost")
        self.btn_refresh.clicked.connect(self.reload_devices)
        for w in (QLabel(I18N.tr("entrada_audio", I18N.get_idioma())), self.cb_in, QLabel(I18N.tr("saida_audio", I18N.get_idioma())), self.cb_out, self.btn_refresh):
            devs.addWidget(w)
        devs.addStretch()
        lay.addLayout(devs)

        ins = AU.list_inputs()
        if ins:
            self.cb_in.setCurrentIndex(AU.guess_input(ins))

        # ---- monitor ao vivo: o botão principal ----
        mon = QHBoxLayout()
        # Tamanho de bloco: a mesma ideia do Reaper. Menor = menos latencia,
        # mas mais chance de estouro se a maquina nao acompanhar.
        lbl_b = QLabel("Latência:"); lbl_b.setStyleSheet("color:#8f8b83;")
        self.cb_block = QComboBox()
        for _b in AU.BLOCK_SIZES:
            _rot = {128: "mínima (risco de estouro)", 256: "baixa",
                    512: "igual ao Reaper", 1024: "alta",
                    2048: "máxima (segura)"}.get(_b, str(_b))
            self.cb_block.addItem(f"{_b} amostras — {_rot}", _b)
        self.cb_block.setCurrentIndex(AU.BLOCK_SIZES.index(AU.DEFAULT_BLOCK))
        self.cb_block.setToolTip(
            "Quanto menor o bloco, menor a latência entre tocar a nota e ouvir.\n"
            "Se o áudio picotar (estalos), aumente. O Reaper usa 512 amostras.")
        self.cb_block.currentIndexChanged.connect(self.preview_latency)
        self.lbl_lat = QLabel(""); self.lbl_lat.setStyleSheet(
            "color:#f0812a; font-size:11px;")
        mon.addWidget(lbl_b); mon.addWidget(self.cb_block); mon.addWidget(self.lbl_lat)

        # Prioridade da thread de áudio (espelha o "Audio Thread Priority"
        # do Reaper). O Qt Multimedia não expõe isso; aplicamos via ctypes
        # (SetThreadPriority) na thread onde o áudio roda.
        mon.addSpacing(12)
        lbl_p = QLabel("Prioridade:"); lbl_p.setStyleSheet("color:#8f8b83;")
        self.cb_prio = QComboBox()
        for _k, (_nome, _v) in AU.PRIORIDADES.items():
            self.cb_prio.addItem(_nome, _k)
        self.cb_prio.setCurrentIndex(
            list(AU.PRIORIDADES).index("normal"))
        self.cb_prio.setToolTip(
            "Prioridade que o Windows dá à thread de áudio.\n"
            "Normal: padrão.\n"
            "Alta: mais CPU para o áudio.\n"
            "Crítica: igual ao Reaper (Time Critical) — menos risco de\n"
            "estouro, mas pode deixar outros programas lentos.\n"
            "Tempo real: máximo; use se a máquina aguentar.")
        mon.addWidget(lbl_p); mon.addWidget(self.cb_prio)

        self.btn_mon = QPushButton(I18N.tr("ouvir_ao_vivo", I18N.get_idioma())); self.btn_mon.setObjectName("primary")
        self.btn_mon.setCheckable(True)
        self.btn_mon.setToolTip(GU.audio_tip("monitor"))
        self.btn_mon.toggled.connect(self.toggle_monitor)
        self.sld_mon = QSlider(Qt.Horizontal)
        self.sld_mon.setRange(0, 100); self.sld_mon.setValue(80)
        self.sld_mon.setFixedWidth(150)
        self.sld_mon.setToolTip(I18N.tr("volume_monitor_tip", I18N.get_idioma()))
        self.sld_mon.valueChanged.connect(self.on_monitor_volume)
        self.lbl_mon = QLabel(I18N.tr("monitor_desligado", I18N.get_idioma())); self.lbl_mon.setObjectName("sig")
        for w in (self.btn_mon, QLabel(I18N.tr("volume_lbl", I18N.get_idioma())), self.sld_mon, self.lbl_mon):
            mon.addWidget(w)
        mon.addStretch()
        lay.addLayout(mon)

        # ---- medidor ----
        meter = QHBoxLayout()
        self.bar = LevelBar()
        self.bar.setToolTip(GU.audio_tip("level"))
        self.lbl_db = QLabel("—"); self.lbl_db.setObjectName("muted")
        meter.addWidget(self.bar, 1); meter.addWidget(self.lbl_db)
        lay.addLayout(meter)

        # ---- gravação ----
        rec = QHBoxLayout()
        self.btn_rec = QPushButton(I18N.tr("gravar_btn", I18N.get_idioma())); self.btn_rec.setObjectName("primary")
        self.btn_rec.setToolTip(GU.audio_tip("record"))
        self.btn_rec.clicked.connect(self.toggle_record)
        self.lbl_time = QLabel("00:00"); self.lbl_time.setObjectName("muted")
        self.lbl_state = QLabel(I18N.tr("pronto_gravar", I18N.get_idioma())); self.lbl_state.setObjectName("sig")
        for w in (self.btn_rec, self.lbl_time, self.lbl_state):
            rec.addWidget(w)
        rec.addStretch()
        lay.addLayout(rec)

        # ---- takes ----
        self.lst_takes = QListWidget()
        self.lst_takes.itemDoubleClicked.connect(lambda _: self.play_selected())
        lay.addWidget(self.lst_takes, 1)

        row = QHBoxLayout()
        row = QHBoxLayout()
        self.btn_play = QPushButton(I18N.tr("ouvir_btn", I18N.get_idioma()))
        self.btn_play.clicked.connect(self.play_selected)
        self.btn_play.setToolTip(GU.audio_tip("latency"))
        self.btn_dsp = QPushButton(I18N.tr("gate_normalizar", I18N.get_idioma()))
        self.btn_dsp.setObjectName("primary")
        self.btn_dsp.setToolTip(GU.audio_tip("dsp"))
        self.btn_dsp.clicked.connect(self.open_dsp)
        self.btn_open = QPushButton("Abrir em outro programa...")
        self.btn_open.setObjectName("ghost")
        self.btn_open.clicked.connect(self.open_selected)
        self.btn_del = QPushButton("Excluir")
        self.btn_del.setObjectName("ghost")
        self.btn_del.clicked.connect(self.delete_selected)
        for b in (self.btn_play, self.btn_dsp, self.btn_open, self.btn_del):
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)

        # ---- sinais ----
        self.recorder.level.connect(self.on_level)
        self.recorder.elapsed.connect(lambda s: self.lbl_time.setText(AU.seconds_label(s)))
        self.recorder.finished.connect(self.on_recorded)
        self.recorder.failed.connect(lambda m: (self.set_idle(), self.win.status(m)))
        self.monitor.failed.connect(self.on_monitor_failed)
        self.monitor.stopped.connect(lambda: self.lbl_mon.setText("Monitor desligado"))
        self.monitor.level.connect(self.on_level)
        # O mesmo nível aparece no bloco "Saída" da aba Pedal: assim dá para
        # ver o volume enquanto mexe nos parâmetros, sem trocar de aba.
        self.monitor.level.connect(self.win.pedal_tab.set_out_level)
        self.player.finished.connect(lambda: self.win.status("Tocação terminada."))
        self.player.failed.connect(lambda m: self.win.status(m))
        self.reload_takes()

    # ---- estado ----
    def preview_latency(self) -> None:
        """Latencia estimada antes de ligar o monitor (ida + volta)."""
        rate = 48000
        try:
            ins = QMediaDevices.audioInputs()
            if ins and 0 <= self.cb_in.currentIndex() < len(ins):
                rate = AU.native_rate(ins[self.cb_in.currentIndex()])
        except Exception:  # noqa: BLE001
            pass
        self.lbl_lat.setText(f"~{AU.latency_ms(self.cb_block.currentData(), rate):.0f} ms")

    def toggle_monitor(self, on: bool) -> None:
        """Liga/desliga o monitor ao vivo. É isto que "ouvir" quer dizer:
        ouvir a guitarra em tempo real, não tocar uma gravação."""
        if on:
            if self.recorder.recording:
                # Gravação e monitor ao vivo disputam a entrada; gravar já
                # entrega o sinal, então o monitor é redundante e só atrapalha.
                QMessageBox.information(
                    self, "Monitor",
                    "Já existe uma gravação em andamento. Pare a gravação para ligar o monitor ao vivo."
                )
                self.btn_mon.setChecked(False)
                return
            prio = self.cb_prio.currentData()
            if prio not in AU.PRIORIDADES:
                prio = "normal"
            self.monitor.start(self.cb_in.currentIndex(), self.cb_out.currentIndex(),
                               self.sld_mon.value() / 100.0,
                               block=self.cb_block.currentData(),
                               prioridade=prio)
            self.lbl_lat.setText(
                f"~{self.monitor.estimated_latency_ms():.0f} ms "
                f"({self.monitor.block} amostras a "
                f"{self.monitor.rate // 1000} kHz)")
            if not self.monitor.active:
                self.btn_mon.setChecked(False)  # o start falhou; desmarca
            else:
                self.player.stop()
                self.lbl_mon.setText("Monitor ligado — toque para ouvir.")
                self.win.status(
                    f"Monitor ao vivo: {self.cb_in.currentText()} → {self.cb_out.currentText()}"
                )
        else:
            self.monitor.stop()
            self.lbl_mon.setText("Monitor desligado")
            self.win.status("Monitor desligado.")

    def on_monitor_failed(self, msg: str) -> None:
        # Falha ao ligar o monitor desmarca o botão: deixar marcado um controle
        # que não está ligado é pior que não ter o controle.
        self.btn_mon.blockSignals(True)
        self.btn_mon.setChecked(False)
        self.btn_mon.blockSignals(False)
        self.lbl_mon.setText(msg)
        self.win.status(msg)

    def on_monitor_volume(self, v: int) -> None:
        self.monitor.set_volume(v / 100.0)

    def set_idle(self) -> None:
        self.recorder.recording = False
        self.btn_rec.setText("● Gravar")
        self.btn_rec.setObjectName("primary")
        self.btn_rec.style().unpolish(self.btn_rec)
        self.btn_rec.style().polish(self.btn_rec)

    def toggle_record(self) -> None:
        if self.recorder.recording:
            self.btn_rec.setText("■ Parar")
            self.btn_rec.setObjectName("")
            self.recorder.stop()
            return
        self.bar._level = 0.0
        self.bar._clip = False
        self.bar.update()
        self.recorder.start(self.cb_in.currentIndex())
        if self.recorder.recording:
            self.btn_rec.setText("■ Parar")
            self.lbl_state.setText("Gravando... toque a guitarra.")
            self.win.status(f"Gravando de '{self.cb_in.currentText()}'.")

    def on_level(self, v: float) -> None:
        self.bar.set_level(v)
        # 0 dBFS = 1.0. O log só é confiável acima de -60 dB; abaixo disso é
        # silêncio e mostrar "-60 dB" só ocupa espaço.
        import math
        if v <= 0.0002:
            self.lbl_db.setText("—")
        else:
            db = max(-60.0, 20 * math.log10(v))
            self.lbl_db.setText(f"{db:+.0f} dB")

    def on_recorded(self, path: str) -> None:
        self.set_idle()
        self.lbl_state.setText("Gravado.")
        self.win.status(f"Gravação salva em {path}")
        self.reload_takes(path)

    # ---- takes ----
    def reload_takes(self, select: str | None = None) -> None:
        self.lst_takes.clear()
        self._takes = sorted(AU.recordings_dir().glob("*.wav"), reverse=True)
        if not self._takes:
            vazio = QListWidgetItem("Nenhuma gravação ainda.\n\n"
                                    "Ligue 'Ouvir ao vivo' para ouvir a guitarra, "
                                    "ou clique em Gravar para guardar um take.")
            vazio.setFlags(Qt.ItemFlag.NoItemFlags)
            vazio.setForeground(Qt.GlobalColor.gray)
            self.lst_takes.addItem(vazio)
            return
        for f in self._takes:
            try:
                size_kb = f.stat().st_size / 1024
            except OSError:
                size_kb = 0
            # Um WAV de verdade tem no minimo 44 bytes de cabecalho. Abaixo
            # disso o arquivo esta quebrado — e_break o avisa na lista em vez
            # de deixar o usuario descobrir quando clicar nele.
            quebrado = f.stat().st_size < 44
            nome = f.stem.replace("cuba-", "")
            if quebrado:
                txt = f"{nome}   ·   arquivo quebrado ({f.stat().st_size} B)"
            else:
                txt = f"{nome}   ·   {size_kb:.0f} KB"
            it = QListWidgetItem(txt)
            if quebrado:
                it.setForeground(QColor("#e8734a"))
                it.setToolTip("Este arquivo não é um WAV válido. "
                              "Apague-o ou grave de novo.")
            it.setData(Qt.UserRole, str(f))
            self.lst_takes.addItem(it)
        if self._takes:
            self.lst_takes.setCurrentRow(0)
        if select:
            for i in range(self.lst_takes.count()):
                if self.lst_takes.item(i).data(Qt.UserRole) == select:
                    self.lst_takes.setCurrentRow(i)
                    break

    def _current(self) -> str:
        it = self.lst_takes.currentItem()
        return it.data(Qt.UserRole) if it else ""

    def play_selected(self) -> None:
        p = self._current()
        if p:
            self.player.play(p)
            self.win.status(f"Tocando {Path(p).name}.")

    def open_dsp(self) -> None:
        p = self._current()
        if p:
            DspDialog(self.win, p).exec()

    def open_selected(self) -> None:
        p = self._current()
        if p:
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))

    def delete_selected(self) -> None:
        p = self._current()
        if p and QMessageBox.question(self, "Excluir", f"Excluir {Path(p).name}?") == QMessageBox.Yes:
            Path(p).unlink(missing_ok=True)
            self.reload_takes()

    def reload_devices(self) -> None:
        self.cb_in.clear(); self.cb_in.addItems(AU.list_inputs())
        self.cb_out.clear(); self.cb_out.addItems(AU.list_outputs())
        ins = AU.list_inputs()
        if ins:
            self.cb_in.setCurrentIndex(AU.guess_input(ins))
        self.win.status("Dispositivos de áudio atualizados.")

    def close_all(self) -> None:
        self.monitor.stop()
        if self.recorder.recording:
            self.recorder.stop()
        self.player.stop()


class LibraryTab(QWidget):
    def __init__(self, win: "MainWindow") -> None:
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        self.listw = QListWidget()
        self.listw.itemDoubleClicked.connect(lambda _: self.load_selected())
        lay.addWidget(self.listw, 1)
        row = QHBoxLayout()
        for text, fn, primary in (
            ("Carregar no slot atual", self.load_selected, True),
            ("Importar arquivos...", self.import_files, False),
            ("Exportar...", self.export_selected, False),
            ("Excluir", self.delete_selected, False),
            ("Abrir pasta", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(PF.library_dir()))), False),
        ):
            b = QPushButton(text); b.clicked.connect(fn)
            if primary:
                b.setObjectName("primary")
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        self.reload()

    def reload(self) -> None:
        self.listw.clear()
        itens = PF.library_list()
        if not itens:
            # Lista vazia sem explicação parece programa quebrado.
            vazio = QListWidgetItem("Nenhum preset salvo ainda.\n\n"
                                    "Use 'Salvar na biblioteca' na aba Pedal, ou "
                                    "importa um arquivo .json.")
            vazio.setFlags(Qt.ItemFlag.NoItemFlags)
            vazio.setForeground(Qt.GlobalColor.gray)
            self.listw.addItem(vazio)
            self.win.status("Biblioteca vazia.")
            return
        for path, name, p in itens:
            it = QListWidgetItem(f"{name}\n{P.PREAMP_TYPES[p['type']][1]} · ganho {p['gain']} · cab {p['cabinet']} · vol {p['volume']}")
            it.setData(Qt.UserRole, (str(path), name, p))
            self.listw.addItem(it)

    def _current(self):
        it = self.listw.currentItem()
        return it.data(Qt.UserRole) if it else None

    def load_selected(self) -> None:
        cur = self._current()
        if cur:
            self.win.pedal_tab.apply_params(cur[1], cur[2])
            self.win.tabs.setCurrentIndex(0)

    def import_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar presets", str(Path.home()), "Presets (*.json)")
        n = 0
        for p in paths:
            try:
                presets, _ = PF.load_file(p)
                for pr in presets:
                    PF.library_add(pr["name"], pr["params"]); n += 1
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "Importar", f"{Path(p).name}: {exc}")
        self.reload(); self.win.status(f"{n} preset(s) importado(s).")

    def export_selected(self) -> None:
        cur = self._current()
        if not cur:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", str(Path.home() / f"{cur[1]}.json"), "Preset (*.json)")
        if path:
            PF.save_file(path, cur[1], cur[2])

    def delete_selected(self) -> None:
        cur = self._current()
        if cur and QMessageBox.question(self, "Excluir", f'Excluir "{cur[1]}" da biblioteca?') == QMessageBox.Yes:
            Path(cur[0]).unlink(missing_ok=True); self.reload()


class TocandoTab(QWidget):
    """A aba de quem esta tocando: cadeia, estilo e as tres somadas.

    Primeira aba de propósito. Quem abre o programa quer ouvir algo, não
    entender a interface — e a cadeia mostra, de relance, o que o som está
    fazendo e onde mexer.
    """

    def __init__(self, win: "MainWindow", parent=None) -> None:
        super().__init__(parent)
        self.win = win
        self._somadas = SOM.carregar()
        self._idx_somada = 0

        # QScrollArea: sem isto, numa janela pequena o conteudo e' cortado e o
        # que sobra fica inalcançavel. Funcionava em tela cheia so porque a altura
        # bastava; em janela normal quebrava.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        # O conteudo rola so em VERTICAL. Sem travar isto, o corpo do scroll
        # cresce para acomodar o width "desejado" dos filhos e chega a 5937px —
        # a cadeia entao mede 5901px e desenha blocos de 818px, sobrepostos.
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: 0; }")
        body = QWidget(); body.setObjectName("tocando_body")
        root = QVBoxLayout(body)
        root.setContentsMargins(18, 12, 18, 12)
        root.setSpacing(8)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)
        self._scroll.setWidget(body)

        from . import i18n
        _lang = i18n.get_idioma()
        cab = QHBoxLayout()
        ttl = QLabel(i18n.tr("aba_tocando", _lang))
        ttl.setStyleSheet("font-size:16px; font-weight:600; color:#f0812a;")
        cab.addWidget(ttl)
        self.lbl_atalho = QLabel("")
        self.lbl_atalho.setStyleSheet("color:#8f8b83; font-size:11px;")
        cab.addStretch(); cab.addWidget(self.lbl_atalho)
        root.addLayout(cab)

        # ---- cadeia ----
        self.chain = CHN.SignalChain()
        self.chain.bloco_escolhido.connect(self._ir_para_bloco)
        self.chain.bloco_ajustado.connect(self._ajustar_bloco)
        root.addWidget(self.chain)

        # ---- somadas ----
        root.addWidget(self._rotulo(i18n.tr("timbre_bolso", _lang)))
        self.btns_somada: list[QPushButton] = []
        linha = QHBoxLayout()
        for i in range(SOM.MAX_SOMADAS):
            b = QPushButton()
            b.setCheckable(True)
            b.setMinimumHeight(56)
            b.setToolTip(
                f"{i18n.tr('tecla', _lang)} {i + 1}\n\n"
                f"{i18n.tr('somada_vazia_tip', _lang)}\n"
                f"{i18n.tr('somada_cheia_tip', _lang)}")
            b.clicked.connect(lambda _c=False, n=i: self.aplicar_somada(n))
            # Sem largura minima pequena, o texto longo faz cada botao pedir
            # ~1959px e o corpo do scroll cresce para 5937px (a cadeia entao
            # desenha blocos sobrepostos). O tooltip carrega o texto completo.
            b.setMinimumWidth(120)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            linha.addWidget(b, 1)
            self.btns_somada.append(b)
        root.addLayout(linha)

        dica = QLabel(
            i18n.tr("como_usar_somada", _lang))
        dica.setObjectName("sig")
        dica.setWordWrap(True)
        root.addWidget(dica)

        # ---- estilo ----
        root.addWidget(self._rotulo(i18n.tr("oque_ouvindo", _lang)))
        self.meter = CHN.StyleMeter()
        root.addWidget(self.meter, 0)

        self._atualiza_botoes()

    def _rotulo(self, txt: str) -> QLabel:
        l = QLabel(txt)
        l.setStyleSheet("color:#8f8b83; font-size:9px; font-weight:700;")
        return l

    # ---- somadas ----
    def aplicar_somada(self, indice: int) -> None:
        s = self._somadas[indice]
        if s is None:
            self.gravar_somada(indice)
            return
        params = {n: int(v) for n, v in s["params"].items()}
        pt = self.win.pedal_tab
        for n, v in params.items():
            if n in pt.rows:
                pt.rows[n].set_value(v)
            elif n in pt.toggles:
                pt.toggles[n].setChecked(bool(v))
            pt.params[pt.slot][n] = v
        pt.refresh_widgets()
        self.refresh()
        if self.win.pedal and self.win.pedal.connected:
            for n, v in params.items():
                self.win.pedal.write_live_param(pt.slot, n, v)
        self.win.status(f"Tecla {indice + 1}: {s.get('nome', 'somada')}")

    def gravar_somada(self, indice: int) -> None:
        """Guarda o timbre atual na somada. Sem perguntar nome: o programa ja
        tem um nome util — o do preset de origem, ou 'Meu timbre'."""
        pt = self.win.pedal_tab
        params = {n: int(pt.params[pt.slot].get(n, 0)) for n in P.PARAM_NAMES}
        nome = pt.preset_atual or f"Slot {pt.slot}"
        self._somadas[indice] = SOM.do_tempo_atual(params, nome)
        SOM.salvar(self._somadas)
        self._atualiza_botoes()
        self.win.status(f"Tecla {indice + 1} guardada com o timbre atual.")

    def limpar_somada(self, indice: int) -> None:
        self._somadas[indice] = None
        SOM.salvar(self._somadas)
        self._atualiza_botoes()

    def _atualiza_botoes(self) -> None:
        for i, b in enumerate(self.btns_somada):
            s = self._somadas[i]
            nome = SOM.nome_de(s, i)
            desc = SOM.descrever(s)
            b.setText(f"<b>{i + 1}</b>  {nome}")
            b.setChecked(i == self._idx_somada)
            b.setStyleSheet(
                "QPushButton { text-align:left; padding:6px 10px; border:1px solid #4a4a55;"
                "border-radius:6px; background:#242427; color:#c9a227; }"
                "QPushButton:hover { border-color:#f0812a; background:#2b2b2f; }"
                "QPushButton:checked { border-color:#f0812a; background:#2e2620; }")

    def _ir_para_bloco(self, bid: str) -> None:
        """Clique na cadeia leva ao controle. E o que a cadeia e: mapa.
        (Guitarra/Saida/Pre-amp nao tem valor simples de ciclar, entao so
        navegam — os demais blocos mudam o som direto via _ajustar_bloco.)"""
        self.win.tabs.setCurrentIndex(1)   # aba Pedal
        pt = self.win.pedal_tab
        alvo = {"preamp": "type", "cabinet": "cabinet", "mod": "modulation",
                "delay": "mix", "reverb": "reverb", "saida": "volume",
                "entrada": "gain"}.get(bid)
        if alvo is None:
            return
        pt._set_mode("avancado")
        self.win.status(f"{bid}: mexa no controle '{alvo}' da aba Pedal.")

    def _ajustar_bloco(self, bid: str, delta: int) -> None:
        """Cicla o parâmetro do bloco na cadeia, ao vivo, sem trocar de aba."""
        prm = _param_do_bloco(bid)
        if prm is None:
            self._ir_para_bloco(bid)
            return
        pt = self.win.pedal_tab
        maximo = _bloco_max(bid)
        cur = int(pt.params[pt.slot].get(prm, 0))
        novo = (cur + delta) % (maximo + 1)
        pt.params[pt.slot][prm] = novo
        if prm in pt.rows:
            pt.rows[prm].set_value(novo)
        # liga o bloco se ele tem um interruptor proprio (delay, cab, mod, reverb)
        # Modulação e Reverb NÃO têm chave liga/desliga — só Gabinete (IR) e
        # Delay têm. Delay liga o delaySection; gabinete liga o irSection.
        secoes = {"cabinet": "irSection", "delay": "delaySection"}
        if bid in secoes:
            sw = secoes[bid]
            if sw in pt.toggles:
                # setChecked(True) dispara on_param que re-sincroniza o estado;
                # aqui setamos DIRETO (blockSignals) para evitar o loop do guard.
                cb = pt.toggles[sw]
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
                pt.params[pt.slot][sw] = 1
        # envia ao pedal se conectado
        if self.win.pedal and self.win.pedal.connected:
            self.win.pedal.write_live_param(pt.slot, prm, novo)
            if _bloco_trava(bid) and bid in secoes:
                self.win.pedal.write_live_param(pt.slot, secoes[bid], 1)
        self.refresh()
        nome_qld = {"cabinet": "Gabinete", "mod": "Modulação",
                    "delay": "Delay", "reverb": "Reverb"}.get(bid, bid)
        self.win.status(f"{nome_qld}: {novo} (clique = +1, Shift+clique = -1)")

    # ---- atualizacao ----
    def refresh(self) -> None:
        pt = self.win.pedal_tab
        params = pt.params.get(pt.slot) or {}
        self.chain.atualizar(params, pt.slot)
        self.meter.atualizar("", [], {})

def _param_do_bloco(bid: str) -> str | None:
    """De qual parâmetro do pedal o bloco da cadeia manda."""
    return {"cabinet": "cabinet", "mod": "modulation", "delay": "mix",
            "reverb": "reverb"}.get(bid)


def _bloco_max(bid: str) -> int:
    """Faixa superior do parâmetro do bloco (para ciclar sem estourar)."""
    prm = _param_do_bloco(bid)
    if prm == "mix":
        return 118
    if prm == "cabinet" or prm == "modulation":
        return 8
    return 15


def _bloco_trava(bid: str) -> bool:
    """O bloco 'delay' cicla o tempo/mix do delay (no pedal, delaySection e que
    liga). Os outros sao livres. Aqui sempre retorna True (liga o bloco se o
    parametro foi mexido)."""
    return True


class MainWindow(QMainWindow):
    def __init__(self, settings: "Settings | None" = None) -> None:
        super().__init__()
        self.setWindowTitle(f"CUBE Baby Unleashed {__version__}")
        self.settings = settings or Settings()
        # Tamanho mínimo FÍSICO. O tab Pedal (o mais alto) precisa de ~611px de
        # conteudo mais o cabecalho/painel/abas (~151px). Travar em ~795 garante
        # que NENHUMA aba corte quando a janela e' reduzida — quem toca com uma
        # mao nao pode estar protegendo contra corte a cada redimensionamento.
        self.resize(1200, 880)
        self.setMinimumSize(1040, 840)
        self.pedal: BasePedal | None = None
        self.runner = Runner()
        # De qual preset curado veio cada slot. None = valor manual do usuário,
        # que não deve ser re-adaptado ao trocar de guitarra.
        self._preset_source: dict[str, str | None] = {s: None for s in P.SLOT_IDS}

        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(14, 10, 14, 6)
        lay.setSpacing(6)

        # ---------- cabeçalho de marca ----------
        # Sem isto a janela "começa" no meio dos controles e o canto superior
        # esquerdo fica pendurado no vazio. Uma marca real dá a âncora visual e
        # diz o que o programa é, antes de qualquer botão.
        head = QHBoxLayout()
        self.lbl_logo = QLabel("◑")
        self.lbl_logo.setStyleSheet(
            f"color:{T.ACCENT}; font-size:26px; font-weight:700;")
        self.lbl_logo.setToolTip("CUBE Baby Unleashed — editor de timbre independente")
        bloco_nome = QVBoxLayout()
        bloco_nome.setSpacing(0)
        self.lbl_brand = QLabel("CUBE BABY UNLEASHED")
        self.lbl_brand.setStyleSheet(
            f"color:{T.FG}; font-size:16px; font-weight:700; letter-spacing:1px;")
        self.lbl_tag = QLabel("Editor de timbre para o pedal CUVAVE · M-VAVE CUBE Baby")
        self.lbl_tag.setObjectName("muted")
        self.lbl_tag.setStyleSheet(f"color:{T.FG_MUTED}; font-size:{T.FS_TINY};")
        bloco_nome.addWidget(self.lbl_brand)
        bloco_nome.addWidget(self.lbl_tag)
        head.addWidget(self.lbl_logo)
        head.addSpacing(6)
        head.addLayout(bloco_nome, 1)
        # versão no canto direito do cabeçalho
        self.lbl_version = QLabel(f"v{__version__}")
        self.lbl_version.setStyleSheet(f"color:{T.FG_MUTED}; font-size:{T.FS_TINY};")
        head.addWidget(self.lbl_version, 0, Qt.AlignmentFlag.AlignVCenter)

        # seletor de idioma
        from . import i18n
        idioma_salvo = "pt"
        try:
            idioma_salvo = self.settings.get("idioma") or "pt"
        except Exception:  # noqa: BLE001
            pass
        if idioma_salvo in i18n.IDIOMAS:
            i18n.set_idioma(idioma_salvo)
        self.cb_idioma = QComboBox()
        self.cb_idioma.setFixedWidth(110)
        for cod, nome in i18n.IDIOMAS.items():
            self.cb_idioma.addItem(nome, cod)
        self.cb_idioma.setCurrentIndex(
            list(i18n.IDIOMAS).index(i18n.get_idioma()))
        self.cb_idioma.currentIndexChanged.connect(self._trocar_idioma)
        head.addWidget(self.cb_idioma, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(head)

        conn = QHBoxLayout()
        self.cb_in, self.cb_out = QComboBox(), QComboBox()
        for c in (self.cb_in, self.cb_out):
            c.setMinimumWidth(190)
        from . import i18n
        _lang = i18n.get_idioma()
        self.btn_refresh = QPushButton(i18n.tr("Atualizar portas", _lang)); self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect = QPushButton(i18n.tr("Conectar", _lang)); self.btn_connect.setObjectName("primary"); self.btn_connect.clicked.connect(self.toggle_connection)
        self.btn_sim = QPushButton(i18n.tr("Modo simulado", _lang)); self.btn_sim.clicked.connect(self.start_simulated)
        self.lbl_state = QLabel(f"● {i18n.tr('desconectado', _lang)}"); self.lbl_state.setStyleSheet("color:#8b93a1")
        for w in (QLabel(i18n.tr("entrada", _lang)), self.cb_in, QLabel(i18n.tr("saida_lbl", _lang)), self.cb_out, self.btn_refresh, self.btn_connect, self.btn_sim):
            conn.addWidget(w)
        conn.addStretch(); conn.addWidget(self.lbl_state)

        # ---- barra da guitarra: ajuste GLOBAL, não um filtro ----
        gbar = QHBoxLayout()
        self.lbl_guitar = QLabel(i18n.tr("minha_guitarra", _lang))
        self.lbl_guitar.setToolTip(
            "A guitarra muda o timbre final. O programa ajusta os valores de todos os "
            "slots automaticamente quando você troca aqui.")
        self.cb_guitar = QComboBox(); self.cb_guitar.setMinimumWidth(300)
        for g in GT.GUITARS:
            # one_line() inclui a posição: sem isso as três Strat HSS seriam
            # três linhas idênticas no dropdown.
            self.cb_guitar.addItem(g.one_line(), g.key)
        self.cb_guitar.setCurrentIndex([g.key for g in GT.GUITARS].index(GT.DEFAULT_GUITAR))
        self.cb_guitar.currentIndexChanged.connect(self.on_guitar_changed)
        self.lbl_guitar_tip = QLabel(); self.lbl_guitar_tip.setObjectName("sig")
        for w in (self.lbl_guitar, self.cb_guitar, self.lbl_guitar_tip):
            gbar.addWidget(w)
        gbar.addStretch()
        # Botão de ajuda global: não pode depender de o usuário estar numa aba.
        self.btn_help = QPushButton(i18n.tr("ajuda_btn", _lang))
        self.btn_help.setObjectName("ghost")
        self.btn_help.setFixedWidth(88)
        self.btn_help.setToolTip(I18N.tr("ajuda_tooltip", I18N.get_idioma()))
        self.btn_help.clicked.connect(lambda: HelpDialog(self).exec())
        gbar.addWidget(self.btn_help)

        # As duas barras (conexão + guitarra) num ÚNICO painel. Antes elas
        # flutuavam soltas sobre o fundo, e cada uma parecia uma linha
        # perdida no vazio. Unidas, formam a "bancada" de setup do programa.
        self.panel_conexao = QWidget(); self.panel_conexao.setObjectName("panel")
        pconn = QVBoxLayout(self.panel_conexao)
        pconn.setContentsMargins(10, 4, 10, 6)
        pconn.setSpacing(4)
        pconn.addLayout(conn)
        pconn.addLayout(gbar)
        lay.addWidget(self.panel_conexao)
        lay.addLayout(gbar)

        self.tabs = QTabWidget()
        self.aba_tocando = TocandoTab(self)
        self.tabs.addTab(self.aba_tocando, i18n.tr("aba_tocando", _lang))
        self.pedal_tab = PedalTab(self)
        self.presets_tab = PresetsTab(self)
        self.audio_tab = AudioTab(self)
        self.library = LibraryTab(self)
        self.tabs.addTab(self.pedal_tab, i18n.tr("aba_pedal", _lang))
        self.tabs.addTab(self.presets_tab, i18n.tr("aba_presets", _lang))
        self.tabs.addTab(self.audio_tab, i18n.tr("aba_audio", _lang))
        self.tuner_tab = TUN.TunerPanel(self)
        # O afinador precisa saber se o Monitor já abriu a entrada. Se abriu,
        # o afinador usa o MESMO device em vez de abrir um segundo
        # QAudioSource — dois consumidores na mesma entrada WASAPI faziam o
        # Windows dividir o buffer e o som pipocava.
        self.tuner_tab.monitor = self.audio_tab.monitor
        self.tabs.addTab(self.tuner_tab, i18n.tr("aba_afinador", _lang))
        self.ir_tab = IrTab(self)
        self.tabs.addTab(self.ir_tab, i18n.tr("aba_ir", _lang))
        self.tabs.addTab(self.library, i18n.tr("aba_biblioteca", _lang))
        from .ui_donate import DonateTab
        self.donate_tab = DonateTab(self)
        self.tabs.addTab(self.donate_tab, i18n.tr("aba_apoiar", _lang))
        lay.addWidget(self.tabs, 1)

        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setTextVisible(False); self.progress.hide()
        self.runner.progress.connect(self.progress.setValue)
        lay.addWidget(self.progress)

        foot = QLabel(I18N.tr("projeto_independente", I18N.get_idioma()) + ", " + I18N.tr("nao_afiliado", I18N.get_idioma()) + " " + I18N.tr("backup_presets", I18N.get_idioma()))
        foot.setObjectName("muted"); lay.addWidget(foot)

        # reflete o modo salvo no switch, SEM disparar toggle_mode de novo
        self.pedal_tab.sw_modo.blockSignals(True)
        self.pedal_tab.sw_modo.setChecked(self.pedal_tab.mode == "avancado")
        self.pedal_tab.sw_modo.blockSignals(False)
        self._install_shortcuts()
        self.pedal_tab.set_enabled_pedal(False)
        self.refresh_ports()
        self._restore_state()

    # ---- atalhos de teclado -------------------------------------------------
    def _install_shortcuts(self) -> None:
        """Atalhos que todo mundo espera de um programa desktop. Sem eles a
        janela parece um formulário web."""
        from PySide6.QtGui import QKeySequence, QShortcut
        atalhos = [
            ("Ctrl+1", lambda: self.tabs.setCurrentIndex(0)),
            ("Ctrl+2", lambda: self.tabs.setCurrentIndex(1)),
            ("Ctrl+3", lambda: self.tabs.setCurrentIndex(2)),
            ("Ctrl+4", lambda: self.tabs.setCurrentIndex(3)),
            ("F1", lambda: HelpDialog(self).exec()),
            ("Ctrl+Shift+A", lambda: AboutDialog(self, self._restart_onboarding).exec()),
            ("Ctrl+M", self.toggle_monitor),
            ("Ctrl+R", self.refresh_ports),
        ]
        for seq, fn in atalhos:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(fn)

    def toggle_monitor(self) -> None:
        """Ctrl+M: liga o ouvir ao vivo sem precisar ir até a aba Áudio."""
        self.tabs.setCurrentIndex(2)
        self.audio_tab.btn_mon.toggle()

    def _restart_onboarding(self) -> None:
        self.settings.set("primeira_execucao", True)
        self.settings.save()
        self.run_onboarding()

    # ---- estado persistido ----------------------------------------------------
    def _restore_state(self) -> None:
        if self.settings.restore_window(self):
            pass
        i = int(self.settings.get("aba") or 0)
        if 0 <= i < self.tabs.count():
            self.tabs.setCurrentIndex(i)
        at = self.audio_tab
        gi = [g.key for g in GT.GUITARS].index(self.settings.get("guitarra", GT.DEFAULT_GUITAR)) \
            if self.settings.get("guitarra", GT.DEFAULT_GUITAR) in GT.keys() else 0
        self.cb_guitar.setCurrentIndex(gi)
        if at.cb_in.count():
            at.cb_in.setCurrentIndex(min(int(self.settings.get("entrada_audio") or 0),
                                         at.cb_in.count() - 1))
        if at.cb_out.count():
            at.cb_out.setCurrentIndex(min(int(self.settings.get("saida_audio") or 0),
                                          at.cb_out.count() - 1))
        at.sld_mon.setValue(int(self.settings.get("volume_monitor") or 80))

    # ---- teclas 1, 2, 3: trocar de timbre sem ir ate a pedaleira ----
    def keyPressEvent(self, e) -> None:  # noqa: N802
        """As teclas sao capturadas aqui, na MainWindow, e nao na aba: o
        atalho tem de funcionar com o foco em qualquer aba — quando se esta
        tocando, o foco nao esta no programa.

        So as teclas 1/2/3 sao capturadas. Digitar "1" num campo de texto
        tem de continuar funcionando, entao qualquer widget que aceite texto
        deixa o evento passar.
        """
        k = e.key()
        if k in (Qt.Key_1, Qt.Key_2, Qt.Key_3):
            foco = QApplication.focusWidget()
            if foco is not None and foco.isEnabled() and isinstance(
                    foco, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox)):
                return super().keyPressEvent(e)
            if not e.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
                self.somada_rapida(k - Qt.Key_1)
                e.accept()
                return
        return super().keyPressEvent(e)

    def somada_rapida(self, indice: int) -> None:
        """Ativa a somada do indice. Se ela estiver vazia, grava o timbre
        atual — assim da para montar as tres enquanto toca, sem passar
        por nenhum menu."""
        self.aba_tocando.aplicar_somada(indice)


    def _save_state(self) -> None:
        s = self.settings
        s.set("aba", self.tabs.currentIndex())
        s.set("guitarra", self.cb_guitar.currentData() or GT.DEFAULT_GUITAR)
        at = self.audio_tab
        s.set("entrada_audio", at.cb_in.currentIndex())
        s.set("saida_audio", at.cb_out.currentIndex())
        s.set("volume_monitor", at.sld_mon.value())
        # NUNCA gravar self.width() com a janela maximizada: isso e' a largura
        # do MONITOR, nao o tamanho que o usuario escolheu. Na proxima abertura
        # a janela nasce com 2974 px sem estar maximizada. normalGeometry()
        # devolve o tamanho de quando ela nao estava maximizada.
        g = self.normalGeometry()
        w, h = (g.width(), g.height()) if g.isValid() else (self.width(), self.height())
        s.save_window(w, h, self.isMaximized())

    def run_onboarding(self) -> None:
        """Primeira execução: boas-vindas e escolha da guitarra."""
        if WelcomeDialog(self).exec() != QDialog.DialogCode.Accepted:
            self.settings.mark_seen()
            return
        dlg = GuitarPickerDialog(self, self.cb_guitar.currentData() or GT.DEFAULT_GUITAR)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.set_guitar(dlg.selected())
        self.settings.mark_seen()

    # ---- helpers ---------------------------------------------------------------------
    def status(self, msg: str) -> None:
        self.statusBar().showMessage(msg)

    def busy(self, msg: str) -> None:
        self.status(msg); self.progress.setValue(0); self.progress.show()

    def idle(self) -> None:
        self.progress.hide()

    def require_pedal(self) -> bool:
        if self.pedal and self.pedal.connected:
            return True
        QMessageBox.information(self, I18N.tr("pedal_conecte", I18N.get_idioma()).split(".")[0], I18N.tr("pedal_conecte", I18N.get_idioma()))
        return False

    def backup(self, slot: str, params: dict) -> None:
        d = data_dir() / "backups"; d.mkdir(parents=True, exist_ok=True)
        PF.save_file(d / f"slot-{slot}-{datetime.now():%Y%m%d-%H%M%S}.json", f"Backup slot {slot}", params)

    def set_connected(self, pedal: BasePedal | None) -> None:
        self.pedal = pedal
        on = bool(pedal and pedal.connected)
        self.btn_connect.setText("Desconectar" if on else "Conectar")
        self.lbl_state.setText(f"● {pedal.device_name or 'conectado'}" if on else "● desconectado")
        self.lbl_state.setStyleSheet(f"color:{'#38c488' if on else '#8b93a1'}")
        self.pedal_tab.set_enabled_pedal(on)

    # ---- guitarra (ajuste global) ---------------------------------------------
    def guitar(self) -> GT.GuitarProfile:
        return GT.get(self.cb_guitar.currentData())

    def guitarra_key(self) -> str:
        """Chave da guitarra global escolhida. A GuitarProfile correspondente fica
        em self.guitar(). Nome em português de propósito: a janela expõe isto
        como 'a guitarra do usuário', não como um filtro de presets."""
        return self.cb_guitar.currentData() or GT.DEFAULT_GUITAR

    def on_guitar_changed(self, _i: int = 0) -> None:
        """Trocar a guitarra re-adapta os 3 slots de uma vez, sem pedir nada.

        O usuário não deveria precisar saber que existe 'voicing': escolhe a
        guitarra uma vez, e o resto se ajusta. Só re-adaptamos o que veio de um
        preset curado — valores que o usuário mexeu à mão ficam como estão.
        """
        g = self.guitar()
        self.lbl_guitar_tip.setText(f"{g.character} <i>{g.tips}</i>")

        adapted = 0
        for slot in list(self.pedal_tab.params):
            if self._preset_source.get(slot) is None:
                continue  # valor mexido à mão: não mexe no que o usuário fez
            novo = g.adapt(self.pedal_tab.params[slot])
            if novo != self.pedal_tab.params[slot]:
                self.pedal_tab.params[slot] = novo
                adapted += 1
        if adapted:
            self.pedal_tab.refresh_widgets()
        self.pedal_tab.refresh_voicing_note()
        self.status(
            f"Guitarra: {g.label}. {adapted} slot(s) re-adaptado(s) automaticamente."
            if adapted else f"Guitarra: {g.label}. Os valores do editor não foram alterados."
        )

    def set_guitar(self, key: str) -> None:
        i = self.cb_guitar.findData(key)
        if i >= 0:
            self.cb_guitar.setCurrentIndex(i)

    # ---- conexão ---------------------------------------------------------------------
    def refresh_ports(self) -> None:
        self.cb_in.clear(); self.cb_out.clear()
        try:
            ins, outs = list_ports()
        except PedalError as exc:
            self.status(str(exc)); return
        self.cb_in.addItems(ins); self.cb_out.addItems(outs)
        if ins:
            self.cb_in.setCurrentIndex(guess_port(ins))
        if outs:
            self.cb_out.setCurrentIndex(guess_port(outs))
        self.status(f"{len(ins)} entrada(s) e {len(outs)} saída(s) MIDI encontradas.")

    def toggle_connection(self) -> None:
        if self.pedal and self.pedal.connected:
            self.pedal.disconnect(); self.set_connected(None); self.status("Desconectado."); return
        if self.cb_in.currentIndex() < 0 or self.cb_out.currentIndex() < 0:
            QMessageBox.information(self, I18N.tr("conectar", I18N.get_idioma()), I18N.tr("nenhuma_porta", I18N.get_idioma()))
            return
        client = CubeBabyClient()
        i, o = self.cb_in.currentIndex(), self.cb_out.currentIndex()
        self.busy("Conectando...")
        def done(_r, err):
            self.idle()
            if err:
                self.status(str(err)); QMessageBox.warning(self, "Conectar", str(err)); return
            self.set_connected(client); self.status(f"Conectado: {client.device_name}")
            self.pedal_tab.read_from_pedal()
        self.runner.submit(lambda: client.connect(i, o), done)

    def _trocar_idioma(self) -> None:
        """Troca o idioma da interface."""
        from . import i18n
        novo = self.cb_idioma.currentData()
        i18n.set_idioma(novo)
        # Atualiza as strings visíveis mais importantes
        self.lbl_brand.setText("CUBE BABY UNLEASHED")
        self.lbl_tag.setText(i18n.tr("Editor de timbre para o pedal CUVAVE · M-VAVE CUBE Baby", novo))
        self.btn_connect.setText(i18n.tr("Conectar" if not (self.pedal and self.pedal.connected) else "Desconectar", novo))
        self.btn_sim.setText(i18n.tr("Modo simulado", novo))
        self.btn_refresh.setText(i18n.tr("Atualizar portas", novo))
        self.lbl_guitar.setText(i18n.tr("Minha guitarra:", novo))
        self.btn_help.setText(i18n.tr("? Ajuda", novo))
        # Atualiza abas
        self.tabs.setTabText(self.tabs.indexOf(self.aba_tocando), i18n.tr("aba_tocando", novo))
        self.tabs.setTabText(self.tabs.indexOf(self.pedal_tab), i18n.tr("aba_pedal", novo))
        self.tabs.setTabText(self.tabs.indexOf(self.presets_tab), i18n.tr("aba_presets", novo))
        self.tabs.setTabText(self.tabs.indexOf(self.audio_tab), i18n.tr("aba_audio", novo))
        self.tabs.setTabText(self.tabs.indexOf(self.tuner_tab), i18n.tr("aba_afinador", novo))
        self.tabs.setTabText(self.tabs.indexOf(self.ir_tab), i18n.tr("aba_ir", novo))
        self.tabs.setTabText(self.tabs.indexOf(self.library), i18n.tr("aba_biblioteca", novo))
        self.tabs.setTabText(self.tabs.indexOf(self.donate_tab), i18n.tr("aba_apoiar", novo))
        # Salva nas preferências
        try:
            self.settings.set("idioma", novo)
            self.settings.save()
        except Exception:  # noqa: BLE001
            pass

    def start_simulated(self) -> None:
        self.set_connected(SimulatedPedal()); self.status("Modo simulado: nada é enviado a um pedal de verdade.")
        self.pedal_tab.read_from_pedal()

    def closeEvent(self, e) -> None:
        try:
            self.tuner_tab.close_all()
        except Exception:  # noqa: BLE001
            pass  # noqa: N802
        self.audio_tab.close_all()
        if self.pedal:
            self.pedal.disconnect()
        try:
            self._save_state()
        except Exception:  # noqa: BLE001
            pass  # salvar preferência nunca pode impedir o fechamento
        super().closeEvent(e)


def _install_crash_handler() -> Path:
    """Registra erros (Python e crashes nativos) em ~/TomCUBEBaby/crash.log e mostra numa janela."""
    import faulthandler
    import traceback

    log_dir = data_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "crash.log"
    fh = open(log_path, "a", buffering=1, encoding="utf-8")
    faulthandler.enable(file=fh)  # pega até crash nativo (segfault) e escreve a pilha

    def hook(exc_type, exc, tb) -> None:
        # KeyboardInterrupt não é crash: é o Ctrl+C de quem está usando o
        # run_debug.bat. Tratar como erro abria um QMessageBox modal que
        # travava o programa esperando clique, e o processo nunca saía.
        if issubclass(exc_type, KeyboardInterrupt):
            fh.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] encerrado com Ctrl+C\n")
            fh.flush()
            os._exit(130)  # código convencional de SIGINT; encerra na hora
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        fh.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] v{__version__}\n{text}")
        try:
            QMessageBox.critical(None, "Erro no CUBE Baby Unleashed", f"{text}\nSalvo em:\n{log_path}")
        except Exception:  # noqa: BLE001
            pass

    sys.excepthook = hook
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    return log_path


def build_app(argv: list[str] | None = None):
    """Cria o QApplication COM o tema aplicado.

    Existe para que testes, screenshots e o programa real usem exatamente o
    mesmo caminho de inicialização. Sem esta função, `tests/shot.py` abria a
    janela sem `setStyleSheet` e gerava imagens com as cores erradas — foi
    exatamente o que aconteceu, e só apareceu quando alguém comparou o print
    com a tela de verdade.
    """
    from typing import cast
    app = cast(QApplication, QApplication.instance() or QApplication(argv or []))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    # Ícone da aplicação (janela + barra de tarefas).
    try:
        from pathlib import Path
        from PySide6.QtGui import QIcon
        icon_path = Path(__file__).parent.parent / "icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass
    return app


def build_window(settings=None):
    """Aplica o tema e cria a janela principal."""
    from .settings import Settings
    app = build_app([])
    win = MainWindow(settings or Settings())
    win.show()
    return app, win


def run(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    app = build_app(argv)
    _install_crash_handler()
    win = MainWindow()
    win.show()
    if win.settings.is_first_run():
        # Abrir o diálogo depois do event loop começar: antes disso ele pode
                # aparecer atrás da janela em alguns temas do Windows.
        QTimer.singleShot(250, win.run_onboarding)
    if "--sim" in argv:
        win.start_simulated()
    return app.exec()
