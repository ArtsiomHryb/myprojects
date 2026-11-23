"""Определение криптосети по формату адреса."""

from __future__ import annotations

import re

from case_workspace.crypto.models import CryptoNetwork


def normalize_crypto_address(value: str) -> str:
    return value.strip()


def detect_network(address: str) -> tuple[CryptoNetwork, list[CryptoNetwork]]:
    """Возвращает (определённая сеть, список альтернатив).

    Если адрес может принадлежать нескольким сетям (например, 0x… — это
    ETH/BSC/Polygon/AVAX/Arbitrum), возвращаем ETH как основную и список
    всех EVM-сетей для выбора пользователем.
    """
    a = address.strip()

    # EVM-адреса: 0x + 40 hex
    if re.fullmatch(r"0x[a-fA-F0-9]{40}", a):
        evm = [
            CryptoNetwork.ETH,
            CryptoNetwork.BSC,
            CryptoNetwork.POLYGON,
            CryptoNetwork.AVAX,
        ]
        return CryptoNetwork.ETH, evm

    # Bitcoin legacy: 1…, 3… (26–35 base58)
    if re.fullmatch(r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}", a):
        return CryptoNetwork.BTC, [CryptoNetwork.BTC]

    # Bitcoin bech32: bc1…
    if re.fullmatch(r"bc1[a-z0-9]{25,90}", a):
        return CryptoNetwork.BTC, [CryptoNetwork.BTC]

    # TRON: T + 33 base58
    if re.fullmatch(r"T[a-km-zA-HJ-NP-Z1-9]{33}", a):
        return CryptoNetwork.TRX, [CryptoNetwork.TRX]

    # TON: UQ…/EQ… (48 base64url) или 0:hex
    if re.fullmatch(r"(UQ|EQ)[A-Za-z0-9_-]{46}", a) or re.fullmatch(
        r"0:[a-fA-F0-9]{64}", a
    ):
        return CryptoNetwork.TON, [CryptoNetwork.TON]

    # Solana: base58, 32–44
    if re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", a):
        # пересекается с BTC/TRX по формату, но обычно длина 43-44
        return CryptoNetwork.SOL, [CryptoNetwork.SOL]

    # Litecoin: L…, M…, ltc1…
    if re.fullmatch(r"[LM][a-km-zA-HJ-NP-Z1-9]{25,34}", a):
        return CryptoNetwork.LTC, [CryptoNetwork.LTC]
    if re.fullmatch(r"ltc1[a-z0-9]{25,90}", a):
        return CryptoNetwork.LTC, [CryptoNetwork.LTC]

    # Dogecoin: D…
    if re.fullmatch(r"D[a-km-zA-HJ-NP-Z1-9]{25,34}", a):
        return CryptoNetwork.DOGE, [CryptoNetwork.DOGE]

    return CryptoNetwork.OTHER, []
