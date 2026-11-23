"""Сервис правовой справки: кэш статей + генерация URL для поиска."""

from __future__ import annotations

from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.orm import Session

from case_workspace.legal.models import UkArticleCache


class LegalService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, code: str, part: str = "") -> UkArticleCache | None:
        code = (code or "").strip()
        part = (part or "").strip()
        if not code:
            return None
        return self.session.scalar(
            select(UkArticleCache).where(
                UkArticleCache.code == code, UkArticleCache.part == part
            )
        )

    def save(
        self, code: str, part: str, text: str, comment: str = "", source_url: str = ""
    ) -> UkArticleCache:
        code = code.strip()
        part = part.strip()
        if not code:
            raise ValueError("Не указан номер статьи.")
        row = self.get(code, part)
        if row is None:
            row = UkArticleCache(
                code=code,
                part=part,
                text=text.strip(),
                comment=comment.strip(),
                source_url=source_url.strip(),
            )
            self.session.add(row)
        else:
            row.text = text.strip()
            row.comment = comment.strip()
            if source_url.strip():
                row.source_url = source_url.strip()
        self.session.commit()
        return row

    def delete(self, code: str, part: str = "") -> None:
        row = self.get(code, part)
        if row:
            self.session.delete(row)
            self.session.commit()

    # --- URL для поиска ---
    @staticmethod
    def build_article_search_url(code: str, part: str = "") -> str:
        """Google-поиск текста статьи УК РБ."""
        code = (code or "").strip()
        part = (part or "").strip()
        q = f"статья {code}"
        if part:
            q += f" часть {part}"
        q += " УК Республики Беларусь"
        return f"https://www.google.com/search?q={quote_plus(q)}"

    @staticmethod
    def build_comment_search_url(code: str, part: str = "") -> str:
        """Google-поиск комментария к статье УК РБ."""
        code = (code or "").strip()
        part = (part or "").strip()
        q = f"комментарий статья {code}"
        if part:
            q += f" часть {part}"
        q += " УК Республики Беларусь"
        return f"https://www.google.com/search?q={quote_plus(q)}"

    @staticmethod
    def build_pravo_by_url() -> str:
        """Официальный текст УК РБ на pravo.by."""
        return "https://pravo.by/document/?guid=3871&p0=HK9900275"
