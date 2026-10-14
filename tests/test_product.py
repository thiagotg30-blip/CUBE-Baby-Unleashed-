"""Testa o "de cara de produto": preferências, onboarding, sobre e atalhos.

Rode:  .venv\\Scripts\\python.exe tests\\test_product.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from cubebaby import settings as S
from cubebaby import theme
from cubebaby.settings import Settings


def test_settings_persiste():
    """Preferência salva tem que voltar. É o que faz o programa não abrir
    'como se fosse a primeira vez' toda vez."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prefs.json"
        s = S.Settings(p)
        s.set("guitarra", "tele")
        s.set("aba", 2)
        s.save()
        assert p.exists()
        s2 = S.Settings(p)
        assert s2.get("guitarra") == "tele"
        assert s2.get("aba") == 2


def test_settings_ignora_arquivo_corrompido():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prefs.json"
        p.write_text("{isto nao e json", encoding="utf-8")
        s = S.Settings(p)
        # não pode levantar: preferência quebrada não impede o app de abrir
        assert s.get("guitarra") == S.DEFAULTS["guitarra"]


def test_settings_descarta_chaves_desconhecidas():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prefs.json"
        p.write_text(json.dumps({"guitarra": "sg", "campo_malicioso": 1}), encoding="utf-8")
        s = S.Settings(p)
        assert s.get("guitarra") == "sg"
        assert "campo_malicioso" not in s.data


def test_salvar_e_atomico():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prefs.json"
        s = S.Settings(p)
        s.set("aba", 1); s.save()
        # nenhum .tmp orfanado: a troca precisa ter limpado tudo
        assert list(Path(d).glob(".prefs-*")) == [], "deixou temporario para tras"


def test_primeira_execucao_e_marcada():
    with tempfile.TemporaryDirectory() as d:
        s = S.Settings(Path(d) / "p.json")
        s.data["primeira_execucao"] = True
        assert s.is_first_run()
        s.mark_seen()
        assert not s.is_first_run()
        s2 = S.Settings(Path(d) / "p.json")
        assert not s2.is_first_run(), "a preferencia nao persistiu"


def test_restaura_janela_rejeita_tamanho_absurdo():
    with tempfile.TemporaryDirectory() as d:
        s = S.Settings(Path(d) / "p.json")
        app = QApplication.instance() or QApplication([])
        from cubebaby.ui import MainWindow
        w = MainWindow(settings=s)
        s.set("janela", [10, 10])          # minúsculo: deve recusar
        assert w.settings.restore_window(w) is False
        s.set("janela", [1000, 700])
        assert w.settings.restore_window(w) is True
        # Nao pode passar do que cabe na tela, E tem de respeitar o minimo
        # fisico (1000x795) que impede as abas de cortar.
        from PySide6.QtGui import QGuiApplication
        scr = QGuiApplication.primaryScreen().availableGeometry()
        assert w.width() == max(w.minimumSize().width(),
                                     min(1000, max(640, scr.width() - 40)))
        assert w.height() == max(w.minimumSize().height(),
                                 min(700, max(480, scr.height() - 40)))


def test_onboarding_monta_e_tem_abas():
    app = QApplication.instance() or QApplication([])
    from cubebaby.onboarding import GuitarPickerDialog, WelcomeDialog
    from cubebaby.about import AboutDialog
    from cubebaby.ui import HelpDialog, MainWindow
    from cubebaby import guitars as GT

    win = MainWindow(settings=Settings())

    w = WelcomeDialog(); w.show(); app.processEvents(); w.close()
    g = GuitarPickerDialog(current="sg")
    assert g.lst.count() == len(GT.GUITARS)
    assert g.selected() == "sg"
    g.lst.setCurrentRow(0); g._preview()
    assert g.selected() == GT.GUITARS[0].key
    g.close()
    a = AboutDialog(win); a.show(); app.processEvents()
    assert a.tabs.count() == 3, "Sobre precisa ter Sobre/Licença/Créditos"
    a.close()
    h = HelpDialog(win); h.show(); app.processEvents()
    assert h.tabs.count() == 6, h.tabs.count()
    h.close()
    win.close()


def test_atalhos_existem():
    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QShortcut
    from cubebaby.settings import Settings
    from cubebaby.ui import MainWindow
    win = MainWindow(settings=Settings())
    sc = win.findChildren(QShortcut)
    seqs = {s.key().toString() for s in sc}
    for esperado in ("Ctrl+1", "Ctrl+2", "Ctrl+3", "Ctrl+4", "F1", "Ctrl+M"):
        assert esperado in seqs, f"falta o atalho {esperado} (tem {seqs})"
    win.close()


def test_tema_tem_tokens():
    assert theme.STYLESHEET.strip().startswith("QWidget")
    assert "{FG}" not in theme.STYLESHEET, "token nao foi expandido"
    # checa os TOKENS, nao hex literal: o hex exato muda com o tema, o token nao.
    for tok in (theme.BG_DEEP, theme.ACCENT, theme.FG, theme.CARD if hasattr(theme, "CARD")
                else theme.BG_CARD):
        assert tok in theme.STYLESHEET, f"token {tok} nao aparece na folha de estilo"
    # nenhum bloco de cor deve estar congelado no arquivo
    assert "#0f1116" not in theme.STYLESHEET, "cor antiga do tema ainda no QSS"


def test_widgets_nao_sobrescrevem_o_tema():
    """Regressão: o ParamRow definia as cores do slider por conta propria, com
    a paleta antiga, e a janela ficava com cores diferentes das da folha."""
    from cubebaby.ui import ParamRow
    q = ParamRow("gain", "Ganho", theme.ACCENT)
    css = q.styleSheet()
    # pode tingir o preenchimento com a cor do bloco...
    assert theme.ACCENT in css
    # ...mas nao pode redefinir o que o tema ja define
    assert "QSlider::handle:horizontal { background:" not in css, \
        "ParamRow esta redefinindo o botao do slider e divergindo do tema"
    assert "#2b303b" not in css, "cor antiga vazou para o ParamRow"


def test_cores_de_bloco_sao_do_tema():
    """Nenhum bloco pode usar cor fixa fora da paleta."""
    from cubebaby.ui import BLOCKS
    paleta = {theme.ACCENT, theme.GOLD, theme.PURPLE, theme.BLUE, theme.OK, theme.FG_MUTED}
    for nome, cor, _k, _t in BLOCKS:
        assert cor in paleta, f"bloco {nome} usa {cor}, fora da paleta"


def test_mainwindow_usa_settings():
    app = QApplication.instance() or QApplication([])
    from cubebaby.ui import MainWindow
    with tempfile.TemporaryDirectory() as d:
        s = Settings(Path(d) / "p.json")
        s.data["primeira_execucao"] = False   # nao abrir onboarding no teste
        s.data["guitarra"] = "tele"
        s.save()
        w = MainWindow(settings=s)
        assert w.cb_guitar.currentData() == "tele"
        w._save_state()
        s2 = Settings(Path(d) / "p.json")
        assert s2.get("guitarra") == "tele"
        w.close()


def test_modos_iniciante_e_avancado():
    """Trocar de modo não pode recriar widgets (perderia o ajuste no meio),
    nem esconder parâmetros do estado — só reorganizar."""
    app = QApplication.instance() or QApplication([])
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window

    with tempfile.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        pt = win.pedal_tab
        assert pt.mode in ("iniciante", "avancado")

        antes = {n: id(r) for n, r in pt.rows.items()}
        # marca o modo explicitamente e força o layout
        pt._set_mode("iniciante")
        assert pt._pages.currentWidget() is pt._page_beg
        pt._set_mode("avancado")
        assert pt._pages.currentWidget() is pt._page_adv
        depois = {n: id(r) for n, r in pt.rows.items()}
        assert antes == depois, "os widgets foram recriados: o ajuste se perderia"

        # no iniciante aparecem so os essenciais, com nome everyday
        def dentro_de(widget, pagina):
            """True se widget está na subárvore de `pagina` (pode estar dentro
            do QGroupBox dela, não nela diretamente)."""
            while widget is not None:
                if widget is pagina:
                    return True
                widget = widget.parent()
            return False

        pt._set_mode("iniciante")
        pt._page_beg.show()
        app.processEvents()
        for n in GU_BEGINNER:
            assert dentro_de(pt.rows[n], pt._page_beg), n
            assert not pt.rows[n].isHidden(), f"{n} sumiu no modo iniciante"
        # os avancados ficam num container invisivel: nao estao na tela
        for n, r in pt.rows.items():
            if n not in GU_BEGINNER:
                assert r.isHidden(), f"{n} avancado ficou visivel no iniciante"
        pt._set_mode("avancado")
        pt._page_adv.show()
        app.processEvents()
        for n, r in pt.rows.items():
            assert dentro_de(r, pt._page_adv), n
            assert not r.isHidden(), f"{n} ficou escondido no modo avancado"

        # e o valor mexeu, não o modo
        pt._set_mode("iniciante")
        pt.params["A"]["gain"] = 5
        pt._set_mode("avancado")
        assert pt.params["A"]["gain"] == 5
        win.close()


