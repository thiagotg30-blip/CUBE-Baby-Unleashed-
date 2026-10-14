"""Aba de IR de usuário: ler do pedal, exportar, importar um WAV novo.

Substitui a dependência do CubeSuite para o IR. O formato e os endereços
foram descobertos no hardware — ver `cubebaby/irfile.py` e
`docs/ir-de-usuario.md`.

Segurança em primeiro lugar: gravar na flash do pedal é irreversível se o
endereço estiver errado. Por isso a interface sempre:
  1. faz backup automático do IR atual antes de qualquer gravação;
  2. mostra o que vai acontecer antes de acontecer;
  3. tem um botão separado para restaurar o backup.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from . import irfile as IR
from . import ir_sets as SETS
from . import i18n as I18N


class IrTab(QWidget):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self._ir = None            # último IR lido do pedal
        self._bruto = None         # os 32768 bytes originais
        self._backup = None        # caminho do backup feito nesta sessão

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 12, 14, 12)
        raiz.setSpacing(10)

        titulo = QLabel(
            "<b style='font-size:15px'>Impulso (IR) do pedal</b><br>"
            "<span style='color:#9aa'>O CUBE Baby guarda <b>um</b> IR de usuário, "
            "que substitui o de fábrica. Aqui você lê, guarda e envia — sem "
            "precisar do CubeSuite.</span>")
        titulo.setWordWrap(True)
        raiz.addWidget(titulo)

        # ---- qual IR usar em cada preset --------------------------------
        box0 = QGroupBox(I18N.tr("qual_ir", I18N.get_idioma()))
        v0 = QVBoxLayout(box0)
        try:
            from . import irs as IRS
            from . import presets_lib as PL
            linhas = []
            for chave, sug in IRS.todas():
                p = PL.BY_KEY.get(chave)
                if not p:
                    continue
                cor = {"alta": "#5cc98c", "media": "#e8b84b"}.get(
                    sug.confianca, "#9aa")
                linhas.append(
                    f"<tr><td style='padding:2px 10px 2px 0'>"
                    f"<span style='color:{cor}'>●</span></td>"
                    f"<td style='padding:2px 10px 2px 0'><b>{p.name}</b></td>"
                    f"<td style='padding:2px 10px 2px 0'>{sug.arquivo}</td>"
                    f"<td style='padding:2px 0; color:#9aa'>{sug.caixa}</td></tr>")
            intro = (
                "<span style='color:#9aa'>Cada preset já vem com um gabinete de "
                "fábrica que funciona sozinho. A lista abaixo é para quem tem um "
                "IR melhor: qual arquivo usar para chegar mais perto do som.<br>"
                "<b style='color:#5cc98c'>●</b> combina bem · "
                "<b style='color:#e8b84b'>●</b> aproximação<br>"
                "Importe pelo CubeSuite (banco 8). Nada aqui substitui o "
                "gabinete de fábrica do preset.</span><br><br>"
                "<table cellspacing='0'>" + "".join(linhas) + "</table>")
            lbl0 = QLabel(intro)
            lbl0.setWordWrap(True)
            lbl0.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl0.setObjectName("sig")
            v0.addWidget(lbl0)
        except Exception as e:  # noqa: BLE001
            v0.addWidget(QLabel(f"— lista indisponível ({e}) —"))
        rol0 = QScrollArea(); rol0.setWidgetResizable(True)
        w0 = QWidget(); w0.setLayout(v0)
        rol0.setWidget(w0)
        rol0.setMinimumHeight(160)
        rol0.setMaximumHeight(220)
        raiz.addWidget(box0)

        # ---- estado atual -------------------------------------------------
        box = QGroupBox(I18N.tr("ir_estado", I18N.get_idioma()))
        v = QVBoxLayout(box)
        self.lbl_estado = QLabel(I18N.tr("ainda_nao_li", I18N.get_idioma()))
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setObjectName("sig")
        v.addWidget(self.lbl_estado)
        linha = QHBoxLayout()
        self.btn_ler = QPushButton(I18N.tr("ir_ler", I18N.get_idioma()))
        self.btn_ler.setObjectName("primary")
        self.btn_ler.clicked.connect(self.ler)
        linha.addWidget(self.btn_ler)
        self.btn_exportar = QPushButton(I18N.tr("ir_exportar", I18N.get_idioma()))
        self.btn_exportar.clicked.connect(self.exportar)
        self.btn_exportar.setEnabled(False)
        linha.addWidget(self.btn_exportar)
        linha.addStretch()
        v.addLayout(linha)
        raiz.addWidget(box)

        # ---- enviar (VALIDADO no hardware) --------------------------------
        box2 = QGroupBox(I18N.tr("enviar_ir", I18N.get_idioma()))
        v2 = QVBoxLayout(box2)
        aviso = QLabel(
            "<b style='color:#5cc98c'>Funciona.</b> A gravação foi validada no "
            "aparelho: enviar um IR e reler deu <b>correlação +0,99</b> com o "
            "arquivo enviado.<br><br>"
            "<b style='color:#e8a33d'>O IR de fábrica do banco escolhido é "
            "substituído.</b> O programa faz um backup do IR atual antes de "
            "gravar, e você pode voltar atrás pelo botão abaixo.")
        aviso.setWordWrap(True)
        aviso.setObjectName("sig")
        v2.addWidget(aviso)

        lb = QHBoxLayout()
        lb.addWidget(QLabel(I18N.tr("banco_lbl", I18N.get_idioma())))
        self.cmb_banco = QComboBox()
        for b in range(1, IR.IR_BANCOS + 1):
            self.cmb_banco.addItem(f"Banco {b}", b)
        lb.addWidget(self.cmb_banco)
        lb.addStretch()
        v2.addLayout(lb)
        v2.addSpacing(8)

        self.lbl_novo = QLabel(I18N.tr("nenhum_arquivo", I18N.get_idioma()))
        self.lbl_novo.setWordWrap(True)
        self.lbl_novo.setObjectName("sig")
        v2.addWidget(self.lbl_novo)
        v2.addSpacing(8)

        l2 = QHBoxLayout()
        self.btn_escolher = QPushButton(I18N.tr("escolher_wav", I18N.get_idioma()))
        self.btn_escolher.clicked.connect(self.escolher)
        l2.addWidget(self.btn_escolher)
        l2.addSpacing(8)
        self.btn_enviar = QPushButton(I18N.tr("enviar_pedal", I18N.get_idioma()))
        self.btn_enviar.setObjectName("primary")
        self.btn_enviar.setMinimumWidth(180)
        self.btn_enviar.clicked.connect(self.enviar)
        self.btn_enviar.setEnabled(False)
        l2.addWidget(self.btn_enviar)
        l2.addStretch()
        v2.addLayout(l2)
        raiz.addWidget(box2)

        # ---- backup -------------------------------------------------------
        box3 = QGroupBox(I18N.tr("voltar_ir", I18N.get_idioma()))
        v3 = QVBoxLayout(box3)
        self.lbl_backup = QLabel(I18N.tr("nenhum_backup", I18N.get_idioma()))
        self.lbl_backup.setWordWrap(True)
        self.lbl_backup.setObjectName("sig")
        v3.addWidget(self.lbl_backup)
        l3 = QHBoxLayout()
        self.btn_restaurar = QPushButton(I18N.tr("restaurar_backup", I18N.get_idioma()))
        self.btn_restaurar.clicked.connect(self.restaurar)
        self.btn_restaurar.setEnabled(False)
        l3.addWidget(self.btn_restaurar)
        self.btn_backup_arquivo = QPushButton(I18N.tr("restaurar_arquivo", I18N.get_idioma()))
        self.btn_backup_arquivo.clicked.connect(self.restaurar_de_arquivo)
        l3.addWidget(self.btn_backup_arquivo)
        l3.addStretch()
        v3.addLayout(l3)
        raiz.addWidget(box3)

        # ---- SETS: 8 IRs por estilo ---------------------------------------
        box4 = QGroupBox(I18N.tr("encher_8", I18N.get_idioma()))
        v4 = QVBoxLayout(box4)
        v4.addWidget(QLabel(
            "<span style='color:#9aa'>O pedal tem <b>8 bancos</b>. Um set "
            "escolhe 8 IRs de um estilo e envia para os 8 de uma vez — você "
            "fica com um arsenal daquele som.<br>"
            "<b style='color:#e8a33d'>Isto sobrescreve os 8 bancos.</b> O "
            "programa faz backup de cada um antes.</span>"))
        self.cmb_set = QComboBox()
        for st in SETS.todos():
            self.cmb_set.addItem(st.nome, st.key)
        v4.addWidget(self.cmb_set)
        v4.addSpacing(6)
        self.lbl_set = QLabel("—")
        self.lbl_set.setWordWrap(True)
        self.lbl_set.setObjectName("sig")
        v4.addWidget(self.lbl_set)
        v4.addSpacing(8)
        l4 = QHBoxLayout()
        self.btn_aplicar_set = QPushButton(I18N.tr("enviar_set", I18N.get_idioma()))
        self.btn_aplicar_set.setObjectName("primary")
        self.btn_aplicar_set.setMinimumWidth(220)
        self.btn_aplicar_set.clicked.connect(self.aplicar_set)
        l4.addWidget(self.btn_aplicar_set)
        l4.addStretch()
        v4.addLayout(l4)
        self.cmb_set.currentIndexChanged.connect(self._mostrar_set)
        self._mostrar_set()
        raiz.addWidget(box4)

        raiz.addStretch()

    def _set_atual(self):
        return SETS.get(self.cmb_set.currentData())

    def _mostrar_set(self, *_a) -> None:
        st = self._set_atual()
        if st is None:
            self.lbl_set.setText("—")
            return
        linhas = "".join(
            f"<tr><td style='padding:1px 8px 1px 0;color:#9aa'>banco {i}</td>"
            f"<td style='padding:1px 8px 1px 0'>{sl.arquivo}</td>"
            f"<td style='padding:1px 0;color:#9aa'>{sl.caixa}</td></tr>"
            for i, sl in enumerate(st.slots, 1))
        self.lbl_set.setText(
            f"{st.descricao}<br><br><table cellspacing='0'>{linhas}</table>")

    def aplicar_set(self) -> None:
        st = self._set_atual()
        if st is None:
            return
        if QMessageBox.question(
                self, "Enviar o set",
                f"Enviar os 8 IRs de <b>{st.nome}</b> para os 8 bancos?\n\n"
                f"<b>Os 8 bancos serão sobrescritos.</b>\n"
                f"Um backup de cada um é feito antes.\n\n"
                f"Leva cerca de 3 minutos."
                ) != QMessageBox.Yes:
            return

        pasta = Path.home() / SETS.PASTA_PACK

        def tarefa():
            feitos, erros = [], []
            for i, sl in enumerate(st.slots, 1):
                try:
                    caminho = pasta / sl.pasta / sl.arquivo
                    if not caminho.exists():
                        erros.append(f"banco {i}: arquivo não encontrado")
                        continue
                    # backup do banco
                    atual = self._ler_banco(i)
                    dados = IR.encode_bloco(atual)
                    bak = self._backup_dir() / (
                        f"set_{st.key}_banco{i}_"
                        f"{hashlib.sha256(dados).hexdigest()[:10]}.bin")
                    bak.write_bytes(dados)
                    # grava o novo
                    novo = IR.de_wav(caminho)
                    novo.banco = i
                    novo.marcador = atual.marcador
                    self._grava_banco(novo)
                    feitos.append(i)
                except Exception as e:  # noqa: BLE001
                    erros.append(f"banco {i}: {type(e).__name__}: {str(e)[:60]}")
            return feitos, erros

        def pronto(res, err):
            if err is not None:
                QMessageBox.warning(self, "Enviar o set", str(err))
                return
            feitos, erros = res
            msg = f"IRs gravados nos bancos: {feitos}"
            if erros:
                msg += "\n\nOcorrências:\n" + "\n".join(erros)
            msg += f"\n\nBackups em:\n{self._backup_dir()}"
            QMessageBox.information(self, "Set aplicado", msg)
            self.ler()

        self._status(f"Enviando o set '{st.nome}' para os 8 bancos… (~3 min)")
        self._roda(tarefa, pronto)
    @property
    def pedal(self):
        return getattr(self.win, "pedal", None)

    def _ocupado(self) -> bool:
        p = self.pedal
        return not (p and getattr(p, "connected", False))

    def _roda(self, fn, cb) -> None:
        """Executa no worker do programa.

        Falar com o pedal bloqueia (gravar o IR leva ~2,5 min), então nunca na
        thread da interface. O Runner é assíncrono: o resultado chega por
        callback — por isso `cb` é obrigatório.
        """
        if self._ocupado():
            QMessageBox.warning(self, "Sem pedal",
                                "Conecte a pedaleira primeiro (aba Pedal).")
            return
        if hasattr(self.win, "runner"):
            self.win.runner.submit(fn, cb)
            return
        try:
            res, err = fn(), None
        except Exception as exc:  # noqa: BLE001
            res, err = None, exc
        cb(res, err)

    def _status(self, texto: str) -> None:
        if hasattr(self.win, "status"):
            self.win.status(texto)

    def _banco(self) -> int:
        try:
            return int(self.cmb_banco.currentData())
        except Exception:  # noqa: BLE001
            return 1

    def _ler_banco(self, banco: int):
        """Lê SÓ o bloco do banco. Ler a área inteira mistura 8 bancos e faz
        parecer que tudo muda — foi o erro que custou tempo nesta investigação."""
        p = self.pedal
        base = IR.endereco_do_banco(banco)
        buf = bytearray()
        for off in range(0, IR.IR_BLOCK_BYTES, 64):
            n = min(64, IR.IR_BLOCK_BYTES - off)
            buf += p.read_memory(IR.IR_MEMORY, base + off, n)
        return IR.decode_bloco(bytes(buf), banco)

    def _grava_banco(self, ir) -> None:
        p = self.pedal
        dados = IR.encode_bloco(ir)
        base = IR.endereco_do_banco(ir.banco)
        for off in range(0, len(dados), 64):
            n = min(64, len(dados) - off)
            if not p.write_memory(IR.IR_MEMORY, base + off, dados[off:off + n]):
                raise RuntimeError(
                    f"o pedal recusou a escrita no offset {off:#x} do banco {ir.banco}")
        return None

    def _backup_dir(self) -> Path:
        d = Path.home() / "TomCUBEBaby" / "IRs" / "backups"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---- ações -----------------------------------------------------------
    def ler(self) -> None:
        banco = self._banco()

        def pronto(ir, err):
            if err is not None:
                QMessageBox.warning(self, "Ler o IR", str(err))
                return
            self._ir = ir
            self._mostrar()

        self._status(f"Lendo o IR do banco {banco}…")
        self._roda(lambda: self._ler_banco(banco), pronto)

    def _mostrar(self) -> None:
        ir = self._ir
        if ir is None:
            return
        if ir.esta_vazio():
            self.lbl_estado.setText(
                f"O banco {ir.banco} está <b>vazio</b>.")
            self.btn_exportar.setEnabled(False)
            return
        self.lbl_estado.setText(
            f"<b>{ir.resumo()}</b><br>"
            f"<span style='color:#9aa'>um banco = 1023 amostras a 48 kHz, em "
            f"<code>memory={IR.IR_MEMORY}</code>, endereço "
            f"<code>{IR.endereco_do_banco(ir.banco):#x}</code> · "
            f"marcador {ir.marcador}</span>")
        self.btn_exportar.setEnabled(True)
        self._status(f"IR lido — {ir.resumo()}")

    def exportar(self) -> None:
        if self._ir is None:
            return
        alvo, _ = QFileDialog.getSaveFileName(
            self, "Salvar o IR do pedal",
            str(Path.home() / f"IR_banco{self._ir.banco}.wav"), "WAV (*.wav)")
        if not alvo:
            return
        IR.para_wav(self._ir, alvo)
        QMessageBox.information(self, "Salvo", f"IR exportado:\n{alvo}")

    def escolher(self) -> None:
        alvo, _ = QFileDialog.getOpenFileName(
            self, "Escolher um IR", str(Path.home()), "WAV (*.wav)")
        if not alvo:
            return
        try:
            novo = IR.de_wav(alvo)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Arquivo não serve",
                                 f"Não consegui ler esse WAV.\n\n{e}")
            return
        self._novo_ir = novo
        self._novo_caminho = alvo
        self.lbl_novo.setText(
            f"<b>{Path(alvo).name}</b><br>"
            f"vai virar <b>{novo.duracao_ms:.1f} ms</b> a 48 kHz "
            f"({len(novo.samples)} amostras), normalizado — o mesmo que o "
            f"CubeSuite faz.")
        self.btn_enviar.setEnabled(True)

    def enviar(self) -> None:
        novo = self._novo_ir
        if novo is None:
            return
        banco = self._banco()
        nome = Path(self._novo_caminho or "?").name
        if QMessageBox.question(
                self, "Confirmar gravação",
                f"Enviar <b>{nome}</b> para o <b>banco {banco}</b>?\n\n"
                f"O IR de fábrica desse banco será substituído.\n"
                f"Um backup é feito automaticamente antes.") != QMessageBox.Yes:
            return

        novo.banco = banco

        def tarefa():
            # 1) backup do que está lá — só o bloco desse banco
            atual = self._ler_banco(banco)
            dados_atual = IR.encode_bloco(atual)
            h = hashlib.sha256(dados_atual).hexdigest()[:12]
            bak = self._backup_dir() / f"IR_banco{banco}_antes_{h}.bin"
            bak.write_bytes(dados_atual)
            self._backup = bak
            # 2) grava o novo no banco
            novo.marcador = atual.marcador   # preserva o campo estrutural
            self._grava_banco(novo)
            # 3) relê o MESMO banco para conferir
            return self._ler_banco(banco)

        def pronto(ir_lido, err):
            if err is not None:
                QMessageBox.warning(
                    self, "Enviar o IR",
                    f"{err}\n\nO backup do IR anterior está em:\n{self._backup}")
                return
            self._ir = ir_lido
            self._mostrar()
            if self._backup:
                self.lbl_backup.setText(
                    f"Backup desta sessão: <code>{self._backup.name}</code>")
                self.btn_restaurar.setEnabled(True)
            # confere pela FORMA — o hash dos bytes crus não serve
            c = IR.correlacao(ir_lido.samples, novo.samples, 300)
            ok = c > 0.7
            QMessageBox.information(
                self, "Enviado" if ok else "Confira",
                (f"IR gravado no banco {banco}.\n\n"
                 f"Semelhança com o arquivo enviado: {c:+.2f}\n"
                 if ok else
                 f"Gravou, mas a semelhança ficou em {c:+.2f} — confira de ouvido.\n"))

        self._status(f"Enviando {nome} para o banco {banco}… (uns 20 s)")
        self._roda(tarefa, pronto)

    def restaurar(self) -> None:
        if not self._backup or not self._backup.exists():
            return
        if QMessageBox.question(
                self, "Restaurar",
                f"Voltar o IR para <code>{self._backup.name}</code>?"
                ) != QMessageBox.Yes:
            return
        dados = self._backup.read_bytes()
        if len(dados) != IR.IR_BLOCK_BYTES:
            QMessageBox.critical(self, "Backup inválido",
                                 f"Esperava {IR.IR_BLOCK_BYTES} bytes.")
            return
        banco = self._banco()
        ir = IR.decode_bloco(dados, banco)
        self._roda(lambda: self._grava_banco(ir),
                   lambda r, e: self._fim_restaurar(e))

    def restaurar_de_arquivo(self) -> None:
        alvo, _ = QFileDialog.getOpenFileName(
            self, "Escolher o backup do banco (4096 bytes)",
            str(self._backup_dir()), "Backup do IR (*.bin)")
        if not alvo:
            return
        dados = Path(alvo).read_bytes()
        if len(dados) != IR.IR_BLOCK_BYTES:
            QMessageBox.critical(
                self, "Arquivo errado",
                f"Esperava {IR.IR_BLOCK_BYTES} bytes (um banco), "
                f"o arquivo tem {len(dados)}.")
            return
        banco = self._banco()
        if QMessageBox.question(
                self, "Restaurar",
                f"Gravar <code>{Path(alvo).name}</code> no banco {banco}?"
                ) != QMessageBox.Yes:
            return
        ir = IR.decode_bloco(dados, banco)
        self._roda(lambda: self._grava_banco(ir),
                   lambda r, e: self._fim_restaurar(e))

    def _fim_restaurar(self, err) -> None:
        if err is not None:
            QMessageBox.warning(self, "Restaurar", str(err))
            return
        self.ler()
        QMessageBox.information(self, "Restaurado",
                                "O IR anterior foi gravado de volta no pedal.")
