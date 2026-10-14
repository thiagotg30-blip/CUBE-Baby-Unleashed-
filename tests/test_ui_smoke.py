"""Testa a UI sem mostrar a janela: sobe o QApplication offscreen, monta a
MainWindow e exercita PresetsTab + voicing.

Rode:  .venv\\Scripts\\python.exe tests\\test_ui_smoke.py

Nota: a MainWindow é montada SEM pedal de propósito. Com pedal conectado,
apply_params abre um QMessageBox modal ("Gravar no pedal?") que bloquearia
este teste headless. A gravação é exercitada direto no SimulatedPedal, no fim.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cubebaby.settings import Settings
from cubebaby import guides as GU
from cubebaby import guitars as GT
from cubebaby import presets_lib as PL
from cubebaby import protocol as P
from cubebaby.client import SimulatedPedal
from cubebaby.ui import MainWindow


def test_ui_smoke():
    assert PL.all_errors() == [], PL.all_errors()
    app = QApplication.instance() or QApplication([])

    _tmp = tempfile.TemporaryDirectory()
    win = MainWindow(settings=Settings(Path(_tmp.name) / "p.json"))
    # 8 abas: Tocando, Pedal, Presets, Audio, Afinador, IR, Biblioteca, Apoiar
    assert win.tabs.count() == 8, win.tabs.count()
    assert win.tabs.tabText(0) == "Tocando"
    pt = win.presets_tab
    assert pt.listw.count() == len(PL.PRESETS), pt.listw.count()
    assert pt.current_preset() is not None

    # filtro por gênero
    pt.cb_genre.setCurrentIndex(1)
    assert pt.listw.count() >= 1
    pt.cb_genre.setCurrentIndex(0)
    assert pt.listw.count() == len(PL.PRESETS)

    # busca por texto (conta pode mudar conforme a biblioteca cresce)
    pt.ed_search.setText("grunge")
    assert pt.listw.count() >= 1, pt.listw.count()
    assert pt.current_preset().key == "grunge-mud"
    assert pt.lbl_sig.text(), "a assinatura do preset não apareceu"
    pt.ed_search.setText("")
    assert pt.listw.count() == len(PL.PRESETS)

    # carregar o preset leva para a aba do pedal, já adapted à guitarra global
    pt.load_selected()
    assert win.tabs.currentIndex() == 0
    assert set(win.pedal_tab.params["A"]) == set(P.PARAM_NAMES)
    assert win._preset_source["A"] == "grunge-mud"

    # trocar a guitarra re-adapta os slots de preset, sem mexer nos manuais
    win.set_guitar("stratocaster")
    after_guitar = dict(win.pedal_tab.params["A"])
    assert after_guitar != PL.BY_KEY["grunge-mud"].adapted_for("les-paul"), \
        "trocar de guitarra não re-adaptou o slot do preset"
    for n, v in after_guitar.items():
        assert 0 <= v <= P.PARAM_MAX[n], (n, v)

    # slot com valor manual não é tocado pela troca de guitarra
    win.pedal_tab.params["B"] = P.empty_params()
    win.pedal_tab.params["B"]["volume"] = 42
    win._preset_source["B"] = None
    win.set_guitar("tele")
    assert win.pedal_tab.params["B"]["volume"] == 42, "alterou slot com valor manual"

    # carregar o original marca o slot como cru (não re-adapta depois)
    pt.ed_search.setText("jazz")
    pt.load_raw()
    assert win._preset_source[win.pedal_tab.slot] is None
    assert win.pedal_tab.params[win.pedal_tab.slot] == PL.BY_KEY["jazz-clean"].params

    # toda a biblioteca carrega inteira, em toda guitarra, sem estourar a faixa
    for p in PL.PRESETS:
        for g in GT.keys():
            vals = p.adapted_for(g)
            assert set(vals) == set(P.PARAM_NAMES), (p.key, g)
            for n, v in vals.items():
                assert 0 <= v <= P.PARAM_MAX[n], (p.key, g, n, v)

    # todo parâmetro tem dica de iniciante
    assert GU.coverage() == set(), GU.coverage()

    # aba de doações existe e está acessível
    assert win.donate_tab is not None
    assert win.tabs.indexOf(win.donate_tab) == 7

    win.close()
    return True


def test_preset_chega_ao_pedal_simulado():
    """Um preset curado tem de sobreviver à gravação e à leitura de conferência."""
    pedal = SimulatedPedal()
    p = PL.BY_KEY["metal-tight"]
    params = p.adapted_for(p.guitar)
    assert pedal.write_all_params("A", params) in ("ok", "ok-readback")
    bank = pedal.read_bank()
    for n in P.PARAM_NAMES:
        assert bank["A"][n] == params[n], (n, bank["A"][n], params[n])


if __name__ == "__main__":
    test_ui_smoke()
    test_preset_chega_ao_pedal_simulado()
    print("ok")
