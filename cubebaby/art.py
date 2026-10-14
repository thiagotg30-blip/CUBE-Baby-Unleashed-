"""Desenho dos gabinetes e dos pré-amps, direto na tela.

Duas coisas bem diferentes, e é importante não misturar:

**Gabinete** — Marshall 1960A, Soldano, Mesa, Peavey 5150 são caixas reais, com
formato conhecido. Desenho a *planta* da caixa: o tamanho relativo dos alto-
falantes (10" é menor que 12") e o arranjo (1, 2 ou 4). Isso é ilustração
original, medida a partir das especificações — não é foto, e não substitui ver
a caixa de verdade.

**Pré-amp** — "Power-Zone Clean", "Day Tripper OD", "Mr Smith Dist" são nomes
inventados pela CUVAVE. **Não existe imagem deles para desenhar**, e inventar
uma seria mentira. Então o desenho aqui não tenta parecer um amplificador: é um
diagrama de caráter — duas barras, brilho e sujeira — que diz a mesma coisa que
a descrição em texto, de relance.

Nada de SVG nem de arquivo de imagem: tudo é QPainter, então escala limpa em
qualquer zoom e não entra nenhum arquivo no repositório.
"""
from __future__ import annotations

import re

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

# ---- paleta (espelha cubebaby/theme.py) --------------------------------------
CAB_EDGE = QColor("#4a4a55")
CAB_FACE = QColor("#26262a")
CAB_FACE_2 = QColor("#1c1c1f")
GRILLE = QColor("#202024")
CONE = QColor("#17171a")
DUST = QColor("#3a3a42")
BADGE = QColor("#f0812a")


def parse_spec(spec: str) -> tuple[int, int]:
    """'2×12' -> (2, 12). Tolera 'x' e 'X'. Devolve (0,0) se não entender."""
    m = re.search(r"(\d+)\s*[x×X]\s*(\d+)", spec or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


class CabinetArt(QWidget):
    """Planta de uma caixa de alto-falantes: 1×10, 2×12, 4×12…"""

    def __init__(self, spec: str = "", parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.n, self.inch = parse_spec(spec)
        self.setFixedSize(84, 56)

    def set_spec(self, spec: str) -> None:
        """Troca a especificação e redesenha."""
        if spec != self.spec:
            self.spec = spec
            self.n, self.inch = parse_spec(spec)
            self.update()

    def paintEvent(self, e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad = 3
        box = QRectF(pad, pad, w - pad * 2, h - pad * 2)

        # caixa
        g = QLinearGradient(0, box.top(), 0, box.bottom())
        g.setColorAt(0, CAB_FACE)
        g.setColorAt(1, CAB_FACE_2)
        p.setPen(QPen(CAB_EDGE, 1))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(box, 4, 4)

        if not self.n:
            # bypass: travessão
            p.setPen(QPen(QColor("#54545e"), 2, Qt.PenStyle.SolidLine))
            p.drawLine(int(w * 0.35), int(h / 2), int(w * 0.65), int(h / 2))
            p.end()
            return

        # grade
        inner = box.adjusted(5, 5, -5, -5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(GRILLE)
        p.drawRoundedRect(inner, 3, 3)

        # alto-falantes: 10" ~ 78% do diâmetro de 12"
        cols = 1 if self.n <= 1 else (2 if self.n <= 2 else 2)
        rows = 1 if self.n <= 2 else 2
        cw = inner.width() / cols
        ch = inner.height() / rows
        base = min(cw, ch) * 0.82
        d = base * (0.78 if self.inch == 10 else 1.0)

        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx >= self.n:
                    break
                cx = inner.left() + cw * (c + 0.5)
                cy = inner.top() + ch * (r + 0.5)
                rr = QRectF(cx - d / 2, cy - d / 2, d, d)
                cone = QLinearGradient(rr.topLeft(), rr.bottomRight())
                cone.setColorAt(0, DUST)
                cone.setColorAt(1, CONE)
                p.setBrush(QBrush(cone))
                p.setPen(QPen(QColor("#101012"), 1))
                p.drawEllipse(rr)
                # aro
                p.setPen(QPen(QColor("#45454e"), 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(rr.adjusted(2, 2, -2, -2))
                # poeira central
                rr2 = rr.adjusted(d * 0.36, d * 0.36, -d * 0.36, -d * 0.36)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#0e0e10"))
                p.drawEllipse(rr2)


class PreampArt(QWidget):
    """Diagrama de caráter: brilho (acima) × sujeira (abaixo).

    Não é retrato de amplificador — os pré-amps da CUVAVE não têm imagem
    pública. É um resumo visual do que muda no som.
    """

    def __init__(self, tone: float = 0.5, grit: float = 0.0, accent: str = "#f0812a",
                 parent=None) -> None:
        super().__init__(parent)
        self.tone = max(0.0, min(1.0, tone))
        self.grit = max(0.0, min(1.0, grit))
        self.accent = accent
        self.setFixedSize(84, 56)

    def set_character(self, tone: float, grit: float, accent: str | None = None) -> None:
        self.tone = max(0.0, min(1.0, tone))
        self.grit = max(0.0, min(1.0, grit))
        if accent:
            self.accent = accent
        self.update()

    def paintEvent(self, e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1c1c1f"))
        p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 4, 4)

        bw = w - 22
        x = 14

        def barra(y: float, val: float, cor: QColor, rotulo: str) -> None:
            # trilho
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#26262a"))
            p.drawRoundedRect(QRectF(x, y, bw, 7), 3.5, 3.5)
            # preenchimento
            p.setBrush(cor)
            p.drawRoundedRect(QRectF(x, y, max(6.0, bw * val), 7), 3.5, 3.5)
            p.setPen(QColor("#8f8b83"))
            f = p.font()
            f.setPointSize(7)
            p.setFont(f)
            p.drawText(QRectF(2, y - 2, 11, 11), Qt.AlignmentFlag.AlignCenter, rotulo)

        barra(h * 0.28, self.tone, QColor("#5aa9f0"), "T")
        barra(h * 0.60, self.grit, QColor(self.accent), "G")

        p.end()


# ---------------------------------------------------------------------------
# Dados de caráter por pré-amp: (brilho 0..1, sujeira 0..1, categoria)
# ---------------------------------------------------------------------------
PREAMP_CHARACTER = {
    "Power-Zone Clean":     (0.50, 0.02, "Limpo"),
    "US Gold 100 Clean":    (0.68, 0.03, "Limpo"),
    "Two Stone Coral OD":   (0.55, 0.42, "Overdrive"),
    "Doctor3 B":            (0.45, 0.50, "Overdrive"),
    "Cali JP A":            (0.62, 0.46, "Overdrive"),
    "Day Tripper OD":       (0.40, 0.62, "Overdrive"),
    "Shittcow Dist":        (0.35, 0.90, "Distorção"),
    "Wo Stone Coral OD":    (0.30, 0.78, "Distorção"),
    "Mr Smith Dist":        (0.42, 0.96, "Distorção"),
}


def preamp_character(name: str) -> tuple[float, float, str]:
    """(brilho, sujeira, categoria) de um pré-amp. Desconhecido cai no meio."""
    return PREAMP_CHARACTER.get(name, (0.5, 0.5, "—"))