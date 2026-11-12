"""游戏公共计算：群号、随机时长、@ 目标解析。"""

import random

from gsuid_core.models import Event


def group_id_of(ev: Event) -> str:
    """只处理数字群号：源插件面向 OneBot，非数字群号无法调用禁言接口。"""
    if ev.user_type != "group" or not ev.group_id:
        return ""
    return ev.group_id if ev.group_id.isdigit() else ""


def meta_group_id(ev: Event) -> str:
    group_id = ev.group_id
    if not group_id:
        raw: object = ev.get_meta("group_id")
        if isinstance(raw, str):
            group_id = raw
        elif isinstance(raw, int):
            group_id = str(raw)
    if not group_id or not group_id.isdigit():
        return ""
    return group_id


def is_exact_command(ev: Event, keyword: str) -> bool:
    """源插件只接受“命令字”或“命令字 + 空格”，避免“天弃之子是什么”误触发。"""
    raw = ev.raw_text.strip()
    for prefix in ("", "自爆"):
        body = raw
        if prefix:
            if not body.startswith(prefix):
                continue
            body = body[len(prefix) :].lstrip(" \t\u3000")
        if body == keyword:
            return True
        if body.startswith(keyword):
            rest = body[len(keyword) :]
            if rest and rest[0] in " \t\u3000@":
                return True
    return False


def random_ban_seconds(minimum: int, maximum: int) -> int:
    low, high = (minimum, maximum) if minimum <= maximum else (maximum, minimum)
    return random.randint(low, high)


def format_ban_seconds(seconds: int) -> str:
    minutes, rest = divmod(seconds, 60)
    return f"{minutes}分{rest}秒" if rest else f"{minutes}分钟"


def extract_at_targets(ev: Event, self_id: str) -> list[str]:
    """按 @ 段顺序取用户 ID，排除 bot 自身与 @全体成员。"""
    raw_targets: list[str] = []
    if ev.at_list:
        raw_targets.extend(str(item) for item in ev.at_list)
    elif ev.at:
        raw_targets.append(str(ev.at))

    targets: list[str] = []
    for raw in raw_targets:
        target = raw.strip().lstrip("@").split(":")[-1].strip()
        if not target.isdigit() or target == self_id or target in targets:
            continue
        targets.append(target)
    return targets
