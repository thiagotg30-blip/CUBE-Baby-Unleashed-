"""A cadeia de sinais desenhada como pedaleira, não como caixas de texto.

Antes cada bloco era um retângulo com um rótulo. Aqui cada um é desenhado como
o equipamento que representa: chassi com bisel, parafusos nos cantos, LED de
status, o knob do parâmetro principal (com a marca apontando para o valor) e o
jack na lateral.

Por que isso importa mais do que parece: quem nunca usou pedal não sabe o que
"modulação" quer dizer, mas reconhece um pedal. O desenho ensina a ordem do som
antes de o usuário aprender o nome de qualquer controle — e o LED responde de
relance a pergunta que ele faz o tempo todo: isso está ligado?

Clicar num bloco cicla o parâmetro principal (+1; Shift+clique = -1), ao vivo.
Guitarra, Pré-amp e Saída não têm um valor simples de ciclar: clicar neles leva
ao controle correspondente na aba Pedal.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPen, QRadialGradient, QTextDocument)
from PySide6.QtWidgets import QWidget

from . import cabinets as CAB
from . import genre as GEN
from . import protocol as P

# (id, rotulo, chave liga/desliga, parametro principal)
# A cadeia usa apenas duas cores: âmbar quando ativo, cinza quando inativo.
# Sete cores diferentes (laranja/azul/verde/roxo...) pareciam tema de Windows XP.
BLOCOS = (
    ("entrada",  "Guitarra",   None,           None),
    ("preamp",   "Pré-amp",    None,           "type"),
    ("cabinet",  "Gabinete",   "irSection",    "cabinet"),
    ("mod",      "Modulação",  None,           "modulation"),
    ("delay",    "Delay",      "delaySection", "mix"),
    ("reverb",   "Reverb",     None,           "reverb"),
    ("saida",    "Saída",      None,           "volume"),
)

# Cores de chassi, independentes do acento do bloco.
CHASSI_OFF = QColor("#232327")
BISEL = QColor("#54545e")
TEXTO_OFF = QColor("#6f6b64")
LED_OFF = QColor("#3a3a42")
FUNDO = QColor("#191819")
ACCENT = QColor("#f0812a")


class SignalChain(QWidget):
    """Diagrama da cadeia, desenhado como uma fileira de pedais."""

    bloco_escolhido = Signal(str)
    bloco_ajustado = Signal(str, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(196)
        # Nao impor largura minima: quem manda na largura e' a aba. Se a cadeia
        # exigir largura, o scroll cria barra horizontal e o corpo cresce.
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)
        self._params: dict = {}
        self._slot = "A"
        self._hover: str | None = None
        self._boxes: dict[str, QRectF] = {}
        self.setToolTip(
            "A cadeia do som, na ordem em que ela acontece.\n\n"
            "Clique num bloco: muda o som na hora (+1). Shift+clique diminui.\n"
            "Guitarra, Pré-amp e Saída levam aos controles na aba Pedal.")

    def atualizar(self, params: dict, slot: str = "A") -> None:
        self._params = dict(params or {})
        self._slot = slot
        self.update()

    # ---- estado de cada bloco -------------------------------------------
    def _estado(self, bid: str) -> tuple[str, bool]:
        """(o que mostrar no bloco, está ativo?)"""
        p = self._params
        if bid == "entrada":
            return "entrada de linha", True
        if bid == "saida":
            return f"volume {p.get('volume', 0)}", True
        if bid == "preamp":
            idx = int(p.get("type", 0) or 0)
            nome = P.PREAMP_TYPES[idx][1] if 0 <= idx < len(P.PREAMP_TYPES) else "—"
            return nome, True
        if bid == "cabinet":
            from .ui import fw_key
            c = CAB.get(fw_key(), int(p.get("cabinet", 0) or 0))
            on = bool(p.get("irSection", 1))
            return ("desligado" if not on else (c.short if c.pos else "bypass")), on
        if bid == "reverb":
            return f"{p.get('reverb', 0)}", True
        if bid == "delay":
            return f"mix {p.get('mix', 0)}", bool(p.get("delaySection", 0))
        if bid == "mod":
            return f"{p.get('modulation', 0)}", True
        return "", True

    def _prm_do(self, bid: str) -> str | None:
        for b, _r, _sw, prm in BLOCOS:
            if b == bid:
                return prm
        return None

    def _valor_norm(self, prm: str | None) -> float:
        if prm is None:
            return 0.6
        try:
            v = float(self._params.get(prm, 0))
            mx = float(P.PARAM_MAX.get(prm, 15) or 15)
            return max(0.0, min(1.0, v / mx))
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.6

    # ---- desenho ---------------------------------------------------------
    def paintEvent(self, e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, FUNDO)

        n = len(BLOCOS)
        gap = 22
        larg = (w - gap * (n + 1)) / n
        topo = 30.0
        alt = h - 56.0
        self._boxes.clear()

        p.setPen(QColor("#8f8b83"))
        fc = QFont(); fc.setPointSize(9)
        p.setFont(fc)
        from . import i18n
        _lang = i18n.get_idioma()
        p.drawText(QRectF(0, 6, w, 16), Qt.AlignmentFlag.AlignCenter,
                   i18n.tr("ordem_som", _lang))

        for i, (bid, rot, _sw, _prm) in enumerate(BLOCOS):
            x = gap + i * (larg + gap)
            box = QRectF(x, topo, larg, alt)
            self._boxes[bid] = box
            valor, ativo = self._estado(bid)

            if i:  # cabo entre os pedais, por baixo dos blocos
                cy = box.center().y()
                p.setPen(QPen(QColor("#0e0e10"), 3))
                p.drawLine(QPointF(x - gap + 4, cy), QPointF(x - 4, cy))
                p.setPen(QPen(QColor("#4a4a55"), 1.6))
                p.drawLine(QPointF(x - gap + 4, cy), QPointF(x - 4, cy))

            self._desenha_pedal(p, box, ativo, self._hover == bid,
                                rot, valor, self._valor_norm(_prm))
        p.end()

    def _desenha_pedal(self, p: QPainter, box: QRectF, ativo: bool,
                       hover: bool, rotulo: str, valor: str, norm: float) -> None:
        cor = ACCENT if ativo else QColor("#5a5a62")
        r = QRectF(box)
        if hover:
            r.adjust(-3, -3, 3, 3)

        # corpo: chassi escuro com borda sutil (sem gradiente, sem parafusos)
        p.setBrush(QBrush(CHASSI_OFF if not ativo else QColor("#2a2a2e")))
        p.setPen(QPen(QColor("#3f3f47"), 1))
        p.drawRoundedRect(r, 8, 8)

        # LED de status, com halo quando ligado
        led = QPointF(r.center().x(), r.top() + 19)
        if ativo:
            halo = QRadialGradient(led, 10)
            halo.setColorAt(0.0, QColor(cor.red(), cor.green(), cor.blue(), 95))
            halo.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(halo)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(led, 10, 10)
            p.setBrush(cor)
        else:
            p.setBrush(LED_OFF)
        p.setPen(QPen(QColor("#0e0e10"), 1))
        p.drawEllipse(led, 3.6, 3.6)
        if ativo:
            p.setBrush(QColor(255, 255, 255, 150)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(led.x() - 1.1, led.y() - 1.1), 1.1, 1.1)

        # rótulo
        p.setPen(cor if ativo else TEXTO_OFF)
        fb = QFont(); fb.setPointSize(9); fb.setBold(True)
        p.setFont(fb)
        p.drawText(QRectF(r.left(), r.top() + 31, r.width(), 16),
                   Qt.AlignmentFlag.AlignCenter, rotulo)

        # knob central, com a marca apontando para o valor (sem gradiente 3D)
        kc = QPointF(r.center().x(), r.top() + r.height() * 0.58)
        raio = min(r.width() * 0.21, 17.0)
        p.setBrush(QBrush(QColor("#1a1a1e")))
        p.setPen(QPen(cor if ativo else QColor("#43434b"), 1.4))
        p.drawEllipse(kc, raio, raio)
        ang = math.radians(-135 + 270 * norm)
        p.setPen(QPen(cor if ativo else QColor("#6f6b64"), 2))
        p.drawLine(kc, QPointF(kc.x() + math.cos(ang) * raio * 0.76,
                               kc.y() + math.sin(ang) * raio * 0.76))

        # valor
        p.setPen(QColor("#e6e2da") if ativo else TEXTO_OFF)
        fv = QFont(); fv.setPointSize(8)
        p.setFont(fv)
        p.drawText(QRectF(r.left() + 3, r.bottom() - 28, r.width() - 6, 24),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, valor)



    # ---- interação -------------------------------------------------------
    def _bloco_em(self, e) -> str | None:
        for bid, box in self._boxes.items():
            if box.contains(e.position()):
                return bid
        return None

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        novo = self._bloco_em(e)
        if novo != self._hover:
            self._hover = novo
            self.setCursor(Qt.CursorShape.PointingHandCursor if novo
                           else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e) -> None:  # noqa: N802
        self._hover = None
        self.update()

    def mousePressEvent(self, e) -> None:  # noqa: N802
        bid = self._bloco_em(e)
        if bid is None:
            return
        if bid in ("entrada", "saida", "preamp"):
            self.bloco_escolhido.emit(bid)
            return
        delta = -1 if (e.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1
        self.bloco_ajustado.emit(bid, delta)


class StyleMeter(QWidget):
    """Medidor de estilo: mostra o gênero mais próximo do timbre atual."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(60)
        self._estilo: str = ""
        self._generos: list = []
        self._forcas: dict = {}

    def atualizar(self, estilo: str, generos: list, forcas: dict) -> None:
        self._estilo = estilo
        self._generos = generos
        self._forcas = forcas
        self.update()

    def paintEvent(self, e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#191819"))

        if not self._generos:
            p.setPen(QColor("#6f6b64"))
            f = QFont(); f.setPointSize(10)
            p.setFont(f)
            from . import i18n
            p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                       i18n.tr("ajuste_controles", i18n.get_idioma()))
            return

        # Título
        p.setPen(QColor("#f0812a"))
        ft = QFont(); ft.setPointSize(10); ft.setBold(True)
        p.setFont(ft)
        p.drawText(QRectF(10, 8, w - 20, 18), Qt.AlignmentFlag.AlignLeft,
                   self._estilo)

        # Barras de força
        y = 34
        for g in self._generos[:5]:
            f = self._forcas.get(g, 0.0)
            if f <= 0:
                continue
            p.setPen(QColor("#8f8b83"))
            fb = QFont(); fb.setPointSize(9)
            p.setFont(fb)
            p.drawText(QRectF(10, y, 100, 14), Qt.AlignmentFlag.AlignLeft, g)
            # Barra
            p.setBrush(QColor("#232327"))
            p.setPen(QPen(QColor("#3f3f47"), 1))
            p.drawRoundedRect(QRectF(110, y, w - 130, 10), 3, 3)
            p.setBrush(QColor("#f0812a"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(110, y, int((w - 130) * min(1.0, f)), 10), 3, 3)
            y += 16
        p.end()
