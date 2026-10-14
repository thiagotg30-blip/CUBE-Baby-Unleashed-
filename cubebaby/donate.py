"""Dados de doação do projeto.

PREENCHA com os seus dados reais. Enquanto estiverem como placeholder, a aba
mostra os campos com um aviso de "a configurar" — nunca inventar chave de Pix
ou endereço de cripto.

Licença: o projeto é GPL-3.0 e sem fins lucrativos. Doações são voluntárias,
sem troca de bens ou serviços. Doações entre pessoas físicas (CPF) não são
tributadas como renda. Se o volume crescer, abra um CNPJ (EIRELI/Sociedade
Simples) para receber formalmente.
"""

# ---- Pix -----------------------------------------------------------------
# Chave Pix (CPF, e-mail, telefone, aleatória). Se for CPF, é o seu CPF.
PIX_CHAVE: str = "4b10f63b-304f-4d0c-a205-de386c9d2e9e"
PIX_NOME: str = "THIAGO DE BARROS MACARIO"
PIX_CIDADE: str = ""         # TODO: cidade do recebedor (opcional)

# ---- Cripto ---------------------------------------------------------------
# Endereços de carteira. Redes diferentes: se usar Ethereum/Polygon, avise que
# a rede é essa — enviar pela rede errada perde o valor.
CRIPTO_ENDERECO: str = "BC1QHAW7TVD8AJSX7WYP44RS784Z7K84E4JZQRW64N"
CRIPTO_REDE: str = "Bitcoin"  # rede principal do endereço (bech32)
CRIPTO_TOKEN: str = "BTC"

# ---- Links ---------------------------------------------------------------
GITHUB_SPONSORS: str = ""    # TODO: ex.: "https://github.com/sponsors/seu-usuario"
GITHUB_REPO: str = ""        # TODO: ex.: "https://github.com/seu-usuario/cubebaby-unleashed"
Kofi: str = "https://ko-fi.com/tg_macario"


def pix_copia_e_cola() -> str:
    """Gera o código Pix "copia e cola" (padrão BR, CRC16).

    Se a chave não estiver configurada, devolve string vazia. O formato é o
    "EMV" do BR Code: 00020126...52040000530398654...5802BR59...62...6304+CRC.
    """
    if not PIX_CHAVE:
        return ""
    # Payload Format Indicator
    payload = "000201"
    # Merchant Account Information (GUI: br.gov.bcb.pix)
    merchant = f"0014br.gov.bcb.pix01{len(PIX_CHAVE):02d}{PIX_CHAVE}"
    payload += f"26{len(merchant):02d}{merchant}"
    # Merchant Category Code
    payload += "52040000"
    # Transaction Currency (986 = BRL)
    payload += "5303986"
    # Transaction Amount (vazio = valor definido pelo usuário no app)
    # Country Code
    payload += "5802BR"
    # Merchant Name
    nome = PIX_NOME[:25] or "CUBE BABY UNLEASHED"
    payload += f"59{len(nome):02d}{nome}"
    # Merchant City
    cidade = (PIX_CIDADE or "Brasil")[:15]
    payload += f"60{len(cidade):02d}{cidade}"
    # Additional Data Field (txid)
    payload += "62050500000"   # placeholder txid
    payload += "6304"
    # CRC16-CCITT
    crc = _crc16_ccitt(payload)
    return payload + crc.upper()


def _crc16_ccitt(data: str) -> str:
    """CRC16-CCITT (0xFFFF, polinômio 0x1021)."""
    crc = 0xFFFF
    for ch in data.encode("utf-8"):
        crc ^= ch << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"
