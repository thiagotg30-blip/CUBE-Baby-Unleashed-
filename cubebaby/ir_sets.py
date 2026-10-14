"""Sets de 8 IRs — um conjunto por estilo, pronto para encher os 8 bancos.

POR QUE ISTO É POSSÍVEL
-----------------------
O pedal tem exatamente **8 bancos de IR** (descoberto no hardware: 8 blocos de
4096 bytes em `memory=0 @0x69000`, cada um um banco independente). E agora o
CUBE Baby Unleashed **grava** nesses bancos sem o CubeSuite.

Ou seja: um "set" é um estilo musical ocupando os 8 bancos de uma vez. Você
escolhe o estilo, o programa envia os 8, e o pedal fica com um arsenal daquele
som.

O QUE ISTO É — E O QUE NÃO É
----------------------------
É uma **curadoria**: para cada estilo, escolhi 8 caixas/falantes que aquele
gênero realmente usa, com variedade de captação (SM57 no centro, MD421,
Ribbon, borda do cone) para o usuário ter opções e não 8 variações da mesma
coisa.

Não é medição nem "o IR oficial" de nada. Os arquivos vêm do pack do usuário,
todos verificados no disco. Nenhum set aponta para arquivo inexistente.

CUIDADO: aplicar um set SOBRESCREVE os 8 bancos. Faça backup antes — o
programa faz automaticamente, mas o backup é do estado atual, não do de
fábrica.
"""
from __future__ import annotations

from dataclasses import dataclass

PASTA_PACK = "Downloads/Quartinho do Metal - ALL IRs PACK/Guitar Impulses"


@dataclass(frozen=True)
class IRSlot:
    pasta: str      # subpasta dentro do pack
    arquivo: str
    caixa: str      # o que é
    uso: str        # para que serve dentro do set

    def caminho(self) -> str:
        return f"{self.pasta}/{self.arquivo}"


@dataclass(frozen=True)
class SetIR:
    key: str
    nome: str
    generos: tuple
    descricao: str
    slots: tuple[IRSlot, ...]     # sempre 8, um por banco

    def __post_init__(self):
        if len(self.slots) != 8:
            raise ValueError(
                f"o set '{self.key}' tem {len(self.slots)} IRs; "
                f"o pedal tem 8 bancos, então precisa de exatamente 8."
            )


# ---------------------------------------------------------------------------
# OS SETS
# ---------------------------------------------------------------------------

