from __future__ import annotations
from typing import Iterable, Dict, Any, List

import astrbot.api.message_components as Comp
from .steam_web import SteamNewGame


def build_game_chain(
    games: Iterable[SteamNewGame],
    field_switch: Dict[str, Any] | None = None,
):
    fs = field_switch or {}

    show_cover = bool(fs.get("cover", True))
    show_name = bool(fs.get("name", True))
    show_appid = bool(fs.get("appid", True))
    show_link = bool(fs.get("link", True))
    show_release = bool(fs.get("release_date", True))
    show_review = bool(fs.get("review", True))

    chain: List[Any] = []

    # 顶部标题（单独一条 Plain）
    chain.append(Comp.Plain("📅近期发售\n\n"))

    for i, g in enumerate(games, start=1):
        # 1) 该游戏封面（紧跟该游戏文字前）
        if show_cover and g.capsule_url:
            chain.append(Comp.Image.fromURL(g.capsule_url))

        # 2) 该游戏文本块：一次性 Plain，确保换行稳定
        lines: List[str] = []
        lines.append(f"#{i}")

        if show_name:
            lines.append(f"游戏名称: {g.name}")

        if show_appid:
            lines.append(f"AppID: {g.appid}")

        if show_release and g.release_date:
            lines.append(f"发售时间: {g.release_date}")

        if show_link:
            lines.append(f"商店链接: {g.store_url}")

        if show_review and g.review_text:
            lines.append(f"评价: {g.review_text}")

        # 3) 游戏之间空一行：直接拼进同一个 Plain 的末尾（最稳）
        #    这样不会被“Plain 合并压缩”吃掉
        text = "\n".join(lines) + "\n\n"
        chain.append(Comp.Plain(text))

    return chain