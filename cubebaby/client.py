"""Conexão USB/MIDI (SysEx) com o CUBE Baby via python-rtmidi, e um pedal simulado."""
from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from . import protocol as P
from .settings import data_dir

DEFAULT_TIMEOUT = 2.0
WRITE_TIMEOUT = 0.7   # o pedal responde um ack em ~15 ms; se passar disso, a escrita se perdeu
WRITE_RETRIES = 3     # escrever o mesmo valor de novo é inofensivo
SETTLE = 0.15         # o pedal fica ocupado ~100 ms depois de aplicar (ex.: trocar o tipo)
NAME_HINTS = ("cube", "mvave", "m-vave", "cuvave")
# No Windows a lista de saída costuma trazer "Microsoft GS Wavetable Synth" na
# frente do pedal. Escolher a porta 0 por falta de match conectava no
# sintetizador de software e o pedal nunca respondia.
BAD_HINTS = ("wavetable", "synth", "through", "mapeador", "mapper")

# Limites medidos no pedal real (SINCO-CubeBaby).
# 64 bytes: sempre respondeu, em qualquer memory e endereço testado.
# 512 bytes: o pedal PAROU de responder e só voltou depois de reconectar o USB.
# Por isso o teto é 64 e quem precisa de mais divide em pedaços.
MAX_READ_BYTES = 64
PING_TIMEOUT = 0.6    # o pedal responde a identidade em ~15 ms quando está livre
RECOVERY_WAITS = (0.3, 1.0, 2.5)   # espera progressiva antes de desistir


def _MATCH_IDENTITY(m) -> bool:
    return m.kind == "identity-response"


_LOG_LOCK = threading.Lock()


def log_path() -> Path:
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "pedal.log"


def trace(direction: str, data) -> None:
    """Registra tudo que vai e volta do pedal (hex) em ~/CUBEBabyUnleashed/pedal.log."""
    try:
        p = log_path()
        if p.exists() and p.stat().st_size > 2_000_000:
            p.write_text("", encoding="utf-8")
        text = data if isinstance(data, str) else bytes(data).hex(" ")
        with _LOG_LOCK, open(p, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" {direction} {text}\n")
    except Exception:  # noqa: BLE001 - log nunca pode derrubar o programa
        pass


class PedalError(Exception):
    pass


class PedalTimeout(PedalError):
    def __init__(self, msg="O pedal não respondeu a tempo. Verifique o cabo USB e se o CubeSuite está fechado."):
        super().__init__(msg)


def list_ports() -> tuple[list[str], list[str]]:
    """Retorna (entradas, saídas) MIDI do sistema."""
    try:
        import rtmidi
    except ImportError as exc:  # pragma: no cover
        raise PedalError("Biblioteca python-rtmidi não instalada (pip install python-rtmidi).") from exc
    try:
        mi, mo = rtmidi.MidiIn(), rtmidi.MidiOut()
    except Exception as exc:  # noqa: BLE001 - rtmidi levanta SystemError sem subsistema MIDI
        raise PedalError(f"Sistema MIDI indisponível neste computador ({exc}).") from exc
    try:
        return list(mi.get_ports()), list(mo.get_ports())
    finally:
        mi.delete(); mo.delete()


def guess_port(ports: list[str]) -> int:
    """Escolhe a porta do pedal.

    Prefere um nome que case com NAME_HINTS e nunca escolhe uma porta
    claramente sintética (BAD_HINTS): no Windows o "Microsoft GS Wavetable
    Synth" costuma vir na frente do pedal, e escolhê-lo faz a conexão falhar.
    """
    for i, name in enumerate(ports):
        if any(h in name.lower() for h in NAME_HINTS):
            return i
    uteis = [i for i, n in enumerate(ports)
             if not any(b in n.lower() for b in BAD_HINTS)]
    if uteis:
        return uteis[0]
    return 0 if ports else -1


class _Assembler:
    """Remonta SysEx que chegam fatiados."""

    def __init__(self, emit: Callable[[bytes], None]):
        self._emit, self._buf, self._in = emit, bytearray(), False

    def push(self, chunk) -> None:
        for b in chunk:
            if b >= 0xF8:
                continue
            if self._in:
                self._buf.append(b)
                if b == 0xF7:
                    self._emit(bytes(self._buf)); self._buf = bytearray(); self._in = False
            elif b == 0xF0:
                self._buf = bytearray([b]); self._in = True


