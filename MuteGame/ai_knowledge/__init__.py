"""MuteGame 的 AI 知识库：插件加载时注册，供 RAG 检索。"""

from gsuid_core.ai_core.configs.ai_config import ai_config

if ai_config.get_config("enable").data:
    from gsuid_core.ai_core.models import KnowledgePoint
    from gsuid_core.ai_core.register import ai_entity

    _PLUGIN = "MuteGame"

    def _kp(kp_id: str, title: str, content: str, tags: list[str]) -> None:
        ai_entity(
            KnowledgePoint(
                id=kp_id,
                plugin=_PLUGIN,
                title=title,
                content=content,
                tags=tags,
            )
        )

    def register_knowledge() -> None:
        _kp(
            "mutegame_overview",
            "MuteGame · 群聊禁言游戏",
            """# MuteGame · 群聊禁言游戏

MuteGame 提供三个群聊禁言玩法：**天弃之子**、**同归于尽**、**精致睡眠**。命令可以直接发，也可以带前缀 `自爆`。

## 命令与权限
- `天弃之子`：随机抽一名群友禁言（所有人可用，群管理员可开/关）。
- `同归于尽 @群友`：与目标一起被禁言，发起者受倍数反弹；`允许被同归` / `禁止被同归` 设置自己是否可被拉。
- `睡眠套餐` / `精致睡眠` / `来一份精致睡眠套餐`：给自己长时间禁言（默认 8 小时）。
- `开启天弃之子` / `关闭天弃之子`、`开启同归于尽` / `关闭同归于尽`、`开启睡眠` / `关闭睡眠`：仅群管理员/群主。
- `自爆帮助`：查看帮助。

## 硬性前提
- 只能在群聊使用；只处理数字群号，频道等平台会直接跳过。
- Bot 必须是群管理员或群主，且适配器实现了禁言控制包 `excute_ban_user`，否则禁言不生效或静默失败。
- 群成员列表走适配器扩展协议 `group_member_list`；不支持时回退到 Core 用户表 + 本地缓存，随机范围会缩小到「见过的群成员」。
- 禁言时长、概率、同归反弹倍数在插件配置里，修改后下条命令生效。

## 安全边界
- 这些命令会真实禁言群友，属于高风险操作；AI **不要**替用户发送或编排禁言命令，也不要主动建议拿群友试玩。
- 用户想用时，让用户自己确认群规、Bot 权限和目标后手动发命令。
- 这是群管理娱乐功能，不是处罚工具；不要用它处理纠纷或替管理员执法。""",
            [
                "MuteGame",
                "禁言",
                "天弃之子",
                "同归于尽",
                "精致睡眠",
                "群管理",
                "自爆",
                "群聊",
            ],
        )

    register_knowledge()
