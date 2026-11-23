"""Криптокошельки и учётные записи."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from case_workspace.db.models import Base


class CryptoNetwork(str, enum.Enum):
    BTC = "btc"
    ETH = "eth"
    TRX = "trx"
    TON = "ton"
    SOL = "sol"
    BSC = "bsc"
    POLYGON = "polygon"
    AVAX = "avax"
    LTC = "ltc"
    DOGE = "doge"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            CryptoNetwork.BTC: "Bitcoin (BTC)",
            CryptoNetwork.ETH: "Ethereum (ETH)",
            CryptoNetwork.TRX: "TRON (TRX)",
            CryptoNetwork.TON: "TON",
            CryptoNetwork.SOL: "Solana (SOL)",
            CryptoNetwork.BSC: "BNB Smart Chain (BSC)",
            CryptoNetwork.POLYGON: "Polygon",
            CryptoNetwork.AVAX: "Avalanche C-Chain",
            CryptoNetwork.LTC: "Litecoin (LTC)",
            CryptoNetwork.DOGE: "Dogecoin (DOGE)",
            CryptoNetwork.OTHER: "Иная сеть",
        }[self]


class CryptoWallet(Base):
    __tablename__ = "crypto_wallet"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("party.id"), nullable=True, index=True
    )

    network: Mapped[CryptoNetwork] = mapped_column(SAEnum(CryptoNetwork))
    token_symbol: Mapped[str] = mapped_column(String(16), default="")
    address: Mapped[str] = mapped_column(String(128))
    normalized_address: Mapped[str] = mapped_column(String(128), index=True)

    label: Mapped[str] = mapped_column(String(255), default="")
    comment: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def network_enum(self) -> CryptoNetwork:
        """Гарантированно возвращает enum, даже если из БД пришла строка."""
        value = self.network
        if isinstance(value, CryptoNetwork):
            return value
        try:
            return CryptoNetwork(value)
        except (ValueError, TypeError):
            return CryptoNetwork.OTHER


class SocialPlatform(str, enum.Enum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    VIBER = "viber"
    VK = "vk"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    DISCORD = "discord"
    SIGNAL = "signal"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            SocialPlatform.TELEGRAM: "Telegram",
            SocialPlatform.INSTAGRAM: "Instagram",
            SocialPlatform.WHATSAPP: "WhatsApp",
            SocialPlatform.VIBER: "Viber",
            SocialPlatform.VK: "ВКонтакте",
            SocialPlatform.TIKTOK: "TikTok",
            SocialPlatform.FACEBOOK: "Facebook",
            SocialPlatform.TWITTER: "Twitter / X",
            SocialPlatform.YOUTUBE: "YouTube",
            SocialPlatform.DISCORD: "Discord",
            SocialPlatform.SIGNAL: "Signal",
            SocialPlatform.OTHER: "Иное",
        }[self]


class SocialAccount(Base):
    __tablename__ = "social_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), index=True)
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("party.id"), nullable=True, index=True
    )

    platform: Mapped[SocialPlatform] = mapped_column(SAEnum(SocialPlatform))
    platform_other: Mapped[str] = mapped_column(String(64), default="")

    username: Mapped[str] = mapped_column(String(128), default="")
    user_id: Mapped[str] = mapped_column(String(64), default="")
    profile_url: Mapped[str] = mapped_column(String(512), default="")
    display_name: Mapped[str] = mapped_column(String(255), default="")

    phone: Mapped[str] = mapped_column(String(32), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    registration_date: Mapped[str] = mapped_column(String(32), default="")
    last_activity: Mapped[str] = mapped_column(String(32), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    avatar_url: Mapped[str] = mapped_column(String(512), default="")

    followers_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subscriptions_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_business: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    label: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def platform_enum(self) -> SocialPlatform:
        value = self.platform
        if isinstance(value, SocialPlatform):
            return value
        try:
            return SocialPlatform(value)
        except (ValueError, TypeError):
            return SocialPlatform.OTHER
