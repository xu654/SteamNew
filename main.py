# main.py
from __future__ import annotations

import asyncio
from datetime import datetime

from croniter import croniter

from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, StarTools, register

from .utils.steam_web import fetch_html, parse_recent_games
from .utils.join import build_game_chain
from .utils.subscribe import remember_group_umo, resolve_umo

@register(
    "SteamNEW",
    "xu654",
    "Steam 近期发售游戏查询与定时推送（/new）",
    "1.0.0",
    "https://github.com/xu654/SteamNEW",
)
class SteamNEW(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.fetch_url: str = config.get("fetch_url", "")
        self.top_n: int = int(config.get("top_n", 10) or 10)
        self.timeout_sec: int = int(config.get("timeout_sec", 15) or 15)
        self.user_agent: str = str(config.get("user_agent", "") or "")

        self.cron_time: str = str(config.get("cron_time", "") or "").strip()
        push_group_ids_raw = config.get("push_group_ids", [])
        if isinstance(push_group_ids_raw, list):
            self.push_group_ids: list[str] = [str(x).strip() for x in push_group_ids_raw if str(x).strip()]
        else:
            self.push_group_ids = []

        field_switch_raw = config.get("field_switch", {})
        self.field_switch = field_switch_raw if isinstance(field_switch_raw, dict) else {}

        # 数据目录：存 group_id -> umo
        self.data_dir = StarTools.get_data_dir("SteamNEW")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.group_umo_path = self.data_dir / "group_umo_map.json"

        # cron task
        self._cron_task: asyncio.Task | None = None

        # 热重载场景：__init__ 可能已在运行中 loop 内
        try:
            asyncio.get_running_loop()
            if self.cron_time:
                self._start_cron_task()
                logger.info(f"[SteamNEW] cron 已启动（热重载）：{self.cron_time}")
        except RuntimeError:
            # 冷启动：交给 on_loaded
            pass

    async def on_loaded(self):
        # 冷启动后再启动 cron
        if self.cron_time:
            self._start_cron_task()
            logger.info(f"[SteamNEW] cron 已启动：{self.cron_time}")

    async def terminate(self):
        if self._cron_task and not self._cron_task.done():
            self._cron_task.cancel()
            logger.info("[SteamNEW] cron 已取消")

    # ========== 指令：/new ==========
    @filter.command("new")
    async def cmd_new(self, event: AstrMessageEvent):
        """
        获取 Steam 近期发售游戏（按 WebUI 配置 top_n 返回）
        """
        # 记录 UMO：用群号区分推送目标
        try:
            group_id = (event.message_obj.group_id or "").strip()
            if group_id:
                remember_group_umo(self.group_umo_path, group_id, event.unified_msg_origin)
        except Exception as e:
            logger.warning(f"[SteamNEW] 记录 group->UMO 失败: {e}")

        # 拉取与解析
        try:
            html = await fetch_html(
                url=self.fetch_url,
                timeout_sec=self.timeout_sec,
                user_agent=self.user_agent,
            )
            games = parse_recent_games(html)
        except Exception as e:
            logger.error(f"[SteamNEW] 抓取/解析失败: {e}")
            yield event.plain_result("获取 Steam 近期发售列表失败（可能被限流/网络异常/页面结构变化）。")
            return

        if not games:
            yield event.plain_result("没有解析到游戏列表（页面结构可能变化）。")
            return

        n = max(1, min(self.top_n, 50))
        top_games = games[:n]

        chain = build_game_chain(top_games, field_switch=self.field_switch)
        yield event.chain_result(chain)

    # ========== 定时任务 ==========
    def _start_cron_task(self):
        if self._cron_task and not self._cron_task.done():
            self._cron_task.cancel()
        self._cron_task = asyncio.create_task(self._cron_loop())

    async def _cron_loop(self):
        try:
            cron = croniter(self.cron_time)
        except Exception as e:
            logger.error(f"[SteamNEW] 无效 cron 表达式 '{self.cron_time}': {e}")
            return

        while True:
            try:
                next_time = cron.get_next(datetime)
                now = datetime.now()
                wait_seconds = (next_time - now).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"[SteamNEW] 下次推送: {next_time.strftime('%Y-%m-%d %H:%M:%S')}（等待 {wait_seconds:.0f}s）")
                    await asyncio.sleep(wait_seconds)

                await self._cron_push_once()

            except asyncio.CancelledError:
                logger.info("[SteamNEW] cron loop cancelled")
                break
            except Exception as e:
                logger.error(f"[SteamNEW] cron loop 异常: {e}，60 秒后重试")
                await asyncio.sleep(60)

    async def _cron_push_once(self):
        # 解析目标：按群号查 UMO
        targets: list[str] = []
        for gid in list(dict.fromkeys(self.push_group_ids)):
            umo = resolve_umo(self.group_umo_path, gid)
            if not umo:
                # 没记录过 UMO：提示日志（用户需要在该群里至少触发一次 /new 或任意指令以记录）
                logger.warning(f"[SteamNEW] 群 {gid} 尚未记录 UMO：请先在该群里触发一次 /new 以便记录会话来源（UMO）")
                continue
            targets.append(umo)

        if not targets:
            logger.info("[SteamNEW] 没有可用推送目标（push_group_ids 为空或都没记录 UMO）")
            return

        # 抓取内容
        try:
            html = await fetch_html(
                url=self.fetch_url,
                timeout_sec=self.timeout_sec,
                user_agent=self.user_agent,
            )
            games = parse_recent_games(html)
        except Exception as e:
            logger.error(f"[SteamNEW] 定时推送抓取/解析失败: {e}")
            return

        if not games:
            return

        n = max(1, min(self.top_n, 50))
        top_games = games[:n]
        # chain = build_game_chain(top_games, field_switch=self.field_switch)
        chain_list = build_game_chain(top_games, field_switch=self.field_switch)

        message_chain = MessageChain(chain=chain_list)  # ✅ 关键

        for umo in targets:
            try:
                await self.context.send_message(umo, message_chain)
            except Exception as e:
                logger.error(f"[SteamNEW] 主动推送失败 umo={umo}: {e}")
        # # 主动发送
        # for umo in targets:
        #     try:
        #         await self.context.send_message(umo, chain)
        #     except Exception as e:
        #         logger.error(f"[SteamNEW] 主动推送失败 umo={umo}: {e}")