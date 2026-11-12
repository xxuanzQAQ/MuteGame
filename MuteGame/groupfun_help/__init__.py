"""帮助：注册到 core 帮助一览，并提供文本帮助。"""

from PIL import Image

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.help.utils import register_help, clean_plugin_help

from ..utils.game import is_exact_command
from ..utils.resource_path import ICON_PATH

HELP_TEXT = """【天弃之子】发送"天弃之子"随机选一位群友禁言
【同归于尽】发送"同归于尽@群友"拉人一起禁言；发送"允许被同归/禁止被同归"设置自己是否可被同归
【精致睡眠】发送"睡眠套餐/精致睡眠/来一份精致睡眠套餐"给自己禁言8小时
管理员可发送"关闭天弃之子/关闭同归于尽/关闭睡眠"来关闭对应功能

以上命令也可以带上前缀「自爆」。

注意：群成员列表通过适配器扩展请求；当前 ws-plugin 已支持，
未支持时回退到本地缓存。禁言通过 excute_ban_user 下发，
也需要适配器实现；请确保 Bot 是群管理员或群主。"""

sv_help = SV("自爆帮助", area="ALL")


@sv_help.on_command("自爆帮助", block=True, aside=False)
async def send_help(bot: Bot, ev: Event) -> None:
    if not is_exact_command(ev, "自爆帮助"):
        return
    await bot.send(HELP_TEXT)


clean_plugin_help("MuteGame")
register_help(
    "MuteGame",
    "自爆帮助",
    Image.open(ICON_PATH) if ICON_PATH.exists() else None,
)
