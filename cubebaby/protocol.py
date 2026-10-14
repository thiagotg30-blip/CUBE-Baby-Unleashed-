"""Protocolo SysEx do CUBE Baby (M-VAVE/CUVAVE).

Portado do preset-studio (TypeScript), que por sua vez veio da engenharia reversa
comunitária: cubecontrol (MIT) e cuvave-midi (GPL-3.0, só como referência).
Projeto independente, não afiliado à M-VAVE/CUVAVE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ----------------------------------------------------------------------------
# Codificação 7 bits (SysEx só aceita bytes 0..127)
# ----------------------------------------------------------------------------

def encode_seven_bit(source: bytes) -> bytes:
    dest = bytearray()
    bit_count = 0
    acc = 0
    for byte in source:
        acc = (acc | (byte << (bit_count & 0x1F))) & 0xFFFFFFFF
        bit_count += 1
        while True:
            dest.append(acc & 0x7F)
            acc >>= 7
            if bit_count < 7:
                break
            bit_count -= 7
    if acc > 0:
        dest.append(acc & 0x7F)
    padded = -(-len(source) * 8 // 7)  # ceil(n*8/7)
    while len(dest) < padded:
        dest.append(0)
    return bytes(dest)


def decode_seven_bit(source: bytes) -> bytes:
    dest = bytearray()
    bit_count = 0
    last = 0
    for byte in source:
        mask = 0 if bit_count == 0 else (0xFFFFFFFF >> (32 - bit_count))
        acc = byte & mask
        if bit_count > 0:
            dest.append(((last & 0x7F) | (acc << (8 - bit_count))) & 0xFF)
        last = byte >> bit_count
        bit_count = (bit_count + 1) % 8
    if last > 0:
        dest.append(last)
    return bytes(dest)


# ----------------------------------------------------------------------------
# Envelope: 00 59 <tipo> <len24 LE> <conteúdo> <checksum>
# ----------------------------------------------------------------------------

MAGIC0, MAGIC1 = 0x00, 0x59
MSG_ACK = 0x00
MSG_IDENTITY = 0x11
MSG_ERASE = 0x21
MSG_MEM_WRITE = 0x22
MSG_MEM_READ = 0x23


class DecodeError(Exception):
    pass


def calculate_checksum(content: bytes) -> int:
    return (~sum(content)) & 0xFF


def _u24(data: bytes, off: int) -> int:
    return data[off] | (data[off + 1] << 8) | (data[off + 2] << 16)


def _u32(data: bytes, off: int) -> int:
    return data[off] | (data[off + 1] << 8) | (data[off + 2] << 16) | (data[off + 3] << 24)


def _w24(v: int) -> bytes:
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF))


def _w32(v: int) -> bytes:
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF))


@dataclass
class Envelope:
    message_type: int
    content: bytes
    checksum: int
    checksum_valid: bool


def encode_envelope(message_type: int, content: bytes) -> bytes:
    clear = bytes((MAGIC0, MAGIC1, message_type)) + _w24(len(content)) + content + bytes((calculate_checksum(content),))
    return b"\xF0" + encode_seven_bit(clear) + b"\xF7"


def decode_envelope(sysex: bytes) -> Envelope:
    if len(sysex) < 2 or sysex[0] != 0xF0 or sysex[-1] != 0xF7:
        raise DecodeError("faltam os marcadores F0/F7")
    clear = decode_seven_bit(sysex[1:-1])
    if len(clear) < 6:
        raise DecodeError("payload curto demais")
    if clear[0] != MAGIC0 or clear[1] != MAGIC1:
        raise DecodeError("assinatura (magic) desconhecida")
    declared = _u24(clear, 3)
    expected = 7 + declared
    # O decodificador 7-bit descarta um último byte 0x00 (checksum zero); recupera.
    if len(clear) == expected - 1:
        clear += b"\x00"
    if len(clear) != expected:
        raise DecodeError(f"tamanho inconsistente: esperado {expected}, veio {len(clear)}")
    content = clear[6:6 + declared]
    checksum = clear[6 + declared]
    return Envelope(clear[2], content, checksum, checksum == calculate_checksum(content))


# ----------------------------------------------------------------------------
# Pedidos
# ----------------------------------------------------------------------------

def encode_identity_request() -> bytes:
    return encode_envelope(MSG_IDENTITY, b"")


def encode_memory_read_request(memory: int, address: int, length: int) -> bytes:
    return encode_envelope(MSG_MEM_READ, bytes((memory,)) + _w32(address) + _w24(length))


def encode_memory_write_request(memory: int, address: int, data: bytes) -> bytes:
    return encode_envelope(MSG_MEM_WRITE, bytes((memory,)) + _w32(address) + _w24(len(data)) + bytes(data))


def encode_erase_request(memory: int, address: int) -> bytes:
    return encode_envelope(MSG_ERASE, bytes((memory,)) + _w32(address))


# ----------------------------------------------------------------------------
# Mensagens decodificadas
# ----------------------------------------------------------------------------

@dataclass
class Message:
    kind: str  # identity-request | identity-response | memory-read-request |
               # memory-read-response | memory-write-request | ack | unknown
    envelope: Envelope
    name: str = ""
    accepted: bool = False
    memory: int = 0
    address: int = 0
    length: int = 0
    data: bytes = b""
    raw_value: int = 0


def decode_message(sysex: bytes) -> Message:
    env = decode_envelope(sysex)
    c = env.content
    if env.message_type == MSG_IDENTITY:
        if not c:
            return Message("identity-request", env)
        end = next((i for i, b in enumerate(c) if b < 0x20 or b > 0x7E), None)
        n = min(16, len(c)) if end is None else end
        return Message("identity-response", env, name=c[:n].decode("ascii", "replace").rstrip())
    if env.message_type == MSG_ACK and len(c) == 1:
        # Confirmado no pedal real: o ack "00" vem junto com a escrita aplicada => 0 significa sucesso.
        return Message("ack", env, accepted=c[0] == 0, raw_value=c[0])
    if env.message_type in (MSG_MEM_WRITE, MSG_MEM_READ) and len(c) >= 8:
        mem, addr, length, data = c[0], _u32(c, 1), _u24(c, 5), c[8:]
        if env.message_type == MSG_MEM_WRITE:
            return Message("memory-write-request", env, memory=mem, address=addr, length=length, data=data)
        if not data:
            return Message("memory-read-request", env, memory=mem, address=addr, length=length)
        return Message("memory-read-response", env, memory=mem, address=addr, length=length, data=data)
    return Message("unknown", env)


# ----------------------------------------------------------------------------
# Presets / parâmetros ao vivo
# ----------------------------------------------------------------------------

SLOT_IDS = ("A", "B", "C")
PRESET_SLOT_BYTES = 16
PRESET_BANK_BYTES = PRESET_SLOT_BYTES * 3

LIVE_PARAM_MEMORY = 5
LIVE_PARAM_BASE_ADDRESS = 0x80000000
BANK_MEMORY = 5
BANK_ADDRESS = 0x00000000

# Ordem = offset do byte dentro do slot de 16 bytes
PARAM_NAMES = (
    "type", "gain", "tone", "reverb", "feedback", "volume", "time",
    "mix", "modulation", "cabinet", "irSection", "delaySection", "toneSection",
)
PARAM_MAX = {
    "type": 8, "gain": 7, "tone": 15, "reverb": 15, "feedback": 127, "volume": 127,
    "time": 31, "mix": 118, "modulation": 15, "cabinet": 8,
    "irSection": 1, "delaySection": 1, "toneSection": 1,
}

PREAMP_TYPES = (
    (0, "Power-Zone Clean", "Clean"),
    (1, "US Gold 100 Clean", "Clean"),
    (2, "Two Stone Coral OD", "Overdrive"),
    (3, "Doctor3 B", "Overdrive"),
    (4, "Cali JP A", "Overdrive"),
    (5, "Day Tripper OD", "Distortion"),
    (6, "Shittcow Dist", "Distortion"),
    (7, "Wo Stone Coral OD", "Distortion"),
    (8, "Mr Smith Dist", "Distortion"),
)


def clamp_param(name: str, value) -> int:
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(PARAM_MAX[name], v))


def clamp_params(raw: dict) -> dict:
    return {n: clamp_param(n, raw.get(n, 0)) for n in PARAM_NAMES}


def empty_params() -> dict:
    return {n: 0 for n in PARAM_NAMES}


def live_param_address(name: str, slot: str) -> int:
    return LIVE_PARAM_BASE_ADDRESS + SLOT_IDS.index(slot) * PRESET_SLOT_BYTES + PARAM_NAMES.index(name)


def decode_preset_bank(data: bytes) -> dict:
    """48 bytes -> {'A': {...}, 'B': {...}, 'C': {...}}"""
    if len(data) != PRESET_BANK_BYTES:
        raise ValueError(f"o banco de presets precisa ter {PRESET_BANK_BYTES} bytes (veio {len(data)})")
    out = {}
    for i, slot in enumerate(SLOT_IDS):
        chunk = data[i * PRESET_SLOT_BYTES:(i + 1) * PRESET_SLOT_BYTES]
        out[slot] = {n: chunk[k] for k, n in enumerate(PARAM_NAMES)}
    return out


def modulation_label(v: int) -> str:
    if 0 <= v <= 6:
        return f"Chorus {v}/6"
    if v in (7, 8):
        return "Desligado"
    return f"Phaser {v - 8}/7"


def cabinet_label(v: int) -> str:
    return "Sem gabinete (bypass)" if v == 0 else f"Cabinet {v}"
