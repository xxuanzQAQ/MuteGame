"""天弃之子：随机抽一位群友禁言。"""

import random

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..utils.game import group_id_of, is_exact_command, format_ban_seconds, random_ban_seconds
from ..utils.roles import (
    ROLE_ADMIN,
    ROLE_OWNER,
    sender_role,
    sender_display_name,
    is_group_admin_or_owner,
)
from ..utils.store import get_store
from ..utils.members import GroupMember, get_bot_role, list_group_members
from ..groupfun_config import load_settings

sv_tianqi = SV("天弃之子", area="GROUP")


@sv_tianqi.on_command("天弃之子", block=True, aside=False)
async def tianqi_child(bot: Bot, ev: Event) -> None:
    if not is_exact_command(ev, "天弃之子"):
        return
    group_id = group_id_of(ev)
    if not group_id:
        return

    settings = load_settings()
    store = get_store()
    state = await store.get_group(group_id)
    if not state["tianqi_enabled"]:
        await bot.send("天弃之子功能已关闭")
        return

    bot_role = await get_bot_role(bot, ev, group_id)
    if bot_role not in (ROLE_ADMIN, ROLE_OWNER):
        await bot.send("Bot需要管理员权限才能执行此操作")
        return

    members = await list_group_members(bot, ev, group_id)
    if not any(member.user_id == ev.user_id for member in members):
        members.append(GroupMember(ev.user_id, sender_display_name(ev), sender_role(ev)))
    # Bot 是管理员时排除群主和其他管理员；Bot 是群主时只排除群主。
    excluded = (ROLE_OWNER, ROLE_ADMIN) if bot_role == ROLE_ADMIN else (ROLE_OWNER,)
    candidates = [member for member in members if member.user_id != ev.bot_self_id and member.role not in excluded]
    if not candidates:
        await bot.send("没有可以禁言的群友")
        return

    victim = random.choice(candidates)
    victim_name = victim.name

    if random.random() < settings.tianqi_miss_prob:
        miss_texts = [
            f"一道闪电劈向了 {victim_name}，但是歪了，毫发无伤。",
            f"雷公打了个盹，闪电劈到了旁边的树上，{victim_name} 逃过一劫。",
            f"一只鸽子挡住了闪电，{victim_name} 安然无恙。",
            f"天空一声巨响，结果只是下了场小雨，{victim_name} 今天运气不错。",
        ]
        await bot.send(random.choice(miss_texts))
        return

    ban_time = random_ban_seconds(settings.tianqi_ban_min, settings.tianqi_ban_max)
    await bot.ban(victim.user_id, group_id, ban_time)

    text = f"一道闪电劈中了 {victim_name}，成为今天的天弃之子，禁言 {format_ban_seconds(ban_time)}"

    sender_id = ev.user_id
    if victim.user_id != sender_id and random.random() < settings.tianqi_self_ban_prob:
        if not is_group_admin_or_owner(sender_role(ev)):
            self_ban_time = random_ban_seconds(settings.tianqi_ban_min, settings.tianqi_ban_max)
            await bot.ban(sender_id, group_id, self_ban_time)
            sender_name = sender_display_name(ev)
            text += f"\n闪电余波波及了召唤者 {sender_name}，禁言 {format_ban_seconds(self_ban_time)}"

    await bot.send(text)