class BasePedal:
    """Interface comum (pedal real e simulado). Todas as chamadas são bloqueantes:
    rode em thread de trabalho, nunca na thread da interface."""

    connected: bool = False
    device_name: str = ""

    def identify(self) -> str: raise NotImplementedError
    def read_memory(self, memory: int, address: int, length: int) -> bytes: raise NotImplementedError
    def write_memory(self, memory: int, address: int, data: bytes) -> bool: raise NotImplementedError
    def disconnect(self) -> None: self.connected = False

    # ---- operações de alto nível --------------------------------------------
    def read_bank(self) -> dict:
        data = self.read_memory(P.BANK_MEMORY, P.BANK_ADDRESS, P.PRESET_BANK_BYTES)
        return P.decode_preset_bank(data)

    def write_live_param(self, slot: str, name: str, value: int) -> bool:
        addr = P.live_param_address(name, slot)
        return self.write_memory(P.LIVE_PARAM_MEMORY, addr, bytes((P.clamp_param(name, value),)))

    last_ack = None  # valor bruto da última resposta (ack) do pedal

    def write_all_params(self, slot: str, params: dict, progress: Optional[Callable[[int], None]] = None) -> str:
        """Grava os 13 parâmetros. Não confia só no 'ack': se algum vier recusado, lê de volta
        e compara. Retorna 'ok' ou 'ok-readback'; levanta PedalError se de fato não aplicou."""
        acks: dict[str, tuple[bool, object]] = {}
        for i, name in enumerate(P.PARAM_NAMES):
            ok = self.write_live_param(slot, name, params[name])
            acks[name] = (ok, self.last_ack)
            if progress:
                progress(int((i + 1) / len(P.PARAM_NAMES) * 100))
            time.sleep(0.015)
        refused = [n for n, (ok, _) in acks.items() if not ok]
        trace("#", f"gravação slot {slot}: acks=" + ", ".join(f"{n}={a[1]}" for n, a in acks.items()))
        if not refused:
            return "ok"
        try:
            bank = self.read_bank()
        except PedalError as exc:
            raise PedalError(f"O pedal respondeu 'recusado' para: {', '.join(refused)}, e a leitura de conferência falhou ({exc}). Veja {log_path()}") from exc
        diff = [n for n in P.PARAM_NAMES if bank[slot][n] != params[n]]
        trace("#", f"conferência por leitura: diferentes={diff or 'nenhum'}")
        if not diff:
            return "ok-readback"
        raise PedalError(
            f"O pedal não aplicou: {', '.join(diff)} (respostas: "
            + ", ".join(f"{n}={acks[n][1]}" for n in diff) + f"). Veja {log_path()}")


