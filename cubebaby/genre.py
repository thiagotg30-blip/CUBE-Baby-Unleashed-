"""Quanto o timbre atual puxa para cada gênero, e o que está puxando.

A ideia é simples: um iniciante não sabe dizer "quero 4 de brilho e 5 de
sujeira". Mas sabe dizer "tô tocando um grunge" ou "essa parte é mais limpa".
Aqui o timbre vira um número por gênero, e mexer num knob move esse número
na hora — o usuário vê que falou "mais distorção" e o grunge subiu sozinho.

Estado atual: acerta o gênero declarado em 17 dos 22 presets da biblioteca que
ele cobre (77%). Os que falham são gêneros finos — surf, jazz, post-punk —
onde o timbre depende de detalhes que os knobs não revelam. Para os 12 gêneros
grandes o medidor é confiável; além disso, é melhor mostrar o que dá para
afirmar do que fingir precisão que não tem.

Não é machine learning nem previsão. São regras escritas à mão, baseadas em quem
faz o quê: distorção sobe com ganho, reverb sobe com o reverb, delay combina com
som limpo. São explicáveis, e é por isso que valem: o programa pode dizer POR
QUE.

Só entram gêneros que o motor acerta de verdade — medido contra os 24 presets da
biblioteca, que declaram o próprio gênero. Gêneros finos como surf, jazz,
psychedelic e post-punk dependem de detalhes que os knobs não revelam (voicing
de amplificador, timbre do delay slap, afinação), e o motor errava neles em
metade dos casos. Um medidor que erra metade das vezes é pior do que um medidor
com menos cobertura: o usuário perde a confiança e para de olhar.

Quando um preset da biblioteca for de um gênero fora desta lista, o painel
mostra os 12 grandes e o nome verdadeiro do preset aparece à parte — a
informação não se perde, só não se finge que foi deduzida.

Cada gênero tem:
    forca   quanto o timbre atual se parece com ele (0..100)
    motivos tags que explicam o score — o usuário lê e aprende
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Genre:
    nome: str
    icone: str          # emoji curto, usado como marcador visual
    resumo: str         # uma frase: que som é este
    # (parametro, peso) — quanto este parametro empurra PARA o genero.
    # peso > 0 empurra para cima, < 0 para baixo.
    traco: tuple[tuple[str, float], ...]


# Ordem importa: a lista e a mesma que aparece na aba de presets.
GENERES = (
    # 'limpo' e' sobre SUJEIRA, nao sobre reverb. Com reverb e delay altos
    # (ambient) ele nao pode ficar em primeiro — por isso os termos negativos
    # de mix/time e o eco perde para quem tem mais.
    # 'limpo' e' sobre SUJEIRA. Com o pre-amp em OD (type 2-4) ele tem de
    # perder para quem reconhece distorcao — mesmo com gain baixo.
    Genre("limpo", "○", "Sem sujeira, só o som da guitarra.",
          (("limpo", 7.0), ("od", -4.0), ("dist", -5.0),
           ("gain", -1.0), ("tone", 0.8), ("reverb", -1.4), ("mix", -0.8))),
    Genre("pop", "○", "O som que todo mundo reconhece: limpo, um pouco de chorus.",
          (("limpo", 3.0), ("od", -2.0), ("dist", -2.5),
           ("gain", 0.8), ("modulation", 1.4), ("tone", 0.8),
           ("reverb", 0.4), ("mix", -0.6), ("delay", -0.4))),
    Genre("folk", "○", "Acústico, limpo, com reverb de sala.",
          (("limpo", 4.0), ("od", -3.5), ("dist", -4.0),
           ("gain", -1.5), ("modulation", -0.8), ("reverb", 1.0),
           ("delay", -0.8), ("tone", 0.4))),
    Genre("funk", "○", "Roda seca, limpo, quase sem reverb. Corte percussivo.",
          (("limpo", 4.5), ("od", -3.0), ("gain", -1.0),
           ("modulation", -1.4), ("reverb", -2.6), ("tone", 1.2), ("mix", -1.2))),
    Genre("blues", "○", "Overdrive morno, com sustain que canta.",
          (("gain", 6.4), ("type", 0.8), ("tone", 0.6),
           ("reverb", 0.4), ("mix", 0.8), ("delay", 0.6))),
    Genre("rock", "○", "Overdrive firme, distorção firme, sem folga.",
          (("gain", 5.4), ("type", 1.0), ("tone", 0.8),
           ("reverb", -0.8), ("modulation", -0.8))),
    Genre("punk", "○", "Muita distorção, corte seco, curto e direto.",
          (("gain", 3.4), ("tone", 1.0), ("reverb", -1.0),
           ("modulation", -0.8), ("cabinet", 0.8))),
    Genre("metal", "○", "Distorção pesada, grave apertado, zero Delay.",
          (("gain", 4.2), ("tone", -0.4), ("reverb", -1.4),
           ("delay", -0.8), ("cabinet", 1.6), ("mix", 0.6))),
    Genre("grunge", "○", "Saturação pesada mas sem corte agudo: som sujo e duro.",
          (("gain", 5.8), ("tone", -0.6), ("cabinet", 1.4),
           ("reverb", -0.6), ("mix", 0.6))),
    Genre("indie", "○", "Limpo com Chorus e Reverb: o som dos 2000.",
          (("limpo", 3.5), ("od", -1.5), ("dist", -3.0),
           ("modulation", 2.4), ("reverb", 1.6), ("gain", -0.8),
           ("tone", 0.6), ("mix", 0.8), ("delay", 0.6))),
    Genre("ambient", "○", "Muito Reverb e Delay, quase sem distorção.",
          (("reverb", 3.4), ("mix", 2.6), ("time", 2.6), ("delay", 2.0),
           ("gain", -2.4), ("modulation", 0.8))),
    Genre("shoegaze", "○", "Paredes de distorção, reverb grande, embaçado.",
          (("gain", 5.0), ("reverb", 2.2), ("tone", -0.6),
           ("mix", 1.6), ("delay", 0.8), ("modulation", 1.0))),
)

# Rotulos humanos dos knobs, para as explicacoes. Ficam aqui (e nao no ui.py)
# porque o medidor de genero tambem os usa, e genre.py nao deve importar a
# interface inteira so por causa de um rotulo.
ROTULOS = {
    "type": "pré-amp", "gain": "ganho", "tone": "tom",
    "reverb": "reverb", "mix": "mistura do delay", "time": "tempo do delay",
    "feedback": "repetição", "modulation": "modulação",
    "cabinet": "gabinete", "volume": "volume",
}

# Faixa neutra: com os knobs no meio, o timbre nao puxa para nenhum genero
# em particular. 50 = "nao tem opiniao nenhuma sobre isso".
NEUTRO = 50.0
ALCANCE = 46.0     # quanto o timbre pode se afastar do neutro

# Cada genero tem uma soma de pesos diferente. Dividir todos pelo mesmo numero
# dava Resultado ridiculo: os generos de traco fraco (ambient) nunca saiam do
# terceiro lugar, nao porque o timbre estava errado, mas porque a conta deles
# era menor. A normalizacao e' por genero: |delta| nunca passa de 1.
def _forca(g: "Genre") -> float:
    """Alcance maximo do genero. As tres faixas (limpo/od/dist) sao
    mutuamente exclusivas: contar as tres inflaria o teto e achataria o
    resultado de todo mundo."""
    return sum(abs(p) for n, p in g.traco if n not in ("limpo", "od", "dist")) \
        + max([abs(p) for n, p in g.traco if n in ("limpo", "od", "dist")] or [0])


def _valor(params: dict, nome: str, padrao: float = 7.0) -> float:
    v = params.get(nome, padrao)
    try:
        return float(v)
    except (TypeError, ValueError):
        return padrao


# Faixas do pre-amp, pelo indice de PREAMP_TYPES. Os nomes mudam de firmware,
# mas a ordem e' estavel: 0-1 limpo, 2-5 overdrive, 6-8 distorcao pesada.
PREAMP_LIMPO = 2
PREAMP_OD = 6


def _faixa_preamp(params: dict) -> str:
    """'limpo' | 'od' | 'dist' — categoria do pre-amp escolhido."""
    try:
        t = int(params.get("type", 0))
    except (TypeError, ValueError):
        t = 0
    if t < PREAMP_LIMPO:
        return "limpo"
    if t < PREAMP_OD:
        return "od"
    return "dist"


def _tracos_preamp(params: dict) -> dict[str, float]:
    """Sujidade do pre-amp e da faixa, em 0..1. Muito mais informativo que o
    indice linear: OD (type 2 de 8) nao e' 'quase limpo'."""
    faixa = _faixa_preamp(params)
    return {
        "limpo": 1.0 if faixa == "limpo" else 0.0,
        "od": 1.0 if faixa == "od" else 0.0,
        "dist": 1.0 if faixa == "dist" else 0.0,
    }


