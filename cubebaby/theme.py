"""Sistema visual: tokens centralizados e a folha de estilo (QSS).

Por que isto existe: a folha de estilo anterior era um bloco de texto com
cinquenta cores hex repetidas e nenhuma escala de espaçamento. Mudar o tema
exigia caçar hex por arquivo, e dois widgets que deveriam ter a mesma aparência
acabavam com tons diferentes.

Aqui o tema é um conjunto de nomes. Mudar a cor de acento é trocar UMA linha.
A folha de estilo só referencia `var(--nome)`, exatamente como CSS.
"""
from __future__ import annotations

# ---- paleta (inspirada no AmpliTube 5) ---------------------------------------
# Grafite quente quase preto, com acento âmbar e texto creme. A referência é o
# AmpliTube 5 da IK: painel de equipamento escuro, laranja de destaque, e borda
# clara em cima de cada módulo para dar a sensação de metal.
BG_DEEP = "#121114"        # fundo mais profundo
BG_PANEL = "#191819"       # topo da janela
BG_CARD = "#232326"        # módulo
BG_CARD_2 = "#1c1c1f"      # sombra do módulo
BG_INPUT = "#151517"       # campo, trilho
BG_HOVER = "#2f2f33"
BG_SUBTLE = "#26262a"

BORDER = "#33333a"
BORDER_STRONG = "#43434c"
# Borda clara no topo: é o que faz o cartão parecer chapa de metal em vez de
# retângulo chapado. Sem isso fica "flat" e a interface parece um formulário.
BEVEL = "#4a4a55"

FG = "#ece9e3"             # creme, não branco puro (branco puro cansa no escuro)
FG_DIM = "#c9c5bd"
FG_MUTED = "#8f8b83"       # cinza quente
FG_FAINT = "#a5a199"

ACCENT = "#f0812a"         # âmbar/orange — a assinatura do AmpliTube
# Profundidade do fundo: um gradiente suave da borda para o canto para o cant
# inferior resolve o "plano vazio" — a tela deixa de parecer um retângulo
# chapado e passa a ter profundidade, como um palco.
VIGNETTE = "rgba(240, 129, 42, 0.05)"
VIGNETTE_BOTTOM = "rgba(0, 0, 0, 0.35)"
ACCENT_HOVER = "#ff9440"
ACCENT_DEEP = "#c25f14"
OK = "#5cc98c"
WARN = "#e8b84b"
DANGER = "#e05a5a"
PURPLE = "#b98cff"
BLUE = "#5aa9f0"
GOLD = "#e8b84b"

# ---- escala de espaçamento (multiplos de 4, como um grid real) --------------
S1, S2, S3, S4, S5, S6 = 4, 8, 10, 12, 16, 24

# ---- tipografia -------------------------------------------------------------
FS_TITLE = "15px"
FS_HEAD = "13px"
FS_BODY = "13px"
FS_SMALL = "12px"
FS_TINY = "11px"

def shade(hex_color: str, percent: int) -> str:
    """Escurece (percent<0) ou clareia (percent>0) uma cor em N%.

    Usado para gerar o degradê do slider a partir de UMA cor de bloco, em vez
    de escrever o par de cores à mão em cada lugar.
    """
    c = hex_color.lstrip("#")
    if len(c) != 6:
        return hex_color
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    if percent < 0:
        f = 1 + percent / 100.0
        r, g, b = int(r * f), int(g * f), int(b * f)
    else:
        f = percent / 100.0
        r = int(r + (255 - r) * f)
        g = int(g + (255 - g) * f)
        b = int(b + (255 - b) * f)
    return "#%02x%02x%02x" % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def alpha(hex_color: str, a: float) -> str:
    """Cor com alfa, para sobrepor sobre um fundo desconhecido."""
    c = hex_color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {a})"