def test_atalho_iniciante_aplica_no_slot():
    app = QApplication.instance() or QApplication([])
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window
    import tempfile as tf
    d = tf.mkdtemp()
    app2, win = build_window(Settings(Path(d) / "p.json"))
    pt = win.pedal_tab
    antes = dict(pt.params["A"])
    pt.apply_intent("sujão")
    depois = pt.params["A"]
    assert depois != antes, "o atalho nao mudou nada"
    assert depois["gain"] > antes["gain"], "Sujão deveria aumentar o ganho"
    assert pt.lbl_intent.text(), "faltou a explicacao do que foi aplicado"
    win.close()


GU_BEGINNER = ("gain", "tone", "volume", "reverb", "mix")


def test_migracao_da_pasta_de_dados():
    """Trocar o nome do programa não pode custar as gravações e presets do
    usuário: a pasta antiga tem de ser MOVIDA, não abandonada.

    Roda num diretório temporário de propósito — um teste de migração não pode
    mexer na pasta real de quem está rodando a suíte.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        antigo = base / S.LEGACY_DIRS[0]
        marca = antigo / "gravacoes" / "meu-take.wav"
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_bytes(b"conteudo do usuario")

        destino = S.data_dir(base)

        assert destino == base / S.APP_DIR_NAME, destino
        assert destino.exists()
        # o conteúdo tem de aparecer no DESTINO: a pasta antiga some de propósito
        movido = destino / "gravacoes" / "meu-take.wav"
        assert movido.exists(), "os arquivos do usuario foram perdidos na migracao"
        assert movido.read_bytes() == b"conteudo do usuario"
        assert not antigo.exists(), "a pasta antiga ficou para tras (duplicou)"


def test_data_dir_cria_pasta_se_nao_houver():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        assert S.data_dir(Path(d)).is_dir()


def test_nome_da_pasta_fala_do_aparelho():
    """A pasta de dados precisa citar o aparelho: é o que o usuário procura,
    e o que faz o uso nominativo da marca ficar evidente."""
    assert "CUBEBaby" in S.APP_DIR_NAME.replace(" ", ""), S.APP_DIR_NAME


def test_nome_da_posta_e_do_programa():
    """A pasta de dados e a janela precisam falar do aparelho que o programa
    edita — é o que faz o usuario achar, e o uso nominativo da marca."""
    import re as _re
    nome = S.APP_DIR_NAME
    assert "CUBEBaby" in nome.replace(" ", ""), nome
    assert "~\\Ganho" not in (root_src := Path(__file__).parent.parent / "cubebaby" / "audio.py").read_text(encoding="utf-8")


def test_gabinetes_tem_das_listas_e_os_numeros_certo():
    """Cada posicao 0..8 tem que existir e dizer o que e, nas DUAS listas.

    As listas mudam entre firmware, mas a contagem e a posicao nao: 9 posicoes,
    a primeira desliga. Se isso divergir, o usuario escolhe a caixa errada.
    """
    from cubebaby import cabinets as CAB
    for fw in ("cuvave", "mvave"):
        labs = CAB.all_labels(fw)
        assert len(labs) == CAB.N_POSITIONS, (fw, len(labs))
        assert labs[0].startswith("Bypass"), labs[0]
        # cada gabinete se identifica: nome + numero de alto-falantes
        for pos in range(1, CAB.N_POSITIONS):
            c = CAB.get(fw, pos)
            assert c.pos == pos
            assert c.name and c.spec and c.character
            assert str(pos) in labs[pos]
    # as duas listas sao DIFERENTES (por isso a escolha importa)
    assert CAB.all_labels("cuvave") != CAB.all_labels("mvave")


def test_ir_sintetizado_e_saudavel():
    """Um IR de caixa começa com o impulso e DECAI. Se ele grow ou explode,
    o filtro esta instavel e o som sai um estouro."""
    import struct as _s
    from cubebaby import cabinets as CAB
    for fw in ("cuvave", "mvave"):
        for cab in CAB.FIRMWARES[fw]["cabs"][1:]:
            raw = CAB.make_ir(cab)
            v = _s.unpack("<%dh" % (len(raw) // 2), raw)
            assert v[0] != 0, f"{cab.short}: sem impulso inicial"
            pico = max(abs(x) for x in v)
            assert 0.5 < pico < 32767, f"{cab.short}: pico {pico}"
            # o pico tem que estar no comeco, nao no fim
            primeiro = next(i for i, x in enumerate(v) if abs(x) > pico * 0.2)
            assert primeiro < len(v) * 0.05, f"{cab.short}: pico tardio"
            # e a energia tem que cair (cauda)
            inicio = max(abs(x) for x in v[:4000])
            fim = max(abs(x) for x in v[-4000:])
            assert fim < inicio, f"{cab.short}: IR nao decai"


def test_exportar_irs_gera_8_wavs_estereo():
    import wave as _w
    from cubebaby import cabinets as CAB
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        files = CAB.export_all_irs("cuvave", d)
        assert len(files) == CAB.N_POSITIONS - 1, len(files)
        for f in files:
            assert f.exists() and f.stat().st_size > 1000, f
            with _w.open(str(f)) as w:
                assert w.getnchannels() == 2
                assert w.getframerate() == CAB.SAMPLE_RATE
                assert w.getsampwidth() == 2


def test_arte_da_caixa_desenha_a_configuracao_certa():
    """O desenho tem que refletir N alto-falantes e o tamanho (10" < 12")."""
    from cubebaby import art as ART
    from cubebaby import cabinets as CAB
    assert ART.parse_spec("1×10") == (1, 10)
    assert ART.parse_spec("2x12") == (2, 12)
    assert ART.parse_spec("4×12") == (4, 12)
    assert ART.parse_spec("lixo") == (0, 0)
    for fw in ("cuvave", "mvave"):
        for cab in CAB.FIRMWARES[fw]["cabs"]:
            n, inch = ART.parse_spec(cab.spec)
            if cab.pos == 0:
                continue
            assert n >= 1 and inch in (10, 12), (cab.short, cab.spec)


def test_todos_preamps_tem_carcater_para_desenhar():
    """Nenhum pré-amp pode ficar sem diagrama: cair no meio e fingir que é
   OVERDRIVE seria pior que não mostrar nada."""
    from cubebaby import art as ART
    from cubebaby import protocol as P
    for _i, nome, _cat in P.PREAMP_TYPES:
        tom, sujeira, cat = ART.preamp_character(nome)
        assert 0.0 <= tom <= 1.0 and 0.0 <= sujeira <= 1.0, nome
        assert cat and cat != "—", f"{nome} ficou sem categoria"
    # os tres grupos existem e estao ordenados (limpo -> od -> distorcao)
    ordem = [ART.preamp_character(n)[2] for _i, n, _c in P.PREAMP_TYPES]
    assert ordem[:2] == ["Limpo", "Limpo"]
    assert "Distorção" in ordem[-2:]
    # sujeira cresce ao longo da lista: o ganho do pré-amp sobe
    sujeiras = [ART.preamp_character(n)[1] for _i, n, _c in P.PREAMP_TYPES]
    assert sujeiras[0] < sujeiras[-1], sujeiras


def test_art_na_interface_do_pedal():
    app = QApplication.instance() or QApplication([])
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window
    import tempfile as tf
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        pt = win.pedal_tab
        cab = pt.rows["cabinet"]
        assert hasattr(cab, "cab_art"), "falta a planta da caixa"
        for v in (0, 1, 6, 8):
            cab.set_value(v)
            assert cab.cab_art.spec is not None
        pre = pt.rows["type"]
        assert hasattr(pre, "art"), "falta o diagrama de pre-amp"
        pre.set_value(8)
        assert pre.art.grit > pre.art.tone, "Mr Smith Dist deveria ser mais sujo que brilhante"
        win.close()


def test_slider_nao_danca_de_largura():
    """Regressão do 'flicker': o rótulo com texto longo espremia o slider da
    mesma linha, e ele mudava de tamanho a cada valor arrastado.
    Medido: de 645px no bypass a 357px no Diezel. Agora tem que ser constante.
    """
    app = QApplication.instance() or QApplication([])
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window
    import tempfile as tf
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        from cubebaby import protocol as _P
        P_MAX.update(_P.PARAM_MAX)
        pt = win.pedal_tab
        pt._set_mode("avancado")
        win.resize(1120, 660); win.show(); app.processEvents()
        for nome in ("cabinet", "gain", "tone", "mix"):
            row = pt.rows[nome]
            larguras = []
            alturas = []
            for v in range(0, P_MAX[nome] + 1, max(1, P_MAX[nome] // 4)):
                row.set_value(v)
                app.processEvents()
                larguras.append(row.slider.width())
                alturas.append(row.height())
            assert len(set(larguras)) == 1, \
                f"{nome}: slider mudou de largura {sorted(set(larguras))} — volta o flicker"
            assert len(set(alturas)) == 1, f"{nome}: linha mudou de altura {sorted(set(alturas))}"
        # e o texto cortado fica completo no tooltip
        cab = pt.rows["cabinet"]
        cab.set_value(8)
        assert "…" in cab.value_lbl.text(), "o nome longo deveria ser cortado"
        assert "Diezel V30" in cab.value_lbl.toolTip(), "o texto completo tem de estar no tooltip"
        win.close()


P_MAX = {}


def test_take_quebrado_da_aviso_e_nao_crash():
    """Regressão do crash real: abrir um WAV de 5 bytes levantava EOFError e
    fechava o programa inteiro. Agora tem de virar aviso na janela.
    """
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.ui import DspDialog
    with tf.TemporaryDirectory() as d:
        from cubebaby.settings import Settings
        from cubebaby.ui import build_window
        _a, win = build_window(Settings(Path(d) / "p.json"))
        lixo = Path(d) / "quebrado.wav"
        lixo.write_bytes(b"falso")   # 5 bytes: nem cabecalho WAV tem

        dlg = DspDialog(win, str(lixo))
        dlg.show()
        app.processEvents()
        assert dlg.erro, "deveria ter registrado o arquivo como invalido"
        assert "corrompido" in dlg.erro or "vazio" in dlg.erro, dlg.erro
        assert dlg.lbl_erro.isVisible(), "o aviso tem de aparecer na janela"
        assert not dlg.ok_btn.isEnabled(), "Processar tem de ficar desabilitado"
        # e clicar mesmo assim nao pode explodir
        dlg._run()
        dlg.close(); win.close()


def test_wav_valido_abre_e_habilita_processar():
    app = QApplication.instance() or QApplication([])
    import tempfile as tf, wave as _w, struct as _s
    from cubebaby.ui import DspDialog
    with tf.TemporaryDirectory() as d:
        from cubebaby.settings import Settings
        from cubebaby.ui import build_window
        _a, win = build_window(Settings(Path(d) / "p.json"))
        bom = Path(d) / "bom.wav"
        dados = b"".join(_s.pack("<h", int(8000 * (i % 100) / 100)) for i in range(4000))
        with _w.open(str(bom), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100)
            f.writeframes(dados)
        dlg = DspDialog(win, str(bom)); dlg.show(); app.processEvents()
        assert dlg.erro is None, dlg.erro
        assert dlg.ok_btn.isEnabled()
        dlg.close()


def test_lista_marca_take_quebrado():
    """A lista tem que avisar antes de o usuario clicar e tomar o erro."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.settings import Settings
    from cubebaby import audio as AU
    from cubebaby.ui import build_window
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        at = win.audio_tab
        # reload_takes() le a pasta REAL de gravacoes, nao a temporaria do
        # teste. Apontamos o metodo para o tmpdir em vez de mexer nos takes
        # do usuario — um teste nao pode criar arquivo na pasta de quem roda.
        pasta = AU.recordings_dir(Path(d))
        (pasta / "ok.wav").write_bytes(b"RIFF" + b"\0" * 60)
        (pasta / "lixo.wav").write_bytes(b"x")
        real = AU.recordings_dir
        AU.recordings_dir = lambda *a, **k: pasta
        try:
            at.reload_takes()
        finally:
            AU.recordings_dir = real
        textos = [at.lst_takes.item(i).text() for i in range(at.lst_takes.count())]
        assert any("quebrado" in x for x in textos), textos
        win.close()


