"""精致睡眠：给自己来一份长时间禁言套餐。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment

from ..utils.game import group_id_of, is_exact_command
from ..utils.roles import ROLE_ADMIN, ROLE_OWNER, sender_role
from ..utils.store import get_store
from ..utils.members import get_bot_role
from ..groupfun_config import load_settings

sv_sleep = SV("精致睡眠", area="GROUP")

_SLEEP_KEYWORDS = ("睡眠套餐", "精致睡眠", "来一份精致睡眠套餐")


@sv_sleep.on_command(_SLEEP_KEYWORDS, block=True, aside=False)
async def sleep_ban(bot: Bot, ev: Event) -> None:
    if not is_exact_command(ev, ev.command):
        return
    group_id = group_id_of(ev)
    if not group_id:
        return

    settings = load_settings()
    store = get_store()
    state = await store.get_group(group_id)
    if not state["sleep_enabled"]:
        await bot.send("精致睡眠功能已关闭")
        return

    # 源插件先检查 Bot 权限，再按 Bot 是管理员/群主分别限制发起者。
    bot_role = await get_bot_role(bot, ev, group_id)
    if bot_role not in (ROLE_ADMIN, ROLE_OWNER):
        await bot.send("Bot需要管理员权限才能执行此操作")
        return
    role = sender_role(ev)
    if bot_role == ROLE_ADMIN and role in (ROLE_OWNER, ROLE_ADMIN):
        await bot.send("无法对管理员/群主执行禁言")
        return
    if bot_role == ROLE_OWNER and role == ROLE_OWNER:
        await bot.send("群主无法使用此功能")
        return

    await bot.ban(ev.user_id, group_id, settings.sleep_duration)

    hours = settings.sleep_duration // 3600
    chain = [
        MessageSegment.at(ev.user_id),
        MessageSegment.text(f" 晚安，已开启 {hours} 小时精致睡眠套餐。"),
    ]
    await bot.send(chain)
