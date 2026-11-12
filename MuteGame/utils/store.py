"""群状态与群成员缓存的持久化。

状态文件保持 astrbot_plugin_group_fun 的原始结构，可直接迁移；
成员缓存只服务于“随机抽一位群友”，与功能开关状态分开存放。
"""

import json
import time
import asyncio
from typing import Literal, TypedDict
from pathlib import Path

from gsuid_core.pool import to_thread
from gsuid_core.logger import logger

from .resource_path import STATE_PATH, MEMBERS_PATH

FeatureKey = Literal["tianqi_enabled", "tonggui_enabled", "sleep_enabled"]

_MEMBERS_SAVE_INTERVAL = 600.0


class GroupState(TypedDict):
    tianqi_enabled: bool
    tonggui_enabled: bool
    sleep_enabled: bool
    tonggui_allow: dict[str, bool]


class MemberRecord(TypedDict):
    card: str
    nickname: str
    role: str
    last_seen: int


def default_group_state() -> GroupState:
    return {
        "tianqi_enabled": True,
        "tonggui_enabled": True,
        "sleep_enabled": True,
        "tonggui_allow": {},
    }


def _copy_state(state: GroupState) -> GroupState:
    return {
        "tianqi_enabled": state["tianqi_enabled"],
        "tonggui_enabled": state["tonggui_enabled"],
        "sleep_enabled": state["sleep_enabled"],
        "tonggui_allow": dict(state["tonggui_allow"]),
    }


def _parse_bool(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _parse_allow(raw: object) -> dict[str, bool]:
    if not isinstance(raw, dict):
        return {}
    allow: dict[str, bool] = {}
    for user_id, value in raw.items():
        if isinstance(user_id, str) and user_id and isinstance(value, bool):
            allow[user_id] = value
    return allow


def _parse_group(raw: object) -> GroupState:
    if not isinstance(raw, dict):
        return default_group_state()
    return {
        "tianqi_enabled": _parse_bool(raw["tianqi_enabled"], True) if "tianqi_enabled" in raw else True,
        "tonggui_enabled": _parse_bool(raw["tonggui_enabled"], True) if "tonggui_enabled" in raw else True,
        "sleep_enabled": _parse_bool(raw["sleep_enabled"], True) if "sleep_enabled" in raw else True,
        "tonggui_allow": _parse_allow(raw["tonggui_allow"]) if "tonggui_allow" in raw else {},
    }


def _parse_state(raw: object) -> dict[str, GroupState]:
    if not isinstance(raw, dict):
        return {}
    state: dict[str, GroupState] = {}
    for group_id, item in raw.items():
        if isinstance(group_id, str) and group_id:
            state[group_id] = _parse_group(item)
    return state


def _parse_member(raw: object) -> MemberRecord | None:
    if not isinstance(raw, dict):
        return None
    card = raw["card"] if "card" in raw and isinstance(raw["card"], str) else ""
    nickname = raw["nickname"] if "nickname" in raw and isinstance(raw["nickname"], str) else ""
    role = raw["role"] if "role" in raw and isinstance(raw["role"], str) else "member"
    last_seen = raw["last_seen"] if "last_seen" in raw and isinstance(raw["last_seen"], int) else 0
    return MemberRecord(card=card, nickname=nickname, role=role, last_seen=last_seen)


def _parse_members(raw: object) -> dict[str, dict[str, MemberRecord]]:
    if not isinstance(raw, dict):
        return {}
    members: dict[str, dict[str, MemberRecord]] = {}
    for group_id, group_raw in raw.items():
        if not isinstance(group_id, str) or not group_id or not isinstance(group_raw, dict):
            continue
        group: dict[str, MemberRecord] = {}
        for user_id, record_raw in group_raw.items():
            if not isinstance(user_id, str) or not user_id:
                continue
            record = _parse_member(record_raw)
            if record is not None:
                group[user_id] = record
        members[group_id] = group
    return members


@to_thread
def _read_json(path: Path) -> object:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"[MuteGame] 读取 {path.name} 失败: {e}")
        return {}


@to_thread
def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


