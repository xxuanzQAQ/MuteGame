"""功能开关：仅群管理员/群主可用。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..utils.game import group_id_of, is_exact_command
from ..utils.roles import sender_role, is_group_admin_or_owner
from ..utils.store import FeatureKey, get_store

sv_toggle = SV("自爆功能开关", area="GROUP")

_TOGGLES: dict[str, tuple[FeatureKey, bool, str]] = {
    "关闭天弃之子": ("tianqi_enabled", False, "天弃之子"),
    "开启天弃之子": ("tianqi_enabled", True, "天弃之子"),
    "关闭同归于尽": ("tonggui_enabled", False, "同归于尽"),
    "开启同归于尽": ("tonggui_enabled", True, "同归于尽"),
    "关闭睡眠": ("sleep_enabled", False, "精致睡眠"),
    "开启睡眠": ("sleep_enabled", True, "精致睡眠"),
}

_TOGGLE_KEYWORDS = tuple(_TOGGLES)


@sv_toggle.on_command(_TOGGLE_KEYWORDS, block=True, aside=False)
async def toggle_feature(bot: Bot, ev: Event) -> None:
    if not is_exact_command(ev, ev.command):
        return
    group_id = group_id_of(ev)
    if not group_id:
        return

    if not is_group_admin_or_owner(sender_role(ev)):
        await bot.send("需要群管理员/群主权限")
        return

    command = ev.command
    if command not in _TOGGLES:
        return

    feature, value, label = _TOGGLES[command]
    await get_store().set_enabled(group_id, feature, value)
    action = "开启" if value else "关闭"
    await bot.send(f"已{action}{label}")
