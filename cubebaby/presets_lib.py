"""Biblioteca de presets curados: assinatura sonora, gênero e guitarra de referência.

Cada preset é um ponto de partida auditado — nenhum número aqui é aleatório.
Os valores vivem dentro da faixa física do CUBE Baby (PARAM_MAX no protocol.py)
e `PRESETS` é validado no import: se alguém digitar type=99, o módulo levanta
na hora em vez de gravar lixo no pedal.

O campo `signature` é a descrição de como o preset soa, e `genres` é para que
tipo de música ele serve. `guitar` é o instrumento em que ele foi pensado — o
perfil só ajusta o *voicing* (ver guitars.py), o preset em si continua o mesmo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import protocol as P
from .guitars import DEFAULT_GUITAR, GUITARS, get as guitar_of


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    genres: tuple
    guitar: str
    signature: str
    params: dict = field(default_factory=dict)
    notes: str = ""
    # Afinacao que o preset espera (chave do tuner.AFINACOES). Vazio = padrao.
    # Sem isto o usuario carrega um preset de Drop C com a guitarra em Mi e
    # acha que o preset e' ruim.
    afinacao: str = ""

    def adapted_for(self, guitar_key: str) -> dict:
        """Os parâmetros deste preset já voiced para a guitarra pedida."""
        return guitar_of(guitar_key).adapt(self.params)

    def check(self) -> list[str]:
        """Erros de sanidade deste preset (vazio = ok)."""
        bad = []
        for n in P.PARAM_NAMES:
            if n not in self.params:
                bad.append(f"{self.key}: falta o parâmetro '{n}'")
            elif not 0 <= self.params[n] <= P.PARAM_MAX[n]:
                bad.append(f"{self.key}: {n}={self.params[n]} fora de 0..{P.PARAM_MAX[n]}")
        if self.guitar not in {g.key for g in GUITARS}:
            bad.append(f"{self.key}: guitarra '{self.guitar}' não existe")
        # Coerência: delay mix alto com o bloco desligado é um preset mentiroso.
        if not self.params.get("delaySection") and self.params.get("mix", 0) > 40:
            bad.append(f"{self.key}: mix={self.params['mix']} mas delaySection=0")
        return bad


def _p(**kw) -> dict:
    """Atalho: preenche os 13 parâmetros, o que faltar é 0."""
    return P.clamp_params(kw)


PRESETS = (
    # ---------------------------------------------------------------- limpo ----
    Preset(
        key="clean-country",
        name="Country Clean",
        genres=("country", "folk", "rockabilly"),
        guitar="tele",
        signature="Tele com bridge estalado, delay slap curto e quase nenhum reverb. O corpo do twang.",
        params=_p(type=0, gain=1, tone=12, reverb=3, feedback=14, volume=104, time=6, mix=22,
                  modulation=8, cabinet=4, irSection=1, delaySection=1, toneSection=1),
        notes="O assoalho da pedaleira de country. Segure o volume no pedal, não na guitarra.",
    ),
    Preset(
        key="folk-fingerpicking",
        name="Folk Acústico",
        genres=("folk", "acoustic", "singer-songwriter"),
        guitar="acustica",
        signature="Sem distorção nenhuma: o pedal vira delay curto e reverb curto, e o violão faz o resto.",
        params=_p(type=0, gain=0, tone=9, reverb=9, feedback=20, volume=112, time=11, mix=34,
                  modulation=8, cabinet=2, irSection=0, delaySection=1, toneSection=0),
        notes="Testei com dreadnought e parlor. Se for violão com nylon, abaixe o tone em 2.",
    ),
    Preset(
        key="ambient-shimmer",
        name="Ambient Shimmer",
        genres=("ambient", "post-rock", "dream pop", "shoegaze"),
        guitar="jazzmaster",
        signature="Reverb longo, delay com retorno alto e chorus: a guitarra desaparece dentro de uma parede de som.",
        params=_p(type=1, gain=2, tone=11, reverb=14, feedback=52, volume=88, time=24, mix=58,
                  modulation=4, cabinet=6, irSection=1, delaySection=1, toneSection=1),
        notes="Aqui o gain baixo é o truque: reverb faz o trabalho que a distorção faria mal.",
    ),
    Preset(
        key="jazz-clean",
        name="Jazz Clean",
        genres=("jazz", "blues", "soul", "bossa"),
        guitar="semihollow",
        signature="Sustentado e round, com um chorus discreto. Tom de comping limpio, sem brilho de single-coil.",
        params=_p(type=0, gain=1, tone=6, reverb=6, feedback=8, volume=100, time=4, mix=12,
                  modulation=3, cabinet=1, irSection=0, delaySection=0, toneSection=0),
        notes="Nada de delay aqui. O que segura é o sustain da 335.",
    ),

    # --------------------------------------------------------------- overdrive -
    Preset(
        key="grunge-mud",
        name="Grunge Mud",
        genres=("grunge", "alternative", "post-grunge", "stoner"),
        guitar="les-paul",
        signature="Overdrive sujo e grudento, chorus ativo, delay quase ausente. O som do Nirvana com a cabeça arranhando.",
        params=_p(type=3, gain=4, tone=5, reverb=7, feedback=10, volume=96, time=9, mix=16,
                  modulation=2, cabinet=2, irSection=1, delaySection=1, toneSection=1),
        notes="O gain é o instrumento inteiro. Suba o tone se a guitarra for muito grave.",
    ),
    Preset(
        key="blues-overdrive",
        name="Blues Warm Overdrive",
        genres=("blues", "rock", "jazz", "soul"),
        guitar="les-paul",
        signature="Overdrive morno que responde ao volume da mão. Push-pull com a sustain da Les Paul.",
        params=_p(type=2, gain=3, tone=8, reverb=5, feedback=6, volume=102, time=5, mix=10,
                  modulation=8, cabinet=3, irSection=1, delaySection=0, toneSection=1),
        notes="Desligar o delay aqui é proposital: o overdrive já ocupa o espaço.",
    ),
    Preset(
        key="punk-chorus",
        name="Punk Muted Chorus",
        genres=("punk", "pop-punk", "emo", "indie"),
        guitar="tele",
        signature="Tom cortado e percussivo, chorus no fundo, quase sem reverb. Frustração com palm mute.",
        params=_p(type=1, gain=1, tone=13, reverb=3, feedback=0, volume=110, time=3, mix=10,
                  modulation=2, cabinet=4, irSection=1, delaySection=0, toneSection=1),
        notes="Se tocar sem cortar a mão, soa wash. É pra staccato.",
    ),

    # ---------------------------------------------------------------- distorção -
    Preset(
        key="metal-tight",
        name="Metal Tight",
        genres=("metal", "djent", "technical", "thrash"),
        guitar="metal",
        signature="Distorção de altaustain com o grave apertado e o delay desligado. Notas palmadas sem virar ruído.",
        params=_p(type=8, gain=5, tone=4, reverb=2, feedback=0, volume=94, time=4, mix=0,
                  modulation=8, cabinet=5, irSection=1, delaySection=0, toneSection=1),
        notes="Se virar mush, é a guitarra. Em EMG, baixe o gain da guitarra antes de mexer aqui.",
    ),
    Preset(
        key="classic-rock-lead",
        name="Classic Rock Lead",
        genres=("rock", "classic rock", "hard rock", "arena"),
        guitar="les-paul",
        signature="Distorção de sustain longo com delay de eco curto. O riff que fica na cabeça.",
        params=_p(type=6, gain=6, tone=7, reverb=5, feedback=30, volume=98, time=10, mix=30,
                  modulation=8, cabinet=3, irSection=1, delaySection=1, toneSection=1),
        notes="O sustain vem da guitarra. Dica: suba o volume da Les Paul de 7 pra 10 e deixe o pedal brilhar.",
    ),
    Preset(
        key="garage-fuzz",
        name="Garage Fuzz",
        genres=("garage rock", "indie", "lo-fi", "psych"),
        guitar="stratocaster",
        signature="Fuzz rasgado com chorus instável e delay grosso. Deliberadamente sujo, para ficar feio bonito.",
        params=_p(type=7, gain=7, tone=9, reverb=10, feedback=44, volume=86, time=20, mix=52,
                  modulation=1, cabinet=7, irSection=1, delaySection=1, toneSection=1),
        notes="O único preset onde o gain no máximo é a ideia. Não cleansar isso.",
    ),

    # -------------------------------------------------------------------- delay -
    Preset(
        key="hendrix-quack",
        name="Hendrix Quack",
        genres=("blues", "funk", "rock", "psychedelic"),
        guitar="hss-position2",
        signature="A posição 2 da HSS com overdrive limpo e sem delay: aquele timbre de "
                  "pedal que corta, o mais copiado da história do rock.",
        params=_p(type=2, gain=3, tone=10, reverb=3, feedback=0, volume=108, time=0, mix=0,
                  modulation=8, cabinet=4, irSection=1, delaySection=0, toneSection=1),
        notes="Nada de delay aqui — o que sustenta é o corte das notas. O gain baixo é "
              "de propósito: subir transforma o quack em chiado. Se ficar fino, é a "
              "posição do seletor, não o pedal.",
    ),
    Preset(
        key="surf-slide",
        name="Surf Slide",
        genres=("surf", "rockabilly", "country", "ska"),
        guitar="jazzmaster",
        signature="O surf inteiro: delay slap com retorno alto, chorus de Surfaris e reverb de praia.",
        params=_p(type=0, gain=1, tone=12, reverb=8, feedback=64, volume=102, time=7, mix=66,
                  modulation=4, cabinet=4, irSection=1, delaySection=1, toneSection=1),
        notes="Slide guitar com a mão no atraso: o delay EM volta da nota, não atrás dela.",
    ),
    Preset(
        key="echo-doubles",
        name="Echo Doubles",
        genres=("indie", "pop", "folk", "acoustic"),
        guitar="stratocaster",
        signature="Primeiro delay canônico, eco no terceiro tempo. A voz sobre si mesma, com o timbre intacto.",
        params=_p(type=0, gain=1, tone=10, reverb=5, feedback=38, volume=100, time=12, mix=40,
                  modulation=8, cabinet=2, irSection=0, delaySection=1, toneSection=0),
        notes="A-ré-mi's trick: ajuste o delay no andamento da música, não no valor bonito.",
    ),
    Preset(
        key="temple-theremin",
        name="Temple Theremin",
        genres=("psychedelic", "experimental", "ambient", "prog"),
        guitar="semihollow",
        signature="Reverb no máximo, delay com retorno alto e volume baixo. O som parece vir de outra sala.",
        params=_p(type=2, gain=3, tone=4, reverb=15, feedback=96, volume=74, time=28, mix=78,
                  modulation=5, cabinet=6, irSection=1, delaySection=1, toneSection=1),
        notes="Volume baixo de propósito. Se a caber no palco, está alto demais.",
    ),

    # ---------------------------------------------------------------- novos ----
    Preset(
        key="shoegaze-wall",
        name="Shoegaze Wall",
        genres=("shoegaze", "dream pop", "noise rock", "alternative"),
        guitar="jazzmaster",
        signature="Reverb enorme, delay com retorno alto e volume baixo: uma parede de som "
                  "onde a nota se dissolve. O oposto do som limpo e definido.",
        params=_p(type=3, gain=5, tone=6, reverb=13, feedback=72, volume=70, time=26, mix=72,
                  modulation=3, cabinet=7, irSection=1, delaySection=1, toneSection=1),
        notes="Volume BAIXO de propósito — a música é o reverb, não a guitarra. "
              "Use palm mute e strokes curtos, ou vira ruído branco.",
    ),
    Preset(
        key="funk-groove",
        name="Funk Groove",
        genres=("funk", "soul", "pop", "disco"),
        guitar="stratocaster",
        signature="Percussão de fase única com delay curtinho e quase nada de reverb. "
                  "O timbre precisa Attack para as notas soarem secas.",
        params=_p(type=1, gain=2, tone=9, reverb=2, feedback=22, volume=106, time=4, mix=26,
                  modulation=8, cabinet=4, irSection=1, delaySection=1, toneSection=1),
        notes="O Delay curto é a assinatura do funk. Delay longo aqui mata o groove.",
    ),
    Preset(
        key="indie-clean-riff",
        name="Indie Clean Riff",
        genres=("indie", "pop", "alternative", "emo"),
        guitar="tele",
        signature="Limpo com leve overdrive, chorus e delay sutil. O som de banda "
                  "indie que não usa distorção pesada.",
        params=_p(type=1, gain=2, tone=11, reverb=6, feedback=30, volume=104, time=15, mix=42,
                  modulation=3, cabinet=4, irSection=1, delaySection=1, toneSection=1),
        notes="Volume de guitarra médio: o timbre limpo precisa de sustain para soar.",
    ),
    Preset(
        key="hard-roots",
        name="Hard Roots",
        genres=("hard rock", "rock", "classic rock", "heavy metal"),
        guitar="sg",
        signature="Overdrive quente e definhado com sustain. O riff que abre com uma "
                  "nota grave e deixa a guitarra cantar.",
        params=_p(type=6, gain=6, tone=6, reverb=4, feedback=16, volume=100, time=8, mix=24,
                  modulation=8, cabinet=3, irSection=1, delaySection=1, toneSection=1),
        notes="A SG já é agressiva: comece com gain baixo e suba. Em guitar com "
              "humbucker muito forte, baixe o gain da guitarra.",
    ),
    Preset(
        key="acoustic-ballad",
        name="Acoustic Ballad",
        genres=("folk", "acoustic", "singer-songwriter", "soft rock"),
        guitar="acustica",
        signature="Violão limpo com reverb longo e delay curto. Sem nenhuma "
                  "distorção — a acústica mora aqui.",
        params=_p(type=0, gain=0, tone=8, reverb=11, feedback=26, volume=108, time=15, mix=40,
                  modulation=8, cabinet=2, irSection=0, delaySection=1, toneSection=0),
        notes="Se o violão for de nylon (clássico), abaixe o tone em 2 e o volume em 4.",
    ),
    Preset(
        key="ambient-space",
        name="Ambient Space",
        genres=("ambient", "post-rock", "drone", "experimental"),
        guitar="semihollow",
        signature="Chorus suave com reverb no máximo e delay muito longo. Notas "
                  "sustentadas viram paisagem sonora.",
        params=_p(type=1, gain=3, tone=5, reverb=15, feedback=88, volume=64, time=31, mix=80,
                  modulation=4, cabinet=6, irSection=1, delaySection=1, toneSection=1),
        notes="SUSTENTE as notas. O efeito precisa de tempo para se desenvolver — "
              "notas picadas não funcionam neste preset.",
    ),
    Preset(
        key="post-punk-tight",
        name="Post-Punk Tight",
        genres=("post-punk", "punk", "new wave", "industrial"),
        guitar="tele",
        signature="Overdrive seco e percussivo, sem reverb, sem delay. Cada nota "
                  "tem que cortar como uma faca.",
        params=_p(type=2, gain=3, tone=11, reverb=1, feedback=0, volume=112, time=0, mix=0,
                  modulation=8, cabinet=5, irSection=1, delaySection=0, toneSection=1),
        notes="Reverb e delay aqui são ENEMIGOS do som. Se quiser delay, é outro preset.",
    ),
    Preset(
        key="blues-shuffle",
        name="Blues Shuffle",
        genres=("blues", "rock", "jazz", "swamp"),
        guitar="les-paul",
        signature="Overdrive morno com leve chorus. O som do shuffle de 12 tempos, "
                  "com sustain gordo e arredondado.",
        params=_p(type=2, gain=4, tone=8, reverb=5, feedback=10, volume=100, time=6, mix=18,
                  modulation=3, cabinet=2, irSection=1, delaySection=1, toneSection=1),
        notes="Shuffle é ritmo, não timbre: toque as frases com swing mesmo com o "
              "preset certo.",
    ),
    Preset(
        key="surf-outrun",
        name="Surf Outrun",
        genres=("surf", "rockabilly", "synthwave", "retro"),
        guitar="jazzmaster",
        signature="Fase única com reverb de surf e delay slap: o som dos surfistas dos "
                  "anos 60 com um tempero moderno.",
        params=_p(type=0, gain=1, tone=13, reverb=7, feedback=58, volume=106, time=6, mix=60,
                  modulation=4, cabinet=4, irSection=1, delaySection=1, toneSection=1),
        notes="O reverb curto e o delay slap juntos são o segredo. Cuidado com o "
              "volume da guitarra para não saturar o reverb.",
    ),
    Preset(
        key="crunch-rhythm",
        name="Crunch Rhythm",
        genres=("rock", "punk", "grunge", "garage rock"),
        guitar="stratocaster",
        signature="Distorção de média força para power chords: o som das guitarras "
                  "rítmicas que seguram a música.",
        params=_p(type=5, gain=5, tone=9, reverb=3, feedback=8, volume=102, time=4, mix=12,
                  modulation=8, cabinet=3, irSection=1, delaySection=1, toneSection=1),
        notes="Distorção média: forte o bastante para cortar, fraca o bastante para "
              "não virar chiado. Se tocar sujo, baixe o gain.",
    ),
    # --------------------------------------------------- Skillet / Monster (fiel) --
    # Reconstrução a partir do equipamento DOCUMENTADO da gravação de "Monster"
    # (álbum Awake, 2009):
    #   amp    Mesa/Boogie Dual Rectifier, canal Red (Modern)
    #   guitarra Gibson Les Paul (Ben Kasica) — humbucker de ponte
    #   caixa  Mesa Rectifier 4x12 com Celestion Vintage 30
    #   boost  Ibanez TS9 (gain baixo, level alto) para apertar a frente
    #   gate   Boss NS-2
    #   afinação Drop D
    # Os knobs do Rectifier nos reviews publicados ficam em torno de
    #   gain 8 · bass 6 · mid 5 · treble 6.5 · presence 6.5 · reverb 1.5
    # (escala 0-10). O mapeamento abaixo converte para a escala do CUBE Baby.
    Preset(
        key="monster-fiel",
        name="Monster (fiel ao original)",
        genres=("metal", "hard rock", "alternative metal", "rock"),
        guitar="les-paul",
        afinacao="drop-d",
        signature="Reconstrução do timbre de estúdio: Mesa Dual Rectifier no canal Red "
                  "empurrado por TS9, com caixa Mesa 4×12 de V30. Palm mute apertado, "
                  "grave articulado e agudo presente sem chiado.",
        params=_p(type=8, gain=6, tone=10, reverb=2, feedback=0, volume=100, time=0, mix=0,
                  modulation=0, cabinet=8, irSection=1, delaySection=0, toneSection=1),
        notes="IMPORTE O IR NO BANCO 8 antes de usar. A caixa da gravação é a Mesa "
              "Rectifier 4×12 com V30 — e ela EXISTE no catálogo de fábrica do "
              "CubeSuite com o nome 'MesaRectifierV30' (aba Ajuda → Gabinetes de "
              "fábrica). No seu pack, as mais próximas são "
              "'Brohymn-Mesa-4x12-SM57-V30-5' ou 'Kalthallen 005d-SM57-V30-4x12'. "
              "Riff é seco de propósito (sem delay, sem modulação): o original também é. "
              "Se o palm mute soar frouxo, suba o tom — não o ganho.",
    ),
    Preset(
        key="monster-lead",
        name="Monster (solo / ponte)",
        genres=("metal", "hard rock", "rock"),
        guitar="les-paul",
        afinacao="drop-d",
        signature="O mesmo Rectifier com delay curto e reverb mais aberto: serve para o "
                  "solo e a ponte, onde a nota precisa sustentar e ter espaço.",
        params=_p(type=8, gain=6, tone=9, reverb=6, feedback=22, volume=100, time=13, mix=32,
                  modulation=0, cabinet=8, irSection=1, delaySection=1, toneSection=1),
        notes="IMPORTE O IR NO BANCO 8 (o mesmo do riff). Aqui o delay sobe de propósito: "
              "no original o riff é seco e o solo tem ambiência. Alterne com as teclas "
              "de timbre de bolso na aba Tocando.",
    ),
    # ------------------------------------------------- metal com IR de terceiros --
    # Estes presets pressupõem um IR carregado pelo CubeSuite num banco
    # específico. O número do gabinete aponta para esse banco. Sem o IR certo
    # o preset ainda funciona — só não soa como descrito.
    Preset(
        key="monster-ir",
        name="Monster (com IR de metal)",
        genres=("metal", "hard rock", "alternative metal"),
        guitar="metal",
        afinacao="drop-c",
        signature="O Monster com IR de terceiros: o 5150 do pedal empurra uma caixa "
                  "4×12 com V30, e o palm mute estala sem virar chiado.",
        params=_p(type=8, gain=5, tone=9, reverb=2, feedback=8, volume=98, time=6, mix=12,
                  modulation=0, cabinet=8, irSection=1, delaySection=1, toneSection=1),
        notes="Antes de usar: carregue um IR 4×12 com V30 no BANCO 8 pelo CubeSuite "
              "(sugestão: Kalthallen '005d-SM57-V30-4x12'). O gain fica em 5, e não 6, "
              "porque um IR bom já entrega parte do ataque — suba só se faltar corpo.",
    ),
    Preset(
        key="tight-riff-ir",
        name="Riff Apertado (IR de metal)",
        genres=("metal", "djent", "progressive metal"),
        guitar="metal",
        afinacao="drop-c",
        signature="Ganho controlado e tom alto: o riff fica definido nota por nota, "
                  "sem embolar. O IR faz o trabalho de corpo.",
        params=_p(type=7, gain=4, tone=11, reverb=2, feedback=6, volume=98, time=5, mix=10,
                  modulation=0, cabinet=8, irSection=1, delaySection=0, toneSection=1),
        notes="Carregue o IR no BANCO 8. Este preset é sobre CLAREZA: se soar fino, "
              "resista a subir o ganho — suba o tom.",
    ),
    Preset(
        key="lead-sustain-ir",
        name="Lead com Sustain (IR de metal)",
        genres=("metal", "hard rock", "rock"),
        guitar="metal",
        afinacao="drop-c",
        signature="Ganho mais alto e reverb curto: a nota sustenta para solo, e o "
                  "delay dá profundidade sem sujar a definição.",
        params=_p(type=8, gain=6, tone=8, reverb=5, feedback=18, volume=100, time=12, mix=28,
                  modulation=0, cabinet=8, irSection=1, delaySection=1, toneSection=1),
        notes="Carregue o IR no BANCO 8 (o mesmo do Monster). Aqui o delay sobe: "
              "solo precisa de ar, riff não.",
    ),
    # --------------------------------------------------------------- metal/moderno --
    Preset(
        key="monster-riff",
        name="Monster Riff",
        genres=("metal", "hard rock", "alternative metal", "rock"),
        guitar="metal",
        afinacao="drop-c",
        signature="Distorção moderna apertada, com o palm mute estalando: o grave fica "
                  "seco e o ataque corta. Reverb curto para não embolar o riff.",
        params=_p(type=8, gain=6, tone=8, reverb=3, feedback=10, volume=100, time=7, mix=14,
                  modulation=0, cabinet=6, irSection=1, delaySection=1, toneSection=1),
        notes="Precisa estar em DROP C (C G C F A D) — use o seletor do Afinador. "
              "Em Mi padrão o riff sai nas notas erradas. Se o palm mute soar mole, "
              "suba o tone e corte o reverb; se picotar, baixe o gain 1.",
    ),
    # ------------------------------------------------------------- metal/moderno --
    Preset(
        key="djent-palm",
        name="Djent Palm Mute",
        genres=("djent", "metal", "progressive metal"),
        guitar="metal",
        signature="Distorção apertada com grave cortado: o palm mute estala como um tambor. "
                  "Pouco reverb de propósito, para não embolar os riffs.",
        params=_p(type=7, gain=6, tone=7, reverb=2, feedback=4, volume=98, time=3, mix=6,
                  modulation=0, cabinet=7, irSection=1, delaySection=0, toneSection=1),
        notes="Se soar fino demais, suba o gain 1. O segredo aqui é o tone alto, não o ganho.",
    ),
    Preset(
        key="doom-drone",
        name="Doom Drone",
        genres=("doom", "stoner", "sludge", "metal"),
        guitar="sg",
        signature="Distorção lenta e grave, com reverb longo por baixo. Som de parede de "
                  "amplificador num galpão.",
        params=_p(type=6, gain=5, tone=3, reverb=11, feedback=30, volume=94, time=18, mix=40,
                  modulation=2, cabinet=7, irSection=1, delaySection=1, toneSection=1),
        notes="Grave com reverb longo pede cuidado: se embolar, baixe o mix antes do reverb.",
    ),
    Preset(
        key="emo-twang",
        name="Emo Twang",
        genres=("emo", "midwest emo", "indie", "math rock"),
        guitar="tele",
        signature="Limpo com twang e delay pontuado: acordes abertos que deixam cada nota "
                  "soar separada.",
        params=_p(type=0, gain=2, tone=11, reverb=5, feedback=34, volume=102, time=13, mix=36,
                  modulation=5, cabinet=3, irSection=1, delaySection=1, toneSection=1),
        notes="O delay pontuado é o som da escola. Toque com o tempo marcado que ele encaixa.",
    ),
    Preset(
        key="bossa-nylon",
        name="Bossa Nylon",
        genres=("bossa", "jazz", "latin", "mpb"),
        guitar="acustica",
        signature="Sem distorção e sem delay: reverb de sala curto e tom macio. O violão "
                  "fica na frente, com espaço.",
        params=_p(type=0, gain=0, tone=5, reverb=7, feedback=6, volume=108, time=3, mix=8,
                  modulation=2, cabinet=1, irSection=0, delaySection=0, toneSection=0),
        notes="Tocando com nylon, abaixe o tone 2. Aqui menos efeito é mais som.",
    ),
    Preset(
        key="praise-shimmer",
        name="Praise Shimmer",
        genres=("worship", "praise", "ambient", "pop"),
        guitar="stratocaster",
        signature="Limpo com delay e reverb generosos: notas que ficam no ar enquanto os "
                  "acordes trocam por baixo.",
        params=_p(type=0, gain=2, tone=10, reverb=13, feedback=44, volume=96, time=19, mix=52,
                  modulation=6, cabinet=5, irSection=1, delaySection=1, toneSection=1),
        notes="É o som de igreja moderno: volume baixo, delay alto, muita ambiência.",
    ),
    Preset(
        key="ska-upstroke",
        name="Ska Upstroke",
        genres=("ska", "reggae", "dub", "punk"),
        guitar="tele",
        signature="Limpo, seco e percussivo: quase sem reverb, para o upstroke cortar como "
                  "uma bateria.",
        params=_p(type=0, gain=1, tone=12, reverb=1, feedback=10, volume=104, time=5, mix=14,
                  modulation=3, cabinet=2, irSection=0, delaySection=0, toneSection=1),
        notes="O corte vem do reverb BAIXO. Não coloque reverb em ska: embola o contratempo.",
    ),
    Preset(
        key="funk-wah-clean",
        name="Funk Clean Cut",
        genres=("funk", "soul", "rnb", "groove"),
        guitar="stratocaster",
        signature="Muito limpo, reverb zero, tom no alto. Cada nota percute como se você "
                  "tivesse batido na corda.",
        params=_p(type=0, gain=1, tone=13, reverb=0, feedback=8, volume=102, time=4, mix=10,
                  modulation=2, cabinet=2, irSection=0, delaySection=0, toneSection=1),
        notes="Funk é ritmo e mão abafada. Se o som ficar mole, suba o tone e corte o reverb.",
    ),
    Preset(
        key="garage-punk",
        name="Garage Punk",
        genres=("garage rock", "punk", "garage punk", "lo-fi"),
        guitar="sg",
        signature="Distorção crua e brilhante, sem reverb e sem delay: o som de uma banda "
                  "tocando num quarto pequeno.",
        params=_p(type=6, gain=6, tone=11, reverb=1, feedback=6, volume=104, time=3, mix=8,
                  modulation=0, cabinet=6, irSection=1, delaySection=0, toneSection=1),
        notes="Sem efeito nenhum além da distorção. O charme é justamente o som cru.",
    ),
)

BY_KEY = {p.key: p for p in PRESETS}


def all_errors() -> list[str]:
    """Todos os erros de sanidade da biblioteca (vazio = tudo ok)."""
    out: list[str] = []
    seen = set()
    for p in PRESETS:
        if p.key in seen:
            out.append(f"chave duplicada: {p.key}")
        seen.add(p.key)
        out.extend(p.check())
    return out


def search(query: str = "", genre: str = "", guitar: str = "") -> list[Preset]:
    """Filtra por texto (nome/assinatura/gêneros), gênero exato e guitarra de referência."""
    q = query.strip().lower()
    out = []
    for p in PRESETS:
        if genre and genre not in p.genres:
            continue
        if guitar and p.guitar != guitar:
            continue
        if q:
            hay = f"{p.name} {p.signature} {' '.join(p.genres)} {p.notes}".lower()
            if q not in hay:
                continue
        out.append(p)
    return out


def genres() -> list[str]:
    """Gêneros ordenados, com a contagem de presets de cada um."""
    counts: dict[str, int] = {}
    for p in PRESETS:
        for g in p.genres:
            counts[g] = counts.get(g, 0) + 1
    return sorted(counts, key=lambda g: (-counts[g], g))


def describe(p: Preset) -> str:
    """Resumo de uma linha para a lista da UI."""
    g = guitar_of(p.guitar)
    return f"{p.name} · {g.label} · {p.genres[0]}"
