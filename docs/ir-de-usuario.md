# O IR de usuário do CUBE Baby — formato decifrado

Descoberto **no hardware** (pedal `SINCO-CubeBaby`, firmware A 2022-07-06), só
com leitura. O módulo que implementa isto é `cubebaby/irfile.py`.

## Onde fica

| | |
|---|---|
| `memory` | **0** (não é o 5, que é o banco de presets) |
| endereço | **`0x69000`** |
| tamanho | **32768 bytes** |

Foi essa comparação que localizou a área: ela estava **32768 bytes de zero**
antes do import e cheia depois.

## O formato

**8 blocos de 4096 bytes — e cada bloco é um BANCO independente.** Cada bloco:

```
+0     int32 LE      marcador estrutural
+4     1023 × float32 LE    amostras
```

Um banco guarda um IR **completo** de **1023 amostras = 21,3 ms a 48 kHz** —
não um pedaço de um IR maior.

### A prova de que são 8 bancos

Comparando duas capturas (antes e depois de um import pelo CubeSuite):

| bloco | resultado |
|---|---|
| 1 (o ativo) | **mudou** |
| 2 a 8 | **byte a byte idênticos** |

Se fossem um IR fatiado, o bloco 2 casaria com o *trecho 2* do WAV. Ele casa
com o **início** — ou seja, recomeça. São bancos distintos.

## A escrita funciona

Gravando um IR novo no banco ativo e relendo:

| comparação | resultado |
|---|---|
| semelhança com o IR **enviado** | **+0,99** |
| semelhança com o **anterior** | −0,10 |
| restaurar o original | **+1,0000** |

## O erro que custou tempo (e a correção)

Eu lia os **32768 bytes de uma vez** e comparava o **hash** do bloco inteiro.
O bloco do banco **ativo** muda entre leituras (é o espelho do que o pedal
processa), então o hash nunca batia — e parecia que a região era toda volátil
e que a escrita não funcionava.

Não era nada disso:

- os blocos **inativos** são estáveis byte a byte;
- a **forma** do IR é estável mesmo no bloco ativo.

**Regra:** leia o bloco do banco (não a área inteira) e verifique pela forma
(correlação), nunca pelo hash dos bytes crus.

O crédito da virada é do usuário, que sugeriu que cada bloco fosse um banco.
Era.

## Como foi confirmado (não por dedução)

O usuário importou `6 - Brohymn-Mesa-4x12-SM57-V30-5.wav` (96001 amostras,
48 kHz, 2000 ms) pelo CubeSuite. O IR reconstruído da memória do pedal deu:

| comparação | correlação |
|---|---|
| **Brohymn-Mesa-4x12-SM57-V30-5** | **+0,89** |
| VOX AC30 (2º colocado) | +0,18 |
| os outros 6 da pasta | entre −0,39 e −0,03 |

A correlação é de forma, não de escala: o pedal guarda o WAV **reamostrado para
48 kHz, normalizado e cortado em 170 ms**. O pico cai no mesmo lugar e a
inversão de fase aparece igual nas duas curvas.

## Ler e gravar

```python
from cubebaby import client as C, irfile as IR

ins, outs = C.list_ports()
p = C.CubeBabyClient(); p.connect(C.guess_port(ins), C.guess_port(outs))

# ler um banco (1..8)
ir = IR.ler_banco(p, 8)
print(ir.resumo())                    # "banco 8: 21.3 ms · pico ..."

IR.para_wav(ir, "banco8.wav")         # exportar

# enviar um WAV novo para um banco
novo = IR.de_wav("meu_ir.wav")        # trata o WAV como o pedal espera
novo.banco = 8
IR.gravar_banco(p, novo)              # grava só o bloco do banco 8

# conferir pela FORMA (não pelo hash)
lido = IR.ler_banco(p, 8)
print(IR.correlacao(lido.samples, novo.samples))   # ~ +0,99

p.disconnect()
```

## Cuidados

- **O IR de fábrica do banco escolhido é substituído.** Faça backup antes — a
  interface faz automaticamente, mas guarde o seu também.
- **Leia por banco, nunca a área inteira.** Ler os 32768 bytes mistura os 8
  bancos e faz parecer que tudo muda.
- **Verifique pela forma.** O hash dos bytes crus do bloco ativo não serve
  como identidade.
