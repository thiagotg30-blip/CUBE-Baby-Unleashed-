# O que a leitura no pedal real revelou

Sessão com o pedal **SINCO-CubeBaby** conectado, usando só `MEM_READ` e
`IDENTITY` (nenhuma escrita). Tudo abaixo é **observado no hardware**.

## O espaço de endereços

| `memory` | o que é | evidência |
|---|---|---|
| **5** | **o espaço real e endereçável** | os 3 slots em `0x00/0x10/0x20` com valores distintos e coerentes |
| 4 | floats de parâmetro | em `0x764`/`0x768` devolve `float32` (`0.7, 0.659, 0.814, 0.79`) — bate com as chaves `IR usable`/`IR dist` do CubeSuite |
| 0, 1, 2, 3, 6, 7 | **sintéticos, não são ROM** | o 1º byte é `(const − endereço/256) & 0xFF`: muda com o endereço *pedido*, não é dado do aparelho |

Os `memory` 1, 2, 3, 6, 7 devolvem um template com `?? 65 42 61 62 79 20 20 20 20 20 01 13 14 15 16 17 18 19 1e`
(`..eBaby     ..`) em qualquer endereço. O `0x65` é o eco do pedido.

## O banco de presets (memory=5, endereço 0)

48 bytes = 3 slots de 16, na ordem de `PARAM_NAMES`. Lido do pedal real:

```
0x00  slot A  06 06 01 00 22 59 12 28 02 08 01 00 01 00 00 00
0x10  slot B  01 07 0f 03 21 7d 13 05 04 08 01 01 01 00 00 00
0x20  slot C  07 03 0d 06 34 39 14 0c 05 07 01 00 01 00 00 00
```

Decodifica com `decode_preset_bank()` sem ajuste. **O `read_bank()` do projeto
estava correto.**

## Não há área de IR legível por MEM_READ

- A varredura de `0x68000`–`0x71000` (que a análise do CubeSuite apontou como
  área de IR) devolve **o mesmo template sintético**, não IR.
- A pista `IR RAM 0x0f68` do CubeSuite **não se confirmou**: em `memory=5`
  essa região é zero.
- Conclusão: a leitura da ROM de IR por SysEx **não é acessível por esse
  caminho**. O upload continua dependendo do CubeSuite.

## Limites medidos — e o travamento

| pedido | resultado |
|---|---|
| 64 bytes | sempre respondeu, em todo memory/endereço testado |
| 256 / 512 / 1024 / 2048 / 4096 (memory=1) | responderam |
| **512 bytes (memory=4, `0x700`)** | **o pedal PAROU de responder** |

O travamento: o pedido foi enviado e **nunca houve resposta** — nem a ele, nem
às identificações seguintes. O pedal só voltou **depois de reconectar o cabo
USB**. Não houve escrita nenhuma; os presets ficaram intactos.

Causa no código: `_request()` enviava e esperava, sem caminho de abortar ou
reiniciar. **Corrigido:**

- `MAX_READ_BYTES = 64` — recusa antes de enviar, com mensagem explicando
- `ping()` — pergunta se o pedal está vivo sem levantar exceção
- `_recuperar()` — espera progressiva (0.3s, 1s, 2.5s), confirma que voltou, e
  se não voltar diz **exatamente o que fazer** (reconectar o USB)

## Bug de conexão corrigido

`guess_port()` escolhia a **saída 0 = "Microsoft GS Wavetable Synth"** em vez do
pedal (`USB-Midi 1`), e a conexão falhava sempre num Windows com esse
sintetizador na lista. Agora há uma lista de portas a evitar.

## Reproduzir

```bash
.venv/Scripts/python.exe -c "
from cubebaby import client as C
ins, outs = C.list_ports()
p = C.CubeBabyClient(); p.connect(C.guess_port(ins), C.guess_port(outs))
print(p.device_name)                      # SINCO-CubeBaby
print(p.read_memory(5, 0x0, 48).hex(' ')) # os 3 slots
p.disconnect()"
```
