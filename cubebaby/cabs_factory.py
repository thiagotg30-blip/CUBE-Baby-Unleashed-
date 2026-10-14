"""Os 32 nomes de gabinete que o CubeSuite oficial traz no arquivo `bin/BOR.bin`.

PROCEDÊNCIA — leia antes de usar
-------------------------------
Estes nomes foram EXTRAÍDOS do arquivo `bin/BOR.bin` que acompanha o CubeSuite
oficial (CUBE Baby), por leitura direta dos bytes. O arquivo tem 262.144 bytes
= 32 blocos de 8.192 bytes. Cada bloco começa com um nome ASCII terminado em
NUL, seguido da marca `patchCAB`, e depois ~4.075 amostras int16 (84,9 ms a
48 kHz) que decaem como uma resposta de impulso.

  offset      nome                    bytes do áudio
  0x00000     TweedDeluxe             42
  0x02000      ShowmanD130s 1         42
  0x04000     Roland JC120            42
  ...

O QUE ISTO **NÃO** PROVA
------------------------
1. **A ordem do arquivo não é a ordem do botão IR CAB do pedal.** O pedal tem
   8 posições (1..8); aqui há 32 entradas. "MesaRectifierV30" é a entrada de
   índice 24 — não a 8. Não há, neste arquivo, nenhum campo que ligue uma
   entrada a uma posição do pedal. Quem afirmar "gabinete 8 = MesaRectifierV30"
   está chutando.

2. **Não são as IRs da ROM do pedal.** São a biblioteca que o *programa* usa.
   A ROM do pedal é outra região, acessada por SysEx.

3. **Não substituem um IR medido.** São respostas curtas (84,9 ms) de um
   catálogo de fábrica, não capturas com microfone.

Para que serve então: dá ao usuário **nomes reais** para procurar, comparar de
ouvido e reconhecer. E permite dizer, com base em evidência, qual caixa de
fábrica corresponde à gravação que ele quer copiar — no caso de "Monster", a
"MesaRectifierV30", que é a Mesa Rectifier 4×12 com V30 usada no disco.
"""
from __future__ import annotations

from dataclasses import dataclass

# Procedência do arquivo analisado.
FONTE_ARQUIVO = "CubeSuite/bin/BOR.bin"
FONTE_TAMANHO = 262144
FONTE_BLOCOS = 32
FONTE_BLOCO_BYTES = 8192
FONTE_MARCA = "patchCAB"
FONTE_AUDIO_OFFSET = 42          # 28 quando o nome tem 15+ caracteres
FONTE_AUDIO_AMOSTRAS = 4075      # 84,9 ms a 48 kHz
FONTE_AUDIO_FORMATO = "int16 LE mono, 48 kHz"


@dataclass(frozen=True)
class CabFabrica:
    idx: int          # posição no arquivo BOR.bin (0..31) — NÃO é a posição do pedal
    nome: str         # como está escrito no arquivo
    spec: str         # deduzido do nome: 4x12, 1x12, 2x12, baixo...
    familia: str      # 'guitarra' ou 'baixo'
    nota: str         # o que é, em linguagem de quem está começando