STYLESHEET = f"""
QWidget {{
    color: {FG};
    font-size: {FS_BODY};
}}
QMainWindow, QWidget#root {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {BG_PANEL}, stop:1 {BG_DEEP});
}}
QWidget#root {{ border-top: 2px solid {ACCENT}; }}

/* A "bancada" de setup: junta conexão e guitarra num só lugar. Uma caixa
   com sombra embaixo e borda clara em cima, para parecer uma chapa apoiada,
   e não duas linhas flutuando no vazio. */
QWidget#tocando_body, QScrollArea, QScrollArea QWidget#tocando_body {{
    background: transparent;
}}
QWidget#panel {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1d20, stop:1 #19181b);
    border: 1px solid {BORDER};
    border-top: 1px solid {BEVEL};
    border-radius: 10px;
}}

/* ---------------- abas ---------------- */
QTabWidget::pane {{ border: 0; background: transparent; }}
QTabBar::tab {{
    background: transparent; padding: 6px 16px; color: {FG_MUTED};
    border-bottom: 2px solid transparent; margin-right: 2px;
}}
QTabBar::tab:hover {{ color: {FG_DIM}; }}
QTabBar::tab:selected {{ color: #ffffff; border-bottom: 2px solid {ACCENT}; }}

/* ---------------- cartões ---------------- */
QGroupBox {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {BG_CARD}, stop:1 {BG_CARD_2});
    border: 1px solid {BORDER};
    border-top: 1px solid {BEVEL};
    border-radius: 10px;
    margin-top: 9px; padding: 10px 11px 9px 11px; font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 14px; padding: 0 7px;
    color: {FG_MUTED};
}}
QGroupBox:hover {{ border-color: {BORDER_STRONG}; }}

/* ---------------- botões ---------------- */
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #2c2c31, stop:1 #232327);
    border: 1px solid {BORDER};
    border-top: 1px solid {BEVEL};
    border-radius: 6px; padding: 5px 12px; color: {FG_DIM};
}}
QPushButton:hover {{ background: {BG_HOVER}; border-color: {BORDER_STRONG}; color: {FG}; }}
QPushButton:pressed {{ background: {BG_INPUT}; }}
QPushButton:disabled {{ color: #545b68; background: {BG_CARD_2}; border-color: #262b34; }}
QPushButton:default {{ border: 1px solid {ACCENT}; }}

QPushButton#primary {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {ACCENT}, stop:1 {ACCENT_DEEP});
    border-color: {ACCENT_DEEP};
    border-top: 1px solid #ffb066;
    color: #1a1208; font-weight: 700;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: #3a3229; border-color: #3a3229; color: #7d7169; }}

QPushButton#slot {{
    padding: 6px 20px; font-weight: 600; color: {FG_MUTED};
}}
QPushButton#slot:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: #fff; }}

QPushButton#ghost {{ background: transparent; border-color: {BORDER}; color: {FG_MUTED}; }}
QPushButton#ghost:hover {{ color: {FG_DIM}; border-color: {BORDER_STRONG}; background: {BG_SUBTLE}; }}

/* ---------------- campos ---------------- */
QComboBox, QListWidget, QLineEdit {{
    background: {BG_INPUT}; border: 1px solid #333a47; border-radius: 8px;
    padding: 6px 9px; selection-background-color: {BG_HOVER};
}}
QComboBox:hover, QLineEdit:focus {{ border-color: {ACCENT}; }}
QComboBox:disabled {{ color: #545b68; background: {BG_CARD_2}; }}
QComboBox::drop-down {{ border: 0; width: 22px; }}
QComboBox::down-arrow {{
    image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {FG_MUTED}; margin-right: 8px;
}}
QComboBox QAbstractItemView::item {{ min-height: 26px; padding-left: 8px; }}
QComboBox QAbstractItemView {{
    background: {BG_INPUT}; border: 1px solid #333a47;
    selection-background-color: {BG_HOVER}; outline: 0; padding: 4px;
}}
QListWidget::item {{ padding: 9px 10px; border-radius: 8px; }}
QListWidget::item:hover {{ background: {BG_SUBTLE}; }}
QListWidget::item:selected {{ background: {BG_HOVER}; color: #fff; }}

QLineEdit::placeholder {{ color: #5b6270; }}

/* ---------------- sliders ---------------- */
QSlider::groove:horizontal {{
    height: 4px; background: {BG_INPUT}; border-radius: 3px;
    border: 1px solid #101012;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {ACCENT}, stop:1 {ACCENT_DEEP});
    border-radius: 4px;
}}
QSlider::handle:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #f2f0ec, stop:1 #c9c6c0);
    border: 1px solid #6a6862;
    width: 13px; margin: -6px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #ffffff, stop:1 #dcd8d2);
    border-color: {ACCENT};
}}
QSlider::groove:horizontal:disabled {{ background: #262b34; }}
QSlider::sub-page:horizontal:disabled {{ background: #3a3f48; }}

/* ---------------- progresso ---------------- */
QProgressBar {{ background: {BG_INPUT}; border: 0; border-radius: 4px; height: 7px; }}
QProgressBar::chunk {{ background: {OK}; border-radius: 4px; }}

/* ---------------- rótulos e status ---------------- */
QLabel#muted {{ color: {FG_MUTED}; }}
QLabel#sig {{ color: #a8afbd; font-size: {FS_SMALL}; }}
QStatusBar {{ color: {FG_MUTED}; }}
QStatusBar::item {{ border: 0; }}

QCheckBox {{ spacing: 8px; color: {FG_DIM}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid {BORDER_STRONG};
    border-top-color: #54545e;
    background: {BG_INPUT};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #333a47; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #454d5d; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{
    background: #10131a; color: {FG}; border: 1px solid {BORDER_STRONG};
    border-radius: 6px; padding: 6px 8px;
}}

QMenu {{ background: {BG_INPUT}; border: 1px solid #333a47; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {BG_HOVER}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
"""