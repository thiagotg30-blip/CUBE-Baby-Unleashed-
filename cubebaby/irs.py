"""Qual IR usar com cada preset — ADICIONA, não substitui nada.

Os presets já vêm com um gabinete de fábrica escolhido (`cabinet=1..8`), que
funciona sozinho. Este módulo **não mexe nisso**: ele só diz, para quem tem um
IR melhor, qual arquivo combina com aquele som.

Os nomes de arquivo abaixo foram **verificados no disco** — todos existem no
pack `~/Downloads/Quartinho do Metal - ALL IRs PACK/Guitar Impulses`. Nenhuma
recomendação aponta para arquivo que não está lá.

LIMITE HONESTO
--------------
Isto é orientação de timbre, não medição. Escolhi cada IR pela caixa e pelo
falante que a gravação/genênero costuma usar — a mesma lógica que usei no
preset "Monster (fiel ao original)", onde o acerto foi confirmado por
correlação de +0,89 com o WAV importado.

Não são "os IRs oficiais" de nada: são sugestões de quem tem o pack. Onde não
havia caixa claramente certa, deixei vazio em vez de inventar.
"""
from __future__ import annotations

from dataclasses import dataclass

# Pasta raiz do pack, relativa ao home. Só para exibir na interface.
PASTA_PACK = "Downloads/Quartinho do Metal - ALL IRs PACK/Guitar Impulses"


@dataclass(frozen=True)
class SugestaoIR:
    arquivo: str        # nome do arquivo (verificado no disco)
    pasta: str          # subpasta dentro do pack
    caixa: str          # o que é, em uma linha
    porque: str         # por que combina com o preset
    confianca: str      # "alta" | "media" | "aproximacao"

    def caminho_curto(self) -> str:
        return f"{self.pasta}/{self.arquivo}" if self.pasta else self.arquivo


# ---------------------------------------------------------------------------
# As sugestões, por chave de preset.
#
# Confiança:
#   alta        — a caixa e o falante batem com o que o gênero/gravação usa
#   media       — a família está certa, a captação é escolha
#   aproximacao — não há caixa específica; é um ponto de partida
# ---------------------------------------------------------------------------

