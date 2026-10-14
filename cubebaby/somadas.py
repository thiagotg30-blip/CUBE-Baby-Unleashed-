"""Timbre de bolso: três somadas que você monta com uma tecla, sem ir até o pedal.

O problema que resolve: a pedaleira fica longe, com o cabo esticado. Para
trocar de som no meio de uma música, o caminho normal seria levantar, esticar
o cabo e apertar o footswitch — inviável tocando.

Aqui você escolhe três somadas (por exemplo "intro limpo", "verso", "final
com crunch") e fica em 1, 2 e 3. Trocar de som vira apertar uma tecla, com as
duas mãos na guitarra.

Diferença em relação aos slots A/B/C do pedal, que já existem:

- Os slots moram DENTRO do aparelho: ficam gravados nele, e um splas pode usa-los
  se o computador for desligado. Trocar entre eles custa tempo de SysEx.
- As somadas ficam no COMPUTADOR. Trocar é instantâneo e o pedal não é
  consultado: é só enviar os 13 parâmetros do timbre escolhido.

Por isso as duas coisas não se anulam: os slots servem para deixar timbres
salvos no aparelho, as somadas servem para tocar.

Nada de inventar nome: a somada é "os 13 parâmetros" e nada mais. O que ela
faz é guardar isso e devolver na hora.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import protocol as P

MAX_SOMADAS = 3
ARQUIVO = "somadas.json"


def caminho(base: Path | None = None) -> Path:
    from .settings import data_dir
    return data_dir(base) / ARQUIVO


def vazias() -> list[dict | None]:
    return [None] * MAX_SOMADAS


def carregar(base: Path | None = None) -> list[dict | None]:
    """Lê as somadas. Arquivo corrompido ou ausente devolve vazio — nunca
    levanta, porque perder as somadas é ruim mas fechar o programa é pior."""
    p = caminho(base)
    if not p.exists():
        return vazias()
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return vazias()
    out = vazias()
    if not isinstance(dados, list):
        return out
    for i, item in enumerate(dados[:MAX_SOMADAS]):
        if _valido(item):
            out[i] = item
    return out


def _valido(item) -> bool:
    """Um item so vale se tiver TODOS os 13 parametros do pedal. Um timbre
    pela metade mudaria o pedal para um estado que o usuario nao pediu."""
    if not isinstance(item, dict):
        return False
    params = item.get("params")
    if not isinstance(params, dict):
        return False
    faltando = [n for n in P.PARAM_NAMES if n not in params]
    if faltando:
        return False
    for n, v in params.items():
        if not isinstance(v, int) or isinstance(v, bool):
            return False
        if n in P.PARAM_MAX and not (0 <= v <= P.PARAM_MAX[n]):
            return False
    return True


def salvar(somadas: list[dict | None], base: Path | None = None) -> bool:
    """Grava em .tmp e troca. Se fechar no meio, as somadas antigas sobrevivem
    em vez de sobrar um arquivo pela metade."""
    p = caminho(base)
    limpo = [s for s in somadas[:MAX_SOMADAS]]
    tmp = p.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(limpo, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
        return True
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def nome_de(somada: dict | None, indice: int) -> str:
    if not somada:
        return f"Tecla {indice + 1} — vazia"
    return somada.get("nome") or f"Tecla {indice + 1}"


def _completar(params: dict) -> dict:
    """Preenche os 13 parametros, com o que vier.

    Um preset da biblioteca nem sempre declara os 13: pode faltar
    feedback, por exemplo. Sem completar, a somada seria rejeitada na hora de
    gravar — e o usuario perderia o timbre sem entender por que.
    """
    return {n: int(params.get(n, 0)) for n in P.PARAM_NAMES}


def de_preset(preset) -> dict:
    """Monta uma somada a partir de um preset da biblioteca.

    Sempre completa os 13 parametros: e o que a validacao exige, e o que o
    pedal precisa para o timbre ficar inteiro.
    """
    params = getattr(preset, "params", None)
    if params is None and isinstance(preset, dict):
        params = preset.get("params", {})
    nome = (getattr(preset, "name", None) or getattr(preset, "nome", None)
            or (preset.get("nome") if isinstance(preset, dict) else None) or "Somada")
    genres = getattr(preset, "genres", None)
    if genres is None and isinstance(preset, dict):
        genres = preset.get("generos") or preset.get("genres")
    return {"nome": nome,
            "genres": list(genres or ())[:2],
            "params": _completar(dict(params or {}))}


def do_tempo_atual(params: dict, nome: str = "Meu timbre") -> dict:
    """Monta uma somada com o timbre que esta no pedal agora."""
    return {"nome": nome, "genres": [],
            "params": _completar(dict(params or {}))}


def descrever(somada: dict | None) -> str:
    """Linha curta pro botão: nome + o que define o timbre."""
    if not somada:
        return "vazia — aperte para gravar o timbre atual"
    p = somada.get("params", {})
    partes = []
    tipo = int(p.get("type", 0) or 0)
    if 0 <= tipo < len(P.PREAMP_TYPES):
        partes.append(P.PREAMP_TYPES[tipo][1])
    cab = int(p.get("cabinet", 0) or 0)
    if p.get("irSection") and cab:
        partes.append(f"gab {cab}")
    if p.get("reverbSection") and p.get("reverb", 0):
        partes.append(f"rev {p['reverb']}")
    if p.get("delaySection") and p.get("mix", 0):
        partes.append(f"delay {p['mix']}")
    return " · ".join(partes) or "limpo"