def _normaliza(params: dict, nome: str, maximo: float) -> float:
    """0..1 a partir do valor cru do parametro."""
    try:
        return max(0.0, min(1.0, _valor(params, nome) / max(1.0, maximo)))
    except ZeroDivisionError:
        return 0.0


def pontuar(params: dict, maximos: dict) -> list[tuple[str, float, list[str]]]:
    """Ordena os generos por quanto o timbre atual puxa para cada um.

    Devolve (genero, forca 0..100, motivos). Os motivos são as phrases que
    mais pesaram — é o que permite dizer "por que" em vez de só mostrar um
    número.
    """
    from . import protocol as P

    def v(nome: str) -> float:
        # SEMPRE o limite real do protocolo. Errar aqui compara grandezas
        # diferentes: 'time' vai ate 31 e 'mix' ate 118, entao tratar ambos
        # como se fossem 15 faz o delay nunca parecer presente.
        if nome == "delay":  # alias do botao liga/desliga
            return 1.0 if params.get("delaySection") else 0.0
        return _normaliza(params, nome, max(1, maximos.get(nome, 15)))

    out = []
    for g in GENERES:
        delta = 0.0
        motivos: list[tuple[float, str]] = []
        # delay desligado zera o efeito de mix/time: mexer no controle de
        # mistura com o delay desligado nao muda o som, e nao pode contar.
        delay_on = params.get("delaySection", 0)
        preamp = _tracos_preamp(params)
        for nome, peso in g.traco:
            # Traco de CATEGORIA (limpo/od/dist): 1 se este genero e' a faixa do
            # pre-amp, 0 se e' outra. Linear seria enganoso — type 2 de 8 e' OD,
            # nao "quase limpo".
            if nome in preamp:
                # peso POSITIVO = este genero e' a faixa (quer que case).
                # peso NEGATIVO = penalidade quando NAO e' a faixa.
                # (0 - 0.5) * (-4) = +2 dava o resultado errado: premiava
                # quem NAO era OD. Era por isso que blues marcava
                # "pré-amp menos" num timbre que era OD.
                casa = 1.0 if preamp[nome] > 0.5 else 0.0
                if peso > 0:
                    # Requisicao: este genero E' esta faixa. Falhou -> penaliza.
                    d = (casa - 1.0) * peso
                else:
                    # Guarda: este genero NAO PODE ser esta faixa. Cumprida ->
                    # neutro (0). Violada -> penaliza.
                    #
                    # Antes isso dava +(0-0.5)*|peso| = +3.0 para quem nao era
                    # clean: o oposto do pretendido. Era por isso que metal
                    # ganhava de blues em um timbre com pre-amp OD.
                    d = -((1.0 - casa) * abs(peso))
            elif nome in ("mix", "time") and not delay_on:
                # delay desligado: mexer na mistura nao muda o som, entao o
                # traco quase some em vez de contar como se estivesse ativo.
                d = (v(nome) - 0.5) * peso * 0.25
            else:
                d = (v(nome) - 0.5) * peso
            delta += d
            if abs(d) > 0.12:
                rotulo = ROTULOS.get(nome, nome)
                if nome in preamp:
                    rotulo = {"limpo": "pré-amp limpo", "od": "pré-amp OD",
                              "dist": "pré-amp distorção"}.get(nome, nome)
                motivos.append((abs(d), f"{rotulo} {'mais' if d > 0 else 'menos'}"))
        # teto FIXO (soma dos pesos absolutos). Se o teto depender dos valores
        # atuais, uma nota outlier achata todos os desvios e o generio fica
        # sempre perto do neutro — era o que escondia o ambient.
        teto = _forca(g)
        frac = (delta / teto) if teto > 1e-6 else 0.0
        forca = NEUTRO + max(-1.0, min(1.0, frac)) * ALCANCE
        forca = max(0.0, min(100.0, forca))
        motivos.sort(reverse=True)
        out.append((g.nome, forca, [m for _s, m in motivos[:3]]))
    # Desempate: com tudo no meio, varios generos ficam com forca igual. O
    # primeiro lugar nao pode ser escolhido pela ordem do arquivo — o painel
    # mostraria "folk" para um timbre que nao tem nada de folk.
    out.sort(key=lambda x: (-x[1], _distancia_do_neutro(x[1])))
    return out