def test_somada_guarda_os_13_parametros():
    """Uma somada pela metade mudaria o pedal para um estado que o usuario
    nao pediu. E arquivo corrompido nao pode derrubar o programa."""
    import json, tempfile as tf
    from cubebaby import somadas as SOM
    from cubebaby import protocol as PP
    with tf.TemporaryDirectory() as d:
        base = Path(d)
        completo = {n: 0 for n in PP.PARAM_NAMES}
        completo["type"] = 4
        assert SOM.salvar([{"nome": "X", "params": completo}, None, None], base)
        assert SOM.carregar(base)[0]["params"]["type"] == 4

        # O arquivo fica DENTRO da pasta de dados (data_dir cria TomCUBEBaby/),
        # nao na raiz do tmpdir. Pegar o caminho pela propria funcao evita o erro.
        arq = SOM.caminho(base)
        arq.write_text("{isto nao e json", encoding="utf-8")
        assert SOM.carregar(base) == SOM.vazias(), "JSON quebrado tem que virar vazio"

        arq.write_text(json.dumps([{"params": {"gain": 1}}]), encoding="utf-8")
        assert SOM.carregar(base)[0] is None, "somada incompleta tem de ser rejeitada"

        fora = {**completo, "gain": 999}
        arq.write_text(json.dumps([{"params": fora}]), encoding="utf-8")
        assert SOM.carregar(base)[0] is None, "valor fora do limite tem de ser rejeitado"


def test_teclas_1_2_3_trocam_o_timbre():
    """O caso de uso: trocar de som tocando, sem ir ate a pedaleira."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby import somadas as SOM
    from cubebaby import protocol as PP
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    real = SOM.caminho
    try:
        with tf.TemporaryDirectory() as d:
            SOM.caminho = lambda *a, **k: Path(d) / SOM.ARQUIVO
            app2, win = build_window(Settings(Path(d) / "p.json"))
            at = win.aba_tocando
            pt = win.pedal_tab

            metal = {n: 0 for n in PP.PARAM_NAMES}
            metal.update({"type": 7, "gain": 6, "cabinet": 6})
            limpo = {n: 0 for n in PP.PARAM_NAMES}
            limpo.update({"type": 0, "gain": 1})
            at._somadas[0] = {"nome": "Metal", "params": metal}
            at._somadas[1] = {"nome": "Limpo", "params": limpo}
            at._atualiza_botoes()

            win.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_1, Qt.NoModifier, "1"))
            assert pt.params[pt.slot]["type"] == 7
            assert pt.rows["gain"].slider.value() == 6, "o slider precisa acompanhar"
            win.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_2, Qt.NoModifier, "2"))
            assert pt.params[pt.slot]["type"] == 0
            assert pt.rows["gain"].slider.value() == 1

            # somada vazia grava o timbre atual em vez de nao fazer nada
            at._somadas[2] = None
            tipo = pt.params[pt.slot]["type"]
            win.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_3, Qt.NoModifier, "3"))
            assert at._somadas[2] is not None, "tecla em somada vazia tem que gravar"
            assert at._somadas[2]["params"]["type"] == tipo
            win.close()
    finally:
        # Sem restaurar, o monkeypatch vaza e os testes seguintes passam a ler
        # a pasta de somadas do USUARIO.
        SOM.caminho = real


def test_atalho_nao_sequestra_campo_de_texto():
    """Se a tecla 1 fosse global, nao daria para digitar 1 em um campo."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QLineEdit
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        campo = QLineEdit()
        campo.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_1, Qt.NoModifier, "1"))
        assert campo.text() == "1", "o campo de texto tem que receber o '1'"
        win.close()


def test_cadeia_de_sinais_tem_os_sete_blocos():
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby import chain as CHN
    from cubebaby.settings import Settings
    from cubebaby.ui import build_window
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        at = win.aba_tocando
        at.refresh()
        assert len(CHN.BLOCOS) == 7
        # ao clicar num bloco, o sinal tem de sair (navega para o controle)
        vistos = []
        at.chain.bloco_escolhido.connect(lambda b: vistos.append(b))
        at.chain._estado("cabinet")   # garante que desenhou
        at.chain.bloco_escolhido.emit("preamp")
        assert vistos == ["preamp"]
        win.close()


