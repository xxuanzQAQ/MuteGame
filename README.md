# MuteGame

群聊禁言游戏插件，提供**天弃之子**、**同归于尽**、**精致睡眠**三个玩法。

移植自 AstrBot 插件 [`astrbot_plugin_group_fun`](https://github.com/xxuanzQAQ/astrbot_plugin_group_fun)，
命令、提示文案、配置项和状态文件格式保持与原插件一致。

## 环境要求

- GsCore（`gsuid-core`）
- 支持禁言控制的适配器（OneBot v11 / NapCat / Lagrange 等）
- Bot 账号须具有群管理员或群主权限

## 命令

命令可以直接发送，也可以加前缀 `自爆`。

| 命令 | 权限 | 说明 |
|------|------|------|
| `天弃之子` | 所有人 | 随机抽取一名群友禁言 |
| `同归于尽 @群友` | 所有人 | 与目标一同被禁言，发起者受倍数反弹 |
| `允许被同归` | 所有人 | 允许自己被他人同归于尽 |
| `禁止被同归` | 所有人 | 拒绝被他人同归于尽 |
| `睡眠套餐` / `精致睡眠` / `来一份精致睡眠套餐` | 所有人 | 对自己执行长时间禁言 |
| `开启天弃之子` / `关闭天弃之子` | 群管理员/群主 | 开关天弃之子 |
| `开启同归于尽` / `关闭同归于尽` | 群管理员/群主 | 开关同归于尽 |
| `开启睡眠` / `关闭睡眠` | 群管理员/群主 | 开关精致睡眠 |
| `自爆帮助` | 所有人 | 查看帮助 |

## 配置

在 Web 控制台的插件配置页调整以下参数，修改后下一条命令立即生效。

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `tianqi_ban_min` | int | 60 | 天弃之子最短禁言时间（秒） |
| `tianqi_ban_max` | int | 600 | 天弃之子最长禁言时间（秒） |
| `tianqi_miss_prob` | float | 0.15 | 天弃之子劈空概率，范围 0~1 |
| `tianqi_self_ban_prob` | float | 0.2 | 天弃之子连带禁言召唤者的概率，范围 0~1 |
| `tonggui_ban_min` | int | 60 | 同归于尽最短禁言时间（秒） |
| `tonggui_ban_max` | int | 600 | 同归于尽最长禁言时间（秒） |
| `sleep_duration` | int | 28800 | 精致睡眠禁言时长（秒），默认 8 小时 |

## 数据存储

- 功能开关与同归于尽白名单：`data/MuteGame/group_fun_state.json`
- 群成员缓存：`data/MuteGame/group_members.json`

状态文件与 AstrBot 原插件的 `group_fun_state.json` 完全同构。从 AstrBot 迁移时，把
`AstrBot/data/plugin_data/astrbot_plugin_group_fun/group_fun_state.json` 复制到
`data/MuteGame/group_fun_state.json` 即可保留各群开关。

本次移植已把目标环境原有的 78 个群状态复制到 `data/MuteGame/group_fun_state.json`。

## 与原插件的差异

GsCore 与 AstrBot 的平台能力不同，以下几处只能做等价近似：

1. **群成员列表走适配器扩展协议**。GsCore 标准 WS 协议没有成员列表请求，插件用
   `excute_get_group_member_list` 控制包向适配器请求，适配器用
   `meta-group_member_list` 回传全量名单；当前 Yunzai `ws-plugin` 已实现这条链路。
   适配器不支持时，插件等待 3 秒后回退到 core 的 `CoreUser` 表 + 本地缓存，并在
   10 分钟内不再重复等待。回退模式下“随机群友”是“见过的群成员”，长期不发言且在新装
   插件前就退群的人无法完全剔除；真实列表模式下以协议端返回的成员和角色为准。
2. **Bot 群身份**。成员列表包含 Bot 自身时，插件按列表里的 `role` 判断 Bot 是群主/
   管理员/成员；列表不含 Bot 或回退到缓存时按管理员处理。Bot 不是管理员时，真实列表
   会触发原插件的“Bot需要管理员权限才能执行此操作”提示。
3. **禁言是单向控制包**。`bot.ban()` 只把 `excute_ban_user` 交给适配器，core 不等待
   适配器回执；适配器必须实现这个控制包，未实现时会静默丢弃。因此原插件
   “禁言失败: ...” 的提示无法保留，提示文案按成功路径发送。
4. **仅处理数字群号**。源插件面向 OneBot；频道、非数字群号等平台会直接跳过禁言玩法，
   避免向适配器发送无法执行的禁言包。

除上述平台边界外，命令、概率、权重、文案和状态结构均与原插件一致。
