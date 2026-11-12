"""MuteGame 定向测试：文案、禁言参数、状态持久化。"""

import random
import asyncio
from pathlib import Path

import MuteGame.utils.members as members_module
import MuteGame.groupfun_sleep as sleep_module
import MuteGame.groupfun_tianqi as tianqi_module
import MuteGame.groupfun_toggle as toggle_module
import MuteGame.groupfun_tonggui as tonggui_module
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from MuteGame.utils.game import is_exact_command, extract_at_targets, format_ban_seconds
from MuteGame.utils.store import MemberRecord, GroupFunStore
from MuteGame.utils.members import GroupMember
from MuteGame.groupfun_config import GroupFunSettings


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[str | list[MessageSegment]] = []
        self.bans: list[tuple[str, str, int]] = []

    async def send(self, message: str | list[MessageSegment]) -> None:
        self.sent.append(message)

    async def ban(self, user_id: str, group_id: str, duration: int) -> None:
        self.bans.append((user_id, group_id, duration))


class FakeStore:
    def __init__(self) -> None:
        self.last_enabled: tuple[str, str, bool] | None = None
        self.last_allow: tuple[str, str, bool] | None = None
        self.replaced: dict[str, dict[str, MemberRecord]] | None = None

    async def get_group(self, group_id: str) -> dict[str, object]:
        return {
            "tianqi_enabled": True,
            "tonggui_enabled": True,
            "sleep_enabled": True,
            "tonggui_allow": {},
        }

    async def get_allow(self, group_id: str, user_id: str) -> bool | None:
        return None

    async def set_enabled(self, group_id: str, feature: str, value: bool) -> None:
        self.last_enabled = (group_id, feature, value)

    async def set_allow(self, group_id: str, user_id: str, value: bool) -> None:
        self.last_allow = (group_id, user_id, value)

    async def has_members_group(self, group_id: str) -> bool:
        return False

    async def replace_members(self, group_id: str, members: dict[str, MemberRecord]) -> None:
        self.replaced = {group_id: members}


def make_event(
    *,
    raw_text: str = "",
    at_list: list[str] | None = None,
    sender: dict[str, str] | None = None,
    command: str = "",
) -> Event:
    return Event(
        user_type="group",
        group_id="10001",
        user_id="20002",
        bot_self_id="30003",
        sender=sender or {"role": "member", "nickname": "Alice", "card": "小A"},
        at_list=at_list or [],
        raw_text=raw_text,
        command=command,
    )


def make_settings() -> GroupFunSettings:
    return GroupFunSettings(
        tianqi_ban_min=60,
        tianqi_ban_max=60,
        tianqi_miss_prob=0.0,
        tianqi_self_ban_prob=0.0,
        tonggui_ban_min=60,
        tonggui_ban_max=60,
        sleep_duration=28800,
    )


async def fake_members(bot: FakeBot, ev: Event, group_id: str) -> list[GroupMember]:
    return [
        GroupMember("20002", "小A", "member"),
        GroupMember("40004", "小B", "member"),
    ]


async def fake_bot_role(bot: FakeBot, ev: Event, group_id: str) -> str:
    return "admin"


def test_format_ban_seconds() -> None:
    assert format_ban_seconds(60) == "1分钟"
    assert format_ban_seconds(61) == "1分1秒"
    assert format_ban_seconds(600) == "10分钟"


def test_extract_at_targets() -> None:
    event = Event(
        user_type="group",
        group_id="10001",
        bot_self_id="30003",
        at_list=["40004", "30003", "102688627:all", "40004"],
    )
    assert extract_at_targets(event, "30003") == ["40004"]


def test_is_exact_command() -> None:
    assert is_exact_command(make_event(raw_text="天弃之子"), "天弃之子")
    assert is_exact_command(make_event(raw_text="天弃之子 是什么"), "天弃之子")
    assert is_exact_command(make_event(raw_text="自爆天弃之子"), "天弃之子")
    assert is_exact_command(make_event(raw_text="自爆 天弃之子"), "天弃之子")
    assert not is_exact_command(make_event(raw_text="天弃之子是什么"), "天弃之子")


