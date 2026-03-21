import asyncio
import logging
import sys

import psutil
from pycloudflared import try_cloudflare

from app import BOT, Message, bot
from app.webui.server import webui_manager
from app.webui.config import WebUIConfig
from app.webui.security import get_or_create_totp_secret

LOGGER = logging.getLogger(__name__)

_active_tunnel = None


def terminate_tunnel():
    global _active_tunnel
    try:
        if _active_tunnel:
            _active_tunnel = None
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] and "cloudflared" in proc.info["name"].lower():
                proc.kill()
        LOGGER.info("Cloudflared tunnel terminated.")
    except Exception as e:
        LOGGER.error(f"Error terminating cloudflare tunnel: {e}")


@bot.add_cmd(cmd="webui")
async def start_webui(bot: BOT, message: Message):
    """
    CMD: WEBUI
    INFO: Start the local WebUI server and establish a secure Cloudflare tunnel.
    USAGE: .webui
    """
    global _active_tunnel

    msg = (
        await message.reply("Initializing WebUI Server...", quote=True)
        if message.reply_to_message else
        await message.edit("Initializing WebUI Server...")
    )

    try:
        secret, uri, is_new = get_or_create_totp_secret()
        if is_new:
            try:
                await bot.send_message(
                    "me",
                    "<b>WebUI TOTP Security Initialization</b>\n\n"
                    f"<b>Secret Key:</b> <code>{secret}</code>\n\n"
                    "Please add this to your authenticator app (Google Authenticator, Authy). You will need it to log in.\n\n"
                    f"<b>Provisioning URI:</b>\n<code>{uri}</code>"
                )
            except Exception as e:
                LOGGER.error(f"Failed to transmit TOTP to Saved Messages: {e}")

        await webui_manager.start()
        await msg.edit("Server active. Negotiating Cloudflare Tunnel...")
        
        if _active_tunnel is None:
            _active_tunnel = await asyncio.to_thread(try_cloudflare, port=WebUIConfig.PORT)
            
        tunnel_url = _active_tunnel.tunnel
        
        text = (
            "<b>WebUI Dashboard Online</b>\n\n"
            f"<b>URL:</b> <code>{tunnel_url}</code>\n\n"
            "<i>Note: Authentication is strictly required (TOTP/WebUI_Plugins Active).</i>"
        )
        await msg.edit(text)

    except Exception as e:
        LOGGER.error(f"Failed to start WebUI: {e}", exc_info=True)
        await msg.edit(f"<b>Error initializing WebUI:</b> <code>{e}</code>")
