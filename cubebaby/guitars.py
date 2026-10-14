"""Perfis de guitarra: como o mesmo preset se adapta a cada instrumento.

O CUBE Baby é um pedal de ganho/delay/reverb — ele não sabe qual guitarra está
plugada. O que ele faz é aplicar o preset nos *parâmetros*; a guitarra decide
o timbre final. Por isso a adaptação aqui não manda nada pro pedal: ela é uma
camada de *voicing*, um viés aplicado aos parâmetros antes de gravar.

Cada perfil declara um viés aditivo por parâmetro, dentro da faixa física do
pedal (ver PARAM_MAX no protocol.py). Toques de fase única pedem mais brilho e
mais Delay mix; humbuckers quentes pedem menos brilho e menos distorção.

Um preset não é destruído: `unadapt` devolve os valores originais para quem
quer ouvir ou editar a versão "crua".

Sobre as variantes HSS (humbucker + 2 single-coils): a guitarra é uma só, mas
a posição do seletor muda tudo. Neck, posição 2 e ponte soam como três
guitarras diferentes, então são três perfis. A posição 2 — fase única no meio
contra o humbucker da ponte — é o som de Stevie Ray Vaughan: o "quack" que todo
mundo tenta imitar sem saber o nome.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import protocol as P


@dataclass(frozen=True)
class GuitarProfile:
    key: str
    label: str
    family: str            # single-coil | humbucker | active | semi-hollow | híbrida | acústica
    character: str         # uma frase: como essa guitarra soa
    tips: str              # o que mexer quando o preset não encaixa
    position: str = ""     # só para as de seletor de posição (HSS e afins)
    voicing: dict = field(default_factory=dict)

    def adapt(self, params: dict) -> dict:
        """Devolve os parâmetros com o viés desta guitarra aplicado e travados na faixa."""
        out = dict(params)
        for name, delta in self.voicing.items():
            out[name] = P.clamp_param(name, out.get(name, 0) + delta)
        return out

    def preview(self, params: dict) -> list[tuple[str, int, int]]:
        """Mudanças que a adaptação faria: (parâmetro, antes, depois)."""
        out = self.adapt(params)
        return [(n, params[n], out[n]) for n in P.PARAM_NAMES if out[n] != params[n]]

    def unadapt(self, params: dict) -> dict:
        """Desfaz a adaptação, devolvendo o preset original travado na faixa."""
        out = dict(params)
        for name, delta in self.voicing.items():
            out[name] = P.clamp_param(name, out.get(name, 0) - delta)
        return out

    def one_line(self) -> str:
        base = f"{self.label} · {self.family}"
        return f"{base} — {self.position}" if self.position else base


# Viês pensados como "o que a guitarra faz com o sinal", não como compensação cega:
#   tone       -> fase única é mais brilhante, humbucker quente rola o agudo
#   cabinet    -> cabinets claros combinam com pickups de fase única
#   volume     -> fase única perde ~6 dB de saída; o pedal precisa trabalhar mais
#   mix        -> delay mais pro fundo, porque a guitarra já ocupa o topo
#   feedback   -> fase única com delay longo canta mais, logo mais retorno
#   type       -> humbuckers aguentam e pedem mais distorção antes de saturar
#   gain       -> ativos já comprimem o sinal; empurrar vira ruído
GUITARS = (
    # ------------------------------------------------- fase única (SSS) --------
    GuitarProfile(
        key="stratocaster",
        label="Stratocaster SSS",
        family="single-coil",
        character="Três pickups de fase única: brilho, dinâmica e o corpo no fundo do grave.",
        tips="Se o som ficar fino, baixe o gain em 1 e suba o tone em 1. Delay com chorus fica perfeito aqui.",
        voicing={"tone": +2, "cabinet": +1, "volume": +7, "mix": -5, "type": -1},
    ),
    GuitarProfile(
        key="tele",
        label="Telecaster",
        family="single-coil",
        character="Bridge T-model estalado: seco, metálico, percussão de dois dedos.",
        tips="Favorita de country e rock. O Delay precisa ser curto e de retorno baixo.",
        voicing={"tone": +3, "cabinet": +1, "volume": +6, "mix": -8, "feedback": -8, "time": -4},
    ),
    GuitarProfile(
        key="jazzmaster",
        label="Jazzmaster",
        family="single-coil",
        character="Offset, surf indestrutível: brightness com chorus, sem o poder de um humbucker.",
        tips="Soa áspero com overdrive. Use o tipo limpo (0) como base e deixe o chorus fazer o trabalho.",
        voicing={"tone": +3, "volume": +7, "type": -2, "modulation": +2},
    ),

    # ------------------------------------------------------------- HSS ---------
    # Três perfis da MESMA guitarra, um por posição do seletor. A 2 é o "quack".
    GuitarProfile(
        key="hss-bridge",
        label="Strat HSS",
        family="híbrida",
        character="Humbucker na ponte: grosso, quente e com sustain longo. Guitarra de rock por inteiro.",
        tips="É a posição mais quente da HSS. Agenta distorção sem ficar fina.",
        position="ponte (humbucker)",
        voicing={"tone": -1, "volume": +2, "gain": +1, "type": +1},
    ),
    GuitarProfile(
        key="hss-position2",
        label="Strat HSS",
        family="híbrida",
        character="Posição 2: fase única no meio contra o humbucker da ponte. O Famous Quack, o timbre mais imitado do mundo.",
        tips="Não é loud nem limpo: é percussivo. Delay curto, gain baixo, e deixe o timbre trabalhar.",
        position="posição 2 (o quack)",
        voicing={"tone": +2, "cabinet": +1, "volume": +5, "gain": -1, "type": -1, "mix": -4},
    ),
    GuitarProfile(
        key="hss-neck",
        label="Strat HSS",
        family="híbrida",
        character="Fase única no neck: o canto limpo mais redondo que existe, com corpo de violão.",
        tips="Perfeita para clean e jazz. Com overdrive ela fica fina — abaixe o gain em 2.",
        position="neck (fase única)",
        voicing={"tone": +1, "volume": +7, "gain": -1, "type": -2, "mix": -4, "reverb": +1},
    ),

    # -------------------------------------------------------- humbucker --------
    GuitarProfile(
        key="les-paul",
        label="Les Paul",
        family="humbucker",
        character="Humbucker de médios: sustain grosso, com o aperto clássico do rock.",
        tips="Guitarra de sustain: segurar o delay em mix alto e o reverb baixo deixa o timbre afogar.",
        voicing={"tone": -2, "volume": -5, "gain": +1, "feedback": +4},
    ),
    GuitarProfile(
        key="sg",
        label="Gibson SG",
        family="humbucker",
        character="Dois humbuckers sem aquela madeira: direto, definido, nasty.",
        tips="Não precisa de brilho. Em modo de lead, mantenha o tone baixo e o cabinet no meio.",
        voicing={"tone": -3, "gain": +1, "type": +1, "volume": -3},
    ),

    # ----------------------------------------------------------- ativos --------
    GuitarProfile(
        key="metal",
        label="Ibanez RG (EMG/DiMarzio)",
        family="active",
        character="Ativos com compressor interno: ataque infinito, sustain infinito, grave apertado.",
        tips="Empurrar o gain aqui só vira ruído. Baixe o tipo e deixe o EQ fazer o trabalho.",
        voicing={"tone": -1, "gain": -2, "type": -1, "volume": -2, "reverb": -3, "mix": -6},
    ),

    # ---------------------------------------------------- semi-acústica --------
    GuitarProfile(
        key="semihollow",
        label="ES-335 (semi-acústica)",
        family="semi-hollow",
        character="Centro oco: calor com uma microfonia nos agudos, o chorus fica luxuoso.",
        tips="Já tem presença de sobra — mexa só no gain e no Delay mix, não no tone.",
        voicing={"tone": -1, "volume": -3, "reverb": +2, "mix": +4, "modulation": +2},
    ),

    # --------------------------------------------------------- acústica --------
    GuitarProfile(
        key="acustica",
        label="Violão (steel-string)",
        family="acústica",
        character="Sem distorção, sem ataque: caixa acústica pura, com a dinâmica dos dedos.",
        tips="O pedal vira delay e reverb. O tipo de pré-amp tem que ficar em 0 ou 1.",
        voicing={"type": -2, "gain": -2, "tone": +1, "volume": -3, "mix": +6, "reverb": +3, "modulation": -2},
    ),
)

DEFAULT_GUITAR = "les-paul"

_BY_KEY = {g.key: g for g in GUITARS}


def get(key: str) -> GuitarProfile:
    return _BY_KEY.get(key, _BY_KEY[DEFAULT_GUITAR])


def keys() -> list[str]:
    return [g.key for g in GUITARS]


def family_of(key: str) -> str:
    return get(key).family
