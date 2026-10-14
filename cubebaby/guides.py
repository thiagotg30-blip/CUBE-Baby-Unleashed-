"""Guias para iniciante: o que cada controle faz e por onde começar.

O CUBE Baby é um pedal de entrada — a maioria de quem compra não sabe o que é
"tone" nem onde mexer. Estas textos existem para a interface poder explicar em
português, no lugar certo, o que um slider faz e o que acontece se você mexer
nele. Nada aqui é mistério técnico: é a mesma informação dos manuais, escrita
para quem está começando.

Dois níveis:
  KNOB_TIPS   — o que é cada parâmetro, tooltip que aparece no slider
  BLOCK_TIPS  — o que o bloco inteiro faz, e o erro típico de iniciante
  FIRST_STEPS — um roteiro de 5 minutos para sair tocando
"""
from __future__ import annotations

from . import protocol as P

# O que é, e o que acontece se você mexer. Curto de propósito: cabe num tooltip.
KNOB_TIPS = {
    "type": "Escolhe o pré-amp que gera a distorção. 0-1 é limpo, 2-4 overdrive, "
            "5-9 distorção pesada. Comece no 0 e suba de dois em dois.",
    "gain": "Quanto o pré-amp distorce. 0 é limpo, 7 é distorção extrema. "
            "Este é o controle mais importante: ele define o timbre inteiro.",
    "tone": "EQ de presença. Baixo = som escuro e abafado; alto = som fino e "
            "cantarolante. Se a guitarra for grave, suba 2 ou 3.",
    "reverb": "Cauda de reverb. 0 é seco; acima de 10 vira outra sala. "
              "Em overdrive, mantenha baixo, senão o som afoga.",
    "feedback": "Retorno do delay: cada repetição repete também. Valores altos "
                "com delay curto =/plugins de sustain. 0 desliga o canto.",
    "volume": "Volume de saída do pedal. Cuidado: se estiver alto demais, distorção "
              "muito alta vira chiado.",
    "time": "Tempo do delay. Comece no meio (15) e ajuste até encaixar na batida. "
            "0 é quase imperceptível.",
    "mix": "Quanto delay aparece junto da guitarra. 30-40 é discreto, acima de 70 "
           "o delay vira a música.",
    "modulation": "Chorus (0-6), desligado (7-8) ou Phaser (9-15). Chorus deixa "
                  "o som mais grosso; Phaser faz aquele efeito de varredura.",
    "cabinet": "Simula o amps/cabinete. 0 é bypass (som cru). Mude se a guitarra "
               "estiver fina demais ou grossa demais.",
    "irSection": "Liga ou desliga o gabinete. Desligado, você ouve a guitarra crua.",
    "delaySection": "Liga ou desliga o delay. Desligado, tempo e mix param sum.",
    "toneSection": "Liga ou desliga o EQ de presença. Só note a diferença com ligado.",
}

BLOCK_TIPS = {
    "Pré-amp": "É o som sujo. Os 3 controles juntos definem a distorção: tipo escolhe "
              "QUAL pré-amp, ganho escolhe QUANTO, tom ajusta o brilho.",
    "Gabinete": "Troca o som da guitarra crua por um amplificador. Se você tem um "
                "amplificador bom, deixe em bypass (0).",
    "Modulação": "Chorus e Phaser. Vem ligada de fábrica; se a guitarra parece fina "
                 "demais, suba para 9 e ouça um phaser.",
    "Delay": "A repetição depois da nota. Comece com mix baixo (25) e subindo — a "
             "maioria dos iniciantes exagera no retorno e vira um buraco.",
    "Reverb": "O espaço em volta do som. Pouco reverb deixa a música com cola; muito "
              "reverb afoga a guitarra.",
    "Saída": "O volume final do pedal. Ajuste olhando os medidores do seu amplificador.",
}

# Roteiro de quem nunca usou um pedal. Cada passo diz o QUE fazer e POR QUE.
FIRST_STEPS = [
    ("1. Comece limpo, e do volume da guitarra", "Escolha o preset 'Jazz Clean' e "
     "deixe o tipo em 0. Baixe o volume da guitarra até quase sumir, depois suba. "
     "Nada de distorção no começo: você quer ouvir o que cada controle faz."),
    ("2. Um efeito por vez", "Quer sustain? Suba o GANHO devagar. Quer delay? Ligue "
     "o DELAY e suba o MIX aos poucos. Mexer em tudo junto impede de saber o que "
     "funcionou."),
    ("3. O brilho por último", "Só mexa no TOM se o resto estiver bom. É o controle "
     "que mais estraga um som que já estava funcionando."),
    ("4. Grave antes de gostar", "Escolha A, B ou C e grave. Assim você não perde o "
     "preset e pode comparar depois. Um preset que você gostou é mais fácil de "
     "lembrar do que um que você ajustou e esqueceu."),
    ("5. Sua guitarra muda tudo", "Se você trocar de guitarra, volte ao topo e mude a "
     "guitarra: o programa re-adapta os valores dos três slots sozinho."),
]

