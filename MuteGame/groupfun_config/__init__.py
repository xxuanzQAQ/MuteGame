"""配置读取：每次命令执行时现读，热重载/控制台修改立即生效。"""

from dataclasses import dataclass

from gsuid_core.utils.plugins_config.models import GSC, GsIntConfig, GsFloatConfig
from gsuid_core.utils.plugins_config.gs_config import StringConfig

from .config_default import CONFIG_DEFAULT
from ..utils.resource_path import CONFIG_PATH

CONFIG = StringConfig("MuteGame", CONFIG_PATH, CONFIG_DEFAULT)


@dataclass(frozen=True)
class GroupFunSettings:
    """一次命令期间使用的配置快照。"""

    tianqi_ban_min: int
    tianqi_ban_max: int
    tianqi_miss_prob: float
    tianqi_self_ban_prob: float
    tonggui_ban_min: int
    tonggui_ban_max: int
    sleep_duration: int


def _int(key: str, default: int) -> int:
    if key not in CONFIG.config:
        return default
    item: GSC = CONFIG.config[key]
    return int(item.data) if isinstance(item, GsIntConfig) else default


def _float(key: str, default: float) -> float:
    if key not in CONFIG.config:
        return default
    item: GSC = CONFIG.config[key]
    if isinstance(item, GsFloatConfig):
        return float(item.data)
    if isinstance(item, GsIntConfig):
        return float(item.data)
    return default


def load_settings() -> GroupFunSettings:
    return GroupFunSettings(
        tianqi_ban_min=_int("tianqi_ban_min", 60),
        tianqi_ban_max=_int("tianqi_ban_max", 600),
        tianqi_miss_prob=_prob("tianqi_miss_prob", 0.15),
        tianqi_self_ban_prob=_prob("tianqi_self_ban_prob", 0.2),
        tonggui_ban_min=_int("tonggui_ban_min", 60),
        tonggui_ban_max=_int("tonggui_ban_max", 600),
        sleep_duration=_int("sleep_duration", 28800),
    )


def _prob(key: str, default: float) -> float:
    return max(0.0, min(1.0, _float(key, default)))