def test_tianqi_ignores_longer_text() -> None:
    original = (
        tianqi_module.load_settings,
        tianqi_module.get_store,
        tianqi_module.list_group_members,
        tianqi_module.get_bot_role,
    )
    try:
        tianqi_module.load_settings = make_settings
        tianqi_module.get_store = lambda: FakeStore()
        tianqi_module.list_group_members = fake_members
        tianqi_module.get_bot_role = fake_bot_role
        bot = FakeBot()
        asyncio.run(tianqi_module.tianqi_child.__wrapped__(bot, make_event(raw_text="天弃之子是什么")))
    finally:
        (
            tianqi_module.load_settings,
            tianqi_module.get_store,
            tianqi_module.list_group_members,
            tianqi_module.get_bot_role,
        ) = original
    assert bot.sent == []
    assert bot.bans == []


def test_store_roundtrip(tmp_path: Path) -> None:
    async def run() -> None:
        state_path = tmp_path / "state.json"
        members_path = tmp_path / "members.json"
        store = GroupFunStore(state_path, members_path)
        await store.set_enabled("10001", "tianqi_enabled", False)
        await store.set_allow("10001", "20002", False)
        await store.seed_group("10001", [("20002", "小A")])
        await store.touch_member("10001", "20002", "小A", "Alice", "admin")
        await store.flush()

        reloaded = GroupFunStore(state_path, members_path)
        state = await reloaded.get_group("10001")
        assert state["tianqi_enabled"] is False
        assert await reloaded.get_allow("10001", "20002") is False
        record = (await reloaded.members("10001"))["20002"]
        assert record["card"] == "小A"
        assert record["role"] == "admin"

    asyncio.run(run())


def test_accept_group_members_meta() -> None:
    original = members_module.get_store
    store = FakeStore()
    members_module.get_store = lambda: store
    try:
        event = Event(
            user_type="group",
            group_id="10001",
            meta_event_type="group_member_list",
            meta_event_data={
                "members": [
                    {"user_id": 20002, "nickname": "小A", "card": "A", "role": "admin"},
                    {"user_id": "40004", "nickname": "小B", "card": "", "role": "member"},
                    {"user_id": "", "role": "owner"},
                ]
            },
        )
        asyncio.run(members_module.accept_group_members(event))
    finally:
        members_module.get_store = original

    assert store.replaced is not None
    group = store.replaced["10001"]
    assert group["20002"]["role"] == "admin"
    assert group["40004"]["card"] == ""
    assert "" not in group


def test_get_bot_role_from_members() -> None:
    original = members_module.list_group_members

    async def bot_members(bot: FakeBot, ev: Event, group_id: str) -> list[GroupMember]:
        return [GroupMember("30003", "Bot", "owner"), GroupMember("20002", "小A", "member")]

    members_module.list_group_members = bot_members
    try:
        assert asyncio.run(members_module.get_bot_role(FakeBot(), make_event(), "10001")) == "owner"
    finally:
        members_module.list_group_members = original

    async def no_bot_members(bot: FakeBot, ev: Event, group_id: str) -> list[GroupMember]:
        return [GroupMember("20002", "小A", "member")]

    members_module.list_group_members = no_bot_members
    try:
        assert asyncio.run(members_module.get_bot_role(FakeBot(), make_event(), "10001")) == "admin"
    finally:
        members_module.list_group_members = original


def test_tianqi_message() -> None:
    original = (
        tianqi_module.load_settings,
        tianqi_module.get_store,
        tianqi_module.list_group_members,
        tianqi_module.get_bot_role,
    )
    try:
        random.seed(1)
        tianqi_module.load_settings = make_settings
        tianqi_module.get_store = lambda: FakeStore()
        tianqi_module.list_group_members = fake_members
        tianqi_module.get_bot_role = fake_bot_role
        bot = FakeBot()
        asyncio.run(tianqi_module.tianqi_child.__wrapped__(bot, make_event(raw_text="天弃之子")))
    finally:
        (
            tianqi_module.load_settings,
            tianqi_module.get_store,
            tianqi_module.list_group_members,
            tianqi_module.get_bot_role,
        ) = original

    assert len(bot.bans) == 1
    assert bot.bans[0][1] == "10001"
    assert "禁言 1分钟" in str(bot.sent[0])