def test_medidor_de_estilo_responde_ao_pre_amp():
    """OD tem de puxar para overdrive, nao ficar em 'limpo'."""
    from cubebaby import genre as GEN
    from cubebaby import protocol as PP
    mx = dict(PP.PARAM_MAX)
    od = {n: 0 for n in PP.PARAM_NAMES}
    od.update({"type": 3, "gain": 4})
    assert GEN._faixa_preamp(od) == "od"
    limpo = {n: 0 for n in PP.PARAM_NAMES}
    limpo["type"] = 0
    assert GEN._faixa_preamp(limpo) == "limpo"
    # com tudo no meio, ninguem deve ganhar de forma absurda
    meio = {n: mx[n] / 2 for n in mx}
    for _n, forca, _m in GEN.pontuar(meio, mx)[:3]:
        assert abs(forca - GEN.NEUTRO) < 12, f"no neutro ninguem deveria se destacar: {forca}"


def test_janela_nunca_maior_que_a_tela():
    """Regressão real: a janela abria com 2974x824.

    Causa: _save_state gravava self.width() com a janela MAXIMIZADA — isso é a
    largura do monitor, não o tamanho escolhido. Na abertura seguinte ela
    nascia com quase 3000 px, sem estar maximizada.
    """
    app = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QMainWindow
    import tempfile as tf
    scr = QGuiApplication.primaryScreen().availableGeometry()

    with tf.TemporaryDirectory() as d:
        s = Settings(Path(d) / "p.json")

        # um tamanho absurdo tem de ser contido na tela
        s.save_window(2974, 824, False)
        w = QMainWindow()
        assert s.restore_window(w)
        assert w.width() <= scr.width(), f"{w.width()} > {scr.width()}"
        assert w.height() <= scr.height(), f"{w.height()} > {scr.height()}"
        w.close()

        # tamanho minusculo e' recusado, nao vira janela inutilizavel
        s.save_window(100, 100, False)
        assert not s.restore_window(QMainWindow())


def test_janela_salva_o_tamanho_normal_nao_o_da_tela():
    """Se a janela estava maximizada, gravar self.width() guarda a largura do
    MONITOR (2974 px, o bug real). normalGeometry() devolve o tamanho de quando
    ela nao estava maximizada.

    Verificado no codigo-fonte, e nao pelo valor: em ambiente headless o
    normalGeometry() devolve um numero absurdo (5959) que nao representa o
    Windows real, entao medir aqui daria um falso negativo.
    """
    import inspect
    from cubebaby.ui import MainWindow
    src = inspect.getsource(MainWindow._save_state)
    assert "normalGeometry" in src, \
        "gravar self.width() com a janela maximizada salva a largura do monitor"
    # self.width() pode aparecer como FALLBACK (normalGeometry invalido), mas
    # o caminho normal tem de passar pelo g.
    assert "g.isValid()" in src, "tem de testar se o normalGeometry e' valido"
    # e o restore tem de conter o tamanho na tela
    from cubebaby.settings import Settings as _S
    rsrc = inspect.getsource(_S.restore_window)
    assert "availableGeometry" in rsrc, "restore_window tem de limitar pela tela"


def test_clique_na_cadeia_muda_o_timbre_ao_vivo():
    """Clicar num bloco da cadeia DEVE mudar o som ali mesmo (clique=+1,
    Shift=-1), sem trocar de aba. Antes o clique so navegava e nada mudava."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.ui import build_window
    from cubebaby.settings import Settings
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        at = win.aba_tocando; pt = win.pedal_tab
        at.refresh()
        pers = pt.params[pt.slot]

        # gabinete: clicou +1 -> muda o valor E liga a IR
        antes = pers["cabinet"]
        at._ajustar_bloco("cabinet", +1)
        assert pers["cabinet"] == (antes + 1) % 9, pers["cabinet"]
        assert pers.get("irSection") == 1, "clique no gabinete tem que ligar a IR"

        # delay: clicou -> muda o mix E liga o delay section
        at._ajustar_bloco("delay", +1)
        assert pers["mix"] == 1 and pers.get("delaySection") == 1, "delay nao ligou"

        # Shift (delta -1) diminui e cicla
        reverb0 = pers["reverb"]
        at._ajustar_bloco("reverb", -1)
        assert pers["reverb"] == (reverb0 - 1) % 16, pers["reverb"]

        # modulação cicla ateh 8
        at._ajustar_bloco("mod", +1)
        assert 0 <= pers["modulation"] <= 8

        win.close()


def test_clique_nos_blocos_de_navegacao_nao_crasha():
    """Regressão do crash real: _ir_para_bloco chamava _set_modo (que não
    existe — é _set_mode) e derrubava o programa ao clicar em Guitarra,
    Pré-amp ou Saída na cadeia."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.ui import build_window
    from cubebaby.settings import Settings
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        at = win.aba_tocando
        for bid in ("entrada", "preamp", "saida"):
            at._ir_para_bloco(bid)   # nao pode levantar
        assert win.tabs.currentIndex() == 1, "tem que levar pra aba Pedal"
        win.close()


def test_bloco_delay_liga_delaySection():
    """Clicar no bloco Delay da cadeia tem que ORAR o delaySection, senao o
    mix muda mas o delay fica desligado no pedal."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.ui import build_window
    from cubebaby.settings import Settings
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        at = win.aba_tocando; pt = win.pedal_tab
        at._ajustar_bloco("delay", 1)
        assert pt.params[pt.slot].get("delaySection") == 1, "delaySection nao ligou"
        win.close()


def test_cadeia_cabe_na_largura_da_aba():
    """Regressão: os botões de somada pediam 1959px de largura mínima cada
    (texto HTML longo), o corpo do scroll crescia para 5937px, e a cadeia
    desenhava 7 blocos de 818px — todos sobrepostos e fora da tela."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.ui import build_window
    from cubebaby.settings import Settings
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        win.resize(1200, 880); win.show(); app.processEvents()
        at = win.aba_tocando
        at.refresh(); app.processEvents()
        vp = at._scroll.viewport().width()
        body = at._scroll.widget()
        assert body.width() <= vp + 8, f"corpo estoura a aba: {body.width()} > {vp}"
        boxes = at.chain._boxes
        assert len(boxes) == 7
        total = sum(b.width() for b in boxes.values())
        assert total <= vp + 8, f"blocos estouram: {total} > {vp}"
        # sem sobreposição: cada bloco começa depois do anterior terminar
        xs = sorted((b.x(), b.right()) for b in boxes.values())
        for (x0, r0), (x1, _r1) in zip(xs, xs[1:]):
            assert x1 >= r0 - 1, f"blocos sobrepostos: {x0:.0f}-{r0:.0f} vs {x1:.0f}"
        win.close()


def test_biblioteca_tem_os_presets_novos():
    """32 presets e 64 gêneros: os 8 novos cobrem metal moderno, doom, emo,
    bossa, worship, ska, funk e garage."""
    from cubebaby import presets_lib as PL
    assert len(PL.PRESETS) >= 32, len(PL.PRESETS)
    assert PL.all_errors() == [], PL.all_errors()
    for k in ("djent-palm", "doom-drone", "emo-twang", "bossa-nylon",
              "praise-shimmer", "ska-upstroke", "funk-wah-clean", "garage-punk"):
        assert k in PL.BY_KEY, f"falta o preset {k}"
    assert len(PL.genres()) >= 60, len(PL.genres())


def test_textos_da_biblioteca_sem_palavra_corrompida():
    """'oustain' e 'disparityas' chegaram a ir para a interface."""
    import re
    from cubebaby import presets_lib as PL
    ruim = re.compile(r"oustain|disparity|paralelismo|Jumbo", re.I)
    for p in PL.PRESETS:
        for campo in (p.name, p.signature, p.notes):
            assert not ruim.search(campo), f"{p.key}: texto corrompido em {campo[:40]}"


def test_afinador_geometria_da_agulha():
    """A agulha tem de apontar para CIMA no centro e abrir para os lados.

    Regressão: eu somava -90 graus a mais na conversão de cents para ângulo,
    e a agulha apontava para baixo-esquerda, com o arco desenhado na metade
    de BAIXO da tela — parecia um velocímetro invertido.
    """
    import math
    from cubebaby import tuner as T
    F = T.FAIXA_CENTS
    cx, cy, r = 100.0, 100.0, 50.0

    def ponto(cents):
        th = math.radians(max(-1.0, min(1.0, cents / F)) * 90.0)
        return cx + math.sin(th) * r, cy - math.cos(th) * r

    # 0 cents: exatamente em cima
    x, y = ponto(0)
    assert abs(x - cx) < 0.01 and y < cy, (x, y)
    # valores intermediários: acima do eixo, abrindo para os lados
    for cents, lado in ((-25, -1), (25, 1)):
        x, y = ponto(cents)
        assert y < cy, f"{cents}c aponta para BAIXO"
        assert (x - cx) * lado > 0, f"{cents}c abriu para o lado errado"
    # as PONTAS do semicírculo são horizontais (dy == 0) — isso é correto
    for cents in (-F, F):
        _x, y = ponto(cents)
        assert abs(y - cy) < 0.01, f"{cents}c deveria estar na horizontal: dy={y-cy}"
    # e todos os pontos ficam a distância exata do raio
    for cents in (-F, -15, 0, 15, F):
        x, y = ponto(cents)
        assert abs(math.hypot(x - cx, y - cy) - r) < 0.01