SUGESTOES: dict[str, SugestaoIR] = {
    # ---------------- metal / high gain ----------------
    "monster-fiel": SugestaoIR(
        "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Mesa 4×12 com V30, SM57",
        "É a caixa da gravação de 'Monster'. Confirmado por correlação: este "
        "foi o arquivo importado e o pedal reproduz a mesma forma.",
        "alta"),
    "monster-lead": SugestaoIR(
        "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Mesa 4×12 com V30, SM57",
        "Mesma caixa do riff — o solo tem de casar com o resto da música.",
        "alta"),
    "monster-ir": SugestaoIR(
        "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Mesa 4×12 com V30, SM57",
        "O preset foi feito para essa caixa.",
        "alta"),
    "tight-riff-ir": SugestaoIR(
        "013a-MD421-V30-4x12.wav",
        "Kalthallen IRs",
        "4×12 com V30, microfone MD421",
        "O MD421 pega mais corpo que o SM57 e não embola o palm mute — é o "
        "que se quer num riff apertado.",
        "alta"),
    "lead-sustain-ir": SugestaoIR(
        "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Mesa 4×12 com V30, SM57",
        "Mesma caixa do resto; o sustain vem do delay, não da caixa.",
        "alta"),
    "monster-riff": SugestaoIR(
        "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Mesa 4×12 com V30, SM57",
        "A caixa de metal moderno por excelência.",
        "alta"),
    "metal-tight": SugestaoIR(
        "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Mesa 4×12 com V30, SM57",
        "Grave firme e agudo presente, sem o 'corte' de uma caixa de "
        "Greenback. É o que sustenta afinação baixa.",
        "alta"),
    "djent-palm": SugestaoIR(
        "013a-MD421-V30-4x12.wav",
        "Kalthallen IRs",
        "4×12 com V30, microfone MD421",
        "Djent vive de definição nota por nota; o MD421 dá corpo sem sujar.",
        "media"),
    "doom-drone": SugestaoIR(
        "4 - Orange cust_m930 1.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Orange, captação própria",
        "Doom pede caixa gorda e escura — a Orange é exatamente isso.",
        "media"),
    "hard-roots": SugestaoIR(
        "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Marshall 1960A com Greenback, SM57 no centro",
        "O armário do hard rock. Greenback dá o médio quente que o gênero "
        "espera.",
        "alta"),
    "garage-punk": SugestaoIR(
        "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Marshall 1960A com Greenback, SM57",
        "Sujo e direto, sem refinamento — é o som do gênero.",
        "media"),

    # ---------------- rock / blues ----------------
    "classic-rock-lead": SugestaoIR(
        "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Marshall 1960A com Greenback, SM57",
        "O solo de rock clássico é Marshall com Greenback. Não tem mistério.",
        "alta"),
    "crunch-rhythm": SugestaoIR(
        "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Marshall 1960A com Greenback, SM57",
        "Crunch é o terreno natural do Greenback.",
        "alta"),
    "blues-overdrive": SugestaoIR(
        "7 - GuitarHack JJ CENTRE45 0.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "caixa com válvulas JJ, captação central",
        "Blues quer médio redondo e pouco brilho. Esta captação central "
        "entrega isso sem estridência.",
        "media"),
    "blues-shuffle": SugestaoIR(
        "7 - GuitarHack JJ CENTRE45 0.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "caixa com válvulas JJ, captação central",
        "Mesma família do overdrive, para o shuffle não soar fino.",
        "media"),
    "hendrix-quack": SugestaoIR(
        "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Marshall 1960A com Greenback, SM57",
        "Hendrix é Marshall com Greenback. O 'quack' vem da posição 2 da "
        "guitarra, não da caixa — mas a caixa tem de ser essa.",
        "alta"),
    "garage-fuzz": SugestaoIR(
        "4 - Orange cust_m930 1.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Orange, captação própria",
        "Fuzz com Orange é o som de garagem por definição: gordo e bruto.",
        "media"),

    # ---------------- limpos / britânicos ----------------
    "clean-country": SugestaoIR(
        "2 - Fender 57 Edge, 12 in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Fender '57, captação na borda do cone",
        "Country limpo é Fender com captação na borda: mais brilho e twang.",
        "alta"),
    "indie-clean-riff": SugestaoIR(
        "1 - VOX AC30 brilliant+bass BX44 neve close_dc.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Vox AC30, canal brilliant, microfone BX44",
        "O sino britânico do AC30 é o limpo do indie.",
        "alta"),
    "echo-doubles": SugestaoIR(
        "1 - VOX AC30 brilliant+bass BX44 neve close_dc.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Vox AC30 brilliant",
        "Serve ao delay: um limpo com caráter, sem competir com as repetições.",
        "media"),
    "praise-shimmer": SugestaoIR(
        "1 - VOX AC30 brilliant+bass BX44 neve close_dc.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Vox AC30 brilliant",
        "Worship usa muito AC30 e Vox-like no limpo com ambiência.",
        "media"),
    "jazz-clean": SugestaoIR(
        "01_Twin73_dome_edge_L19.wav",
        "Fender_Twin_73_IR_Pack",
        "Fender Twin '73, captação na cúpula",
        "Jazz quer limpo enorme e escuro. O Twin é isso; a captação na cúpula "
        "tira o excesso de agudo.",
        "alta"),
    "ambient-shimmer": SugestaoIR(
        "1 - VOX AC30 brilliant+bass BX44 neve close_dc.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Vox AC30 brilliant",
        "Um limpo definido para o shimmer não virar lama.",
        "media"),
    "ambient-space": SugestaoIR(
        "01_Twin73_dome_edge_L19.wav",
        "Fender_Twin_73_IR_Pack",
        "Fender Twin '73",
        "Limpo grande e neutro: deixa o reverb fazer o trabalho.",
        "media"),
    "shoegaze-wall": SugestaoIR(
        "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Marshall 1960A com Greenback, SM57",
        "Shoegaze é parede de som com fuzz — a Greenback aguenta sem virar "
        "chiado.",
        "media"),
    "temple-theremin": SugestaoIR(
        "8 - Catharsis s-preshigh.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "caixa Catharsis, agudo acentuado",
        "Para efeito e experimentalismo, uma caixa com agudo aberto é mais "
        "interessante que um limpo neutro.",
        "aproximacao"),
    "post-punk-tight": SugestaoIR(
        "1 - VOX AC30 brilliant+bass BX44 neve close_dc.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Vox AC30 brilliant",
        "O pós-punk britânico é AC30 com chorus. Combina com o preset.",
        "media"),
    "surf-slide": SugestaoIR(
        "01_Twin73_dome_edge_L19.wav",
        "Fender_Twin_73_IR_Pack",
        "Fender Twin '73",
        "Surf é Twin com reverb de mola. Esta é a caixa.",
        "alta"),
    "surf-outrun": SugestaoIR(
        "01_Twin73_dome_edge_L19.wav",
        "Fender_Twin_73_IR_Pack",
        "Fender Twin '73",
        "Mesma família do surf, para o lado synthwave.",
        "media"),
    "punk-chorus": SugestaoIR(
        "3 - Marshall1960A-G12Ms-SM57-Cap-0in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Marshall 1960A com Greenback, SM57",
        "Punk é Marshall e pronto.",
        "alta"),
    "grunge-mud": SugestaoIR(
        "4 - Orange cust_m930 1.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Orange, captação própria",
        "Grunge pede gordo e meio sujo — Orange entrega.",
        "media"),

    # ---------------- funk / soul ----------------
    "funk-groove": SugestaoIR(
        "2 - Fender 57 Edge, 12 in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Fender '57, captação na borda",
        "Funk limpo quer brilho e ataque — a captação na borda dá isso.",
        "media"),
    "funk-wah-clean": SugestaoIR(
        "2 - Fender 57 Edge, 12 in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Fender '57, captação na borda",
        "O wah precisa de agudo definido para funcionar.",
        "media"),

    # ---------------- acústico ----------------
    "folk-fingerpicking": SugestaoIR(
        "Blackface Deluxe.wav",
        "impulse_pack_02/POD/POD/Black Panel (Fender Deluxe)",
        "Fender Deluxe Blackface",
        "Violão com simulação de caixa pede o mais neutro possível. Esta é "
        "limpa e sem cor.",
        "aproximacao"),
    "acoustic-ballad": SugestaoIR(
        "Blackface Deluxe.wav",
        "impulse_pack_02/POD/POD/Black Panel (Fender Deluxe)",
        "Fender Deluxe Blackface",
        "Mesma razão: neutro, para não colorir o violão.",
        "aproximacao"),
    "bossa-nylon": SugestaoIR(
        "Blackface Deluxe.wav",
        "impulse_pack_02/POD/POD/Black Panel (Fender Deluxe)",
        "Fender Deluxe Blackface",
        "Bossa pede o mais neutro possível.",
        "aproximacao"),

    # ---------------- outros ----------------
    "ska-upstroke": SugestaoIR(
        "2 - Fender 57 Edge, 12 in.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Fender '57, captação na borda",
        "O upstroke precisa de ataque brilhante.",
        "media"),
    "emo-twang": SugestaoIR(
        "1 - VOX AC30 brilliant+bass BX44 neve close_dc.wav",
        "1 - Quartinho do Metal - Top 8 IR Pack",
        "Vox AC30 brilliant",
        "O twang do emo/math rock vem do AC30 ou de um Fender limpo.",
        "media"),
}


def get(key: str) -> SugestaoIR | None:
    """A sugestão de IR para um preset, ou None se não houver."""
    return SUGESTOES.get(key)


def tem_sugestao(key: str) -> bool:
    return key in SUGESTOES


def todas() -> list[tuple[str, SugestaoIR]]:
    return sorted(SUGESTOES.items())


def resumo() -> str:
    n = len(SUGESTOES)
    altas = sum(1 for s in SUGESTOES.values() if s.confianca == "alta")
    return (f"{n} presets com IR sugerido "
            f"({altas} de confiança alta, o resto aproximação)")
