# Engenharia reversa do CubeSuite (como o IR chega ao pedal)

Investigação do `CubeSuite.exe` oficial (3.945.984 bytes, PE x86, Qt5, MSVC)
feita com **Ghidra 12.1.4** via **REA**. O objetivo era descobrir o caminho que
um IR de usuário percorre até a flash do CUBE Baby — e se dava para fazê-lo sem
passar pelo CubeSuite.

Tudo abaixo está marcado como **observado** (lido do binário) ou **inferido**.
O que não deu para provar está listado no fim, como desconhecido.

## Ferramentas usadas

| | |
|---|---|
| Ghidra | 12.1.4 (NSA, Apache-2.0), headless |
| JDK | Temurin 21.0.12.1 (necessário para o Ghidra) |
| REA | 6.4.0 (`rea search`, `rea xrefs`, `rea function`) |
| SHA-256 do alvo | `0e0183fd6dc1b347534c9ce1e3677ecda2a6ae77fe3da8d6314d43c7c2cfd2e6` |

O binário está **stripped**: `rea search --kind procedures` devolve **0**
funções nomeadas para os termos do domínio (`CubeSugarIR`, `Wav`, `Flash`,
`Amp`). Os poucos acertos de `IR` e `Cab` são símbolos de DLL do Qt
(`QDir::count`, `QWidget::redirected`) e tabelas de unwind do MSVC — ruído de
coincidência textual, não funções do aplicativo. Por isso o caminho foi pelas
*strings* e pelas *referências cruzadas* a elas.

## Observado: a classe que cuida do IR

O executável carrega metadados de MOC do Qt (nome de classe e slots), o que
entrega os nomes reais sem precisar adivinhar:

| endereço | string |
|---|---|
| `0x584cc0` | `CubeSugarIR` |
| `0x7591f0` | `CCubeSugarIREditDlg` |
| `0x75a524` | `.?AVCCubeSugarIREditDlg@@` (RTTI) |
| `0x584344` | `1OnOpenIRFile()` |
| `0x584380` | `1OnIrFileSelected(QListWidgetItem*)` |

**Leitura:** existe a classe `CCubeSugarIREditDlg` ("CubeSugar IR Edit Dialog").
O **formato interno do IR chama-se `CubeSugarIR`**. Os dois slots do Qt são
`OnOpenIRFile()` (abrir o seletor) e `OnIrFileSelected(QListWidgetItem*)`
(reagir à escolha na lista).

### A interface do diálogo (strings observadas, `0x5840c8`–`0x5859e8`)

```
Factory IR  /    Factory IR          lista dos IRs de fábrica
Open IR Files  /    Open IR Files    abre arquivo(s) .wav
Import IR   /  Import IR to          envia para um destino
Revert Factory IR                    restaura o de fábrica
Save IR  /    Save IR                grava
Please select a IR wav sample file   validação
IR cabinets simulation editor        título
Ir cab · irCab · irCabFine · IRBox · IR Box · IR Edit · Edit IR
m_saveIrAndEq · ir_on · m_irlv       nomes de membro (variáveis da classe)
```

## Observado: o parser de WAV (função `0x508250`, 737 bytes)

Valida o arquivo **nesta ordem**, abortando no primeiro erro:

1. flag `RIFF`
2. formato `WAVE`
3. chunk `format` (procura o literal `WAVEfmt `)
4. chunk `data`

Mensagens: `Wave file '%s' has no RIFF flag` / `no WAVE flat` /
`no format chunk` / `no data chunk`.
Em outro ponto: `File open error! Only PCM wav file is supportted !`

**Leitura:** só entra **WAV PCM**. Nada de float, MP3 ou IR em outro container.

## Observado: o mapa da flash vem de CONFIGURAÇÃO, não do código

A função de validação de endereço (`0x5102f0`, 1436 bytes — a que contém
`FLASH %d`) lê as chaves de um `QSettings`:

```
/TYPE
/Start Address
/End Address
/Sector Size
```

E as mensagens de erro correspondentes:

```
%s address not follow the last flash
FLASH start address is empty
FLASH end address is empty
All FLASH should be same type!
NAND_FLASH_MAX_BLOCK need enlarge!
```

O binário também chama `QCoreApplication::applicationDirPath()`, ou seja, lê um
arquivo de configuração **ao lado do executável**.

**Isto explica um fato que me incomodava:** o comando SysEx `MEM_WRITE` (0x22)
**não aparece como literal** no executável (0 ocorrências), enquanto `ERASE`
(0x24) e `MEM_READ` (0x23) aparecem. O endereço de escrita **não é constante** —
é montado em tempo de execução a partir da configuração.

## Observado: a rotina de gravação (função `0x505530`, 1484 bytes)

