"""同归于尽：拉一位群友一起禁言，发起者受倍数反弹。"""

import random

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment

from ..utils.game import (
    group_id_of,
    is_exact_command,
    extract_at_targets,
    format_ban_seconds,
    random_ban_seconds,
)
from ..utils.roles import (
    ROLE_ADMIN,
    ROLE_OWNER,
    sender_role,
)
from ..utils.store import get_store
from ..utils.members import get_bot_role, get_group_member
from ..groupfun_config import load_settings

sv_tonggui = SV("同归于尽", area="GROUP")


@sv_tonggui.on_command("同归于尽", block=True, aside=False)
async def tonggui(bot: Bot, ev: Event) -> None:
    if not is_exact_command(ev, "同归于尽"):
        return
    group_id = group_id_of(ev)
    if not group_id:
        return

    settings = load_settings()
    store = get_store()
    state = await store.get_group(group_id)
    if not state["tonggui_enabled"]:
        await bot.send("同归于尽功能已关闭")
        return

    sender_id = ev.user_id
    role = sender_role(ev)
    bot_role = await get_bot_role(bot, ev, group_id)
    if bot_role not in (ROLE_ADMIN, ROLE_OWNER):
        await bot.send("Bot需要管理员权限才能执行此操作")
        return
    # 源插件：Bot 不是群主时，发起者若是群主则直接拒绝。
    if bot_role != ROLE_OWNER and role == ROLE_OWNER:
        await bot.send("无法对群主执行禁言")
        return

    target_ids = extract_at_targets(ev, ev.bot_self_id)
    if not target_ids:
        await bot.send("请@一位群友，用法：同归于尽 @群友")
        return

    target_id = target_ids[0]
    if target_id == sender_id:
        await bot.send("不能和自己同归于尽")
        return
    if target_id == ev.bot_self_id:
        await bot.send("不能和我同归于尽")
        return

    target = await get_group_member(bot, ev, group_id, target_id)
    if bot_role == ROLE_ADMIN and target.role in (ROLE_OWNER, ROLE_ADMIN):
        await bot.send("无法对管理员/群主执行禁言")
        return
    if bot_role == ROLE_OWNER and target.role == ROLE_OWNER:
        await bot.send("无法对群主执行禁言")
        return

    allow = await store.get_allow(group_id, target_id)
    if allow is False:
        await bot.send(f"{target.name} 已禁止被同归于尽")
        return

    ban_time = random_ban_seconds(settings.tonggui_ban_min, settings.tonggui_ban_max)
    # 1~9 倍加权随机：1 倍概率最高，9 倍最低。
    weights = [2 * (10 - number) for number in range(1, 10)]
    multiplier = random.choices(range(1, 10), weights=weights, k=1)[0]
    sender_ban = ban_time * multiplier

    can_ban_sender = True
    if bot_role == ROLE_ADMIN and role in (ROLE_OWNER, ROLE_ADMIN):
        can_ban_sender = False
    if bot_role == ROLE_OWNER and role == ROLE_OWNER:
        can_ban_sender = False

    await bot.ban(target_id, group_id, ban_time)
    if can_ban_sender:
        await bot.ban(sender_id, group_id, sender_ban)

    chain = [
        MessageSegment.text("同归于尽！\n"),
        MessageSegment.at(target_id),
        MessageSegment.text(f" 禁言 {format_ban_seconds(ban_time)}\n"),
        MessageSegment.at(sender_id),
        MessageSegment.text(f" 受到 {multiplier} 倍反弹，禁言 {format_ban_seconds(sender_ban)}"),
    ]
    if not can_ban_sender:
        chain.append(MessageSegment.text("\n（权限不足，发起者未被禁言）"))
    await bot.send(chain)


@sv_tonggui.on_command("允许被同归", block=True, aside=False)
async def allow_tonggui(bot: Bot, ev: Event) -> None:
    if not is_exact_command(ev, "允许被同归"):
        return
    group_id = group_id_of(ev)
    if not group_id:
        return
    await get_store().set_allow(group_id, ev.user_id, True)
    await bot.send("你已允许被同归于尽")


@sv_tonggui.on_command("禁止被同归", block=True, aside=False)
async def deny_tonggui(bot: Bot, ev: Event) -> None:
    if not is_exact_command(ev, "禁止被同归"):
        return
    group_id = group_id_of(ev)
    if not group_id:
        return
    await get_store().set_allow(group_id, ev.user_id, False)
    await bot.send("你已禁止被同归于尽")