# "Não sei o que escolher" — o guia mais útil para iniciante: situação -> preset.
# Ordenado do mais simples ao mais específico.
DECISIONS = [
    ("Nunca usei um pedal",
     ["Jazz Clean — sem distorção, só reverb. É por aqui que todo mundo começa.",
      "Punk Muted Chorus — se quiser algo com cara de banda logo no começo."]),
    ("Toco violão",
     ["Folk Acústico — sem distorção nenhuma, com delay de paralelismo.",
      "Acoustic Ballad — o mesmo, com mais reverb. Para balada."]),
    ("Quero o som de uma banda que eu gosto",
     ["Nirvana / grunge → Grunge Mud",
      "Metallica / thrash → Hard Roots",
      "Queen / rock clássico → Classic Rock Lead",
      "Pixies / shoegaze → Shoegaze Wall",
      "Stranglers / post-punk → Post-Punk Tight"]),
    ("Quero um riff com som limpo",
     ["Country Clean — twang de violão, great para country e folk.",
      "Surf Slide — o surf: delay slap e reverb de praia.",
      "Echo Doubles — delay no terceiro tempo, a voz sobre si mesma."]),
    ("Toco metal",
     ["Metal Tight — grave apertado, sem delay. Feito para EMG e DiMarzio."]),
    ("Só quero testar o pedal com os verbos",
     ["Garage Fuzz — o mais sujo de todos, e é de propósito.",
      "Hendrix Quack — o timbre de pedal mais imitado da história."]),
    ("Meu take ficou com chiado",
     ["Use Gate + Normalizar na aba Áudio: corta o zumbido entre as notas e "
      "iguala o volume dos takes, para comparar dois presets sem o volume te enganar."]),
]


def decisions_text() -> str:
    """O guia de decisão, em HTML para a janela de ajuda."""
    partes = []
    for titulo, itens in DECISIONS:
        li = "".join(f"<br>· {i}" for i in itens)
        partes.append(f"<b>{titulo}</b>{li}<br><br>")
    return "".join(partes)

# Nomes mais claros que os nomes técnicos do protocolo, para iniciante.
FRIENDLY = {
    "type": "Pré-amp", "gain": "Ganho", "tone": "Tom", "reverb": "Reverb",
    "feedback": "Retorno", "volume": "Volume", "time": "Tempo", "mix": "Mix do delay",
    "modulation": "Chorus / Phaser", "cabinet": "Gabinete", "irSection": "Gabinete ligado",
    "delaySection": "Delay ligado", "toneSection": "Tom ligado",
}

# Dicas da aba Áudio, no mesmo tom das outras.
AUDIO_TIPS = {
    "monitor": "OUVE A GUITRA AO VIVO. Ligue, toque, e você ouve na hora pela "
               "interface, sem gravar nada. É para conferir o timbre do pedal. "
               "Há um leve atraso (dezenas de milissegundos) — para tocar junto "
               "de verdade, use o monitor direto da sua interface, que não passa "
               "por programa nenhum. IMPORTANTE: entrada e saída precisam ser "
               "dispositivos DIFERENTES. Se a guitarra entra pela interface USB "
               "e a saída também for a mesma interface, o Windows não deixa os "
               "dois abertos ao mesmo tempo. Use um par de fones ou "
               "alto-falante diferente.",
    "dsp": "Gate + Normalizar. O gate corta o silêncio e o zumbido entre as "
           "notas (o chiado fica só embaixo do limiar). O normalizador deixa a "
           "gravação no volume certo, para comparar dois presets sem o volume te "
           "enganar. O arquivo original nunca é alterado: sai uma cópia nova.",
    "input": "A entrada onde a guitarra está plugada. Se você tem uma interface USB "
             "(Scarlett, Focusrite, Behringer), escolha a entrada 'Linha' dela — "
             "não o microfone do notebook. Se usar o microfone, escolha a entrada "
             "'Microfone'.",
    "output": "Onde a gravação é tocada. Em geral, o mesmo par de fones que você já usa.",
    "level": "Se a barra ficar na parte vermelha, a gravação está estourando e "
             "soa distorcido. Abaixe o volume da guitarra ou o gain da interface. "
             "O ideal é ficar na faixa verde, perto do fim.",
    "record": "Grava o que entra na interface. Toque uma vez, grave, toque de novo "
              "com outro preset e compare: é para isso que serve.",
    "latency": "Ouve com um leve atraso — é normal e só incomoda para tocar ao vivo. "
               "Para tocar junto, use o monitor direto da sua interface de áudio.",
    "noise": "Se a gravação tiver chiado, o problema é a interface: gain alto demais, "
             "cabo ruim, ou saturação digital. Baixe o gain e troque o cabo.",
}