SETS: tuple[SetIR, ...] = (
    SetIR(
        key="metal",
        nome="Metal / High Gain",
        generos=("metal", "djent", "hard rock", "thrash", "death metal"),
        descricao="Caixas de high gain com captação apertada. Do palm mute "
                  "seco ao lead com sustain.",
        slots=(
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
                   "Mesa 4×12 com V30, SM57",
                   "Banco 1 — o padrão do metal moderno. Comece por aqui."),
            IRSlot("ZETA_IR_PACK", "Mesa 4x12 SPKR 1 position 1.wav",
                   "Mesa 4×12, posição 1",
                   "Banco 2 — a mesma Mesa com outra captação; mais corpo."),
            IRSlot("ZETA_IR_PACK", "Diezel 1 4x12 SPKR 1 position 1.wav",
                   "Diezel 4×12",
                   "Banco 3 — hi-fi e apertada, para metal moderno/prog."),
            IRSlot("Kalthallen IRs", "005a-SM57-V30-4x12.wav",
                   "4×12 com V30, SM57",
                   "Banco 4 — V30 clássico; menos específica de marca."),
            IRSlot("Kalthallen IRs", "013a-MD421-V30-4x12.wav",
                   "4×12 com V30, MD421",
                   "Banco 5 — MD421 dá corpo sem embolar; ideal para riff."),
            IRSlot("BestpluginsIrPack2", "EVH 5150 III.wav",
                   "EVH 5150 III",
                   "Banco 6 — o som de metal dos anos 90/2000."),
            IRSlot("Emissary", "RKH 4x12 V30 SHR SM57 Center.wav",
                   "4×12 com V30, SM57 no centro",
                   "Banco 7 — ataque direto; bom para djent."),
            IRSlot("BestpluginsIrPack2", "Engl Retro Tube.wav",
                   "ENGL",
                   "Banco 8 — agressiva e definida; alternativa britânica."),
        ),
    ),

    SetIR(
        key="rock",
        nome="Rock / Hard Rock",
        generos=("rock", "classic rock", "hard rock", "punk", "grunge"),
        descricao="Do crunch de Marshall ao gordo da Orange. Caixas que "
                  "sustentam riff sem virar metal.",
        slots=(
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
                   "Marshall 1960A com Greenback, SM57",
                   "Banco 1 — O armário do rock. Greenback dá médio quente."),
            IRSlot("Kalthallen IRs", "009a-SM57-G12T75-4x12.wav",
                   "4×12 com G12T-75, SM57",
                   "Banco 2 — T75: mais agudo e corte que o Greenback."),
            IRSlot("Kalthallen IRs", "009b-SM57-G12T75-4x12.wav",
                   "4×12 com G12T-75, outra posição",
                   "Banco 3 — mesma caixa, captação diferente; compare."),
            IRSlot("Fearcomplexmusic Impulses", "Marshall Mode Four Cab Impulse.wav",
                   "Marshall Mode Four",
                   "Banco 4 — Marshall mais moderno e apertado."),
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "5 - Bogner 4x12 SPKR 1 position 1.wav",
                   "Bogner 4×12",
                   "Banco 5 — high gain com som grande; o hard rock pesado."),
            IRSlot("ZETA_IR_PACK", "Bogner 1 2x12 SPKR 1 position 1.wav",
                   "Bogner 2×12",
                   "Banco 6 — a mesma família em 2×12: mais focada."),
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "4 - Orange cust_m930 1.wav",
                   "Orange, captação própria",
                   "Banco 7 — gorda e escura. Stoner, doom, garage."),
            IRSlot("Fearcomplexmusic Impulses", "orange2x12.wav",
                   "Orange 2×12",
                   "Banco 8 — Orange em caixa menor: médio mais presente."),
        ),
    ),

    SetIR(
        key="blues",
        nome="Blues / Soul / Country",
        generos=("blues", "soul", "country", "rockabilly", "jazz"),
        descricao="Médio redondo e pouco brilho. Caixas que respondem à "
                  "dinâmica da mão em vez de esconder atrás de ganho.",
        slots=(
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "7 - GuitarHack JJ CENTRE45 0.wav",
                   "caixa com válvulas JJ, captação central",
                   "Banco 1 — o blues direto: médio redondo, sem estridência."),
            IRSlot("Guitarhack Impulses/JJ Powertube Impulses",
                   "GuitarHack JJ BBAE 0.wav",
                   "caixa JJ, captação alternativa",
                   "Banco 2 — a mesma família com mais abertura."),
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "8 - Catharsis s-preshigh.wav",
                   "Catharsis, agudo acentuado",
                   "Banco 3 — para slide e country: ataque definido."),
            IRSlot("Catharsis Fredman Impulses", "1on-pres5.wav",
                   "Catharsis Fredman",
                   "Banco 4 — outra Catharsis; compare o agudo."),
            IRSlot("BestpluginsIrPack2", "Mesa Boogie Mark V.wav",
                   "Mesa Mark V",
                   "Banco 5 — limpo com corpo; serve ao soul e ao jazz."),
            IRSlot("Kalthallen IRs", "005b-SM57-V30-4x12.wav",
                   "4×12 com V30, SM57",
                   "Banco 6 — para o blues rock mais pesado."),
            IRSlot("Kalthallen IRs", "013b-MD421-V30-4x12.wav",
                   "4×12 com V30, MD421",
                   "Banco 7 — corpo sem brilho: bom para slide."),
            IRSlot("ZETA_IR_PACK", "Mesa 4x12 SPKR 1 position 2.wav",
                   "Mesa 4×12, posição 2",
                   "Banco 8 — a Mesa com captação mais escura."),
        ),
    ),

    SetIR(
        key="limpos",
        nome="Limpos / Britânicos / Violão",
        generos=("pop", "indie", "ambient", "worship", "folk", "surf", "jazz"),
        descricao="Vox, Fender e caixas neutras. Para quem toca limpo, com "
                  "efeito, ou violão.",
        slots=(
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "1 - VOX AC30 brilliant+bass BX44 neve close_dc.wav",
                   "Vox AC30 brilliant, microfone BX44",
                   "Banco 1 — o sino britânico. O limpo do indie e do pop."),
            IRSlot("AC30 brilliant SNB", "AC30 brilliant bx44 neve close_dc.wav",
                   "Vox AC30 brilliant",
                   "Banco 2 — mesmo AC30, outra tomada."),
            IRSlot("AC30 normal SNB", "AC30 normal sm57 neve close_dc.wav",
                   "Vox AC30 canal normal, SM57",
                   "Banco 3 — AC30 mais neutro; aceita pedal bem."),
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "2 - Fender 57 Edge, 12 in.wav",
                   "Fender '57, captação na borda",
                   "Banco 4 — twang de country e surf."),
            IRSlot("Fender_Twin_73_IR_Pack", "01_Twin73_dome_edge_L19.wav",
                   "Fender Twin '73",
                   "Banco 5 — limpo enorme; jazz, surf, ambient."),
            IRSlot("impulse_pack_02/Jensen 10 inch/Jensen 10 inch",
                   "Jensen 10 4050 onax 48s.wav",
                   "Jensen 10 polegadas",
                   "Banco 6 — caixa pequena com caráter; folk e indie."),
            IRSlot("impulse_pack_02/POD/POD/Black Panel (Fender Deluxe)",
                   "Tweed Deluxe.wav",
                   "Fender Tweed Deluxe",
                   "Banco 7 — média quente; gravação intimista, folk."),
            IRSlot("impulse_pack_01/Fender Bassman/Fender Bassman",
                   "Fender Bassman.wav",
                   "Fender Bassman '59",
                   "Banco 8 — neutra e encorpada. A mais indicada para violão."),
        ),
    ),

    SetIR(
        key="indie",
        nome="Indie / Psych (Mac DeMarco, Tame Impala)",
        generos=("indie", "indie rock", "psych rock", "dream pop", "lo-fi",
                 "bedroom pop", "neo-psych"),
        descricao="O som do indie e do psych: Fender pequeno limpo para o "
                  "bedroom pop (Mac DeMarco) e Vox AC30 com agudo aberto para "
                  "a psicodelia (Tame Impala). Pouco ganho, muita captação.",
        slots=(
            IRSlot("impulse_pack_01/Fender Princeton/Fender Princeton",
                   "Princeton floor_00.wav",
                   "Fender Princeton no chão",
                   "Banco 1 — o limpo pequeno do bedroom pop. Mac DeMarco é "
                   "isso: Fender baixo, chorus, nada de ganho."),
            IRSlot("impulse_pack_01/Fender Princeton/Fender Princeton",
                   "Princeton up_00.wav",
                   "Fender Princeton, microfone mais alto",
                   "Banco 2 — mesma caixa, mais brilho. Para riff limpo."),
            IRSlot("AC30 brilliant SNB",
                   "AC30 brilliant bx44 neve close_dc.wav",
                   "Vox AC30 brilliant, microfone BX44",
                   "Banco 3 — o AC30 é a espinha do psych. Agudo aberto."),
            IRSlot("AC30 brilliant SNB",
                   "AC30 brilliant+bass bx44 stalevel close_dc.wav",
                   "Vox AC30 brilliant+bass, nível estável",
                   "Banco 4 — com mais grave; segura o fuzz sem ficar fino."),
            IRSlot("AC30 normal SNB",
                   "AC30 normal sm57 neve close_dc.wav",
                   "Vox AC30 canal normal, SM57",
                   "Banco 5 — AC30 mais neutro; aceita fuzz e delay bem."),
            IRSlot("impulse_pack_02/POD/POD/Black Panel (Fender Deluxe)",
                   "Tweed Deluxe.wav",
                   "Fender Tweed Deluxe",
                   "Banco 6 — média quente e lo-fi; o lado 'gravado em casa'."),
            IRSlot("impulse_pack_01/Fender 81 Super Champ/Fender 81 Super Champ",
                   "Fender SuperChamp SM57.wav",
                   "Fender Super Champ '81, SM57",
                   "Banco 7 — caixa pequena com caráter; indie cru."),
            IRSlot("impulse_pack_02/Jensen 10 inch/Jensen 10 inch",
                   "Jensen 10 4050 onax 48s.wav",
                   "Jensen 10 polegadas",
                   "Banco 8 — 10 polegadas dá aquele médio estreito dos "
                   "discos de indie gravados em quarto."),
        ),
    ),

    SetIR(
        key="numetal",
        nome="Nu Metal / Alt Metal (Linkin Park, Skillet)",
        generos=("nu metal", "alternative metal", "metal", "hard rock",
                 "rap metal", "post-grunge"),
        descricao="Riff apertado, palm mute e ganho controlado. Mesa "
                  "Rectifier e caixas V30 com captação fechada — o som do "
                  "Linkin Park e do Skillet.",
        slots=(
            IRSlot("1 - Quartinho do Metal - Top 8 IR Pack",
                   "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
                   "Mesa 4×12 com V30, SM57",
                   "Banco 1 — o Rectifier com V30. É a caixa do 'Monster' do "
                   "Skillet, e o padrão do gênero."),
            IRSlot("ZETA_IR_PACK", "Mesa 4x12 SPKR 1 position 1.wav",
                   "Mesa 4×12, posição 1",
                   "Banco 2 — outra tomada da Mesa; mais corpo."),
            IRSlot("BestpluginsIrPack2", "Mesa Boogie Mark V.wav",
                   "Mesa Mark V",
                   "Banco 3 — o Mark é mais apertado que o Rectifier; bom "
                   "para o riff do Linkin Park."),
            IRSlot("Kalthallen IRs", "005a-SM57-V30-4x12.wav",
                   "4×12 com V30, SM57",
                   "Banco 4 — V30 clássico, sem marca específica."),
            IRSlot("Kalthallen IRs", "013a-MD421-V30-4x12.wav",
                   "4×12 com V30, MD421",
                   "Banco 5 — corpo sem embolar: o palm mute fica definido."),
            IRSlot("Emissary", "RKH 4x12 V30 SHR SM57 Center.wav",
                   "4×12 com V30, SM57 no centro",
                   "Banco 6 — ataque direto; o mais 'seco' do set."),
            IRSlot("BestpluginsIrPack2", "EVH 5150 III.wav",
                   "EVH 5150 III",
                   "Banco 7 — o 5150 do metal dos anos 2000."),
            IRSlot("ZETA_IR_PACK", "Diezel 1 4x12 SPKR 1 position 1.wav",
                   "Diezel 4×12",
                   "Banco 8 — hi-fi e apertada; alternativa moderna."),
        ),
    ),
)

POR_CHAVE = {s.key: s for s in SETS}


def get(key: str) -> SetIR | None:
    return POR_CHAVE.get(key)


def todos() -> tuple[SetIR, ...]:
    return SETS


def arquivo_do_slot(st: SetIR, banco: int) -> str:
    """Caminho relativo do IR do banco (1..8)."""
    if not 1 <= banco <= 8:
        raise ValueError(f"banco deve ser 1..8 (veio {banco})")
    return st.slots[banco - 1].caminho()


def resumo() -> str:
    return (f"{len(SETS)} sets de 8 IRs "
            f"({', '.join(s.nome for s in SETS)})")