Pseudocódigo relevante (trecho, traduzido para legibilidade):

```c
/* percorre uma TABELA de segmentos {?, endereco, tamanho} */
local_1c = 0x50;                      /* contador de setores */
do {
    segmento = &tabela[i];
    if (!erase_sector(segmento[0], segmento[1])) {
        log("Erase sector failed,address=0x%.8X", segmento[1]);
        goto falha;
    }
    total += segmento[2];
    QProgressBar::setValue(...);      /* barra de progresso na tela */
    ...
} while (...);

if (espaco_livre < necessario) {
    log("Space not enough !");
    goto falha;
}
```

Strings da mesma função:
`/Config/UpdateNotFinishedPath`, `File not match the connected device,please
confirm`, `Space not enough !`.

**Leitura:** o upload é um **programa de flash por setores**: para cada
segmento da tabela, apaga o setor e escreve, com barra de progresso. Não é um
comando único.

### Quem chama a rotina de gravação

| chamador | tamanho |
|---|---|
| `0x5029d0` | 842 bytes |
| + 2 outros | |

E a função de validação de endereço é chamada por `0x505320` (506 bytes).

## Inferido (com base no observado)

1. **O IR não vai por um SysEx "de IR".** Vai por uma sequência de
   apagar-setor/escrever, controlada por uma tabela de segmentos e uma
   configuração de endereços. É o mesmo mecanismo de uma atualização de
   firmware — e faz sentido: o firmware `.up` que acompanha o CubeSuite
   (`bin/up/cubebaby_A_20220706.up`) tem cabeçalho `CONFIG` com o endereço
   `0x00834000`, bem acima da área de IR `0x71000`.
2. **Replicar isso fora do CubeSuite é possível, mas não é um fim de semana.**
   Seria preciso: (a) saber os valores de `/TYPE`, `/Start Address`,
   `/End Address`, `/Sector Size` para o CUBE Baby; (b) reproduzir a conversão
   WAV → `CubeSugarIR`; (c) emitir a sequência de ERASE/WRITE com os mesmos
   endereços.

## Desconhecido — e por que não vou chutar

| pergunta | situação |
|---|---|
| O que é exatamente o formato `CubeSugarIR`? | Só o **nome** foi observado. O layout de bytes (cabeçalho, taxa, nº de amostras) **não** foi localizado. |
| Quais os valores de `/Start Address`, `/End Address`, `/Sector Size`? | O código os **lê**, mas os valores vêm de configuração. Não estão no `.exe` nem no `AppConfig.ini` (que só tem `SmcMixerExportDir`, `SmcMixerImportDir`, `ConvIRDir`). Provavelmente vêm do descritor do aparelho ou do `.up`. |
| Quantas amostras o pedal guarda? | Deduzido ~8.192 (32.768 bytes ÷ 4) a partir do tamanho da ROM `0x71000`–`0x69000`, **não confirmado**. O `bin/BOR.bin` mostrou IRs de fábrica com **4.075 amostras int16 = 84,9 ms**, que é outra coisa. |
| A conversão WAV → formato do pedal | **Não localizada** como função isolada. Provavelmente dentro do fluxo do `CCubeSugarIREditDlg`. |

## Consequência prática

O upload de IR **continua sendo feito pelo CubeSuite**. O que esta investigação
entrega de concreto é o **entendimento do caminho** — e a confirmação de que
não existe um atalho simples (um SysEx de IR) que eu pudesse implementar sem
risco.

Isso reforça a decisão que já estava no projeto: **a leitura da ROM por
`MEM_READ` é o próximo passo seguro**, porque não escreve nada. Com o dado real
do pedal em mãos, o formato `CubeSugarIR` deixa de ser incógnita — e só então
faria sentido falar em escrever.

## Reproduzir esta análise

```bash
# variáveis (o Ghidra exige Java)
export JAVA_HOME="$HOME/Downloads/rea-tools/jdk-21.0.12.1+1"
export GHIDRA_INSTALL_DIR="$HOME/Downloads/rea-tools/ghidra_12.1.4_PUBLIC"

EXE="C:/Users/ntende/Downloads/CubeSuite/CubeSuite/CubeSuite.exe"
SNAP="$HOME/Downloads/rea-tools/cubesuite.snap"

rea search "$EXE" "CubeSugarIR" --snapshot "$SNAP"        # nome do formato
rea xrefs  "$EXE" 0x59328c --snapshot "$SNAP"             # quem escreve na flash
rea function "$EXE" 0x505a55 --snapshot "$SNAP"           # rotina de gravação
```

Os artefatos brutos (JSON de evidência do REA) estão em
`~/Downloads/rea-tools/`: `strings.json`, `xrefs.json`, `procs.json`,
`fn_*.json`.
