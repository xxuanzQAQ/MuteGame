"""群成员观察：把名片、身份写入本地缓存，供随机抽取使用。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..utils.game import group_id_of, meta_group_id
from ..utils.roles import sender_card, sender_role, sender_nickname
from ..utils.store import get_store
from ..utils.members import accept_group_members

sv_member = SV("自爆群成员缓存", pm=6, priority=99)


@sv_member.on_message(block=False)
async def record_member(bot: Bot, ev: Event) -> None:
    group_id = group_id_of(ev)
    if not group_id:
        return
    await get_store().touch_member(
        group_id,
        ev.user_id,
        sender_card(ev),
        sender_nickname(ev),
        sender_role(ev),
    )


@sv_member.on_meta(("user_join_group", "user_exit_group", "group_member_list"))
async def record_member_meta(bot: Bot, ev: Event) -> None:
    if ev.meta_event_type == "group_member_list":
        await accept_group_members(ev)
        return

    group_id = meta_group_id(ev)
    if not group_id:
        return

    raw_user_id: object = ev.get_meta("user_id")
    if isinstance(raw_user_id, int):
        user_id = str(raw_user_id)
    elif isinstance(raw_user_id, str):
        user_id = raw_user_id
    else:
        return
    if not user_id:
        return

    if ev.meta_event_type == "user_join_group":
        await get_store().touch_member(group_id, user_id, "", "", "member")
    else:
        await get_store().remove_member(group_id, user_id)
