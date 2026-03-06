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
    chain.append(Comp.Plain("📅近期发售\n\n"))

    for i, g in enumerate(games, start=1):
        if show_cover and g.capsule_url:
            chain.append(Comp.Image.fromURL(g.capsule_url))

        lines: List[str] = [f"#{i}"]

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

        chain.append(Comp.Plain("\n".join(lines) + "\n\n"))

    return chain


def build_forward_nodes(
    games: Iterable[SteamNewGame],
    field_switch: Dict[str, Any] | None = None,
    bot_name: str = "SteamNEW",
    bot_uin: int = 10000,
):
    fs = field_switch or {}

    show_cover = bool(fs.get("cover", True))
    show_name = bool(fs.get("name", True))
    show_appid = bool(fs.get("appid", True))
    show_link = bool(fs.get("link", True))
    show_release = bool(fs.get("release_date", True))
    show_review = bool(fs.get("review", True))

    nodes: List[Any] = []

    nodes.append(
        Comp.Node(
            uin=bot_uin,
            name=bot_name,
            content=[Comp.Plain("📅近期发售")]
        )
    )

    for i, g in enumerate(games, start=1):
        content: List[Any] = []

        if show_cover and g.capsule_url:
            content.append(Comp.Image.fromURL(g.capsule_url))

        lines: List[str] = [f"#{i}"]

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

        content.append(Comp.Plain("\n".join(lines)))

        nodes.append(
            Comp.Node(
                uin=bot_uin,
                name=bot_name,
                content=content
            )
        )

    return nodes