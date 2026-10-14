"""Primeira execução: o que um produto faz com quem ainda não conhece o app.

Duas telas, na ordem em que o usuário precisa delas:

1. Boas-vindas, com três frases honestas sobre o que o programa faz.
2. "Qual é a sua guitarra?" — uma escolha, e ela **mexe no app**: define o
   voicing dos três slots e já deixa o preset certo carregado.

Depois disso, a tela não aparece mais (a preferência guarda o visto). E há um
botão "Recomeçar a introdução" em Ajuda > Sobre, para quem quer rever.

Por que perguntar a guitarra primeiro: é a única informação que o app não pode
descobrir sozinho (o pedal é MIDI, não sabe do instrumento), e é a que mais
muda o resultado. Perguntar uma coisa só, que importa, é melhor do que um
formulário de cinco campos.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QWidget,
)

from . import guitars as GT
from . import theme


class WelcomeDialog(QDialog):
    """Passo 1: o que é isso, em três linhas."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bem-vindo ao CUBE Baby Unleashed")
        self.setFixedSize(560, 400)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 24)
        lay.setSpacing(theme.S4)

        t = QLabel("CUBE Baby Unleashed")
        t.setStyleSheet(f"font-size:26px; font-weight:700; color:{theme.FG};")
        lay.addWidget(t)

        s = QLabel("Editor de pedais para o CUBE Baby")
        s.setStyleSheet(f"font-size:{theme.FS_HEAD}; color:{theme.FG_MUTED};")
        lay.addWidget(s)

        lay.addSpacing(theme.S5)

        for texto in (
            "Você conecta o pedal por USB e o programa lê e escreve os três "
            "presets dele direto — sem tocar em nada fisicamente.",
            "Dá para ouvir a guitarra ao vivo, gravar e limpar o chiado, tudo "
            "aqui dentro. Sem REAPER, sem DAW.",
            "Cada preset se adapta sozinho à guitarra que você escolher.",
        ):
            linha = QLabel("• " + texto)
            linha.setWordWrap(True)
            linha.setStyleSheet(f"font-size:{theme.FS_BODY}; color:{theme.FG_DIM};")
            lay.addWidget(linha)

        lay.addStretch()

        dica = QLabel(
            "Dica: se a sua interface de áudio estiver plugada, já dá para "
            "ouvir a guitarra antes de conectar o pedal."
        )
        dica.setWordWrap(True)
        dica.setStyleSheet(f"font-size:{theme.FS_SMALL}; color:{theme.FG_MUTED};")
        lay.addWidget(dica)

        row = QHBoxLayout(); row.addStretch()
        pular = QPushButton("Depois")
        pular.setObjectName("ghost")
        pular.clicked.connect(self.reject)
        seguir = QPushButton("Começar")
        seguir.setObjectName("primary")
        seguir.setDefault(True)
        seguir.clicked.connect(self.accept)
        row.addWidget(pular); row.addWidget(seguir)
        lay.addLayout(row)


class GuitarPickerDialog(QDialog):
    """Passo 2: escolher a guitarra, e o app se configura a partir dela."""

    def __init__(self, parent=None, current: str = "les-paul") -> None:
        super().__init__(parent)
        self.setWindowTitle("Qual é a sua guitarra?")
        self.setFixedSize(560, 460)
        self.escolha = current
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(theme.S3)

        h = QLabel("Qual é a sua guitarra?")
        h.setStyleSheet(f"font-size:{theme.FS_TITLE}; font-weight:600;")
        lay.addWidget(h)

        sub = QLabel(
            "Ela muda o timbre final, e o programa ajusta os valores dos "
            "presets para combinar. Dá para mudar quando quiser, no topo da janela."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"font-size:{theme.FS_SMALL}; color:{theme.FG_MUTED};")
        lay.addWidget(sub)
        lay.addSpacing(theme.S2)

        self.lst = QListWidget()
        for g in GT.GUITARS:
            it = QListWidgetItem(g.one_line())
            it.setData(Qt.UserRole, g.key)
            it.setToolTip(f"{g.character}\n\n{g.tips}")
            self.lst.addItem(it)
        idx = next((i for i in range(self.lst.count())
                    if self.lst.item(i).data(Qt.UserRole) == current), -1)
        self.lst.setCurrentRow(idx if idx >= 0 else 0)
        self.lst.itemDoubleClicked.connect(lambda _: self.accept())
        self.lst.currentItemChanged.connect(self._preview)
        lay.addWidget(self.lst, 1)

        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet(f"font-size:{theme.FS_SMALL}; color:{theme.FG_DIM};")
        lay.addWidget(self.preview)

        row = QHBoxLayout(); row.addStretch()
        pular = QPushButton("Depois")
        pular.setObjectName("ghost")
        pular.clicked.connect(self.reject)
        ok = QPushButton("Pronto")
        ok.setObjectName("primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(pular); row.addWidget(ok)
        lay.addLayout(row)

        self._preview()

    def _preview(self, *_a) -> None:
        it = self.lst.currentItem()
        if not it:
            return
        g = GT.get(it.data(Qt.UserRole))
        self.escolha = g.key
        self.preview.setText(f"<b>{g.label}</b> — {g.character}<br><br><i>{g.tips}</i>")

    def selected(self) -> str:
        it = self.lst.currentItem()
        return it.data(Qt.UserRole) if it else self.escolha