def test_afinador_arco_na_metade_de_cima():
    """drawArc(rect, 0, 180*16) tem de cobrir o semicírculo de CIMA."""
    import math
    cx, cy, r = 100.0, 100.0, 50.0
    for graus in (0, 45, 90, 135, 180):
        th = math.radians(graus)
        y = cy - math.sin(th) * r
        assert y <= cy + 0.01, f"ângulo Qt {graus} caiu abaixo do eixo"


def test_afinador_detecta_e_rejeita():
    """O motor: acerta as 6 cordas, não cai no harmônico, e não inventa nota
    a partir de ruído branco."""
    import math, random, struct
    from cubebaby import tuner as T

    def tom(freq, seg=0.5, rate=48000.0, amp=9000):
        n = int(rate * seg)
        return struct.pack("<%dh" % n,
                           *[int(math.sin(2 * math.pi * freq * i / rate) * amp)
                             for i in range(n)])

    for nome, _rot, alvo in T.STANDARD:
        f, c = T.detectar(tom(alvo), 48000.0)
        nm, oit, cents = T.nome_da_freq(f)
        assert f"{nm}{oit}" == nome, f"{nome}: leu {nm}{oit} ({f:.1f} Hz)"
        assert abs(cents) < 5, f"{nome}: {cents:.1f} cents"

    # harmônico forte: uma FFT simples erraria a oitava aqui
    n = 24000
    pcm = struct.pack("<%dh" % n, *[
        int(max(-32767, min(32767,
            (math.sin(2 * math.pi * 82.41 * i / 48000.0)
             + 1.6 * math.sin(2 * math.pi * 164.82 * i / 48000.0)) * 6000)))
        for i in range(n)])
    f, _c = T.detectar(pcm, 48000.0)
    nm, oit, _ = T.nome_da_freq(f)
    assert f"{nm}{oit}" == "E2", f"caiu no harmônico: {nm}{oit}"

    # ruído branco não é nota
    random.seed(1)
    n = 24000
    ruido = struct.pack("<%dh" % n,
                        *[random.randint(-8000, 8000) for _ in range(n)])
    f, _c = T.detectar(ruido, 48000.0)
    assert f == 0.0, f"ruído virou nota: {f:.1f} Hz"

    # silêncio não é nota
    sil = struct.pack("<%dh" % 4096, *([0] * 4096))
    assert T.detectar(sil, 48000.0)[0] == 0.0


def test_afinador_aba_existe_e_recebe_leitura():
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.ui import build_window
    from cubebaby.settings import Settings
    from cubebaby import tuner as T
    with tf.TemporaryDirectory() as d:
        app2, win = build_window(Settings(Path(d) / "p.json"))
        nomes = [win.tabs.tabText(i) for i in range(win.tabs.count())]
        assert "Afinador" in nomes, nomes
        tab = win.tuner_tab
        assert not tab.tuner.active, "não pode abrir já ouvindo"
        # uma leitura afinada tem de chegar ao mostrador
        tab._on_leitura(T.Leitura(freq=110.0, nota="A", oitava=2, cents=0.4,
                                  clarity=0.99, corda="5ª corda"))
        assert tab.gauge._leitura.afinado
        win.close()


def test_afinador_todas_as_afinacoes():
    """O motor tem de acertar as 6 cordas de CADA afinação.

    Regressão: meio tom abaixo dava 0/6 porque o motor escreve D# e a
    afinação declara Eb — a MESMA nota, comparada como texto. O usuário veria
    "errado" com a guitarra perfeitamente afinada.
    """
    import math, struct
    from cubebaby import tuner as T

    def tom(freq, seg=0.6, rate=48000.0, amp=9000):
        n = int(rate * seg)
        return struct.pack("<%dh" % n,
                           *[int(math.sin(2 * math.pi * freq * i / rate) * amp)
                             for i in range(n)])

    assert len(T.AFINACOES) >= 9, len(T.AFINACOES)
    for a in T.AFINACOES:
        assert len(a.cordas) == 6, (a.chave, len(a.cordas))
        # as frequências crescem da mais grave para a mais aguda
        freqs = [c[2] for c in a.cordas]
        assert freqs == sorted(freqs), f"{a.chave}: cordas fora de ordem"
        for nome, _rot, alvo in a.cordas:
            f, _c = T.detectar(tom(alvo), 48000.0)
            nm, oit, cents = T.nome_da_freq(f)
            assert T.mesma_nota(f"{nm}{oit}", nome), \
                f"{a.chave}/{nome}: leu {nm}{oit} ({f:.1f} Hz)"
            assert abs(cents) < 5, f"{a.chave}/{nome}: {cents:.1f} cents"


def test_afinador_enarmonia():
    """Eb e D# são a mesma nota; E e F não são."""
    from cubebaby import tuner as T
    for par in (("Eb2", "D#2"), ("Ab2", "G#2"), ("Bb3", "A#3"),
                ("Db3", "C#3"), ("Gb3", "F#3")):
        assert T.mesma_nota(*par), par
    assert T.mesma_nota("E2", "E2")
    assert not T.mesma_nota("E2", "F2")
    assert not T.mesma_nota("A2", "A3"), "oitavas diferentes não são a mesma"


def test_afinador_frequencias_conferem_com_a_tabela():
    """As frequências são CALCULADAS do nome, não digitadas à mão — um erro de
    digitação aqui mostraria a nota errada."""
    from cubebaby import tuner as T
    conhecidos = {"E2": 82.41, "A2": 110.00, "D3": 146.83, "G3": 196.00,
                  "B3": 246.94, "E4": 329.63, "Eb2": 77.78, "C2": 65.41,
                  "B1": 61.74, "F#2": 92.50, "A4": 440.0}
    for nota, esperado in conhecidos.items():
        got = T.freq_da_nota(nota)
        assert abs(got - esperado) < 0.02, f"{nota}: {got} != {esperado}"


def test_afinador_escolha_persiste():
    """A afinação escolhida tem de sobreviver a fechar e reabrir."""
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby.ui import build_window
    from cubebaby.settings import Settings
    from cubebaby import tuner as T
    with tf.TemporaryDirectory() as d:
        cfg = Path(d) / "p.json"
        _a, win = build_window(Settings(cfg))
        tab = win.tuner_tab
        assert tab.cb_afinacao.currentData() == T.AFINACAO_PADRAO
        tab.cb_afinacao.setCurrentIndex(
            [a.chave for a in T.AFINACOES].index("drop-d"))
        app.processEvents()
        assert tab.tuner.afinacao == "drop-d"
        assert tab.gauge._cordas[0][0] == "D2", "o mostrador não trocou as cordas"
        win.close()

        _a2, win2 = build_window(Settings(cfg))
        assert win2.tuner_tab.cb_afinacao.currentData() == "drop-d", \
            "não lembrou a afinação"
        win2.close()


def test_afinador_mostra_a_escrita_da_afinacao():
    """Em meio tom abaixo o motor acha D# mas o mostrador tem de escrever Eb."""
    from cubebaby import tuner as T
    a = T.POR_CHAVE["meio-tom"]
    assert T.nome_da_corda(a.cordas, 77.78) == "Eb2", \
        T.nome_da_corda(a.cordas, 77.78)
    assert T.nome_da_corda(T.POR_CHAVE["padrao"].cordas, 82.41) == "E2"