# A ordem é a do arquivo, lida byte a byte. Não reordene.
FABRICA = (
    CabFabrica(0, "TweedDeluxe", "1x12", "guitarra",
               "Fender Tweed Deluxe: caixa pequena e macia, o som limpo e quente dos anos 50."),
    CabFabrica(1, "ShowmanD130s", "1x15", "guitarra",
               "Fender Showman com falante JBL D130: limpo enorme, muito grave."),
    CabFabrica(2, "Roland JC120", "2x12", "guitarra",
               "O chorus mais famoso do mundo. Limpo cristalino, sem sujeira."),
    CabFabrica(3, "Marshall 1960B 1", "4x12", "guitarra",
               "Marshall 1960B: o armário fechado do rock. Aqui com um falante claro."),
    CabFabrica(4, "Marshall basket1", "4x12", "guitarra",
               "Marshall com falantes 'basket weave' (Greenback): médio quente."),
    CabFabrica(5, "Marshall 1960B 2", "4x12", "guitarra",
               "Mesma caixa, outra captação. Ouça a diferença de microfone."),
    CabFabrica(6, "Marshall 1960B 3", "4x12", "guitarra",
               "Terceira variação da 1960B. É a referência do hard rock."),
    CabFabrica(7, "Marshall basket2", "4x12", "guitarra",
               "Outra tomada da basket weave. Compare com a de índice 4."),
    CabFabrica(8, "BOGNER Uberkab", "4x12", "guitarra",
               "Bogner Uberkab: caixa de high gain, som enorme e apertado."),
    CabFabrica(9, "ENGLProV30s", "4x12", "guitarra",
               "ENGL Pro com Vintage 30: agressiva, muito definida no metal."),
    CabFabrica(10, "Peavey 5150", "4x12", "guitarra",
               "A caixa do 5150: o som de metal dos anos 90."),
    CabFabrica(11, "TwinD120s", "2x12", "guitarra",
               "Fender Twin com falantes JBL D120: limpo alto e brilhante."),
    CabFabrica(12, "TwinJensenC12N", "2x12", "guitarra",
               "Twin com Jensen C12N: mais macio que a de D120."),
    CabFabrica(13, "VoxAC30 1", "2x12", "guitarra",
               "Vox AC30 com Blue: o sino britânico dos Beatles."),
    CabFabrica(14, "VoxAC30 2", "2x12", "guitarra",
               "Outra tomada do AC30. Um pouco mais aberta."),
    CabFabrica(15, "TwinD120s 2", "2x12", "guitarra",
               "Segunda variação do Twin D120."),
    CabFabrica(16, "ShowmanD130s 2", "1x15", "guitarra",
               "Segunda variação do Showman D130."),
    CabFabrica(17, "Orange4X12", "4x12", "guitarra",
               "Orange 4x12: gordo, escuro e rosnado. O som do stoner."),
    CabFabrica(18, "Diezel V30", "4x12", "guitarra",
               "Diezel com V30: hi-fi e apertada, para metal moderno."),
    CabFabrica(19, "Mesa Boogie", "4x12", "guitarra",
               "Mesa Boogie: corpo grande com agudo controlado."),
    CabFabrica(20, "Electrovoice", "1x12", "guitarra",
               "Electro-Voice EVM: limpo altíssimo, quase sem compressão."),
    CabFabrica(21, "Rimental", "4x12", "guitarra",
               "Captação alternativa de 4x12. Nome de catálogo, sem marca pública."),
    CabFabrica(22, "Supro", "1x10", "guitarra",
               "Supro pequena: o som rasgado do rock de garagem dos 60."),
    CabFabrica(23, "Matchless ES212", "2x12", "guitarra",
               "Matchless: classe A com muito corpo. O som do rock alternativo."),
    CabFabrica(24, "MesaRectifierV30", "4x12", "guitarra",
               "Mesa Rectifier com Vintage 30 — a caixa usada na gravação de "
               "'Monster' do Skillet. É a que você quer para esse timbre."),
    CabFabrica(25, "Jensen 4050 BASS", "1x15", "baixo",
               "Caixa de baixo com falante Jensen."),
    CabFabrica(26, "Studio 441 BASS", "1x15", "baixo",
               "Caixa de baixo de estúdio."),
    CabFabrica(27, "AMPEG DIS BASS", "1x15", "baixo",
               "Ampeg: o baixo mais gravado da história do rock."),
    CabFabrica(28, "Aguilar  BASS", "1x12", "baixo",
               "Aguilar: baixo moderno, definido e apertado."),
    CabFabrica(29, "TP5 421 BASS", "4x10", "baixo",
               "Caixa de baixo 4x10 com microfone 421."),
    CabFabrica(30, "EDEN DIS BASS", "1x15", "baixo",
               "Eden: baixo limpo e encorpado."),
    CabFabrica(31, "Work 4050 2 BASS", "1x15", "baixo",
               "Caixa de baixo com falante de 15 polegadas."),
)

GUITARRA = tuple(c for c in FABRICA if c.familia == "guitarra")
BAIXO = tuple(c for c in FABRICA if c.familia == "baixo")

POR_NOME = {c.nome.lower(): c for c in FABRICA}


def get(idx: int) -> CabFabrica:
    return FABRICA[max(0, min(len(FABRICA) - 1, int(idx)))]


def procurar(termo: str) -> list[CabFabrica]:
    """Busca por nome ou nota. 'mesa' acha Mesa Boogie e MesaRectifierV30."""
    t = termo.strip().lower()
    if not t:
        return list(FABRICA)
    return [c for c in FABRICA if t in c.nome.lower() or t in c.nota.lower()
            or t in c.spec.lower()]


# A gravação de referência e a caixa de fábrica que corresponde a ela.
MONSTER_CAB = POR_NOME["mesarectifierv30"]

AVISO = (
    "Estes 32 nomes vêm do arquivo bin/BOR.bin do CubeSuite oficial e estão na "
    "ORDEM DO ARQUIVO. O pedal tem 8 posições no botão IR CAB; este arquivo tem "
    "32 entradas e não traz nenhum campo ligando uma à outra. Por isso o número "
    "aqui NÃO é a posição do pedal — é só o índice no arquivo."
)
