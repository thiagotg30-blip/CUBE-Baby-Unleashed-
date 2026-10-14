"""Internacionalização (i18n) — PT-BR (padrão), EN, ES."""

IDIOMAS = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
}
IDIOMA_PADRAO = "pt"

TRADUCOES = {
    # ---- abas principais ----
    "aba_tocando":      {"pt": "Tocando",        "en": "Playing",       "es": "Tocando"},
    "aba_pedal":        {"pt": "Pedal",          "en": "Pedal",         "es": "Pedal"},
    "aba_presets":      {"pt": "Presets curados","en": "Curated Presets","es": "Presets curados"},
    "aba_audio":        {"pt": "Áudio",          "en": "Audio",         "es": "Audio"},
    "aba_afinador":     {"pt": "Afinador",       "en": "Tuner",         "es": "Afinador"},
    "aba_ir":           {"pt": "Impulso (IR)",   "en": "Impulse (IR)",  "es": "Impulso (IR)"},
    "aba_biblioteca":   {"pt": "Biblioteca",     "en": "Library",       "es": "Biblioteca"},
    "aba_ajuda":        {"pt": "Ajuda",          "en": "Help",          "es": "Ayuda"},
    "aba_apoiar":       {"pt": "Apoiar o projeto", "en": "Support the project", "es": "Apoyar el proyecto"},

    # ---- cabeçalho / conexão ----
    "conectar":         {"pt": "Conectar",       "en": "Connect",       "es": "Conectar"},
    "desconectar":      {"pt": "Desconectar",    "en": "Disconnect",    "es": "Desconectar"},
    "atualizar_portas": {"pt": "Atualizar portas","en": "Refresh ports", "es": "Actualizar puertos"},
    "modo_simulado":    {"pt": "Modo simulado",  "en": "Simulated mode","es": "Modo simulado"},
    "desconectado":     {"pt": "desconectado",   "en": "disconnected",  "es": "desconectado"},
    "conectado":        {"pt": "conectado",      "en": "connected",     "es": "conectado"},
    "entrada":          {"pt": "Entrada",        "en": "Input",         "es": "Entrada"},
    "saida":            {"pt": "Saída",          "en": "Output",        "es": "Salida"},
    "minha_guitarra":   {"pt": "Minha guitarra:", "en": "My guitar:",    "es": "Mi guitarra:"},

    # ---- rodapé ----
    "ajuda_btn":        {"pt": "? Ajuda",        "en": "? Help",        "es": "? Ayuda"},
    "projeto_independente": {"pt": "Projeto independente", "en": "Independent project", "es": "Proyecto independiente"},
    "nao_afiliado":     {"pt": "não afiliado a M-VAVE, CUVAVE ou Sinco.", "en": "not affiliated with M-VAVE, CUVAVE or Sinco.", "es": "no afiliado a M-VAVE, CUVAVE o Sinco."},
    "backup_presets":   {"pt": "Faça backup dos seus presets antes de gravar no pedal.", "en": "Back up your presets before writing to the pedal.", "es": "Haz una copia de seguridad de tus presets antes de escribir en el pedal."},
    "pedal_conecte":    {"pt": "Conecte o pedal primeiro (ou use o Modo simulado).", "en": "Connect the pedal first (or use Simulated mode).", "es": "Conecta el pedal primero (o usa el Modo simulado)."},
    "nenhuma_porta":    {"pt": "Nenhuma porta MIDI encontrada. Plugue o pedal e clique em Atualizar portas.", "en": "No MIDI port found. Plug the pedal and click Refresh ports.", "es": "No se encontró ningún puerto MIDI. Conecta el pedal y haz clic en Actualizar puertos."},

    # ---- PedalTab ----
    "ler_do_pedal":     {"pt": "Ler do pedal",   "en": "Read from pedal","es": "Leer del pedal"},
    "importar_arquivo": {"pt": "Importar arquivo...", "en": "Import file...", "es": "Importar archivo..."},
    "exportar_slot":    {"pt": "Exportar este slot...", "en": "Export this slot...", "es": "Exportar este slot..."},
    "salvar_biblioteca":{"pt": "Salvar na biblioteca", "en": "Save to library", "es": "Guardar en biblioteca"},
    "modo":             {"pt": "Modo:",           "en": "Mode:",          "es": "Modo:"},
    "marque_controles": {"pt": "Marque para ver todos os controles do pedal", "en": "Check to see all pedal controls", "es": "Marque para ver todos los controles del pedal"},
    "iniciante":        {"pt": "Iniciante",      "en": "Beginner",      "es": "Principiante"},
    "avancado":         {"pt": "Avançado",       "en": "Advanced",      "es": "Avanzado"},
    "meu_timbre":       {"pt": "Meu timbre",     "en": "My tone",        "es": "Mi tono"},
    "modo_desc":        {"pt": "Iniciante: só o que importa, com atalhos prontos.\nAvançado: os 13 controles do pedal, organizados por bloco.", "en": "Beginner: only what matters, with handy shortcuts.\nAdvanced: all 13 pedal controls, organized by block.", "es": "Principiante: solo lo que importa, con atajos prácticos.\nAvanzado: los 13 controles del pedal, organizados por bloque."},
    "controles_finos":  {"pt": "Controles finos (pré-amp, gabinete, chorus…) ficam no modo Avançado.", "en": "Fine controls (preamp, cab, chorus…) are in Advanced mode.", "es": "Controles finos (preamp, cab, chorus…) están en modo Avanzado."},

    # ---- PresetsTab ----
    "buscar_preset":    {"pt": "Buscar por nome, som ou gênero...", "en": "Search by name, tone or genre...", "es": "Buscar por nombre, tono o género..."},
    "genero_lbl":       {"pt": "Gênero:",         "en": "Genre:",         "es": "Género:"},
    "presets_adaptam":  {"pt": "Os {n} presets se adaptam à guitarra escolhida acima.", "en": "The {n} presets adapt to the guitar chosen above.", "es": "Los {n} presets se adaptan a la guitarra elegida arriba."},
    "todos":            {"pt": "Todos",           "en": "All",            "es": "Todos"},
    "carregar_adaptado":{"pt": "Carregar adaptado", "en": "Load adapted", "es": "Cargar adaptado"},
    "carregar_original":{"pt": "Carregar original", "en": "Load original", "es": "Cargar original"},
    "carregar_adaptado_tip": {"pt": "Carrega já adaptado à guitarra escolhida na barra de cima", "en": "Loads already adapted to the guitar chosen in the top bar", "es": "Carga ya adaptado a la guitarra elegida en la barra superior"},
    "carregar_original_tip": {"pt": "Carrega os valores originais, sem adaptar à guitarra", "en": "Loads original values, without adapting to the guitar", "es": "Carga los valores originales, sin adaptar a la guitarra"},

    # ---- AudioTab ----
    "ouvir_ao_vivo":    {"pt": "▶ Ouvir ao vivo", "en": "▶ Listen live",  "es": "▶ Escuchar en vivo"},
    "gravar_btn":       {"pt": "● Gravar",       "en": "● Record",       "es": "● Grabar"},
    "parar_btn":        {"pt": "■ Parar",        "en": "■ Stop",         "es": "■ Parar"},
    "ouvir_btn":        {"pt": "Ouvir",          "en": "Play",          "es": "Escuchar"},
    "gate_normalizar":  {"pt": "Gate + Normalizar", "en": "Gate + Normalize", "es": "Gate + Normalizar"},
    "pronto_gravar":    {"pt": "Pronto para gravar.", "en": "Ready to record.", "es": "Listo para grabar."},
    "monitor_ligado":   {"pt": "Monitor ligado", "en": "Monitor on",    "es": "Monitor activado"},
    "monitor_desligado":{"pt": "Monitor desligado", "en": "Monitor off", "es": "Monitor desactivado"},
    "latencia":         {"pt": "Latência:",      "en": "Latency:",      "es": "Latencia:"},
    "prioridade":       {"pt": "Prioridade:",    "en": "Priority:",     "es": "Prioridad:"},
    "entrada_lbl":      {"pt": "Entrada:",        "en": "Input:",         "es": "Entrada:"},
    "saida_lbl":        {"pt": "Saída:",          "en": "Output:",        "es": "Salida:"},
    "volume_lbl":       {"pt": "Volume:",         "en": "Volume:",        "es": "Volumen:"},
    "volume_monitor_tip": {"pt": "Volume do monitor (não afeta a gravação)", "en": "Monitor volume (does not affect recording)", "es": "Volumen del monitor (no afecta la grabación)"},
    "audio_intro":      {"pt": "Ouvir e gravar a guitarra sem sair do programa: entrada, VU, gravação, takes.", "en": "Listen and record your guitar without leaving the program: input, VU, recording, takes.", "es": "Escuchar y grabar la guitarra sin salir del programa: entrada, VU, grabación, takes."},
    "abrir_outro":      {"pt": "Abrir em outro programa...", "en": "Open in another program...", "es": "Abrir en otro programa..."},
    "excluir":          {"pt": "Excluir",        "en": "Delete",         "es": "Eliminar"},
    "nao_e_wav":        {"pt": "Este arquivo não é um WAV válido. ", "en": "This file is not a valid WAV. ", "es": "Este archivo no es un WAV válido. "},

    # ---- Afinador ----
    "afinacao":         {"pt": "Afinação:",       "en": "Tuning:",        "es": "Afinación:"},
    "ligar_afinador":   {"pt": "▶ Ligar o afinador", "en": "▶ Turn on tuner", "es": "▶ Encender afinador"},
    "desligar_afinador":{"pt": "■ Desligar o afinador", "en": "■ Turn off tuner", "es": "■ Apagar afinador"},
    "afinador_estado":  {"pt": "Ouvindo a entrada ({rate} kHz). Toque uma corda solta.", "en": "Listening to input ({rate} kHz). Play an open string.", "es": "Escuchando la entrada ({rate} kHz). Toca una cuerda suelta."},
    "toque_corda":      {"pt": "Toque UMA corda solta e deixe soar — não abafe com a mão.", "en": "Play ONE open string and let it ring — don't mute it.", "es": "Toca UNA cuerda suelta y deja sonar — no la silencies."},
    "agulha":           {"pt": "A agulha vai para a esquerda se a corda está frouxa (aperte) e para a direita se está esticada (afrouxe). No centro, está afinado.", "en": "The needle goes left if the string is loose (tighten) and right if it's tight (loosen). Center means in tune.", "es": "La aguja va a la izquierda si la cuerda está floja (aprieta) y a la derecha si está tensa (afloja). En el centro, está afinado."},
    "afinacao_tip":     {"pt": "Qual afinação a guitarra está. Muda as notas que o mostrador espera.", "en": "Which tuning the guitar is in. Changes the notes the tuner expects.", "es": "Qué afinación tiene la guitarra. Cambia las notas que el afinador espera."},
    "desligado":        {"pt": "Desligado.",     "en": "Off.",           "es": "Apagado."},

    # ---- TocandoTab ----
    "timbre_bolso":     {"pt": "TIMBRES DE BOLSO — teclas 1, 2 e 3", "en": "POCKET TONES — keys 1, 2 and 3", "es": "TONOS DE BOLSILLO — teclas 1, 2 y 3"},
    "ordem_som":        {"pt": "A ORDEM DO SOM  ·  clique para mexer, Shift+clique para diminuir", "en": "SIGNAL CHAIN  ·  click to adjust, Shift+click to decrease", "es": "CADENA DE SEÑAL  ·  clic para ajustar, Shift+clic para disminuir"},
    "oque_ouvindo":     {"pt": "O QUE VOCÊ ESTÁ OUVINDO AGORA", "en": "WHAT YOU'RE HEARING NOW", "es": "LO QUE ESTÁS ESCUCHANDO AHORA"},
    "como_usar_somada": {"pt": "Como usar: monte os três timbres da música (intro, verso, final) e troque com 1, 2 e 3 sem largar a guitarra. Para gravar uma somada, ajuste o som como quiser e clique no botão dela — a tecla funciona igual.", "en": "How to use: set up the three song tones (intro, verse, final) and switch with 1, 2 and 3 without letting go of the guitar. To record a pocket tone, adjust the sound as you like and click its button — the key works the same.", "es": "Cómo usar: monta los tres tonos de la canción (intro, estribillo, final) y cambia con 1, 2 y 3 sin soltar la guitarra. Para grabar un tono de bolsillo, ajusta el sonido como quieras y haz clic en su botón — la tecla funciona igual."},
    "somada_vazia_tip": {"pt": "Se estiver vazia, apertar grava o timbre que está no pedal agora.", "en": "If empty, pressing records the tone currently on the pedal.", "es": "Si está vacía, al presionar graba el tono que está en el pedal ahora."},
    "somada_cheia_tip": {"pt": "Se estiver cheia, apertar troca para ela na hora.", "en": "If full, pressing switches to it right away.", "es": "Si está llena, al presionar cambia a él en el acto."},
    "tecla":            {"pt": "Tecla",           "en": "Key",            "es": "Tecla"},
    "vazia":            {"pt": "vazia",           "en": "empty",          "es": "vacía"},
    "cheia":            {"pt": "cheia",           "en": "full",           "es": "llena"},
    "ajuste_controles": {"pt": "Ajuste os controles para ver o estilo", "en": "Adjust the controls to see the style", "es": "Ajusta los controles para ver el estilo"},
    "clique_bloco":     {"pt": "{bid}: mexa no controle '{alvo}' da aba Pedal.", "en": "{bid}: adjust the '{alvo}' control in the Pedal tab.", "es": "{bid}: ajusta el control '{alvo}' en la pestaña Pedal."},

    # ---- IR / Impulso ----
    "ir_titulo":        {"pt": "Impulso (IR)",   "en": "Impulse (IR)",  "es": "Impulso (IR)"},
    "ir_ler":           {"pt": "Ler IR do pedal", "en": "Read IR from pedal", "es": "Leer IR del pedal"},
    "ir_exportar":      {"pt": "Exportar WAV",  "en": "Export WAV",    "es": "Exportar WAV"},
    "ir_enviar":        {"pt": "Enviar para o pedal", "en": "Send to pedal", "es": "Enviar al pedal"},
    "ir_tabela":        {"pt": "IRs recomendados por preset", "en": "Recommended IRs per preset", "es": "IRs recomendados por preset"},
    "ir_sets":          {"pt": "Encher os 8 bancos com um estilo", "en": "Fill all 8 banks with a style", "es": "Llenar los 8 bancos con un estilo"},
    "ir_aplicar_set":   {"pt": "Enviar o set para o pedal", "en": "Send set to pedal", "es": "Enviar el set al pedal"},
    "ir_intro":         {"pt": "O CUBE Baby guarda um IR de usuário, que substitui o de fábrica. Aqui você lê, guarda e envia — sem precisar do CubeSuite.", "en": "The CUBE Baby stores one user IR, which replaces the factory one. Here you read, save and send — without needing CubeSuite.", "es": "El CUBE Baby guarda un IR de usuario, que reemplaza el de fábrica. Aquí lees, guardas y envías — sin necesitar CubeSuite."},
    "qual_ir":          {"pt": "Qual IR combina com cada preset", "en": "Which IR matches each preset", "es": "Qué IR combina con cada preset"},
    "ir_estado":        {"pt": "O que está no pedal agora", "en": "What's on the pedal now", "es": "Qué hay en el pedal ahora"},
    "ainda_nao_li":     {"pt": "— ainda não li o pedal —", "en": "— haven't read the pedal yet —", "es": "— aún no he leído el pedal —"},
    "enviar_ir":        {"pt": "Enviar um IR para o pedal", "en": "Send an IR to the pedal", "es": "Enviar un IR al pedal"},
    "envir_ir_funciona": {"pt": "Funciona. A gravação foi validada no aparelho: enviar um IR e reler deu correlação +0,99 com o arquivo enviado.", "en": "It works. Recording was validated on the device: sending an IR and rereading gave +0.99 correlation with the sent file.", "es": "Funciona. La grabación fue validada en el aparato: enviar un IR y releer dio correlación +0,99 con el archivo enviado."},
    "ir_substituido":   {"pt": "O IR de fábrica do banco escolhido é substituído. O programa faz um backup do IR atual antes de gravar, e você pode voltar atrás pelo botão abaixo.", "en": "The factory IR of the chosen bank is replaced. The program backs up the current IR before writing, and you can revert with the button below.", "es": "El IR de fábrica del banco elegido es reemplazado. El programa hace una copia de seguridad del IR actual antes de grabar, y puedes revertir con el botón de abajo."},
    "banco_lbl":        {"pt": "Banco:",          "en": "Bank:",          "es": "Banco:"},
    "banco_n":          {"pt": "Banco {n}",       "en": "Bank {n}",       "es": "Banco {n}"},
    "nenhum_arquivo":   {"pt": "— nenhum arquivo escolhido —", "en": "— no file chosen —", "es": "— ningún archivo elegido —"},
    "escolher_wav":     {"pt": "Escolher um WAV…", "en": "Choose a WAV…",  "es": "Elegir un WAV…"},
    "enviar_pedal":     {"pt": "Enviar para o pedal", "en": "Send to pedal", "es": "Enviar al pedal"},
    "voltar_ir":        {"pt": "Voltar ao IR anterior", "en": "Revert to previous IR", "es": "Volver al IR anterior"},
    "nenhum_backup":    {"pt": "— nenhum backup nesta sessão —", "en": "— no backup this session —", "es": "— ninguna copia en esta sesión —"},
    "restaurar_backup": {"pt": "Restaurar o backup", "en": "Restore backup", "es": "Restaurar copia"},
    "restaurar_arquivo": {"pt": "Restaurar de um arquivo…", "en": "Restore from file…", "es": "Restaurar de un archivo…"},
    "encher_8":         {"pt": "Encher os 8 bancos com um estilo", "en": "Fill all 8 banks with a style", "es": "Llenar los 8 bancos con un estilo"},
    "encher_8_desc":    {"pt": "O pedal tem 8 bancos. Um set escolhe 8 IRs de um estilo e envia para os 8 de uma vez — você fica com um arsenal daquele som.", "en": "The pedal has 8 banks. A set picks 8 IRs of one style and sends them to all 8 at once — you get an arsenal of that sound.", "es": "El pedal tiene 8 bancos. Un set elige 8 IRs de un estilo y los envía a los 8 de una vez — tienes un arsenal de ese sonido."},
    "enviar_set":       {"pt": "Enviar o set para o pedal", "en": "Send set to pedal", "es": "Enviar el set al pedal"},
    "confirmar_envio":  {"pt": "Isto vai substituir o IR do banco {b}. Um backup é feito automaticamente antes. Continuar?", "en": "This will replace the IR of bank {b}. A backup is made automatically first. Continue?", "es": "Esto reemplazará el IR del banco {b}. Se hace una copia automáticamente antes. ¿Continuar?"},
    "confirmar_envio_set": {"pt": "Isto vai substituir os 8 bancos. Um backup de cada um é feito automaticamente antes. Continuar?", "en": "This will replace all 8 banks. A backup of each is made automatically first. Continue?", "es": "Esto reemplazará los 8 bancos. Se hace copia de cada uno automáticamente antes. ¿Continuar?"},
    "confirmar_restaurar": {"pt": "Restaurar o backup feito nesta sessão? O IR atual será substituído.", "en": "Restore the backup made this session? The current IR will be replaced.", "es": "¿Restaurar la copia hecha en esta sesión? El IR actual será reemplazado."},
    "confirmar_restaurar_arquivo": {"pt": "Restaurar o IR deste arquivo? O IR atual será substituído.", "en": "Restore the IR from this file? The current IR will be replaced.", "es": "¿Restaurar el IR de este archivo? El IR actual será reemplazado."},
    "sem_pedal":        {"pt": "Sem pedal",        "en": "No pedal",        "es": "Sin pedal"},
    "sem_pedal_msg":    {"pt": "Conecte o pedal para ler o IR.", "en": "Connect the pedal to read the IR.", "es": "Conecta el pedal para leer el IR."},
    "salvo":            {"pt": "Salvo",            "en": "Saved",           "es": "Guardado"},
    "ir_exportado":     {"pt": "IR exportado:\n{alvo}", "en": "IR exported:\n{alvo}", "es": "IR exportado:\n{alvo}"},
    "arquivo_nao_serve": {"pt": "Arquivo não serve", "en": "File not usable", "es": "Archivo no válido"},
    "arquivo_nao_serve_msg": {"pt": "Este arquivo não é um WAV válido.", "en": "This file is not a valid WAV.", "es": "Este archivo no es un WAV válido."},
    "backup_invalido":  {"pt": "Backup inválido",  "en": "Invalid backup",  "es": "Copia inválida"},
    "restaurado":       {"pt": "Restaurado",       "en": "Restored",       "es": "Restaurado"},
    "erro":             {"pt": "Erro",             "en": "Error",          "es": "Error"},
    "set_aplicado":     {"pt": "Set aplicado",     "en": "Set applied",    "es": "Set aplicado"},
    "enviando_set":     {"pt": "Enviando o set para o pedal...", "en": "Sending set to pedal...", "es": "Enviando el set al pedal..."},
    "enviando_ir":      {"pt": "Enviando IR para o pedal...", "en": "Sending IR to pedal...", "es": "Enviando IR al pedal..."},
    "erro_envio":       {"pt": "Erro ao enviar",  "en": "Send error",     "es": "Error al enviar"},
    "ir_lido":          {"pt": "IR lido do pedal", "en": "IR read from pedal", "es": "IR leído del pedal"},

    # ---- LibraryTab ----
    "biblioteca_intro": {"pt": "A biblioteca guarda seus presets e gravações.", "en": "The library stores your presets and recordings.", "es": "La biblioteca guarda tus presets y grabaciones."},
    "biblioteca_vazia": {"pt": "A biblioteca está vazia. Salve um preset para começar.", "en": "The library is empty. Save a preset to get started.", "es": "La biblioteca está vacía. Guarda un preset para empezar."},
    "salvar_preset":    {"pt": "Salvar preset",   "en": "Save preset",     "es": "Guardar preset"},
    "renomear":         {"pt": "Renomear",        "en": "Rename",         "es": "Renombrar"},
    "carregar":         {"pt": "Carregar",        "en": "Load",           "es": "Cargar"},
    "nome_preset":      {"pt": "Nome do preset",  "en": "Preset name",    "es": "Nombre del preset"},
    "confirmar_excluir": {"pt": "Excluir este preset?", "en": "Delete this preset?", "es": "¿Eliminar este preset?"},

    # ---- Doações ----
    "apoiar_intro":     {"pt": "O CUBE Baby Unleashed é um projeto independente, gratuito e de código aberto (GPL-3.0). Se o programa ajudou você a conseguir seu timbre, considere fazer uma doação.", "en": "CUBE Baby Unleashed is a free, open-source (GPL-3.0) independent project. If the program helped you get your tone, consider a donation.", "es": "CUBE Baby Unleashed es un proyecto independiente, gratuito y de código abierto (GPL-3.0). Si el programa te ayudó a conseguir tu tono, considera hacer una donación."},
    "pix_titulo":       {"pt": "Pix (BRL)",        "en": "Pix (BRL)",       "es": "Pix (BRL)"},
    "pix_chave":        {"pt": "Chave Pix:",       "en": "Pix key:",       "es": "Clave Pix:"},
    "pix_copia_e_cola": {"pt": "Código Pix copia e cola:", "en": "Pix copy & paste code:", "es": "Código Pix copiar y pegar:"},
    "pix_a_configurar": {"pt": "Chave Pix ainda não configurada. Edite cubebaby/donate.py e adicione sua chave Pix real.", "en": "Pix key not yet configured. Edit cubebaby/donate.py and add your real Pix key.", "es": "Clave Pix aún no configurada. Edita cubebaby/donate.py y agrega tu clave Pix real."},
    "cripto_titulo":    {"pt": "Criptomoedas",    "en": "Cryptocurrencies", "es": "Criptomonedas"},
    "cripto_a_configurar": {"pt": "Endereço de cripto ainda não configurado. Edite cubebaby/donate.py e adicione seu endereço.", "en": "Crypto address not yet configured. Edit cubebaby/donate.py and add your address.", "es": "Dirección de cripto aún no configurada. Edita cubebaby/donate.py y agrega tu dirección."},
    "rede":             {"pt": "Rede",            "en": "Network",         "es": "Red"},
    "token":            {"pt": "Token",           "en": "Token",           "es": "Token"},
    "links_titulo":     {"pt": "Outras formas de apoiar", "en": "Other ways to support", "es": "Otras formas de apoyar"},
    "links_a_configurar": {"pt": "Links ainda não configurados. Edite cubebaby/donate.py.", "en": "Links not yet configured. Edit cubebaby/donate.py.", "es": "Enlaces aún no configurados. Edita cubebaby/donate.py."},
    "github_sponsors":  {"pt": "GitHub Sponsors",  "en": "GitHub Sponsors", "es": "GitHub Sponsors"},
    "github_repo":      {"pt": "Repositório no GitHub", "en": "GitHub repository", "es": "Repositorio en GitHub"},
    "kofi":             {"pt": "Ko-fi",            "en": "Ko-fi",           "es": "Ko-fi"},
    "aviso_legal":      {"pt": "Aviso legal",     "en": "Legal notice",    "es": "Aviso legal"},
    "aviso_texto":      {"pt": "Doações são voluntárias, sem troca de bens ou serviços. Este programa é gratuito e de código aberto (GPL-3.0).", "en": "Donations are voluntary, without exchange of goods or services. This program is free and open-source (GPL-3.0).", "es": "Las donaciones son voluntarias, sin intercambio de bienes o servicios. Este programa es gratuito y de código abierto (GPL-3.0)."},
    "copiar":           {"pt": "Copiar",          "en": "Copy",            "es": "Copiar"},
    "copiar_codigo":    {"pt": "Copiar código",   "en": "Copy code",       "es": "Copiar código"},

    # ---- Ajuda (HelpDialog) ----
    "ajuda_titulo":     {"pt": "Ajuda — Cube Baby Studio", "en": "Help — Cube Baby Studio", "es": "Ayuda — Cube Baby Studio"},
    "os_controles_importantam": {"pt": "Os controles que importam", "en": "The controls that matter", "es": "Los controles que importan"},
    "ajuda_tooltip":    {"pt": "Guia: por onde começar, qual preset usar, o que é cada controle", "en": "Guide: where to start, which preset to use, what each control does", "es": "Guía: por dónde empezar, qué preset usar, qué hace cada control"},
    "comeco":           {"pt": "Comece aqui",     "en": "Start here",     "es": "Empieza aquí"},
    "qual_preset":      {"pt": "Qual preset eu escolho?", "en": "Which preset should I choose?", "es": "¿Qué preset elijo?"},
    "os_controles":     {"pt": "Os controles",    "en": "The controls",   "es": "Los controles"},
    "sua_guitarra":     {"pt": "Sua guitarra",    "en": "Your guitar",    "es": "Tu guitarra"},
    "audio_tab":        {"pt": "Áudio",          "en": "Audio",         "es": "Audio"},
    "gabinetes":        {"pt": "Gabinetes de fábrica", "en": "Factory cabinets", "es": "Gabinetes de fábrica"},
    "fechar":           {"pt": "Fechar",          "en": "Close",          "es": "Cerrar"},
    "bem_vindo":        {"pt": "Bem-vindo.",      "en": "Welcome.",       "es": "Bienvenido."},
    "o_que_voce_quer":  {"pt": "O que você quer?", "en": "What do you want?", "es": "¿Qué quieres?"},
    "escolha_ponto":    {"pt": "Escolha um ponto de partida e ajuste à vontade.", "en": "Choose a starting point and adjust as you like.", "es": "Elige un punto de partida y ajusta a tu gusto."},
    "pedal_conecte":    {"pt": "Conecte o pedal primeiro (ou use o Modo simulado).", "en": "Connect the pedal first (or use Simulated mode).", "es": "Conecta el pedal primero (o usa el Modo simulado)."},
    "nenhuma_porta":    {"pt": "Nenhuma porta MIDI encontrada. Plugue o pedal e clique em Atualizar portas.", "en": "No MIDI port found. Plug the pedal and click Refresh ports.", "es": "No se encontró ningún puerto MIDI. Conecta el pedal y haz clic en Actualizar puertos."},

    # ---- Gate/Normalize ----
    "gate_titulo":      {"pt": "Gate + Normalizar", "en": "Gate + Normalize", "es": "Gate + Normalizar"},
    "modo_pico":        {"pt": "Pico (o mais alto fica no alvo)", "en": "Peak (highest goes to target)", "es": "Pico (el más alto va al objetivo)"},
    "modo_rms":         {"pt": "Volume percebido (mais natural)", "en": "Perceived volume (more natural)", "es": "Volumen percibido (más natural)"},
    "cancelar":         {"pt": "Cancelar",        "en": "Cancel",         "es": "Cancelar"},
    "processar":        {"pt": "Processar",       "en": "Process",        "es": "Procesar"},

    # ---- CabsFactory ----
    "filtrar_cab":      {"pt": "Filtrar: mesa, marshall, vox, 4x12, baixo…", "en": "Filter: mesa, marshall, vox, 4x12, bass…", "es": "Filtrar: mesa, marshall, vox, 4x12, bajo…"},
    "nada_encontrado":  {"pt": "Nada encontrado com esse termo.", "en": "Nothing found with that term.", "es": "Nada encontrado con ese término."},

    # ---- Prioridade ----
    "prio_normal":      {"pt": "Normal",         "en": "Normal",        "es": "Normal"},
    "prio_alta":        {"pt": "Alta",           "en": "High",          "es": "Alta"},
    "prio_critica":     {"pt": "Crítica",        "en": "Critical",      "es": "Crítica"},
    "prio_realtime":    {"pt": "Tempo real",     "en": "Real-time",     "es": "Tiempo real"},
}


def tr(chave: str, idioma: str = "pt") -> str:
    """Traduz uma chave para o idioma pedido. Se não existir, cai para PT."""
    if chave in TRADUCOES:
        traducao = TRADUCOES[chave]
        return traducao.get(idioma) or traducao.get("pt") or chave
    return chave


def set_idioma(idioma: str) -> None:
    """Define o idioma global. Se inválido, cai para PT."""
    global _idioma_atual
    if idioma in IDIOMAS:
        _idioma_atual = idioma


def get_idioma() -> str:
    """Retorna o idioma atual (padrão: PT)."""
    return _idioma_atual


_idioma_atual = "pt"
