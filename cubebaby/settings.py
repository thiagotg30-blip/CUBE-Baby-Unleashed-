"""Preferências do usuário, persistidas em JSON.

Um programa que abre toda vez como se fosse a primeira vez não parece produto.
Aqui ficam as coisas que fazem sentido lembrar: tamanho da janela, aba em uso,
qual guitarra, quais dispositivos de áudio, e se a INTRODUCTION já foi vista.

Por que JSON em ~/Ganho e não QSettings: o QSettings no Windows escreve no
registro, que é invisível para o usuário e sobrevive mal a "desinstalar"
apagando uma pasta. Um JSON é portável (dá para levar num pendrive), legível, e
apagar é só apagar.

Gravação é sempre atômica: escreve em .tmp e troca. Se o programa for fechado
no meio (Ctrl+C, queda de energia), a preferência antiga sobrevive em vez de
sobrar um arquivo pela metade.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray

APP_DIR_NAME = "CUBEBabyUnleashed"
CONFIG_NAME = "preferences.json"

# Pastas antigas, em ordem. O programa renomeou mais de uma vez; sem migrar,
# quem já tinha presets e gravações perderia tudo de uma vez.
LEGACY_DIRS = ("Ganho", "CubeBabyStudio")

DEFAULTS = {
    "primeira_execucao": True,   # mostra a introdução
    "guitarra": "les-paul",
    "aba": 0,
    "entrada_audio": 0,
    "saida_audio": 0,
    "volume_monitor": 80,
    "firmware": "cuvave",   # lista de gabinetes: firmware do pedal
    "afinacao": "padrao",   # afinacao escolhida no afinador
    "janela": [1120, 660],       # largura, altura
    "maximizada": False,
    "idioma": "pt",         # idioma da interface: pt, en, es
}


def data_dir(base: Path | None = None) -> Path:
    """Pasta de dados do usuário, migrando a antiga se existir.

    Migrar em vez de só trocar o nome importa: quem já gravou takes e salvou
    presets não pode perder nada por causa de um rename.

    `base` existe para o teste: um teste de migração NÃO pode mexer na pasta
    real do usuário.
    """
    home = Path(base) if base else Path.home()
    d = home / APP_DIR_NAME
    if not d.exists():
        for old_name in LEGACY_DIRS:
            old = home / old_name
            if old.exists() and old.is_dir():
                try:
                    d.parent.mkdir(parents=True, exist_ok=True)
                    old.rename(d)
                    break
                except OSError:
                    pass  # sem permissão ou pasta aberta: usa a nova mesmo
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path(base: Path | None = None) -> Path:
    return data_dir(base) / CONFIG_NAME


class Settings:
    """Leitura/escrita das preferências. Nunca levanta:Prefs quebrado não pode
    impedir o programa de abrir — no pior caso, usa o padrão."""

    def __init__(self, path: Path | None = None) -> None:
        # path é injetável para teste; em produção usa sempre config_path().
        self.path = Path(path) if path else config_path()
        self.data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    # só aceita chaves conhecidas: um arquivo antigo ou editado
                    # à mão não deve injetar campos inesperados no resto do app
                    self.data.update({k: v for k, v in raw.items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass  # preferência corrompida: segue com o padrão

    def save(self) -> None:
        try:
            d = self.path.parent
            fd, tmp = tempfile.mkstemp(dir=str(d), prefix=".prefs-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)   # atômico
        except OSError:
            pass  # disco cheio ou permissão: perder preferência não é fatal

    # ---- acesso ----
    def get(self, key: str, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value) -> None:
        if key in DEFAULTS:
            self.data[key] = value

    # ---- janela ----
    def save_window(self, w, h: int, maximized: bool) -> None:
        self.set("janela", [w, h])
        self.set("maximizada", maximized)
        self.save()

    def restore_window(self, w) -> bool:
        """Aplica tamanho/posição salvos. Devolve False se não havia nada.

        Duas travas importantes:

        1. Um tamanho salvo quando a janela estava MAXIMIZADA é do tamanho da
           tela, não da janela. Restaurar isso sem maximizar deixa a janela
           maior que o monitor — foi o que aconteceu com 2974x824.
        2. Mesmo assim, o tamanho tem de CABER na tela. Monitor trocado,
           resolução reduzida ou dock externo desconectado não podem deixar a
           janela inalcançável.
        """
        try:
            size = self.get("janela")
            if not (isinstance(size, list) and len(size) == 2):
                return False
            width, height = int(size[0]), int(size[1])
            if width < 640 or height < 480:
                return False

            # Cabe na tela? Se nao, encolhe para o que couber (com uma folga
            # para a barra de tarefas e as bordas).
            try:
                from PySide6.QtGui import QGuiApplication
                scr = w.screen() or QGuiApplication.primaryScreen()
                if scr is not None:
                    disp = scr.availableGeometry()
                    width = min(width, max(640, disp.width() - 40))
                    height = min(height, max(480, disp.height() - 40))
            except Exception:  # noqa: BLE001
                pass

            try:
                mini = w.minimumSize()
            except Exception:  # noqa: BLE001
                mini = None
            if mini is not None and mini.isValid():
                # Respeita o mínimo FÍSICO da janela (definido pra nenhuma aba
                # cortar). Restaurar um tamanho menor que isso desfaria a
                # regra de quem toca com uma mão.
                width = max(width, mini.width())
                height = max(height, mini.height())

            w.resize(width, height)
            if self.get("maximizada"):
                w.showMaximized()
            return True
        except (TypeError, ValueError):
            return False

    # ---- primeira execução ----
    def is_first_run(self) -> bool:
        return bool(self.get("primeira_execucao", True))

    def mark_seen(self) -> None:
        self.set("primeira_execucao", False)
        self.save()