import json
from ub_core.utils import run_shell_cmd
from app import BOT, Message

@BOT.add_cmd(cmd=["speedtest", "st"])
async def speedtest_cmd(bot: BOT, message: Message):
    """
    CMD: SPEEDTEST
    INFO: Runs a network speedtest using the Ookla CLI.
    USAGE: .speedtest | .st
    """
    response = await message.reply("`Running Speedtest... This will take about 20 seconds.`")
    
    try:
        output = await run_shell_cmd(cmd="speedtest --accept-license --accept-gdpr -f json", timeout=60)
        
        data = json.loads(output)
        
        server_name = data.get("server", {}).get("name", "Unknown")
        server_location = data.get("server", {}).get("location", "Unknown")
        isp = data.get("isp", "Unknown")
        
        dl_mbps = round(data.get("download", {}).get("bandwidth", 0) * 8 / 1000000, 2)
        ul_mbps = round(data.get("upload", {}).get("bandwidth", 0) * 8 / 1000000, 2)
        
        ping = round(data.get("ping", {}).get("latency", 0), 2)
        packet_loss = round(data.get("packetLoss", 0), 2)
        result_url = data.get("result", {}).get("url", "")
        
        formatted_text = (
            "<b>Network Speedtest Result</b>\n\n"
            f"<b>Server:</b> {server_name} - {server_location}\n"
            f"<b>ISP:</b> {isp}\n"
            f"<b>Latency:</b> {ping} ms\n"
            f"<b>Download:</b> {dl_mbps} Mbps\n"
            f"<b>Upload:</b> {ul_mbps} Mbps\n"
            f"<b>Packet Loss:</b> {packet_loss}%\n\n"
            f"<a href='{result_url}'>Ookla Result Link</a>"
        )
        
        await response.edit(text=formatted_text, disable_preview=True)
        
    except json.JSONDecodeError:
        await response.edit(f"<b>Raw Output:</b>\n<code>{output}</code>")
    except TimeoutError:
        await response.edit("`Speedtest timed out after 60 seconds.`")
    except Exception as e:
        await response.edit(f"`Error: {e}`")