# Atalhos do modo iniciante: "o que você quer?" em vez de 13 controles.
# Cada botão mexe só nos poucos parâmetros que importam para aquele objetivo e
# deixa o resto intacto — é um ponto de partida, não uma sobrescrita cega.
QUICK_INTENTS = [
    ("limpo", "Limpo", "Sem distorção. Paracountry, folk, violão.",
     {"type": 0, "gain": 1, "tone": 10, "reverb": 5, "mix": 0,
      "delaySection": 0, "irSection": 0, "toneSection": 0, "modulation": 8}),
    ("sustain", "Mais sustain", "A guitarra canta e não some.",
     {"type": 2, "gain": 4, "tone": 8, "reverb": 5, "mix": 0,
      "delaySection": 0, "irSection": 1, "toneSection": 1, "modulation": 8}),
    ("sujão", "Sujão", "Distorção pesada, som de amplificador.",
     {"type": 6, "gain": 6, "tone": 7, "reverb": 4, "mix": 0,
      "delaySection": 0, "irSection": 1, "toneSection": 1, "modulation": 8}),
    ("reverb", "Com reverb", "O som ganha espaço, como se fosse numa sala.",
     {"type": 1, "gain": 3, "tone": 9, "reverb": 11, "mix": 0,
      "delaySection": 0, "irSection": 0, "toneSection": 0, "modulation": 8}),
    ("delay", "Com delay", "A nota se repete depois de um tempo.",
     {"type": 2, "gain": 3, "tone": 9, "reverb": 5, "feedback": 30,
      "time": 12, "mix": 34, "delaySection": 1, "irSection": 0,
      "toneSection": 0, "modulation": 8}),
    ("surf", "Surf", "Aquele delay dos anos 60, com reverb de praia.",
     {"type": 0, "gain": 1, "tone": 12, "reverb": 8, "feedback": 60,
      "time": 7, "mix": 60, "delaySection": 1, "irSection": 1,
      "toneSection": 1, "modulation": 8}),
]

# No modo iniciante só aparecem estes. Os outros 8 ficam no modo avançado: são
# necessários para afinar o som, mas atrapalham quem ainda está descobrindo.
BEGINNER_PARAMS = ("gain", "tone", "volume", "reverb", "mix")

# Rótulo e explicação por controle, no modo iniciante.
BEGINNER_LABELS = {
    "gain": ("Sustorção", "0 é limpo. Suba para a guitarra ganhar corpo; "
                         "acima de 5 vira distorção pesada."),
    "tone": ("Brilho", "Deixando escuro fica abafado. Em cima, fino e "
                      "cantarolante. Se a guitarra for grave, suba."),
    "volume": ("Volume", "O volume final do pedal. É aqui que você ajusta "
                         "o som para o seu amplificador."),
    "reverb": ("Espaço", "O quanto o som se espalha no ambiente. Pouco cola "
                         "a música; muito afoga a guitarra."),
    "mix": ("Repetição", "Quanto da repetição aparece junto da guitarra. "
                         "Comece baixo e suba aos poucos."),
}


def knob_tip(name: str) -> str:
    """Tooltip de um parâmetro. Cai no vazio se o nome não existir."""
    tip = KNOB_TIPS.get(name, "")
    friendly = FRIENDLY.get(name, name)
    return f"{friendly}\n\n{tip}" if tip else friendly


def block_tip(title: str) -> str:
    return BLOCK_TIPS.get(title, "")


def first_steps_text() -> str:
    """O roteiro de 5 minutos, em texto simples para uma janela de ajuda."""
    return "\n\n".join(f"<b>{t}</b><br>{d}" for t, d in FIRST_STEPS)


def audio_tip(key: str) -> str:
    """Tooltip da aba Áudio. Cai no vazio se a chave não existir."""
    return AUDIO_TIPS.get(key, "")


def first_steps_texto_com_audio() -> str:
    """Roteiro + uma nota sobre áudio, para a janela de ajuda."""
    extra = (
        "\n\n<b>Gravar para comparar</b><br>"
        "Abra a aba <b>Áudio</b>, escolha a entrada da sua interface e clique em Gravar. "
        "Toque um riff, grave, troque de preset, toque de novo e ouve os dois. "
        "É o jeito mais rápido de saber se o preset funciona na sua guitarra — "
        "e dispensa abrir o REAPER."
    )
    return first_steps_text() + extra


def coverage() -> set[str]:
    """Parâmetros sem dica — usado no teste para a cobertura ficar completa."""
    return set(P.PARAM_NAMES) - set(KNOB_TIPS)
