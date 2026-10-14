"""Medidor de nível (VU) reutilizável.

Fica num módulo à parte porque é usado tanto pela aba Áudio quanto pelo bloco
"Saída" da aba Pedal — e o PedalTab é definido antes do AudioTab, então uma
classe Defined em ui.py chegaria tarde demais.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

# Escalas de cor: verde (headroom), amarelo (atenção), vermelho (clipping).
OK = "#38c488"
WARN = "#f2b84b"
CLIP = "#e5484d"
TRACK = "#1a1d24"
LABEL = "#9aa2b1"


class LevelBar(QWidget):
    """Barra horizontal de nível. Verde até ~-6 dB, amarelo, vermelho no clip.

    Aceita `accent` para tingir a barra de um bloco específico (a cor do
    pré-amp, do delay...) em vez do verde padrão.
    """

    def __init__(self, accent: str | None = None, height: int = 14) -> None:
        super().__init__()
        self.setFixedHeight(height)
        self._level = 0.0
        self._clip = False
        self._accent = accent

    def set_level(self, v: float) -> None:
        self._level = max(0.0, min(1.0, float(v)))
        self.update()

    def mark_clip(self) -> None:
        self._clip = True
        self.update()

    def reset(self) -> None:
        self._level = 0.0
        self._clip = False
        self.update()

    def paintEvent(self, e) -> None:  # noqa: N802
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(TRACK))
        p.drawRoundedRect(0, 0, w, h, h / 2, h / 2)

        n = int(w * self._level)
        if n > 0:
            base = self._accent or OK
            p.setBrush(QColor(base))
            p.drawRoundedRect(0, 0, n, h, h / 2, h / 2)
            # A zona de alerta é sempre a mesma fração da barra, para o olho
            # aprender a ler o medidor sem pensar.
            warn_at = int(w * 0.78)
            if n > warn_at:
                p.setBrush(QColor(WARN))
                p.drawRoundedRect(0, 0, n, h, h / 2, h / 2)
            if self._clip:
                p.setBrush(QColor(CLIP))
                p.drawRoundedRect(0, 0, n, h, h / 2, h / 2)

        p.setPen(QColor(LABEL))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                   "nível da entrada" if not self._accent else "nível")