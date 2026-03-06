# utils/steam_web.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
import aiohttp
from bs4 import BeautifulSoup


@dataclass
class SteamNewGame:
    appid: str
    name: str
    store_url: str
    capsule_url: str
    release_date: str
    review_text: Optional[str] = None


def build_headers(user_agent: str | None = None) -> dict:
    ua = (user_agent or "").strip() or (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://store.steampowered.com/",
    }


async def fetch_html(url: str, timeout_sec: int = 15, user_agent: str | None = None) -> str:
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    headers = build_headers(user_agent)

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(url) as resp:
            # Steam 有时会返回 429/403，直接把状态码抛出去让上层提示
            text = await resp.text(errors="ignore")
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            return text


def _clean_text(s: str) -> str:
    return " ".join((s or "").split())


def parse_recent_games(html: str) -> List[SteamNewGame]:
    soup = BeautifulSoup(html, "lxml")

    container = soup.find("div", id="search_resultsRows")
    if not container:
        return []

    items: list[SteamNewGame] = []

    for a in container.select("a.search_result_row"):
        store_url = (a.get("href") or "").strip()
        appid = (a.get("data-ds-appid") or "").strip()

        title_span = a.select_one("span.title")
        name = _clean_text(title_span.get_text()) if title_span else ""

        img = a.select_one("div.search_capsule img")
        capsule_url = (img.get("src") or "").strip() if img else ""

        released_div = a.select_one("div.search_released")
        release_date = _clean_text(released_div.get_text()) if released_div else ""

        # 评价信息：<span class="search_review_summary positive/mixed/..." data-tooltip-html="...">
        review_span = a.select_one("span.search_review_summary")
        review_text = None
        if review_span:
            # tooltip-html 更全，但带 <br>；这里做轻量清洗
            tooltip = (review_span.get("data-tooltip-html") or "").strip()
            if tooltip:
                review_text = _clean_text(
                    tooltip.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
                )

        if not (appid and store_url and name):
            # 缺关键字段就跳过
            continue

        items.append(
            SteamNewGame(
                appid=appid,
                name=name,
                store_url=store_url,
                capsule_url=capsule_url,
                release_date=release_date,
                review_text=review_text,
            )
        )

    return items