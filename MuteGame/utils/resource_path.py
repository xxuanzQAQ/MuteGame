"""插件运行时路径。"""

from pathlib import Path

from gsuid_core.data_store import get_res_path

PLUGIN_NAME = "MuteGame"

PLUGIN_DIR = Path(__file__).resolve().parents[2]
ICON_PATH = PLUGIN_DIR / "ICON.png"

MAIN_PATH = get_res_path() / PLUGIN_NAME
MAIN_PATH.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = MAIN_PATH / "config.json"
STATE_PATH = MAIN_PATH / "group_fun_state.json"
MEMBERS_PATH = MAIN_PATH / "group_members.json"
