"""Сервисы для криптокошельков и учётных записей."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.crypto.models import (
    CryptoNetwork,
    CryptoWallet,
    SocialAccount,
    SocialPlatform,
)
from case_workspace.crypto.validators import detect_network, normalize_crypto_address


class CryptoService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_wallet(
        self,
        case_id: int,
        address: str,
        network: CryptoNetwork | None = None,
        party_id: int | None = None,
        token_symbol: str = "",
        label: str = "",
        comment: str = "",
    ) -> CryptoWallet:
        a = normalize_crypto_address(address)
        if not a:
            raise ValueError("Введите адрес кошелька.")
        if network is None:
            network, _ = detect_network(a)
        if network == CryptoNetwork.OTHER:
            raise ValueError("Не удалось определить сеть. Укажите её вручную.")
        exists = self.session.scalar(
            select(CryptoWallet).where(
                CryptoWallet.case_id == case_id,
                CryptoWallet.network == network,
                CryptoWallet.normalized_address == a,
            )
        )
        if exists:
            raise ValueError("Этот кошелёк уже добавлен в дело.")
        w = CryptoWallet(
            case_id=case_id,
            party_id=party_id,
            network=network,
            token_symbol=token_symbol.strip(),
            address=address.strip(),
            normalized_address=a,
            label=label.strip(),
            comment=comment.strip(),
        )
        self.session.add(w)
        self.session.commit()
        return w

    def list_wallets(self, case_id: int) -> list[CryptoWallet]:
        return list(
            self.session.scalars(
                select(CryptoWallet)
                .where(CryptoWallet.case_id == case_id)
                .order_by(CryptoWallet.id)
            )
        )

    def delete_wallet(self, wallet_id: int) -> None:
        w = self.session.get(CryptoWallet, wallet_id)
        if w:
            self.session.delete(w)
            self.session.commit()


class SocialService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_account(
        self,
        case_id: int,
        platform: SocialPlatform,
        party_id: int | None = None,
        username: str = "",
        user_id: str = "",
        profile_url: str = "",
        display_name: str = "",
        phone: str = "",
        email: str = "",
        bio: str = "",
        label: str = "",
        notes: str = "",
        platform_other: str = "",
    ) -> SocialAccount:
        if not any([username.strip(), user_id.strip(), phone.strip(), email.strip()]):
            raise ValueError("Заполните хотя бы одно: username, ID, телефон или email.")
        acc = SocialAccount(
            case_id=case_id,
            party_id=party_id,
            platform=platform,
            platform_other=platform_other.strip(),
            username=username.strip(),
            user_id=user_id.strip(),
            profile_url=profile_url.strip(),
            display_name=display_name.strip(),
            phone=phone.strip(),
            email=email.strip(),
            bio=bio.strip(),
            label=label.strip(),
            notes=notes.strip(),
        )
        self.session.add(acc)
        self.session.commit()
        return acc

    def list_accounts(self, case_id: int) -> list[SocialAccount]:
        return list(
            self.session.scalars(
                select(SocialAccount)
                .where(SocialAccount.case_id == case_id)
                .order_by(SocialAccount.platform, SocialAccount.id)
            )
        )

    def delete_account(self, account_id: int) -> None:
        a = self.session.get(SocialAccount, account_id)
        if a:
            self.session.delete(a)
            self.session.commit()