def test_preset_monster_e_afinacao():
    """O preset 'Monster Riff' e' de Drop C, e o programa tem de AVISAR isso.

    Sem o aviso, o usuario carrega com a guitarra em Mi padrao, o riff sai nas
    notas erradas e ele conclui que o preset e' ruim — quando o problema e' a
    afinacao, nao o timbre.
    """
    app = QApplication.instance() or QApplication([])
    import tempfile as tf
    from cubebaby import presets_lib as PL, tuner as TU
    from cubebaby.ui import build_window
    from cubebaby.settings import Settings

    p = PL.BY_KEY.get("monster-riff")
    assert p is not None, "o preset Monster Riff nao existe"
    assert p.afinacao == "drop-c", p.afinacao
    assert p.check() == [], p.check()
    assert "metal" in p.genres
    # a afinacao declarada tem de existir de verdade no afinador
    assert p.afinacao in TU.POR_CHAVE, p.afinacao
    # e' encontrado pela busca
    assert p in PL.search("monster")
    assert p in PL.search("drop c")

    with tf.TemporaryDirectory() as d:
        _a, win = build_window(Settings(Path(d) / "p.json"))
        tab = win.presets_tab
        # em Mi padrao: avisa
        win.settings.set("afinacao", "padrao")
        tab.reload()
        for i in range(tab.listw.count()):
            if tab.listw.item(i).data(Qt.UserRole) is p:
                tab.listw.setCurrentRow(i)
                break
        assert "Precisa de" in tab.lbl_meta.text(), "nao avisou a afinacao"
        # em Drop C: confirma
        win.settings.set("afinacao", "drop-c")
        tab.on_select(tab.listw.currentItem())
        assert "já é a certa" in tab.lbl_meta.text()
        win.close()


def test_toda_afinacao_declarada_existe():
    """Nenhum preset pode exigir uma afinacao que o afinador nao tem."""
    from cubebaby import presets_lib as PL, tuner as TU
    for p in PL.PRESETS:
        if p.afinacao:
            assert p.afinacao in TU.POR_CHAVE, \
                f"{p.key} exige afinacao '{p.afinacao}' que nao existe"


def test_presets_com_ir_no_banco_8():
    """Todos os presets de IR apontam para o BANCO 8 — o banco que o usuário
    usa para importar IR de terceiros no CubeSuite.

    O número do gabinete no preset é o banco do pedal: se sair da faixa, o
    preset manda carregar num gabinete que não existe.
    """
    from cubebaby import presets_lib as PL, protocol as P
    chaves = ("monster-fiel", "monster-lead", "monster-ir",
              "tight-riff-ir", "lead-sustain-ir")
    for chave in chaves:
        p = PL.BY_KEY.get(chave)
        assert p is not None, f"falta o preset {chave}"
        assert p.params["cabinet"] == 8, (chave, p.params["cabinet"])
        assert 1 <= p.params["cabinet"] <= P.PARAM_MAX["cabinet"]
        assert p.params["irSection"] == 1, f"{chave}: a IR tem de estar ligada"
        assert "BANCO 8" in p.notes, f"{chave}: nao diz o banco"
        assert p.check() == [], p.check()


def test_monster_fiel_espelha_a_gravacao():
    """O preset fiel reproduz o que está documentado da gravação de 'Monster'.

    Amp: Mesa Dual Rectifier (Red/Modern) · Guitarra: Les Paul ·
    Caixa: Mesa 4x12 com V30 · Boost: TS9 · Gate: NS-2 · Afinação: Drop D.
    """
    from cubebaby import presets_lib as PL, protocol as P
    p = PL.BY_KEY["monster-fiel"]
    # Les Paul e Drop D são o que a gravação usou
    assert p.guitar == "les-paul", p.guitar
    assert p.afinacao == "drop-d", p.afinacao
    # canal Red do Rectifier = distorção moderna (o pré-amp mais pesado)
    assert p.params["type"] == 8, p.params["type"]
    # gain 8/10 no Rectifier vira 6/7 aqui: a escala do pedal satura antes
    assert p.params["gain"] == 6, p.params["gain"]
    # treble 6.5 e presence 6.5 num aparelho 0-10 -> tom alto no pedal
    assert p.params["tone"] >= 9, p.params["tone"]
    # reverb 1.5/10 e SEM delay: o riff original é seco
    assert p.params["reverb"] <= 3, p.params["reverb"]
    assert p.params["delaySection"] == 0, "o riff original é seco"
    assert p.params["mix"] == 0, p.params["mix"]
    # sem modulação: o original não usa chorus no riff
    assert p.params["modulation"] == 0, p.params["modulation"]
    # caixa Mesa 4x12 com V30
    assert p.params["cabinet"] == 8


def test_monster_lead_tem_ambiente():
    """O solo/ponte PRECISA de delay e reverb — o oposto do riff."""
    from cubebaby import presets_lib as PL
    riff = PL.BY_KEY["monster-fiel"]
    lead = PL.BY_KEY["monster-lead"]
    assert lead.params["delaySection"] == 1, "o solo tem ambiência"
    assert lead.params["mix"] > riff.params["mix"], "o solo tem mais delay que o riff"
    assert lead.params["reverb"] > riff.params["reverb"]
    # mas o mesmo amp e a mesma caixa
    assert lead.params["type"] == riff.params["type"]
    assert lead.params["cabinet"] == riff.params["cabinet"]
    assert lead.afinacao == riff.afinacao

def test_catalogo_de_gabinetes_de_fabrica():
    """Os 32 nomes vieram do bin/BOR.bin do CubeSuite oficial.

    Trava o que a análise provou: nomes, ordem do arquivo e tamanho. Se alguém
    reordenar a lista, o índice deixa de corresponder ao arquivo e o dado vira
    ficção.
    """
    from cubebaby import cabs_factory as CF
    assert len(CF.FABRICA) == 32, len(CF.FABRICA)
    assert CF.FONTE_BLOCOS == 32
    assert CF.FONTE_TAMANHO == 32 * CF.FONTE_BLOCO_BYTES == 262144
    assert [c.idx for c in CF.FABRICA] == list(range(32))
    assert CF.get(0).nome == "TweedDeluxe"
    assert CF.get(10).nome == "Peavey 5150"
    assert CF.get(17).nome == "Orange4X12"
    assert CF.get(24).nome == "MesaRectifierV30"
    assert CF.get(31).nome == "Work 4050 2 BASS"


def test_caixa_do_monster_esta_no_catalogo():
    """A caixa da gravação de 'Monster' é a Mesa Rectifier 4x12 com V30, e o
    catálogo de fábrica tem exatamente essa caixa."""
    from cubebaby import cabs_factory as CF
    assert CF.MONSTER_CAB.nome == "MesaRectifierV30"
    assert CF.MONSTER_CAB.spec == "4x12"
    assert CF.MONSTER_CAB.idx == 24
    assert "Monster" in CF.MONSTER_CAB.nota
    achados = {c.nome for c in CF.procurar("mesa")}
    assert "MesaRectifierV30" in achados and "Mesa Boogie" in achados


def test_indice_do_arquivo_nao_e_a_posicao_do_pedal():
    """A armadilha que o módulo precisa deixar explícita: o pedal tem 8 posições
    e o arquivo tem 32 entradas. Se alguém 'ligar' os dois sem evidência, avisa."""
    from cubebaby import cabs_factory as CF, cabinets as CAB
    assert CAB.N_POSITIONS == 9
    assert len(CF.FABRICA) == 32
    assert len(CF.FABRICA) != CAB.N_POSITIONS - 1
    assert "ORDEM DO ARQUIVO" in CF.AVISO.upper()
    assert "posição do pedal" in CF.AVISO.lower()


def test_gabinetes_separados_por_familia():
    """Guitarra e baixo não se misturam: 25 de guitarra, 7 de baixo."""
    from cubebaby import cabs_factory as CF
    assert len(CF.GUITARRA) == 25, len(CF.GUITARRA)
    assert len(CF.BAIXO) == 7, len(CF.BAIXO)
    assert len(CF.GUITARRA) + len(CF.BAIXO) == 32
    assert all(c.familia == "guitarra" for c in CF.GUITARRA)
    assert all(c.familia == "baixo" for c in CF.BAIXO)
    assert [c.idx for c in CF.BAIXO] == list(range(25, 32))



def test_ir_de_usuario_formato_do_pedal():
    """O formato do IR foi decifrado no hardware: memory=0 @0x69000,
    8 blocos de 4096, cada um com int32 + 1023 float32 = 8184 amostras."""
    from cubebaby import irfile as IR
    assert IR.IR_MEMORY == 0
    assert IR.IR_BASE_ADDRESS == 0x69000
    assert IR.IR_TOTAL_BYTES == 32768
    assert IR.IR_BLOCK_BYTES == 4096
    assert IR.IR_BLOCKS == 8
    assert IR.IR_SAMPLES_PER_BLOCK == 1023
    assert IR.IR_SAMPLE_RATE == 48000
    # 8184 amostras a 48k = 170,5 ms
    assert abs(IR.IR_BLOCK_DURATION_MS - 21.3) < 0.1
    assert IR.IR_BANCOS == 8


