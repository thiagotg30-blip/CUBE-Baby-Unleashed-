# CUBE Baby Unleashed

[![Licença: GPL-3.0](https://img.shields.io/badge/licen%C3%A7a-GPL--3.0-orange)](LICENSE)
[![Windows 64-bit](https://img.shields.io/badge/Windows-64--bit-blue)](https://github.com/thiagotg30-blip/CUBE-Baby-Unleashed-/releases/latest)
[![Versão 4.0.0](https://img.shields.io/badge/vers%C3%A3o-4.0.0-green)](https://github.com/thiagotg30-blip/CUBE-Baby-Unleashed-/releases/latest)

**Editor de timbre para o pedal M-VAVE/CUVAVE CUBE Baby.** Sem navegador, sem CubeSuite.

Projeto independente, **não afiliado** à M-VAVE, CUVAVE ou Sinco.

---

## Baixar e usar

**Não precisa instalar nada.** Não precisa de Python, nem de programa nenhum.

1. Baixe o arquivo **[`CUBEBabyUnleashed-4.0.0-win64.zip`](https://github.com/thiagotg30-blip/CUBE-Baby-Unleashed-/releases/latest)** (53 MB)
2. **Extraia** a pasta em qualquer lugar (ex: na Área de Trabalho)
3. Conecte o pedal CUBE Baby no computador com o cabo USB
4. Clique duas vezes em **`CUBEBabyUnleashed.exe`**

> ⚠️ **Feche o CubeSuite antes.** Dois programas não podem usar a porta MIDI do pedal ao mesmo tempo.

> ℹ️ Não rode de dentro do `.zip` — extraia primeiro. O programa precisa da pasta `_internal` que vem junto.

**Só quer ver como é a interface, sem o pedal?** Abra o Prompt de Comando na pasta e digite:

```cmd
CUBEBabyUnleashed.exe --sim
```

---

## O que ele faz

- 🎛️ **Edita os 13 controles do pedal em tempo real** — pré-amp, gain, tom, delay, reverb, modulação, gabinete, volume
- 🎸 **38 presets curados** — cada um com assinatura sonora, gênero e guitarra de referência
- 🎚️ **Adapta o timbre à sua guitarra** — escolha o modelo no topo e todos os slots se ajustam
- 📦 **Envia IR próprio para o pedal** — sem depender do CubeSuite (validado no hardware, correlação +0,99)
- 🎵 **6 sets de 8 IRs por estilo** — metal, rock, blues, limpos, indie/psych, nu metal
- 🎤 **Ouve e grava a guitarra** — monitor ao vivo, gravação WAV, gate + normalizador
- 🎼 **Afinador** com 8 afinações (padrão, meio tom abaixo, Drop D, etc.)
- 🌎 **Três idiomas** — português, inglês e espanhol
- 💾 **Backup automático** antes de qualquer gravação no pedal

---

## Como usar (iniciante)

1. **Conecte o pedal** por USB e clique em **Conectar**.
2. Escolha sua **guitarra** no topo — o programa adapta todos os timbres.
3. Vá em **Presets curados**, busque pelo som que você quer (ex: "rock", "blues", "metal").
4. Clique em **Carregar adaptado** → o timbre vai para o slot A.
5. Ajuste à vontade na aba **Pedal** (modo Iniciante mostra só o que importa).

**Não sabe o que escolher?** Clique em **? Ajuda** — o guia foi escrito para quem nunca usou um pedal.

---

## Onde ficam seus dados

Tudo em `%USERPROFILE%\CUBEBabyUnleashed`:

```
CUBEBabyUnleashed/
├── biblioteca/      presets que você salvou
├── backups/         backup automático antes de gravar no pedal
├── gravacoes/       takes em WAV
├── IRs/             IRs lidos/gerados
├── preferences.json suas preferências
├── pedal.log        registro do que foi enviado/recebido (hex)
└── crash.log        só existe se algo der errado
```

---

## Apoiar o projeto

O CUBE Baby Unleashed é **gratuito e de código aberto (GPL-3.0)**. Se ele ajudou você a conseguir seu timbre, considere apoiar — as doações vão para os meus estudos.

| método | |
|---|---|
| **Pix** | chave `4b10f63b-304f-4d0c-a205-de386c9d2e9e` |
| **Bitcoin** | `bc1qhaw7tvd8ajsx7wyp44rs784z7k84e4jzqrw64n` |
| **Ko-fi** | https://ko-fi.com/tg_macario |

Há uma aba **"Apoiar o projeto"** dentro do programa com tudo pronto para copiar.

---

## Para desenvolvedores

<details>
<summary>Rodar a partir do código-fonte (clique para abrir)</summary>

Precisa do **Python 3.12** (o 3.14 ainda não tem pacote pronto do `python-rtmidi`).

```cmd
winget install Python.Python.3.12
```

Depois é só dar duplo clique:

| arquivo | o que faz |
|---|---|
| **`run_debug.bat`** | cria o ambiente, instala tudo e abre o programa com console |
| **`build_exe.bat`** | gera o pacote em `dist\CUBEBabyUnleashed\` |

Ou, direto:

```cmd
.venv\Scripts\python main.py --sim
```

### Testes

```cmd
.venv\Scripts\python tests\test_product.py
.venv\Scripts\python tests\test_protocol.py
```

119 testes em 5 suítes. Rode com `QT_QPA_PLATFORM=offscreen` para os testes de UI.

### Documentação técnica

| documento | conteúdo |
|---|---|
| [`docs/ir-de-usuario.md`](docs/ir-de-usuario.md) | formato do IR de usuário, decifrado no hardware |
| [`docs/engenharia-reversa-cubesuite.md`](docs/engenharia-reversa-cubesuite.md) | engenharia reversa do CubeSuite.exe (Ghidra + REA) |
| [`docs/hardware-achados.md`](docs/hardware-achados.md) | achados medidos no pedal real |
| [`docs/README-completo.md`](docs/README-completo.md) | manual completo |

</details>

---

## Licença

**GPL-3.0-or-later** — veja [LICENSE](LICENSE) e [NOTICE](NOTICE).

A licença **não é uma escolha livre**: o protocolo SysEx foi reimplementado a partir de engenharia reversa comunitária que inclui material sob GPL-3.0. O projeto inteiro precisa ser GPL.

Doações são permitidas e não conflitam com a GPL.

---

## Contribuir

Relatos de bug e sugestões são bem-vindos em [Issues](https://github.com/thiagotg30-blip/CUBE-Baby-Unleashed-/issues). Se for testar no hardware, **sempre** faça backup dos presets antes — o programa faz backup automático, mas dois backups não fazem mal.
