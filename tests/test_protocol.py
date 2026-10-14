"""Rodar com:  python -m pytest tests   (ou  python tests/test_protocol.py)"""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cubebaby import protocol as P


def test_seven_bit_so_gera_bytes_validos_e_volta():
    random.seed(1)
    for n in range(1, 80):
        for _ in range(100):
            d = bytes(random.randrange(256) for _ in range(n))
            e = P.encode_seven_bit(d)
            assert all(b < 0x80 for b in e)
            assert P.decode_seven_bit(e).rstrip(b"\0") == d.rstrip(b"\0")


def test_round_trip_de_mensagens():
    random.seed(2)
    for _ in range(5000):
        mem, addr = random.randrange(6), random.choice([0, 0x80000000 + random.randrange(48), 0x69000])
        data = bytes(random.randrange(256) for _ in range(random.choice([1, 16, 48, 128])))
        m = P.decode_message(P.encode_memory_write_request(mem, addr, data))
        assert (m.kind, m.memory, m.address, m.data, m.envelope.checksum_valid) == ("memory-write-request", mem, addr, data, True)


def test_endereco_dos_parametros():
    assert P.live_param_address("type", "A") == 0x80000000
    assert P.live_param_address("toneSection", "C") == 0x8000002C


if __name__ == "__main__":
    test_seven_bit_so_gera_bytes_validos_e_volta(); test_round_trip_de_mensagens(); test_endereco_dos_parametros()
    print("ok")
