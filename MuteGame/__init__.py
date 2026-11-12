"""MuteGame：群聊禁言游戏（天弃之子 / 同归于尽 / 精致睡眠）。

移植自 AstrBot 插件 astrbot_plugin_group_fun，数据格式与配置项保持兼容。
"""

from gsuid_core.sv import Plugins
from gsuid_core.server import on_core_shutdown

Plugins(
    name="MuteGame",
    force_prefix=["自爆"],
    allow_empty_prefix=True,
    alias=["group_fun", "群玩", "自爆"],
)

from . import (  # noqa: E402
    groupfun_help,
    groupfun_sleep,
    groupfun_config,
    groupfun_member,
    groupfun_tianqi,
    groupfun_toggle,
    groupfun_tonggui,
)
from .utils.store import get_store  # noqa: E402


@on_core_shutdown
async def _flush_group_fun_store() -> None:
    await get_store().flush()
