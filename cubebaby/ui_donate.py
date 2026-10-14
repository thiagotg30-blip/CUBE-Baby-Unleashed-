"""Aba "Apoiar o projeto": Pix, cripto, links e aviso legal.

Sem dependência de QR code: o Pix usa "copia e cola" (padrão BR Code/EMV) com
botão copiar. Cripto mostra o endereço com botão copiar. Se os dados não
estiverem configurados em `cubebaby/donate.py`, mostra aviso de "a configurar".
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from . import donate as DON


class DonateTab(QWidget):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win

        from . import i18n
        _lang = i18n.get_idioma()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 14, 18, 14)
        raiz.setSpacing(12)

        # ---- título ----
        ttl = QLabel(f"<b style='font-size:16px; color:#f0812a'>{i18n.tr('aba_apoiar', _lang)}</b>")
        raiz.addWidget(ttl)

        intro = QLabel(i18n.tr("apoiar_intro", _lang))
        intro.setWordWrap(True)
        intro.setObjectName("muted")
        raiz.addWidget(intro)

        # ---- Pix ----
        box_pix = QGroupBox(i18n.tr("pix_titulo", _lang))
        vp = QVBoxLayout(box_pix)
        if DON.PIX_CHAVE:
            lbl_chave = QLabel(i18n.tr("pix_chave", _lang))
            vp.addWidget(lbl_chave)
            ed = QLineEdit(DON.PIX_CHAVE)
            ed.setReadOnly(True)
            vp.addWidget(ed)
            btn_pix = QPushButton(i18n.tr("copiar", _lang))
            btn_pix.clicked.connect(lambda: self._copiar(DON.PIX_CHAVE))
            vp.addWidget(btn_pix)
            # QR code via "copia e cola"
            if DON.pix_copia_e_cola():
                lbl_copia = QLabel(i18n.tr("pix_copia_e_cola", _lang))
                vp.addWidget(lbl_copia)
                ed2 = QLineEdit(DON.pix_copia_e_cola())
                ed2.setReadOnly(True)
                vp.addWidget(ed2)
                btn_pix2 = QPushButton(i18n.tr("copiar_codigo", _lang))
                btn_pix2.clicked.connect(lambda: self._copiar(DON.pix_copia_e_cola()))
                vp.addWidget(btn_pix2)
        else:
            lbl = QLabel(i18n.tr("pix_a_configurar", _lang))
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#e8b84b;")
            vp.addWidget(lbl)
        raiz.addWidget(box_pix)

        # ---- Cripto ----
        box_cripto = QGroupBox(i18n.tr("cripto_titulo", _lang))
        vc = QVBoxLayout(box_cripto)
        if DON.CRIPTO_ENDERECO:
            lbl_rede = QLabel(f"<b>{i18n.tr('rede', _lang)}:</b> {DON.CRIPTO_REDE}")
            vc.addWidget(lbl_rede)
            lbl_token = QLabel(f"<b>{i18n.tr('token', _lang)}:</b> {DON.CRIPTO_TOKEN}")
            vc.addWidget(lbl_token)
            ed3 = QLineEdit(DON.CRIPTO_ENDERECO)
            ed3.setReadOnly(True)
            vc.addWidget(ed3)
            btn_cripto = QPushButton(i18n.tr("copiar", _lang))
            btn_cripto.clicked.connect(lambda: self._copiar(DON.CRIPTO_ENDERECO))
            vc.addWidget(btn_cripto)
        else:
            lbl = QLabel(i18n.tr("cripto_a_configurar", _lang))
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#e8b84b;")
            vc.addWidget(lbl)
        raiz.addWidget(box_cripto)

        # ---- Links ----
        box_links = QGroupBox(i18n.tr("links_titulo", _lang))
        vl = QVBoxLayout(box_links)
        if DON.GITHUB_SPONSORS:
            btn_gh = QPushButton(i18n.tr("github_sponsors", _lang))
            btn_gh.clicked.connect(lambda: self._abrir(DON.GITHUB_SPONSORS))
            vl.addWidget(btn_gh)
        if DON.GITHUB_REPO:
            btn_repo = QPushButton(i18n.tr("github_repo", _lang))
            btn_repo.clicked.connect(lambda: self._abrir(DON.GITHUB_REPO))
            vl.addWidget(btn_repo)
        if DON.Kofi:
            btn_kofi = QPushButton(i18n.tr("kofi", _lang))
            btn_kofi.clicked.connect(lambda: self._abrir(DON.Kofi))
            vl.addWidget(btn_kofi)
        if not any([DON.GITHUB_SPONSORS, DON.GITHUB_REPO, DON.Kofi]):
            lbl = QLabel(i18n.tr("links_a_configurar", _lang))
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#e8b84b;")
            vl.addWidget(lbl)
        raiz.addWidget(box_links)

        # ---- Aviso legal ----
        box_legal = QGroupBox(i18n.tr("aviso_legal", _lang))
        vlg = QVBoxLayout(box_legal)
        txt = QLabel(i18n.tr("aviso_texto", _lang))
        txt.setWordWrap(True)
        txt.setStyleSheet("color:#8f8b83; font-size:11px;")
        vlg.addWidget(txt)
        raiz.addWidget(box_legal)

        raiz.addStretch(1)

    def _copiar(self, texto: str) -> None:
        """Copia para a área de transferência."""
        cb = QApplication.clipboard()
        if cb:
            cb.setText(texto)
        try:
            self.win.status("Copiado para a área de transferência.")
        except Exception:  # noqa: BLE001
            pass

    def _abrir(self, url: str) -> None:
        """Abre no navegador padrão."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))
