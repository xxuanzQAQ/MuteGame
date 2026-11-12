"""发送者昵称与群身份。"""

from gsuid_core.models import Event

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"


def _sender_field(ev: Event, key: str) -> str:
    if key not in ev.sender:
        return ""
    raw: object = ev.sender[key]
    return raw if isinstance(raw, str) else ""


def sender_role(ev: Event) -> str:
    role = _sender_field(ev, "role")
    if role in (ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER):
        return role
    # 部分适配器不填 sender.role，core 已把群身份折算进 user_pm。
    if ev.user_pm == 2:
        return ROLE_OWNER
    if ev.user_pm == 3:
        return ROLE_ADMIN
    return ROLE_MEMBER


def is_group_admin_or_owner(role: str) -> bool:
    return role in (ROLE_OWNER, ROLE_ADMIN)


def sender_nickname(ev: Event) -> str:
    return _sender_field(ev, "nickname") or _sender_field(ev, "user_name")


def sender_card(ev: Event) -> str:
    return _sender_field(ev, "card")


def sender_display_name(ev: Event) -> str:
    return sender_card(ev) or sender_nickname(ev) or ev.user_id