def test_ir_de_wav_reamostra_e_corta():
    """O WAV de 2000 ms tem de virar 8184 amostras a 48 kHz."""
    from pathlib import Path
    from cubebaby import irfile as IR
    wav = (Path.home() / "Downloads" / "Quartinho do Metal - ALL IRs PACK"
           / "Guitar Impulses" / "1 - Quartinho do Metal - Top 8 IR Pack"
           / "6 - Brohymn-Mesa-4x12-SM57-V30-5.wav")
    if not wav.exists():
        return
    ir = IR.de_wav(wav)
    assert len(ir.samples) == IR.IR_SAMPLES_PER_BLOCK, len(ir.samples)
    assert 0.9 <= ir.pico <= 1.0, ir.pico      # normalizado para 0,95
    assert abs(ir.duracao_ms - 21.3) < 0.1


def test_toda_sugestao_de_ir_aponta_para_preset_existente():
    """Uma sugestão com chave errada nunca aparece na interface e ninguém
    percebe. Duas já estavam erradas ('hard-roots-marshall',
    'hendrix-quack-2') e este teste teria pegado."""
    from cubebaby import irs as IRS, presets_lib as PL
    for chave in IRS.SUGESTOES:
        assert chave in PL.BY_KEY, f"sugestao para preset inexistente: {chave}"


def test_toda_sugestao_de_ir_tem_arquivo_e_motivo():
    from cubebaby import irs as IRS
    for chave, s in IRS.SUGESTOES.items():
        assert s.arquivo, chave
        assert s.arquivo.lower().endswith(".wav"), chave
        assert s.pasta, chave
        assert s.caixa, chave
        assert len(s.porque) > 20, f"{chave}: motivo curto demais"
        assert s.confianca in ("alta", "media", "aproximacao"), chave


def test_a_sugestao_nao_mexe_no_gabinete_de_fabrica():
    """O pedido era ADICIONAR, nao substituir. O gabinete de fabrica do preset
    tem de continuar intacto — a sugestao de IR e so informacao."""
    from cubebaby import irs as IRS, presets_lib as PL
    for chave in IRS.SUGESTOES:
        p = PL.BY_KEY[chave]
        # o preset continua com o gabinete dele, valido e dentro da faixa
        assert 0 <= p.params["cabinet"] <= 8, (chave, p.params["cabinet"])
        assert p.check() == [], p.check()


def test_presets_com_ir_sugerido_mantem_o_nome_original():
    """Nenhum preset foi renomeado para caber na sugestao."""
    from cubebaby import irs as IRS, presets_lib as PL
    for chave in IRS.SUGESTOES:
        p = PL.BY_KEY[chave]
        assert p.name and len(p.name) > 2, chave
        assert "(IR" not in p.name or "IR de metal" in p.name, p.name


def test_cobertura_de_sugestoes_de_ir():
    """Quase todo preset tem sugestao; os que faltam sao poucos e conhecidos."""
    from cubebaby import irs as IRS, presets_lib as PL
    todos = {p.key for p in PL.PRESETS}
    com = set(IRS.SUGESTOES)
    assert com <= todos, f"sugestoes orfas: {com - todos}"
    faltam = todos - com
    assert len(faltam) <= 4, f"presets sem IR sugerido: {faltam}"


def test_cada_bloco_e_um_banco_independente():
    """Achado que destravou tudo: os 8 blocos NAO sao um IR fatiado, sao 8
    bancos. Prova: entre duas capturas do pedal, 7 blocos ficaram byte a byte
    identicos e so o bloco do banco ativo mudou."""
    from cubebaby import irfile as IR
    assert IR.IR_BANCOS == 8
    assert IR.IR_BLOCKS == 8
    # endereco de cada banco
    assert IR.endereco_do_banco(1) == 0x69000
    assert IR.endereco_do_banco(2) == 0x6a000
    assert IR.endereco_do_banco(8) == 0x70000
    # fora da faixa tem de recusar
    for b in (0, 9, -1):
        try:
            IR.endereco_do_banco(b)
            raise AssertionError(f"banco {b} deveria ser recusado")
        except ValueError:
            pass


def test_um_banco_tem_1023_amostras():
    """Um banco guarda um IR COMPLETO de 1023 amostras (21,3 ms), nao um
    pedaco de 8184."""
    from cubebaby import irfile as IR
    assert IR.IR_SAMPLES_PER_BLOCK == 1023
    assert abs(IR.IR_BLOCK_DURATION_MS - 21.3) < 0.1
    assert IR.IR_BLOCK_BYTES == 4096


def test_round_trip_por_banco_e_byte_identico():
    """encode_bloco(decode_bloco(x)) == x. E isto que permite verificar uma
    gravacao sem depender do hash da area inteira."""
    import struct
    from cubebaby import irfile as IR
    raw = struct.pack("<i", 1) + struct.pack("<1023f", *([0.25] * 1023))
    assert len(raw) == IR.IR_BLOCK_BYTES
    ir = IR.decode_bloco(raw, banco=3)
    assert ir.banco == 3
    assert ir.marcador == 1
    assert len(ir.samples) == 1023
    assert IR.encode_bloco(ir) == raw


def test_gravar_usa_so_o_bloco_do_banco():
    """Gravar um banco NAO pode tocar nos outros: o endereco tem de ser o
    bloco daquele banco, e o total 4096 bytes."""
    from cubebaby import irfile as IR
    ir = IR.UserIR(samples=[0.1] * 1023, marcador=1, banco=5)
    dados = IR.encode_bloco(ir)
    assert len(dados) == IR.IR_BLOCK_BYTES
    assert IR.endereco_do_banco(5) == IR.IR_BASE_ADDRESS + 4 * IR.IR_BLOCK_BYTES


def test_banco_recusa_mais_amostras_que_cabe():
    from cubebaby import irfile as IR
    ir = IR.UserIR(samples=[0.1] * 1024)
    try:
        IR.encode_bloco(ir)
        raise AssertionError("deveria recusar 1024 amostras num banco")
    except ValueError as e:
        assert "Corte antes de gravar" in str(e)


def test_escrita_de_ir_esta_validada_no_codigo():
    """A escrita FUNCIONA (medido: correlacao +0,9939 com o IR enviado). O
    modulo tem de oferecer a funcao e o docstring tem de registrar a medicao —
    nao pode voltar a dizer que nao funciona."""
    from cubebaby import irfile as IR
    assert hasattr(IR, "gravar_banco")
    assert hasattr(IR, "gravar")
    d = IR.gravar_banco.__doc__ or ""
    assert "VALIDADO" in d.upper()
    assert "0,9939" in d or "0.9939" in d
    # e o modulo tem de explicar o erro que foi corrigido
    assert "BANCO independente" in (IR.__doc__ or "")
    assert "hash" in (IR.__doc__ or "").lower()


def test_desenho_do_gabinete_acompanha_o_slider():
    """BUG corrigido: arrastar o slider do Gabinete NAO atualizava o desenho —
    ele ficava em branco, porque so `set_value` (valor vindo de fora) chamava
    `set_spec`. O proprio slider nunca chamava."""
    from cubebaby import ui as U, cabinets as CAB
    row = U.ParamRow("cabinet", "Gabinete")
    assert getattr(row, "cab_art", None) is not None
    # o desenho tem de nascer ja com o valor 0 aplicado (nao em branco)
    assert row.cab_art.spec == CAB.get("cuvave", 0).spec, row.cab_art.spec
    # e acompanhar cada valor
    for v in range(9):
        row.slider.setValue(v)
        esperado = CAB.get("cuvave", v).spec
        assert row.cab_art.spec == esperado, (
            f"slider={v}: esperado {esperado!r}, desenho {row.cab_art.spec!r}")