def test_tonggui_chain() -> None:
    original = (
        tonggui_module.load_settings,
        tonggui_module.get_store,
        tonggui_module.get_group_member,
        tonggui_module.get_bot_role,
    )
    try:
        random.seed(1)
        tonggui_module.load_settings = make_settings
        tonggui_module.get_store = lambda: FakeStore()
        tonggui_module.get_group_member = lambda bot, ev, group_id, user_id: _member(user_id)
        tonggui_module.get_bot_role = fake_bot_role
        bot = FakeBot()
        event = make_event(raw_text="同归于尽", at_list=["40004"])
        asyncio.run(tonggui_module.tonggui.__wrapped__(bot, event))
    finally:
        (
            tonggui_module.load_settings,
            tonggui_module.get_store,
            tonggui_module.get_group_member,
            tonggui_module.get_bot_role,
        ) = original

    assert len(bot.bans) == 2
    assert bot.bans[0][0] == "40004"
    assert bot.bans[1][0] == "20002"
    chain = bot.sent[0]
    assert isinstance(chain, list)
    assert chain[0].data == "同归于尽！\n"
    assert chain[1].data == "40004"
    assert chain[3].data == "20002"


async def _member(user_id: str) -> GroupMember:
    return GroupMember(user_id, "小B", "member")


def test_sleep_admin_message() -> None:
    original = sleep_module.load_settings, sleep_module.get_store, sleep_module.get_bot_role
    try:
        sleep_module.load_settings = make_settings
        sleep_module.get_store = lambda: FakeStore()
        sleep_module.get_bot_role = fake_bot_role
        bot = FakeBot()
        event = make_event(raw_text="睡眠套餐", command="睡眠套餐", sender={"role": "admin", "nickname": "Admin"})
        asyncio.run(sleep_module.sleep_ban.__wrapped__(bot, event))
    finally:
        sleep_module.load_settings, sleep_module.get_store, sleep_module.get_bot_role = original
    assert bot.sent == ["无法对管理员/群主执行禁言"]


def test_sleep_bot_owner_allows_admin() -> None:
    original = sleep_module.load_settings, sleep_module.get_store, sleep_module.get_bot_role
    try:
        sleep_module.load_settings = make_settings
        sleep_module.get_store = lambda: FakeStore()

        async def owner_role(bot: FakeBot, ev: Event, group_id: str) -> str:
            return "owner"

        sleep_module.get_bot_role = owner_role
        bot = FakeBot()
        event = make_event(raw_text="睡眠套餐", command="睡眠套餐", sender={"role": "admin", "nickname": "Admin"})
        asyncio.run(sleep_module.sleep_ban.__wrapped__(bot, event))
    finally:
        sleep_module.load_settings, sleep_module.get_store, sleep_module.get_bot_role = original
    assert bot.bans == [("20002", "10001", 28800)]
    assert "晚安" in str(bot.sent[0])


def test_sleep_bot_owner_rejects_owner() -> None:
    original = sleep_module.load_settings, sleep_module.get_store, sleep_module.get_bot_role
    try:
        sleep_module.load_settings = make_settings
        sleep_module.get_store = lambda: FakeStore()

        async def owner_role(bot: FakeBot, ev: Event, group_id: str) -> str:
            return "owner"

        sleep_module.get_bot_role = owner_role
        bot = FakeBot()
        event = make_event(raw_text="睡眠套餐", command="睡眠套餐", sender={"role": "owner", "nickname": "Owner"})
        asyncio.run(sleep_module.sleep_ban.__wrapped__(bot, event))
    finally:
        sleep_module.load_settings, sleep_module.get_store, sleep_module.get_bot_role = original
    assert bot.sent == ["群主无法使用此功能"]


def test_toggle_permission() -> None:
    original = toggle_module.get_store
    try:
        toggle_module.get_store = lambda: FakeStore()
        bot = FakeBot()
        asyncio.run(
            toggle_module.toggle_feature.__wrapped__(bot, make_event(raw_text="关闭天弃之子", command="关闭天弃之子"))
        )
        assert bot.sent == ["需要群管理员/群主权限"]

        store = FakeStore()
        toggle_module.get_store = lambda: store
        bot = FakeBot()
        event = make_event(
            raw_text="关闭天弃之子", command="关闭天弃之子", sender={"role": "admin", "nickname": "Admin"}
        )
        asyncio.run(toggle_module.toggle_feature.__wrapped__(bot, event))
        assert bot.sent == ["已关闭天弃之子"]
        assert store.last_enabled == ("10001", "tianqi_enabled", False)
    finally:
        toggle_module.get_store = original


def test_record_struct() -> None:
    record = MemberRecord(card="", nickname="Alice", role="member", last_seen=1)
    assert record["nickname"] == "Alice"