class GroupFunStore:
    """一个进程内共享的状态仓库；文件读写串行化，避免并发覆盖。"""

    def __init__(self, state_path: Path = STATE_PATH, members_path: Path = MEMBERS_PATH) -> None:
        self.state_path = state_path
        self.members_path = members_path
        self._state: dict[str, GroupState] = {}
        self._members: dict[str, dict[str, MemberRecord]] = {}
        self._lock = asyncio.Lock()
        self._loaded = False
        self._members_dirty = False
        self._last_members_save = 0.0

    async def ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            state_raw: object = await _read_json(self.state_path)
            members_raw: object = await _read_json(self.members_path)
            self._state = _parse_state(state_raw)
            self._members = _parse_members(members_raw)
            self._loaded = True

    async def get_group(self, group_id: str) -> GroupState:
        await self.ensure_loaded()
        async with self._lock:
            state = self._state[group_id] if group_id in self._state else default_group_state()
            self._state[group_id] = state
            return _copy_state(state)

    async def set_enabled(self, group_id: str, feature: FeatureKey, value: bool) -> None:
        await self.ensure_loaded()
        async with self._lock:
            state = self._state[group_id] if group_id in self._state else default_group_state()
            state[feature] = value
            self._state[group_id] = state
            await self._save_state_locked()

    async def set_allow(self, group_id: str, user_id: str, value: bool) -> None:
        await self.ensure_loaded()
        async with self._lock:
            state = self._state[group_id] if group_id in self._state else default_group_state()
            state["tonggui_allow"][user_id] = value
            self._state[group_id] = state
            await self._save_state_locked()

    async def get_allow(self, group_id: str, user_id: str) -> bool | None:
        await self.ensure_loaded()
        async with self._lock:
            if group_id not in self._state:
                return None
            allow = self._state[group_id]["tonggui_allow"]
            return allow[user_id] if user_id in allow else None

    async def has_members_group(self, group_id: str) -> bool:
        await self.ensure_loaded()
        async with self._lock:
            return group_id in self._members

    async def members(self, group_id: str) -> dict[str, MemberRecord]:
        await self.ensure_loaded()
        async with self._lock:
            group = self._members[group_id] if group_id in self._members else {}
            return {
                user_id: MemberRecord(
                    card=record["card"],
                    nickname=record["nickname"],
                    role=record["role"],
                    last_seen=record["last_seen"],
                )
                for user_id, record in group.items()
            }

    async def seed_group(self, group_id: str, seeds: list[tuple[str, str]]) -> None:
        """首次见到某个群时，用 core 的历史用户表铺一遍底；之后以本地成员表为准。"""
        await self.ensure_loaded()
        async with self._lock:
            group = self._members[group_id] if group_id in self._members else {}
            for user_id, nickname in seeds:
                if user_id in group:
                    continue
                group[user_id] = MemberRecord(card="", nickname=nickname, role="member", last_seen=0)
            self._members[group_id] = group
            self._members_dirty = False
            await self._save_members_locked()

    async def replace_members(self, group_id: str, members: dict[str, MemberRecord]) -> None:
        """用适配器上报的全量列表替换本地名单，避免把已退群的人继续留在池子里。"""
        if not group_id or not members:
            return
        await self.ensure_loaded()
        async with self._lock:
            self._members[group_id] = {
                user_id: MemberRecord(
                    card=record["card"],
                    nickname=record["nickname"],
                    role=record["role"],
                    last_seen=record["last_seen"],
                )
                for user_id, record in members.items()
                if user_id
            }
            self._members_dirty = False
            self._last_members_save = time.time()
            await self._save_members_locked()

    async def touch_member(self, group_id: str, user_id: str, card: str, nickname: str, role: str) -> None:
        if not group_id or not user_id:
            return
        await self.ensure_loaded()
        async with self._lock:
            group = self._members[group_id] if group_id in self._members else {}
            record = (
                group[user_id] if user_id in group else MemberRecord(card="", nickname="", role="member", last_seen=0)
            )
            record["card"] = card or record["card"]
            record["nickname"] = nickname or record["nickname"]
            record["role"] = role or record["role"]
            record["last_seen"] = int(time.time())
            group[user_id] = record
            self._members[group_id] = group

            now = time.time()
            if now - self._last_members_save < _MEMBERS_SAVE_INTERVAL:
                self._members_dirty = True
                return
            self._last_members_save = now
            self._members_dirty = False
            await self._save_members_locked()

    async def remove_member(self, group_id: str, user_id: str) -> None:
        await self.ensure_loaded()
        async with self._lock:
            if group_id not in self._members:
                return
            group = self._members[group_id]
            if user_id not in group:
                return
            del group[user_id]
            self._members_dirty = False
            await self._save_members_locked()

    async def flush(self) -> None:
        if not self._loaded:
            return
        async with self._lock:
            if self._members_dirty:
                self._members_dirty = False
                await self._save_members_locked()

    async def _save_state_locked(self) -> None:
        snapshot: dict[str, GroupState] = {group_id: _copy_state(state) for group_id, state in self._state.items()}
        try:
            await _write_json(self.state_path, snapshot)
        except (OSError, TypeError) as e:
            logger.warning(f"[MuteGame] 写入 {self.state_path.name} 失败: {e}")

    async def _save_members_locked(self) -> None:
        snapshot: dict[str, dict[str, MemberRecord]] = {
            group_id: {
                user_id: MemberRecord(
                    card=record["card"],
                    nickname=record["nickname"],
                    role=record["role"],
                    last_seen=record["last_seen"],
                )
                for user_id, record in group.items()
            }
            for group_id, group in self._members.items()
        }
        try:
            await _write_json(self.members_path, snapshot)
        except (OSError, TypeError) as e:
            logger.warning(f"[MuteGame] 写入 {self.members_path.name} 失败: {e}")


_STORE = GroupFunStore()


def get_store() -> GroupFunStore:
    return _STORE