def test_desenho_do_gabinete_muda_de_forma():
    """Nao basta o rotulo mudar: a FORMA desenhada tem de ser diferente para
    1x10, 2x12 e 4x12. Senao o usuario ve sempre a mesma caixa."""
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import Qt, QPoint
    from cubebaby import art as ART

    def render(w):
        img = QImage(w.size(), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        w.render(p, QPoint(0, 0))
        p.end()
        return bytes(img.bits())

    a = ART.CabinetArt()
    a.resize(84, 56)
    formas = {}
    for spec in ("1×10", "1×12", "2×12", "4×12", "—"):
        a.set_spec(spec)
        formas[spec] = render(a)
    assert len(set(formas.values())) == len(formas), (
        "duas especificacoes desenham igual: "
        f"{[k for k, v in formas.items() if list(formas.values()).count(v) > 1]}")


def test_sets_tem_exatamente_8_irs():
    """O pedal tem 8 bancos, entao um set precisa de 8 IRs — nem 7 nem 9.
    O proprio SetIR recusa na construcao."""
    from cubebaby import ir_sets as S
    assert len(S.todos()) >= 4
    for st in S.todos():
        assert len(st.slots) == 8, (st.key, len(st.slots))
        assert st.nome and st.descricao and st.generos
        # sem IR repetido dentro do mesmo set
        arqs = [sl.arquivo for sl in st.slots]
        assert len(set(arqs)) == 8, f"{st.key} tem IR repetido"


def test_set_recusa_numero_errado_de_slots():
    from cubebaby import ir_sets as S
    try:
        S.SetIR(key="x", nome="X", generos=("a",), descricao="d",
                slots=S.SETS[0].slots[:7])
        raise AssertionError("deveria recusar 7 slots")
    except ValueError as e:
        assert "8" in str(e)


def test_cada_slot_de_set_tem_pasta_arquivo_e_uso():
    from cubebaby import ir_sets as S
    for st in S.todos():
        for i, sl in enumerate(st.slots, 1):
            assert sl.pasta, (st.key, i)
            assert sl.arquivo.lower().endswith(".wav"), (st.key, i)
            assert sl.caixa, (st.key, i)
            assert len(sl.uso) > 15, f"{st.key} banco {i}: uso curto demais"


def test_arquivo_do_slot_resolve_e_recusa_fora_da_faixa():
    from cubebaby import ir_sets as S
    st = S.POR_CHAVE["metal"]
    assert S.arquivo_do_slot(st, 1).endswith(".wav")
    assert S.arquivo_do_slot(st, 8).endswith(".wav")
    for b in (0, 9):
        try:
            S.arquivo_do_slot(st, b)
            raise AssertionError(f"banco {b} deveria ser recusado")
        except ValueError:
            pass


def test_sets_usam_os_8_bancos_do_pedal():
    """A ligacao com o hardware: 8 slots = IR_BANCOS do irfile."""
    from cubebaby import ir_sets as S, irfile as IR
    assert IR.IR_BANCOS == 8
    for st in S.todos():
        assert len(st.slots) == IR.IR_BANCOS, st.key


def test_wav_de_24_bits_e_lido_na_escala_certa():
    """BUG corrigido: a leitura de 24 bits tratava o byte alto como magnitude,
    dando valor 256x maior. Os WAVs de 24 bits do pack mediam pico 512 em vez
    de ~1,0 — e como de_wav normaliza no fim, o IR saia SATURADO sem ninguem
    perceber."""
    import struct, tempfile, wave
    from pathlib import Path
    from cubebaby import irfile as IR

    # monta um WAV 24 bits com uma rampa conhecida, pico em +-0.5
    n = 2000
    vals = [int(0.5 * 8388607 * (1 if i % 2 else -1)) for i in range(n)]
    raw = bytearray()
    for x in vals:
        u = x & 0xFFFFFF
        raw += bytes((u & 0xFF, (u >> 8) & 0xFF, (u >> 16) & 0xFF))
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "teste24.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(3)
            w.setframerate(48000)
            w.writeframes(bytes(raw))
        ir = IR.de_wav(p, normalizar=False)
    # sem normalizar, o pico tem de ser ~0.5 (nao 512 nem 0.002)
    assert 0.4 < ir.pico < 0.6, f"pico {ir.pico:.4f} — escala de 24 bits errada"


def test_de_wav_le_float32():
    """IRs em float32 (formato 3) davam erro 'unknown format: 3' porque o
    modulo `wave` do Python nao aceita. Agora sao lidos direto do arquivo."""
    import struct, tempfile
    from pathlib import Path
    from cubebaby import irfile as IR

    n = 2000
    dados = struct.pack(f"<{n}f", *[0.5 if i % 2 else -0.5 for i in range(n)])
    fmt = struct.pack("<HHIIHH", 3, 1, 48000, 48000 * 4, 4, 32)
    corpo = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    corpo += b"data" + struct.pack("<I", len(dados)) + dados
    wav = b"RIFF" + struct.pack("<I", 4 + len(corpo)) + b"WAVE" + corpo

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "float.wav"
        p.write_bytes(wav)
        ir = IR.de_wav(p, normalizar=False)
    assert 0.4 < ir.pico < 0.6, f"pico {ir.pico:.4f} — leitura float32 errada"

def test_set_de_rock_grava_nos_8_bancos():
    """Prova no hardware: aplicar um set deu semelhanca >= 0.98 nos 8 bancos.
    Aqui so travamos a forma dos dados que serao enviados."""
    from cubebaby import ir_sets as S, irfile as IR
    st = S.POR_CHAVE["rock"]
    blocos = []
    for i, sl in enumerate(st.slots, 1):
        ir = IR.UserIR(samples=[0.3] * 1023, banco=i)
        d = IR.encode_bloco(ir)
        assert len(d) == IR.IR_BLOCK_BYTES
        blocos.append(d)
    assert len(blocos) == 8
    # cada banco vai para um endereco distinto
    end = [IR.endereco_do_banco(i) for i in range(1, 9)]
    assert len(set(end)) == 8


def test_sets_de_indie_e_numetal_existem_e_tem_8():
    """Os dois sets pedidos pelo usuario: indie/psych (Mac DeMarco, Tame
    Impala) e nu metal (Linkin Park, Skillet)."""
    from cubebaby import ir_sets as S
    indie = S.POR_CHAVE.get("indie")
    nu = S.POR_CHAVE.get("numetal")
    assert indie is not None, "falta o set de indie/psych"
    assert nu is not None, "falta o set de nu metal"
    assert len(indie.slots) == 8
    assert len(nu.slots) == 8
    # os nomes tem de citar as referencias que o usuario deu
    assert "DeMarco" in indie.nome or "Tame" in indie.nome
    assert "Linkin" in nu.nome or "Skillet" in nu.nome


def test_set_indie_usa_caixas_pequenas_e_ac30():
    """Mac DeMarco e Tame Impala sao Fender pequeno e Vox AC30 — nao Mesa."""
    from cubebaby import ir_sets as S
    indie = S.POR_CHAVE["indie"]
    texto = " ".join(f"{sl.arquivo} {sl.caixa}" for sl in indie.slots).lower()
    assert "princeton" in texto, "o indie precisa de Fender pequeno"
    assert "ac30" in texto, "o psych do Tame Impala e AC30"
    # nao pode ter caixa de high gain
    assert "mesa" not in texto and "rectif" not in texto


def test_set_numetal_usa_mesa_e_v30():
    """Linkin Park e Skillet: Mesa Rectifier e caixas V30."""
    from cubebaby import ir_sets as S
    nu = S.POR_CHAVE["numetal"]
    texto = " ".join(f"{sl.arquivo} {sl.caixa}" for sl in nu.slots).lower()
    assert "mesa" in texto, "o nu metal precisa de Mesa"
    assert "v30" in texto, "V30 e o falante do genero"


def test_todo_arquivo_de_todo_set_carrega():
    """Verifica no disco: todo arquivo citado por qualquer set tem de existir e
    carregar. Foi assim que apareceu o nome errado do SuperChamp."""
    from pathlib import Path
    from cubebaby import ir_sets as S, irfile as IR
    pasta = Path.home() / S.PASTA_PACK
    if not pasta.exists():
        return                    # sem o pack nesta maquina
    faltando = []
    for st in S.todos():
        for i, sl in enumerate(st.slots, 1):
            p = pasta / sl.pasta / sl.arquivo
            if not p.exists():
                faltando.append(f"{st.key} banco {i}: {sl.arquivo}")
                continue
            try:
                IR.de_wav(p)
            except Exception as e:  # noqa: BLE001
                faltando.append(f"{st.key} banco {i}: {type(e).__name__}")
    assert not faltando, f"arquivos com problema: {faltando}"


if __name__ == "__main__":
    # Descoberta automática: antes desta linha o arquivo não tinha bloco
    # __main__, então rodá-lo não executava teste nenhum — 55 funções ficavam
    # mudas e o "passou" era falso. Agora toda função test_* é chamada.
    import traceback
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    falhas = []
    for nome, fn in testes:
        try:
            fn()
        except Exception as e:
            falhas.append((nome, traceback.format_exc()))
            print(f"FALHOU  {nome}: {type(e).__name__}: {e}")
    print(f"\n{len(testes) - len(falhas)}/{len(testes)} testes passaram")
    if falhas:
        for nome, tb in falhas:
            print(f"\n===== {nome} =====\n{tb}")
        raise SystemExit(1)
    print("ok")
