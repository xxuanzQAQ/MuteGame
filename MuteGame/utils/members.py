"""群成员来源：适配器上报 + core 的 CoreUser 表 + 本地缓存。

适配器收到成员列表请求后，会把全量名单放进 meta-group_member_list 上报；
插件收到后替换本地名单。适配器不支持或超时时，退回 CoreUser 铺底 + 本地缓存。
"""

import time
import asyncio
from dataclasses import dataclass

from msgspec import json as msgjson

from gsuid_core.bot import Bot
from gsuid_core.models import Event, Message, MessageSend
from gsuid_core.utils.database.models import CoreUser

from .game import meta_group_id
from .store import MemberRecord, get_store

_SYNC_TIMEOUT = 3.0
_SYNC_TTL = 600.0
_SYNC_RETRY = 600.0

_PENDING: dict[str, asyncio.Event] = {}
_LAST_SYNC: dict[str, float] = {}
_SYNC_STATE: bool | None = None
_SYNC_RETRY_AT = 0.0


@dataclass(frozen=True)
class GroupMember:
    user_id: str
    name: str
    role: str


def _record_name(record: MemberRecord) -> str:
    return record["card"] or record["nickname"]


def _is_real_name(name: str) -> bool:
    return bool(name) and name != "1"


def _core_user_info(row: object) -> tuple[str, str]:
    # CoreUser.get_group_all_user 的返回注解误写成 type[CoreUser]，这里按实例守卫。
    if not isinstance(row, CoreUser):
        return "", ""
    user_id = row.user_id
    name = row.user_name
    return (
        user_id if isinstance(user_id, str) else "",
        name if isinstance(name, str) and _is_real_name(name) else "",
    )


def _meta_text(item: dict[object, object], key: str) -> str:
    if key not in item:
        return ""
    value = item[key]
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int):
        return str(value)
    return ""


def _member_record(item: object, seen_at: int) -> tuple[str, MemberRecord] | None:
    if not isinstance(item, dict):
        return None
    user_id = _meta_text(item, "user_id")
    if not user_id:
        return None
    role = _meta_text(item, "role")
    if role not in ("owner", "admin", "member"):
        role = "member"
    return user_id, MemberRecord(
        card=_meta_text(item, "card"),
        nickname=_meta_text(item, "nickname"),
        role=role,
        last_seen=seen_at,
    )


async def accept_group_members(ev: Event) -> None:
    """处理适配器上报的全量成员列表：替换缓存并唤醒等待中的命令。"""
    group_id = meta_group_id(ev)
    if not group_id:
        return
    raw_members: object = ev.get_meta("members")
    if not isinstance(raw_members, list):
        return

    seen_at = int(time.time())
    records: dict[str, MemberRecord] = {}
    for item in raw_members:
        parsed = _member_record(item, seen_at)
        if parsed is None:
            continue
        user_id, record = parsed
        records[user_id] = record
    if not records:
        return

    global _SYNC_STATE
    _SYNC_STATE = True
    _LAST_SYNC[group_id] = time.monotonic()
    await get_store().replace_members(group_id, records)
    if group_id in _PENDING:
        _PENDING[group_id].set()


async def _send_member_request(bot: Bot, ev: Event, group_id: str) -> bool:
    ws = bot.bot.bot
    if ws is None:
        return False
    send = MessageSend(
        content=[
            Message(
                type="excute_get_group_member_list",
                data={"group_id": group_id, "user_id": ev.user_id},
            )
        ],
        bot_id=ev.real_bot_id or ev.bot_id,
        bot_self_id=ev.bot_self_id,
        target_type="group",
        target_id=group_id,
    )
    # 走底层发送队列，避免把控制包当成普通文本写进 AI 会话历史。
    await bot.bot._enqueue_send(ws.send_bytes(msgjson.encode(send)))
    return True


async def ensure_group_members(bot: Bot, ev: Event, group_id: str) -> None:
    """首次/过期时向适配器要一次真实名单；适配器不支持则本次超时后退回缓存。"""
    global _SYNC_STATE, _SYNC_RETRY_AT
    if not group_id:
        return
    now = time.monotonic()
    if _SYNC_STATE is False and now < _SYNC_RETRY_AT:
        return
    if group_id in _LAST_SYNC and now - _LAST_SYNC[group_id] < _SYNC_TTL:
        return

    if group_id in _PENDING:
        pending = _PENDING[group_id]
    else:
        pending = asyncio.Event()
        _PENDING[group_id] = pending
        if not await _send_member_request(bot, ev, group_id):
            del _PENDING[group_id]
            return

    try:
        await asyncio.wait_for(pending.wait(), timeout=_SYNC_TIMEOUT)
    except TimeoutError:
        _SYNC_STATE = False
        _SYNC_RETRY_AT = time.monotonic() + _SYNC_RETRY
    else:
        _SYNC_STATE = True
    finally:
        if group_id in _PENDING:
            del _PENDING[group_id]


async def list_group_members(bot: Bot, ev: Event, group_id: str) -> list[GroupMember]:
    await ensure_group_members(bot, ev, group_id)
    store = get_store()
    rows = await CoreUser.get_group_all_user(group_id)
    db_users: dict[str, str] = {}
    if rows is not None:
        for row in rows:
            user_id, name = _core_user_info(row)
            if user_id:
                db_users[user_id] = name or user_id

    if not await store.has_members_group(group_id):
        await store.seed_group(group_id, list(db_users.items()))

    records = await store.members(group_id)
    members: list[GroupMember] = []
    for user_id, record in records.items():
        name = _record_name(record)
        if not name and user_id in db_users:
            name = db_users[user_id]
        members.append(GroupMember(user_id=user_id, name=name or user_id, role=record["role"]))
    return members


async def get_group_member(bot: Bot, ev: Event, group_id: str, user_id: str) -> GroupMember:
    for member in await list_group_members(bot, ev, group_id):
        if member.user_id == user_id:
            return member
    return GroupMember(user_id=user_id, name=user_id, role="member")


async def get_bot_role(bot: Bot, ev: Event, group_id: str) -> str:
    """从全量成员列表里找 Bot 自身；适配器没返回时按管理员处理。"""
    for member in await list_group_members(bot, ev, group_id):
        if member.user_id == ev.bot_self_id:
            return member.role
    return "admin"
