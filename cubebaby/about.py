"""Janela "Sobre": créditos, licença e o botão de repetir a introdução.

Esta janela não é enfeite. A LGPL exige que o programa que embute Qt/PySide6
mostre os avisos de licença de terceiros, e um executável sem isso é uma
distribuição não conforme. Build com PyInstaller não gera essa tela sozinho.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget,
)

from . import __version__
from . import theme

# Versões das dependências que entram no .exe. Manter em dia na mão: o
# PyInstaller não gera isto.
DEPENDENCIES = [
    ("PySide6", "6.11.2", "LGPL-3.0 / GPL-3.0", "https://doc.qt.io/qtforpython/"),
    ("Qt 6", "6.x", "LGPL-3.0", "https://www.qt.io/licensing/"),
    ("python-rtmidi", "1.5+", "MIT", "https://pypi.org/project/python-rtmidi/"),
    ("Python", "3.12", "PSF License", "https://www.python.org/licenses/"),
]

TERCEIROS = [
    ("cubecontrol", "MIT",
     "Referência de engenharia reversa do protocolo SysEx do CUBE Baby."),
    ("cuvave-midi", "GPL-3.0-or-later",
     "Referência de engenharia reversa. Por ser copyleft, obriga este projeto "
     "inteiro a ser GPL-3.0-or-later."),
    ("preset-studio", "a confirmar",
     "Implementação do protocolo em TypeScript, de onde este código foi "
     "reimplementado. Ver NOTICE."),
]


class AboutDialog(QDialog):
    def __init__(self, parent=None, on_restart=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Sobre o CUBE Baby Unleashed {__version__}")
        self.resize(560, 520)
        self._on_restart = on_restart
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(theme.S3)

        nome = QLabel("CUBE Baby Unleashed")
        nome.setStyleSheet(f"font-size:24px; font-weight:700;")
        lay.addWidget(nome)

        sub = QLabel("Editor de pedais para o CUBE Baby (M-VAVE/CUVAVE)")
        sub.setStyleSheet(f"color:{theme.FG_MUTED};")
        lay.addWidget(sub)

        ver = QLabel(f"versão {__version__} · sem fins lucrativos")
        ver.setStyleSheet(f"font-size:{theme.FS_SMALL}; color:{theme.FG_MUTED};")
        lay.addWidget(ver)
        lay.addSpacing(theme.S2)

        self.tabs = QTabWidget()

        # ---- sobre ----
        w = QWidget(); v = QVBoxLayout(w)
        txt = QLabel(
            "Ferramenta independente para editar os presets do pedal CUBE Baby "
            "por USB-MIDI, com edição em tempo real, presets curados, adaptação "
            "automática à guitarra, e gravação/limpeza de áudio.\n\n"
            "<b>Este projeto não tem qualquer vínculo, patrocínio ou endosso "
            "de M-VAVE, CUVAVE ou Sinco.</b> \"CUBE Baby\" e \"CUVAVE\" são "
            "marcas de seus respectivos proprietários.\n\n"
            "Software livre sob GPL-3.0-or-later. O código-fonte completo está "
            "no repositório do projeto e vem junto com o executável."
        )
        txt.setWordWrap(True)
        txt.setStyleSheet(f"font-size:{theme.FS_BODY}; color:{theme.FG_DIM};")
        v.addWidget(txt)
        v.addStretch()
        self.tabs.addTab(self._scroll(w), "Sobre")

        # ---- licença ----
        w2 = QWidget(); v2 = QVBoxLayout(w2)
        aviso = QLabel(
            "<b>CUBE Baby Unleashed é distribuído sob GPL-3.0-or-later.</b><br>"
            "Esta escolha não é livre: o protocolo SysEx foi reimplementado a "
            "partir de engenharia reversa comunitária cujo material de referência "
            "inclui o <b>cuvave-midi, sob GPL-3.0</b>. A GPL é copyleft, então o "
            "projeto inteiro precisa sair sob GPL e com código-fonte disponível."
        )
        aviso.setWordWrap(True)
        aviso.setStyleSheet(f"font-size:{theme.FS_BODY}; color:{theme.FG_DIM};")
        v2.addWidget(aviso)
        v2.addSpacing(theme.S2)

        links = QHBoxLayout()
        for texto, url in (
            ("Texto da GPL-3.0", "https://www.gnu.org/licenses/gpl-3.0.txt"),
            ("Repositório", "https://github.com/"),
            ("Qt / PySide6 (LGPL)", "https://www.qt.io/licensing/"),
        ):
            b = QPushButton(texto)
            b.setObjectName("ghost")
            b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            links.addWidget(b)
        links.addStretch()
        v2.addLayout(links)
        v2.addStretch()
        self.tabs.addTab(self._scroll(w2), "Licença")

        # ---- terceiros ----
        w3 = QWidget(); v3 = QVBoxLayout(w3)
        v3.addWidget(QLabel("Dependências empacotadas no executável:"))
        for nome_d, versao, lic, url in DEPENDENCIES:
            v3.addWidget(self._linha(f"{nome_d} {versao}", lic, url))
        v3.addSpacing(theme.S3)
        v3.addWidget(QLabel("Projeto de engenharia reversa usado como referência:"))
        for nome_d, lic, desc in TERCEIROS:
            lbl = QLabel(f"<b>{nome_d}</b> — {lic}<br>"
                         f"<span style='color:{theme.FG_MUTED}'>{desc}</span>")
            lbl.setWordWrap(True)
            v3.addWidget(lbl)
        v3.addStretch()
        self.tabs.addTab(self._scroll(w3), "Créditos")

        lay.addWidget(self.tabs, 1)

        row = QHBoxLayout()
        if on_restart:
            restart = QPushButton("Recomeçar a introdução")
            restart.setObjectName("ghost")
            restart.clicked.connect(on_restart)
            row.addWidget(restart)
        row.addStretch()
        fechar = QPushButton("Fechar")
        fechar.setObjectName("primary")
        fechar.setDefault(True)
        fechar.clicked.connect(self.accept)
        row.addWidget(fechar)
        lay.addLayout(row)

    def _scroll(self, w: QWidget) -> QScrollArea:
        s = QScrollArea()
        s.setWidgetResizable(True)
        s.setWidget(w)
        return s

    def _linha(self, nome: str, lic: str, url: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 2, 0, 2)
        l = QLabel(f"{nome} — <span style='color:{theme.FG_MUTED}'>{lic}</span>")
        h.addWidget(l)
        h.addStretch()
        b = QPushButton("site")
        b.setObjectName("ghost")
        b.setFixedWidth(60)
        b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
        h.addWidget(b)
        return w