class CubeBabyClient(BasePedal):
    def __init__(self) -> None:
        self._in = None
        self._out = None
        self._lock = threading.RLock()         # serializa pedidos: o pedal não lida com concorrência
        self._pending: list[tuple[Callable, threading.Event, list]] = []
        self._plock = threading.Lock()
        self._asm = _Assembler(self._on_sysex)
        self.connected = False
        self.device_name = ""

    # ---- conexão -------------------------------------------------------------
    def connect(self, in_index: int, out_index: int) -> None:
        import rtmidi
        self.disconnect()
        mi, mo = rtmidi.MidiIn(), rtmidi.MidiOut()
        try:
            mi.ignore_types(sysex=False, timing=True, active_sense=True)
            mi.open_port(in_index)
            mo.open_port(out_index)
        except Exception as exc:
            mi.delete(); mo.delete()
            raise PedalError(
                f"Não consegui abrir a porta MIDI ({exc}). Feche o CubeSuite e qualquer outro app que use o pedal."
            ) from exc
        mi.set_callback(lambda event, _data=None: self._asm.push(event[0]))
        self._in, self._out = mi, mo
        self.connected = True
        try:
            self.device_name = self.identify()
        except PedalTimeout:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        for port in (self._in, self._out):
            if port is not None:
                try:
                    port.cancel_callback() if port is self._in else None
                    port.close_port()
                    port.delete()
                except Exception:
                    pass
        self._in = self._out = None
        self.connected = False

    # ---- plumbing ------------------------------------------------------------
    def _on_sysex(self, data: bytes) -> None:
        trace("<", data)
        try:
            msg = P.decode_message(data)
        except P.DecodeError:
            trace("!", "mensagem ilegível (ignorada)")
            return
        trace(" ", f"= {msg.kind} ack_raw={msg.raw_value} mem={msg.memory} addr={msg.address:#x} len={len(msg.data)}")
        with self._plock:
            for entry in self._pending:
                match, event, box = entry
                if match(msg):
                    box.append(msg); event.set()
                    self._pending.remove(entry)
                    return

    def _send(self, sysex: bytes) -> None:
        if not self._out:
            raise PedalError("Pedal não conectado.")
        trace(">", sysex)
        self._out.send_message(list(sysex))

    def _request(self, sysex: bytes, match: Callable, timeout: float) -> P.Message:
        event, box = threading.Event(), []
        entry = (match, event, box)
        with self._plock:
            self._pending.append(entry)
        self._send(sysex)
        if not event.wait(timeout):
            with self._plock:
                if entry in self._pending:
                    self._pending.remove(entry)
            raise PedalTimeout()
        return box[0]

    def _handshake(self) -> None:
        self._send(P.encode_identity_request())
        time.sleep(0.08)

    def ping(self, timeout: float = PING_TIMEOUT) -> bool:
        """Pergunta 'você está aí?' sem levantar exceção.

        Usa o mesmo mecanismo de _request para que a resposta tenha onde ser
        casada — sem registrar a pendência, a identidade chega e é descartada.
        """
        if not self._out:
            return False
        try:
            self._request(P.encode_identity_request(), _MATCH_IDENTITY, timeout)
            return True
        except PedalTimeout:
            return False
        except Exception:  # noqa: BLE001 - ping nunca deve derrubar o chamador
            return False

    # ---- API -------------------------------------------------------------------
    def identify(self, timeout: float = DEFAULT_TIMEOUT) -> str:
        with self._lock:
            msg = self._request(P.encode_identity_request(), lambda m: m.kind == "identity-response", timeout)
            return msg.name

    def read_memory(self, memory: int, address: int, length: int, timeout: float = DEFAULT_TIMEOUT) -> bytes:
        if length > MAX_READ_BYTES:
            raise PedalError(
                f"Leitura de {length} bytes é grande demais: o pedal aceita no máximo "
                f"{MAX_READ_BYTES} por pedido (testado em hardware). Divida em pedaços."
            )
        with self._lock:
            self._handshake()
            try:
                msg = self._request(
                    P.encode_memory_read_request(memory, address, length),
                    lambda m: m.kind == "memory-read-response" and m.memory == memory
                    and m.address == address and m.length == length,
                    timeout,
                )
            except PedalTimeout:
                # Não adianta insistir sem confirmar que o pedal está vivo: uma
                # leitura grande pode deixá-lo ocupado. Confirma antes de repetir.
                self._recuperar(memory, address, length)
                msg = self._request(
                    P.encode_memory_read_request(memory, address, length),
                    lambda m: m.kind == "memory-read-response" and m.memory == memory
                    and m.address == address and m.length == length,
                    timeout,
                )
            return msg.data

    def _recuperar(self, memory: int, address: int, length: int) -> None:
        """Tenta devolver o pedal a um estado são depois de um timeout.

        O pedal não responde enquanto está ocupado; insistir só piora. A
        sequência é: dar tempo, perguntar se está vivo, e só então seguir.
        Levanta PedalError com instrução clara se não voltar.
        """
        for espera in RECOVERY_WAITS:
            time.sleep(espera)
            if self.ping():
                trace("#", f"pedal recuperado após {espera}s de espera")
                return
        raise PedalError(
            "O pedal parou de responder e não voltou sozinho. "
            "Desconecte e reconecte o cabo USB da pedaleira para reiniciar o "
            f"firmware — não é preciso mexer nos presets. Veja {log_path()}"
        )

    def write_memory(self, memory: int, address: int, data: bytes, timeout: float = WRITE_TIMEOUT) -> bool:
        with self._lock:
            last_exc: PedalTimeout | None = None
            for attempt in range(1, WRITE_RETRIES + 1):
                try:
                    self._handshake()
                    msg = self._request(P.encode_memory_write_request(memory, address, data), lambda m: m.kind == "ack", timeout)
                except PedalTimeout as exc:
                    last_exc = exc
                    trace("!", f"sem ack na tentativa {attempt}/{WRITE_RETRIES}; pedal provavelmente ocupado")
                    time.sleep(0.25)
                    continue
                self.last_ack = msg.raw_value
                time.sleep(SETTLE)  # deixa o pedal terminar de aplicar antes do próximo pedido
                return msg.accepted
            assert last_exc is not None
            raise last_exc


class SimulatedPedal(BasePedal):
    """Pedal falso em memória: deixa testar a interface sem hardware."""

    def __init__(self) -> None:
        self.connected = True
        self.device_name = "CUBE Baby (simulado)"
        self._lock = threading.Lock()
        presets = [
            dict(type=2, gain=5, tone=8, reverb=4, feedback=10, volume=100, time=12, mix=20, modulation=8, cabinet=3, irSection=1, delaySection=1, toneSection=1),
            dict(type=0, gain=2, tone=6, reverb=8, feedback=30, volume=90, time=20, mix=40, modulation=3, cabinet=1, irSection=1, delaySection=0, toneSection=1),
            dict(type=8, gain=7, tone=10, reverb=2, feedback=0, volume=110, time=0, mix=0, modulation=8, cabinet=5, irSection=1, delaySection=0, toneSection=1),
        ]
        self._bank = bytearray()
        for p in presets:
            self._bank += bytes(p[n] for n in P.PARAM_NAMES) + b"\x00\x00\x00"

    def identify(self) -> str:
        return self.device_name

    def read_memory(self, memory, address, length) -> bytes:
        time.sleep(0.05)
        if memory == P.BANK_MEMORY and address == P.BANK_ADDRESS:
            return bytes(self._bank[:length])
        raise PedalError("Leitura não suportada no pedal simulado.")

    def write_memory(self, memory, address, data) -> bool:
        time.sleep(0.01)
        self.last_ack = 0
        if memory == P.LIVE_PARAM_MEMORY and address >= P.LIVE_PARAM_BASE_ADDRESS:
            off = address - P.LIVE_PARAM_BASE_ADDRESS
            with self._lock:
                self._bank[off:off + len(data)] = data
            return True
        return False
