# CUBE Baby Unleashed

**CUBE Baby Unleashed** é um editor **desktop nativo** (Qt/PySide6, sem navegador) para o pedal M-VAVE/CUVAVE **CUBE Baby**.
Projeto independente, não afiliado à fabricante.

> [!CAUTION]
> **Antes de publicar: leia a seção [Publicar este projeto](#publicar-este-projeto).**
> A licença não é escolha — o protocolo deriva de material sob GPL-3.0.
> E rode `git rm -r --cached .venv build dist` antes do primeiro push.

## Rodar (Windows)
Precisa do **Python 3.12** (o 3.14 ainda não tem pacote pronto do `python-rtmidi`).
Se não tiver: `winget install Python.Python.3.12`. Pode ficar com o 3.14 instalado também.

- **`run_debug.bat`**: cria um ambiente isolado (`.venv`), instala tudo e abre o programa com o console aberto.
- **`build_exe.bat`**: gera `dist\CUBEBabyUnleashed\CUBEBabyUnleashed.exe`.
- Sem pedal: `.venv\Scripts\python main.py --sim` abre com um pedal simulado.

> Feche o CubeSuite antes: dois programas não podem usar a porta MIDI do pedal ao mesmo tempo.
> Se der erro, ele aparece numa janela e fica em `%USERPROFILE%\CUBEBabyUnleashed\crash.log`.

## O que faz
- Conecta no pedal por USB-MIDI (SysEx), detecta a porta sozinho e lê os 3 presets (A/B/C).
- Edita em tempo real: tipo de pré-amp, gain, tom, delay, reverb, modulação, cabinet, volume.
- **38 presets curados** com assinatura sonora, gêneros e guitarra de referência.
- **Adaptação por guitarra**: o mesmo preset se re-voicing para 8 instrumentos (ver abaixo).
- Importa/exporta presets `.json` (compatível com o preset-studio web e com bancos do CubeControl/ToneHub).
- Biblioteca local em `~/CUBEBabyUnleashed/biblioteca`. Backup automático em `~/CUBEBabyUnleashed/backups`
  antes de gravar um preset importado no pedal.

## Presets curados e adaptação por guitarra

A aba **Presets curados** tem 38 presets auditados, cada um com a assinatura sonora
escrita ("overdrive sujo e grudento, chorus ativo..."), os gêneros a que serve e a
guitarra em que foi pensado. Filtre por gênero ou busque por texto.

**A guitarra é um ajuste global, não um filtro.** No topo da janela, em "Minha
guitarra", você informa qual instrumento está plugado — uma vez — e o programa
re-adapta os valores de todos os slots de uma vez. Não existe "adaptar" nem
"aplicar": trocar a guitarra já re-adapta. A lista de presets nunca some em
função da guitarra; todos os 24 continuam disponíveis, cada um mostrando o que
mudaria na sua.

O CUBE Baby não sabe qual guitarra está plugada — ele só aplica os *parâmetros*.
A adaptação acontece no software: cada perfil declara um **viés** por parâmetro,
e o preset é re-voiced antes de ir para o pedal.

| Guitarra | Família | O que o viés faz |
|---|---|---|
| Stratocaster SSS | fase única | +brilho, +volume (fase única perde ~6 dB), −delay mix |
| Telecaster | fase única | +brilho, delay mais curto e mais seco |
| Jazzmaster | fase única | +brilho, +chorus, −distorção |
| **Strat HSS — ponte** | híbrida | humbucker: mais ganho, +volume, tipo +1 |
| **Strat HSS — posição 2** | híbrida | o "quack": +brilho, +volume, −ganho, −tipo |
| **Strat HSS — neck** | híbrida | fase única no neck: +volume, −2 de tipo, +reverb |
| Les Paul | humbucker | −brilho, −volume, +ganho, +feedback |
| Gibson SG | humbucker | −brilho, +distorção |
| Ibanez RG (EMG) | ativos | −ganho, −reverb, aperta o grave |
| ES-335 | semi-acústica | +reverb, +delay mix, +chorus |
| Violão (steel-string) | acústica | −distorção, delay mais presente |

**A HSS aparece em três entradas**, porque a posição do seletor muda o timbre mais
que a marca: ponte, posição 2 e neck soam como três guitarra diferentes. A
posição 2 (fase única no meio contra o humbucker da ponte) é o Famous Quack. No
dropdown elas aparecem como `Strat HSS · híbrida — posição 2 (o quack)`, para não
ficarem idênticas.

Valores que **você** mexeu à mão não são re-adaptados — a troca de guitarra só
re-ajusta o que veio de um preset curado. "Carregar original" ignora a adaptação
e carrega os valores crus.

Adaptar é som, não física: a guitarra continua mandando no timbre final. Os presets
foram pensados para soar bem na guitarra de referência e funcionar razoavelmente
nas outras — o resto é ouvido.

## Dicas para iniciante

O CUBE Baby é um pedal de entrada, e a interface foi escrita para quem nunca mexeu
num:

- **Botão `? Dicas`** na aba Pedal abre um guia com três abas: *Por onde começar*
  (roteiro de 5 minutos), *O que é cada controle* (os 13 parâmetros explicados) e
  *Guitarras* (o que cada perfil faz).
- **Tooltip em todo slider, combo e checkbox** — o que o controle faz e o que
  acontece se você mexer. Os 6 blocos também têm tooltip com o erro típico de
  iniciante ("a maioria exagera no feedback e vira um buraco").

Os textos vivem em `cubebaby/guides.py`, separados da interface, para dar para
editar o tom das dicas sem mexer em código de UI.

## Ouvir a guitarra ao vivo (aba Áudio)

Para conferir um preset não é preciso abrir o REAPER. A aba **Áudio** tem duas
coisas separadas, e a primeira é a que você mais vai usar:

**1. Ouvir ao vivo** — clica em `▶ Ouvir ao vivo`, toca a guitarra, e o som sai
pela interface na hora. Nada é gravado. É para conferir o timbre do pedal antes
de decidir se gosta. Tem um slider de volume do monitor, que não afeta a
gravação.

**2. Gravar** — se quiser guardar pra comparar depois, o `● Gravar` salva a
entrada em WAV:

- **Medidor de nível** em tempo real, em dB. Fica verde até ~-6 dB, amarelo, e
  vermelho quando clipa — para você ver que está estourando *antes* de gravar.
- Os arquivos vão para `~/CUBEBabyUnleashed/gravacoes/cuba-AAAAMMDD-HHMMSS.wav`
  (WAV PCM 16-bit, 44,1 kHz).
- **Ouvir** a gravação, **Gate + Normalizar**, **Abrir em outro programa...**
  (abre no player padrão), e **Excluir**.

O uso típico: monitor ligado, troca o preset a cada riff e ouve a diferença
enquanto toca. Sem trocar de programa, sem gravar nada.

### Gate de ruído e normalizador

O botão **Gate + Normalizar** processa uma gravação selecionada:

- **Gate** — corta o silêncio entre as notas, e com ele o zumbido de 60 Hz e o
  chiado da interface. É envelope-based com histerese e *hold*, como um
  compressor: sem isso o gate abriria e fecharia a cada nota e a guitarra
  "engasgaria". Limiar ajustável de -70 a -20 dB.
- **Normalizador** — deixa a gravação no volume certo, para comparar dois
  presets sem o volume te enganar ("esse é melhor" quando na verdade só está
  mais alto). Dois modos: **pico** (o ponto mais alto vai para o alvo) e
  **volume percebido/RMS** (mais natural, mas respeita um teto de pico para não
  estalar).

**O original nunca é alterado**: o resultado sai num arquivo novo, com
`-processado` no nome. O botão mostra a prévia do que vai acontecer antes de
processar.

Por que `audioop` e não numpy: numpy não está no projeto e acrescentaria
~15 MB ao requirements e ao `.exe` do PyInstaller. O `audioop` é padrão
(deprecated, mas presente até o Python 3.12, que é o que o `setup.bat`
instala) e faz o trabalho pesado em C.

### Sobre latência, drivers ASIO e afins

O monitor passa por uma cadeia WASAPI (captura → mixagem → saída), o que deixa
**~20–60 ms** entre você tocar e ouvir. Isso é irrelevante para conferir timbre,
mas atrapalha para tocar junto.

**Tocar junto com verdade só com monitor direto na interface** — o botão
"Direct Monitor" do Scarlett/Focusrite/Behringer, que é latência zero e não
passa por programa nenhum. Nenhum software no mundo faz melhor que isso.

Sobre ASIO: o PySide6 fala **WASAPI**, que é o caminho nativo do Windows e já é
o que estamos usando. O Qt **não tem backend ASIO** — não é limitação do PySide6,
é do Qt. ASIO exigiria trocar de biblioteca de áudio (sounddevice/PortAudio) e
ainda assim depender do driver ASIO instalado, mais a licença do SDK da
Steinberg. O ganho para um app como este não paga esse custo — e a
`requirements.txt` continua sendo só PySide6 + python-rtmidi, sem DLL extra para
empacotar no `.exe`.

Se a sua interface **só** oferece ASIO (sem WDM), ela não vai aparecer na lista
de entradas. Nesse caso o caminho seria instalar o driver WDM dela, que quase
toda interface moderne tem.

Cuidado com microfone: se a guitarra estiver na frente de um microfone ligado e
você monitorar pela saída, dá microfonia e satura. Com guitarra em entrada de
linha (`Linha`, não `Microfone`) isso não acontece.

## Como se usa

Na **primeira execução** o programa se apresenta e pergunta qual é a sua
guitarra — a única coisa que ele não consegue descobrir sozinho, e a que mais
muda o resultado. A partir daí ele lembra: tamanho da janela, aba em uso,
guitarra, dispositivos de áudio e volume do monitor.

O fluxo normal é:

1. **Conectar** o pedal por USB (e fechar o CubeSuite antes).
2. Escolher um **preset curado** na aba de mesmo nome, ou ajustar na mão.
3. **Ouvir ao vivo** na aba Áudio e trocar de preset enquanto toca.

### Dois modos: iniciante e avançado

A aba **Pedal** abre em modo **Iniciante**, e o seletor no canto troca para
**Avançado**.

**Iniciante** mostra 5 controles com nome de everyday — *Sustorção, Brilho,
Volume, Espaço, Repetição* — e seis atalhos em **"O que você quer?"**: Limpo,
Mais sustain, Sujão, Com reverb, Com delay, Surf. Cada atalho mexe só nos
parâmetros que importam para aquele objetivo e deixa o resto intacto; é um
ponto de partida, não uma sobrescrita.

**Avançado** mostra os 13 parâmetros organizados em blocos (Pré-amp, Gabinete,
Modulação, Delay, Reverb, Saída), com os nomes técnicos do pedal.

Os dois modos usam **os mesmos controles** — nada é recriado ao trocar, então
você pode ir e voltar no meio de um ajuste sem perder nada. O modo fica salvo.

### Atalhos de teclado

| Atalho | O que faz |
|---|---|
| `Ctrl+1` … `Ctrl+4` | troca de aba (Pedal, Presets, Áudio, Biblioteca) |
| `Ctrl+M` | liga/desliga o ouvir ao vivo |
| `Ctrl+R` | atualiza as portas MIDI |
| `F1` | abre a ajuda |
| `Ctrl+Shift+A` | janela "Sobre" (e repete a introdução) |

### Onde ficam as coisas

Preferências, logs e gravações vão para a pasta **`~/CUBEBabyUnleashed`** no seu usuário
(`%USERPROFILE%\CUBEBabyUnleashed` no Windows):

- `preferences.json` — o que o programa lembra de você
- `pedal.log` / `crash.log` — diagnóstico
- `gravacoes/` — suas gravações em WAV
- `biblioteca/` — seus presets em JSON
- `backups/` — cópia automática antes de gravar no pedal

Portátil: copie a pasta e o programa vai junto. Apagou a pasta, recomeça do zero.

## Engenharia reversa do CubeSuite (Ghidra + REA)

O `CubeSuite.exe` oficial foi analisado com **Ghidra 12.1.4** via **REA**, para
descobrir como um IR de usuário chega à flash do pedal. Relatório completo em
[`docs/engenharia-reversa-cubesuite.md`](docs/engenharia-reversa-cubesuite.md).

**O que ficou provado (observado no binário):**

- O IR tem um formato interno chamado **`CubeSugarIR`**, tratado pela classe
  `CCubeSugarIREditDlg` (nomes vindos dos metadados de MOC do Qt).
- Só entra **WAV PCM**: o parser valida `RIFF` → `WAVE` → chunk `format` →
  chunk `data`, abortando no primeiro que faltar.
- O upload **não é um SysEx de IR**: é um **programa de flash por setores** —
  para cada segmento de uma tabela, apaga o setor e escreve, com barra de
  progresso. Explica por que `MEM_WRITE` (0x22) não existe como literal no
  executável: o endereço é montado em tempo de execução.
- O mapa da flash vem de **configuração** (`/TYPE`, `/Start Address`,
  `/End Address`, `/Sector Size`), lida ao lado do executável.

**O que continua desconhecido:** o layout de bytes do `CubeSugarIR`, os valores
da configuração de flash do CUBE Baby, e a função exata de conversão WAV →
formato do pedal. Não há atalho simples (um SysEx de IR) para implementar sem
risco — por isso o upload segue sendo feito pelo CubeSuite, e o próximo passo
seguro continua sendo a **leitura** da ROM por `MEM_READ`.

## IR ideal para cada preset

Os 38 presets passaram a indicar **qual IR usar** para chegar mais perto do som
— sem tirar nada. O gabinete de fábrica de cada preset **continua no lugar**:
a sugestão é informação adicional, para quem tem um IR melhor.

A lista completa aparece na aba **Impulso (IR)** e na ficha de cada preset.
Cada sugestão diz o arquivo, a caixa e **por quê** — e marca o grau de
confiança:

- **combina bem** (16 presets) — a caixa e o falante batem com o que o gênero
  ou a gravação usa. Ex.: `Monster (fiel ao original)` → Mesa 4×12 com V30.
- **aproximação** (4 presets) — não há caixa específica; é um ponto de partida.
  Ex.: os de violão, onde o melhor é uma caixa neutra.

**Todos os nomes de arquivo foram verificados no disco** — nenhuma sugestão
aponta para arquivo que não existe no pack. E todos os presets continuam com o
gabinete de fábrica válido (há teste para isso).

Isto é **orientação de timbre, não medição**. A exceção é o `Monster (fiel ao
original)`, onde o acerto foi confirmado por correlação de +0,89 com o WAV
importado.

## Sets: 8 IRs por estilo musical

O pedal tem **8 bancos** — e o programa grava neles. Então um "set" é um estilo
inteiro ocupando os 8 bancos de uma vez. A aba **Impulso (IR)** tem a seção
**"Encher os 8 bancos com um estilo"**.

| set | o que traz |
|---|---|
| **Metal / High Gain** | Mesa, Diezel, V30 com SM57 e MD421, EVH 5150, ENGL |
| **Rock / Hard Rock** | Marshall com Greenback e T75, Bogner, Orange |
| **Blues / Soul / Country** | caixas JJ, Catharsis, Mesa Mark V |
| **Limpos / Britânicos / Violão** | Vox AC30 (três captações), Fender Twin e Bassman, Jensen |
| **Indie / Psych** | Fender Princeton (Mac DeMarco), Vox AC30 aberto (Tame Impala), Tweed Deluxe |
| **Nu Metal / Alt Metal** | Mesa Rectifier e Mark V, V30 fechado, EVH 5150, Diezel (Linkin Park, Skillet) |

Cada set traz **variedade de captação** de propósito (SM57 no centro, MD421,
borda do cone, ribbon) — não 8 variações da mesma coisa.

**Prova no hardware:** apliquei o set de Rock no pedal e conferi os 8 bancos
pela forma — semelhanças de **+0,98 a +1,00**, e restaurar deu **8/8**.

**Isto sobrescreve os 8 bancos.** O programa faz backup de cada um antes de
gravar.

**Verificação:** os 32 arquivos dos 4 sets carregam (testado), e cada set tem
exatamente 8 IRs sem repetição (há teste).

## Bug corrigido: WAVs de 24 bits saíam saturados

A leitura de 24 bits tratava o byte mais alto como magnitude, dando um valor
**256× maior** que o real. Os WAVs de 24 bits do pack mediam pico **512** em
vez de ~1,0.

Como o `de_wav` normaliza no fim, o erro passava despercebido — mas o IR saía
**saturado**, sem a dinâmica do original. A leitura agora é assinada, e todos
os arquivos medem pico coerente (0,95 depois da normalização).

De quebra, **WAVs em float32 agora são lidos** — antes davam erro
`unknown format: 3`, porque o módulo `wave` do Python não aceita esse formato.



## IR de usuário: leitura E gravação funcionam

**O CUBE Baby Unleashed envia IR próprio para o pedal — sem o CubeSuite.**

O formato do IR do pedal foi **decifrado no hardware**: `memory=0`, endereço
`0x69000`, 8 blocos de 4096 bytes (int32 + 1023 float32) = **8184 amostras,
170,5 ms a 48 kHz**. Confirmado por correlação de **+0,89** com o WAV que foi
importado pelo CubeSuite. Relatório em
[`docs/ir-de-usuario.md`](docs/ir-de-usuario.md).

**A leitura funciona** — a aba **Impulso (IR)** lê o IR de cada banco e exporta
como WAV.

**A gravação funciona** — medida no pedal: enviar um IR e reler deu
**semelhança +0,99** com o arquivo enviado, e restaurar deu **+1,0000**.

- **Cada bloco é um banco independente**, não um pedaço de um IR. Foi a
  hipótese do usuário, e estava certa: entre duas capturas, **7 blocos
  ficaram byte a byte idênticos** e só o do banco ativo mudou.
- O bloco do banco **ativo** muda entre leituras (é o espelho do que o pedal
  processa). Por isso comparar o **hash dos 32768 bytes** fazia parecer que
  a região era toda volátil e que a escrita não funcionava. Não era nada
  disso — era leitura de 8 bancos colados, verificada no lugar errado.
- **Verifique pela forma, não pelo hash.** A conferência usa correlação de
  amostras, que é estável.

### Como usar

Aba **Impulso (IR)**:

- **Ler o IR do pedal** — escolha o banco e leia; **Salvar como WAV** exporta
- **Enviar para o pedal** — escolha o banco, escolha um WAV, envie
- O programa faz **backup automático** do banco antes de gravar, e o botão
  **Restaurar** volta atrás

**Um alerta que continua valendo:** o IR de fábrica do banco escolhido é
substituído. O programa faz backup, mas não custa ter o seu também.

## Os 32 gabinetes de fábrica (lidos do CubeSuite oficial)

O CubeSuite oficial traz, na pasta `bin/`, o arquivo **`BOR.bin`** — 262.144
bytes = **32 blocos de 8.192 bytes**. Cada bloco começa com um nome ASCII
seguido da marca `patchCAB`, e depois ~4.075 amostras int16 (84,9 ms a 48 kHz)
que decaem como uma resposta de impulso.

Esses nomes foram **lidos byte a byte** e estão em `cubebaby/cabs_factory.py`:

| idx | gabinete | | idx | gabinete |
|---|---|---|---|---|
| 0 | TweedDeluxe | | 17 | Orange4X12 |
| 2 | Roland JC120 | | 18 | Diezel V30 |
| 3 | Marshall 1960B 1 | | 19 | Mesa Boogie |
| 8 | BOGNER Uberkab | | 23 | Matchless ES212 |
| 9 | ENGLProV30s | | **24** | **MesaRectifierV30** |
| 10 | Peavey 5150 | | 25–31 | 7 caixas de baixo |
| 13 | VoxAC30 1 | | | |

**A caixa do "Monster" está aqui:** o índice 24 é `MesaRectifierV30` — a Mesa
Rectifier 4×12 com Vintage 30 usada na gravação. A ajuda do programa (aba
**Gabinetes de fábrica**, com busca) mostra a lista inteira.

### O que isto NÃO prova

Duas coisas que seria fácil (e errado) afirmar:

1. **A ordem do arquivo não é a ordem do botão IR CAB do pedal.** O pedal tem
   8 posições; o arquivo tem 32 entradas e **nenhum campo** ligando uma à
   outra. Dizer "gabinete 8 = MesaRectifierV30" seria chute. O teste
   `test_indice_do_arquivo_nao_e_a_posicao_do_pedal` existe para travar isso.
2. **Não são as IRs da ROM do pedal.** São a biblioteca que o *programa* usa.

Os nomes servem para você **reconhecer e procurar** a caixa certa — e para
saber, com base em evidência, que a caixa do Monster existe no catálogo de
fábrica.

## O que foi descartado, e por quê

- **`bin/BBIF.bin` e `BCIF.bin`** (32.768 bytes): o tamanho bate com a ROM de IR
  (8.192 amostras float32 = 171 ms a 48 kHz), mas só **514 amostras** (10,7 ms)
  têm dado — o resto é `0xFFFFFFFF` puro. São IRs **truncadas de propósito**,
  não a ROM completa.
- **`bin/BFI.bin`, `EAE.bin`, `MICRORIG.bin`, `H8.bin`**: parecem float32, mas
  os valores são **rampas literais** (0.15, 0.2, 0.25, 0.3…). São **tabelas de
  interpolação**, não áudio.
- **`CubeSuite.exe`**: os 32 nomes **não** aparecem nele (0 ocorrências). Só no
  `BOR.bin`.
- **`bin/pdf/CUBE_BABY.pdf`**: é a página de atualização de firmware (confirma
  as 3 variantes de hardware A/B/C), não a tabela de gabinetes.

## Bug de teste corrigido

`tests/test_product.py` **não tinha bloco `__main__`** — rodá-lo imprimia
"ok" sem executar teste nenhum. As 55 funções estavam mudas. Agora o arquivo
descobre e chama todas as funções `test_*` automaticamente, e falha com
`SystemExit(1)` se alguma quebrar. Foi assim que apareceram três bugs reais:

- `Qt` não estava importado (`NameError` latente em `test_preset_monster_e_afinacao`)
- a ajuda passou a ter 6 abas, mas o teste ainda esperava 5

## Presets fiéis a gravações reais

O **Monster (fiel ao original)** foi reconstruído a partir do equipamento
**documentado** da gravação de "Monster" (álbum *Awake*, 2009):

| na gravação | no preset |
|---|---|
| Mesa/Boogie Dual Rectifier, canal **Red (Modern)** | pré-amp 8 (Mr Smith Dist) |
| Gibson Les Paul, humbucker de ponte | guitarra **Les Paul** |
| Caixa Mesa Rectifier **4×12 com Celestion V30** | gabinete **banco 8** (seu IR) |
| Boost Ibanez TS9 (gain baixo, level alto) | ganho 6 — a frente já vem apertada |
| Boss NS-2 noise gate | — (o pedal não tem gate) |
| **Drop D** | afinação **Drop D** |

Os knobs do Rectifier aparecem em reviews como gain 8 · bass 6 · mid 5 ·
treble 6,5 · presence 6,5 · reverb 1,5 (escala 0–10). O preset converte isso
para a escala do CUBE Baby — o ganho do pedal satura antes, então 8/10 vira 6/7.

**O riff é seco de propósito:** sem delay, sem modulação, reverb em 2. O
original também é — quem põe delay em riff de metal embola a definição. Para o
solo existe o **Monster (solo / ponte)**, com delay e reverb abertos.

### IR de terceiros (banco 8)

Cinco presets esperam um IR carregado **no banco 8** pelo CubeSuite. O IR que
mais combina com a gravação é uma **Mesa 4×12 com V30 captada por SM57**:

- `Brohymn-Mesa-4x12-SM57-V30-5` — Mesa 4×12, SM57, V30 (mais fiel)
- `Kalthallen 005d-SM57-V30-4x12` — 160 ms, 44,1 kHz (formato mais próximo do pedal)

O formato que o pedal aceita é curto: a ROM tem 32.768 bytes, o que em float32
dá ~8.192 amostras = **171 ms a 48 kHz**. IRs muito longos (o Brohymn tem 2 s)
precisam ser truncados pelo CubeSuite.

## Presets com afinação própria

Alguns presets só funcionam em afinação alternativa — o **Monster Riff** (Skillet)
é um deles: precisa de **Drop C**. Carregá-lo com a guitarra em Mi padrão faz o
riff sair nas notas erradas, e o usuário conclui que o preset é ruim quando o
problema é a corda.

Por isso o preset declara a afinação que espera, e a aba **Presets curados**
avisa na hora de escolher:

- **⚠ Precisa de Drop C** — sua guitarra está em Mi padrão. Troque no seletor da
  aba Afinador.
- **✓ Sua afinação já é a certa.**

A escolha do afinador e o preset falam a mesma língua: se você trocar a afinação
no afinador, o aviso muda sozinho.

## Afinador

Aba **Afinador**: liga a entrada de áudio, você toca uma corda solta e o
mostrador diz a nota e o quanto está fora — em **cents**, que é a unidade que
todo afinador usa (100 cents = um semitom; ±5 já é audível).

Como ler o mostrador:

- **Agulha no centro** = afinado.
- **Para a esquerda** = a corda está **frouxa**. Aperte o carrilhão.
- **Para a direita** = está **esticada**. Afrouxe.
- As seis bolinhas embaixo mostram qual corda solta está mais perto.

### Afinações

O seletor fica no topo da aba e a escolha é lembrada entre sessões.

| afinação | cordas | para que serve |
|---|---|---|
| Padrão | E A D G B E | a de fábrica; se não sabe qual usar, é esta |
| Drop D | D A D G B E | power chords com um dedo só |
| Meio tom abaixo | Eb Ab Db Gb Bb Eb | corda mais macia, som mais grave — blues e hard rock |
| D Standard | D G C F A D | tom inteiro abaixo, ainda com a forma padrão |
| Drop C | C G C F A D | metal moderno, grave apertado |
| Drop B | B F# B E G# C# | metal pesado; pede cordas grossas |
| Open G | D G D G B D | acorde de Sol nas cordas soltas — slide e rock clássico |
| Open D | D A D F# A D | acorde de Ré solto — slide e folk |
| DADGAD | D A D G A D | afinação celta, acordes suspensos |

As frequências são **calculadas do nome da nota**, não digitadas à mão — 82,41
escrito à mão em nove afinações é convite a erro, e um afinador que mostra a
nota errada é pior que nenhum.

O motor foi verificado com as **9 afinações × 6 cordas = 54 casos**: acerta
todos. Também trata **enarmonia** (Eb e D# são a mesma nota — sem isso, meio tom
abaixo dizia "errado" com a guitarra afinada) e mostra a nota na escrita da
afinação escolhida, não na do motor.

Duas decisões técnicas que valem saber:

**Por que autocorrelação e não FFT.** A guitarra tem harmônicos fortes — o 2º e
o 3º podem ser mais altos que a nota fundamental. Uma FFT apontaria para o
harmônico e diria "afinado" uma oitava acima. A autocorrelação acha o período
real da onda, então acerta a corda grave, que é onde o iniciante erra.

**Por que FFT então, afinal.** A autocorrelação direta é O(n²): 2048 amostras ×
660 lags = 1,3 milhão de multiplicações em Python puro, o que travava a
interface. A autocorrelação é calculada **via FFT** (ACF = IFFT(|FFT(x)|²)),
que é O(n log n) — uma análise leva ~30 ms, dentro do orçamento de 120 ms do
timer. A FFT é implementada à mão porque o projeto não usa numpy: puxar numpy
só por causa do afinador somaria ~15 MB ao executável.

O motor foi verificado com frequências geradas: acerta as **6 cordas soltas**,
mede desvios de afinação com erro abaixo de 8 cents, **não cai no harmônico** e
**não inventa nota a partir de ruído branco**.

## Latência (o que o Reaper faz de diferente)

Duas coisas faziam o monitor ter atraso alto:

1. **O programa forçava 44100 Hz.** Se a interface roda a 48 kHz, o Windows
   precisa resamplear, e o resampler enfileira buffer para conseguir converter.
   Esse buffer extra é latência e não aparece em lugar nenhum da interface.
   Agora o programa lê a taxa nativa do dispositivo (`preferredFormat`) e usa
   essa — a placa trabalha na velocidade dela, sem etapa no meio.

2. **Nenhum buffer era definido.** O Qt6 usa buffers padrão bem maiores que o
   necessário. Agora entrada e saída recebem `setBufferSize()` com o tamanho do
   bloco escolhido. Sem isso, sobra atraso mesmo com a taxa certa.

A aba Áudio tem um seletor **Latência**, com a mesma convenção do Reaper:

| bloco | latência @48 kHz | quando usar |
|---|---|---|
| 128 | ~3 ms | mínima; risco de estalo se a máquina não aguentar |
| 256 | ~5 ms | bem baixa |
| **512** | **~11 ms** | **mesma do Reaper (padrão)** |
| 1024 | ~21 ms | alta |
| 2048 | ~43 ms | máxima, segura em máquina fraca |

**Como ler o número:** ele é o piso que o programa controla — um bloco. O Reaper
mostra `latency: 10 ms` para 512 amostras, e é esse mesmo cálculo. O Windows
WASAPI em modo compartilhado ainda junta um buffer próprio que o Qt não deixa
ver, então o número real é um pouco maior que este nos dois programas. Se os
dois divergirem muito, a diferença está no motor do Windows, não no bloco.

**Se a interface tiver Direct Monitor** (monitor direto), use: o sinal não passa
por nenhum programa e a latência é praticamente zero. Só que aí você ouve a
guitarra crua, sem o pedal — é bom para afinar e para gravar limpo, e ruim para
ouvir o som do CUBE Baby.

## Gabinetes (IR) e pré-amps

O botão **IR CAB** do pedal tem 9 posições: a primeira desliga, e as outras 8 são
caixas. **Qual é cada número depende do firmware**, e existem duas listas:

| # | CUVAVE (firmware novo) | M-VAVE (firmware antigo) |
|---|---|---|
| 0 | Desligado | Desligado |
| 1 | Line 6 Vetta 2×12 | Fender Pro Princeton 1×12 |
| 2 | Marshall 1960AV 4×12 | Fender Pro Princeton II 1×12 |
| 3 | Marshall 1960A T75 4×12 | Fender Pro Junior 1×10 |
| 4 | VHT Deliverance 2×12 | GH Dual Rectifier 4×12 |
| 5 | Soldano 2×12 | Line 6 Vetta 1×10 |
| 6 | Peavey 5150 + Mesa 4×12 | Soldano 2×12 |
| 7 | JSX KT77 + Mesa Stiletto 4×12 | Mesa Standard 4×12 |
| 8 | Diezel V30 SM57 4×12 | Marshall 1960A & B 2×12 |

**Como descobrir o seu:** o preset B de fábrica usa "Soldano 2×12 V30". Na lista
nova o Soldano é a **5**, na antiga é a **6**. Confira qual das duas bate.

A lista usada fica nas preferências e muda o que aparece no controle Cabinet.

### Os desenhos

- **Gabinete** — a interface desenha a *planta* da caixa: número e tamanho dos
  alto-falantes (um 10" é visivelmente menor que um 12") e o arranjo 1, 2 ou 4.
  É ilustração feita a partir das especificações, **não é foto** — não usamos
  imagem de terceiros no programa.
- **Pré-amp** — os 9 pré-amps (Power-Zone Clean, Day Tripper OD, Mr Smith Dist…)
  são nomes da CUVAVE e **não têm imagem pública**. Em vez de inventar um
  amplificador falso, o programa mostra um **diagrama de caráter**: duas barras,
  brilho (T) e sujeira (G). Diz a mesma coisa da descrição em texto, de relance.

### IRs

`cubebaby/cabinets.py` gera 8 IRs **sintetizados** em `~/CUBEBabyUnleashed/IRs/`
(180 ms, PCM 16-bit estéreo, o formato que o CubeSuite lê). São aproximações
construídas com a resposta em frequência e a cauda de cada tipo de caixa — úteis
para experimentar, mas **não são os IRs de fábrica**.

Os originais estão na ROM do pedal (`0x71000`, segundo a documentação do
cuvave-midi). Extraí-los exigiria implementar a leitura de IR via SysEx, que é a
mesma família de operação que escreve na flash — por isso continua fora do
escopo.

## Ainda não tem
- Upload/exportação de IR (.wav): mexe na flash do pedal, fica pra uma segunda etapa.
- Atualização de firmware: de propósito, por ser a operação mais arriscada.
- Gravação multitrilha / editar áudio: isto aqui é um gravador de takes para
  comparar presets, não uma DAW. Para editar de verdade, use "Ouvir em outro
  programa..." e abra num editor.

## Testes
```
.venv\Scripts\python.exe tests\test_protocol.py   # codec SysEx
.venv\Scripts\python.exe tests\test_ui_smoke.py   # UI offscreen + voicing
.venv\Scripts\python.exe tests\test_audio.py      # PCM, WAV, VU e a aba Áudio
.venv\Scripts\python.exe tests\test_dsp.py        # gate e normalizador
.venv\Scripts\python.exe tests\test_product.py    # preferências, onboarding, atalhos
.venv\Scripts\python.exe tests\shot.py            # screenshots em shots/
```

## Estrutura
```
cubebaby/protocol.py    SysEx: codificação 7-bit, envelope, checksum, presets, endereços
cubebaby/client.py      conexão rtmidi (CubeBabyClient) + pedal simulado
cubebaby/presetfile.py  .json de presets e biblioteca
cubebaby/guitars.py     perfis de guitarra e o viés de voicing de cada uma
cubebaby/presets_lib.py biblioteca curada (assinatura, gêneros, guitarra de referência)
cubebaby/guides.py      dicas de iniciante: tooltips, roteiro e o que é cada controle
cubebaby/audio.py       monitor ao vivo, gravação em WAV e reprodução
cubebaby/dsp.py         gate de ruído e normalização de volume
cubebaby/meter.py       medidor de nível reutilizável
cubebaby/cabinets.py    as 9 posições do IR CAB, por firmware, e gerador de IR
cubebaby/art.py         desenho das caixas e diagrama de caráter dos pré-amps
cubebaby/theme.py       tokens de cor/espaçamento e a folha de estilo
cubebaby/settings.py    preferências em JSON, com escrita atômica
cubebaby/onboarding.py  telas de primeira execução
cubebaby/about.py       janela "Sobre" e créditos de licença
cubebaby/ui.py          janela Qt
tests/                  protocolo, UI, áudio, DSP, produto e screenshots
```

## Publicar este projeto

Planejando distribuir sem fins lucrativos, com doações? Isto é o que falta resolver.
**Não publique antes de ler esta seção** — há um item que não é opcional.

### 1. Licença: GPL-3.0, e não é escolha sua

`cubebaby/protocol.py` foi reimplementado a partir de engenharia reversa cuja
referência inclui o **cuvave-midi, sob GPL-3.0**. A GPL é copyleft: obra
derivada tem de sair sob GPL, e o código-fonte correspondente completo precisa
estar disponível para quem recebe o binário.

Portanto: **não dá para publicar como MIT, Apache, BSD ou "livre de swirling
vazios"**. Tem de ser GPL-3.0-or-later. Doações são compatíveis com a GPL — a
GPL proíbe cobrar pela licença, não receber doação.

Antes de publicar:
- [ ] Substituir o `LICENSE` pelo texto **verbatim** de https://www.gnu.org/licenses/gpl-3.0.txt
- [ ] Preencher a URL de origem no `NOTICE` (hoje tem um placeholder)
- [ ] Publicar o repositório junto com o `.exe`, com o link visível
- [ ] Confirmar a licença do **preset-studio** (TypeScript) e atribuí-la no `NOTICE`

### 2. Qt/PySide6 (LGPL-3.0) dentro do .exe

Empacotar PySide6 num `.exe` e distribuir é permitido pela LGPL, mas exige:
- [ ] Uma página "about" / avisos de licença do Qt **dentro do executável** —
      hoje o build não inclui isso. É uma lacuna real de conformidade.
- [ ] Oferecer o código-fonte do PySide6 (ou o instalador do Qt) para quem
      recebe o `.exe`, para que possa substituir a biblioteca.

### 3. Marca registrada — uso nominativo

O programa se chama **CUBE Baby Unleashed**. Isso é **uso nominativo** de marca
registrada: nomear a marca para dizer com qual produto o programa é compatível.
É o mesmo que fazem "Katana Editor", "Helix Editor" e afins, e é uso legítimo.

O que mantém isso no caminho certo é o que o programa já faz:

- Declara independência em todas as janelas (rodapé) e no Sobre.
- Não usa o logotipo do fabricante em lugar nenhum.
- O nome do aparelho aparece como referência de compatibilidade, não como
  marca do software: "CUBE Baby Unleashed", não "CUBE Baby" sozinho.
- Não há vínculo, patrocínio, endosso ou relação com M-VAVE, CUVAVE ou Sinco
  em nenhuma página.

Se um dia o projeto crescer muito, vale uma consulta jurídica: não sou advogado,
e a fronteira entre uso nominativo e sugestão de afiliação é um julgamento de
caso. O que importa é manter a declaração visível e não usar o logotipo.

### 4. Coisas que ainda não são um produto pronto

- O `.gitignore` existe, mas **8.076 arquivos do `.venv` continuam versionados**
  no git. Rode `git rm -r --cached .venv build dist` antes do primeiro push —
  senão o repositório público leva 659 MB de arquivos de terceiros.
- Não há CI nem testes rodando automaticamente.
- O `.exe` é gerado com PyInstaller mas não testado em máquina limpa.

---

## Créditos
O protocolo vem da engenharia reversa comunitária: cubecontrol (MIT) e cuvave-midi (GPL-3.0, usado só como referência).
Se for distribuir o programa, confira as licenças desses projetos.