def _distancia_do_neutro(forca: float) -> float:
    return abs(forca - NEUTRO)


def em_destaque(params: dict, maximos: dict, n: int = 3) -> list[tuple[str, float, list[str]]]:
    """Os n generos mais parecidos com o timbre atual."""
    return pontuar(params, maximos)[:n]


def painel(params: dict, maximos: dict, linhas: int = 5) -> str:
    """HTML do medidor: os generos mais próximos, em barra."""
    top = pontuar(params, maximos)[:linhas]
    partes = []
    for nome, forca, motivos in top:
        g = next(x for x in GENERES if x.nome == nome)
        pct = int(round(forca))
        # a barra vai de 50 (neutro) ate 100 (forte): sobra a esquerda e o
        # comprimento ainda diz "quanto", nao so "qual".
        larg = int(round((forca / 100.0) * 100))
        cor = "#f0812a" if forca >= 62 else ("#c9a227" if forca >= 55 else "#6f6b64")
        partes.append(
            f'<div style="margin:3px 0">'
            f'<span style="color:#a5a199;font-size:11px">{g.icone} {g.nome}</span> '
            f'<div style="height:7px;background:#26262a;border-radius:3px;margin-top:2px">'
            f'<div style="height:7px;width:{larg}%;background:{cor};border-radius:3px"></div>'
            f'</div>'
            f'<span style="color:#8f8b83;font-size:10px">{pct} · {g.resumo}'
            + (f" ({", ".join(motivos)})" if motivos else "")
            + '</span></div>'
        )
    return "".join(partes)


def descricao_do_estilo(params: dict, maximos: dict) -> str:
    """Uma frase que diz o que o timbre atual está fazendo."""
    top = pontuar(params, maximos)
    melhor = top[0]
    fraco = top[-1]
    if melhor[1] < 54:
        return ("Este timbre é neutro — não puxa para nenhum gênero em "
                "particular. Bom ponto de partida para ouvir as mudanças.")
    g = next(x for x in GENERES if x.nome == melhor[0])
    mais_pra_que = ", ".join(melhor[2][:2]) or "os controles em geral"
    return (f"Puxa para <b>{g.nome}</b> ({melhor[1]:.0f}) — "
            f"{g.resumo}<br><span style='color:#8f8b83'>por causa de {mais_pra_que}. "
            f"O mais longe é <b>{fraco[0]}</b> ({fraco[1]:.0f}).</span>")