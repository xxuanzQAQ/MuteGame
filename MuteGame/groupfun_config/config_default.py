"""MuteGame 配置项定义。"""

from gsuid_core.utils.plugins_config.models import GSC, GsIntConfig, GsFloatConfig

CONFIG_DEFAULT: dict[str, GSC] = {
    "tianqi_ban_min": GsIntConfig(
        title="天弃之子最短禁言时间(秒)",
        desc="天弃之子功能随机禁言的最短时间，单位：秒",
        data=60,
    ),
    "tianqi_ban_max": GsIntConfig(
        title="天弃之子最长禁言时间(秒)",
        desc="天弃之子功能随机禁言的最长时间，单位：秒",
        data=600,
    ),
    "tianqi_miss_prob": GsFloatConfig(
        title="天弃之子劈空概率",
        desc="天弃之子闪电劈不中人的概率，0表示必中，1表示必空",
        data=0.15,
        min_value=0.0,
        max_value=1.0,
    ),
    "tianqi_self_ban_prob": GsFloatConfig(
        title="天弃之子连带禁言概率",
        desc="天弃之子禁言命中后，闪电余波连带禁言召唤者的概率",
        data=0.2,
        min_value=0.0,
        max_value=1.0,
    ),
    "tonggui_ban_min": GsIntConfig(
        title="同归于尽最短禁言时间(秒)",
        desc="同归于尽功能禁言的最短时间，单位：秒",
        data=60,
    ),
    "tonggui_ban_max": GsIntConfig(
        title="同归于尽最长禁言时间(秒)",
        desc="同归于尽功能禁言的最长时间，单位：秒",
        data=600,
    ),
    "sleep_duration": GsIntConfig(
        title="精致睡眠禁言时长(秒)",
        desc="精致睡眠套餐的禁言时长，默认28800秒（8小时）",
        data=28800,
    ),
}
