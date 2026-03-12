import asyncio
import os
import time

import aiohttp
import requests

from app import BOT, Message

QBIT_URL  = os.environ.get("QBIT_URL",  "http://127.0.0.1:8080")
QBIT_USER = os.environ.get("QBIT_USER", "admin")
QBIT_PASS = os.environ.get("QBIT_PASS", "")

BANNED_TRACKERS = ["limetorrent"]



def _auth_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Referer": f"{QBIT_URL}/", "Origin": QBIT_URL})
    auth = session.post(
        f"{QBIT_URL}/api/v2/auth/login",
        data={"username": QBIT_USER, "password": QBIT_PASS},
    )
    if auth.text != "Ok.":
        raise Exception("Authentication rejected by daemon.")
    return session


def _execute_search(query: str) -> list:
    session = _auth_session()
    start = session.post(
        f"{QBIT_URL}/api/v2/search/start",
        data={"pattern": query, "plugins": "enabled", "category": "all"},
    )
    if start.status_code != 200:
        raise Exception(f"Search start failed. HTTP {start.status_code}")

    search_id = start.json().get("id")
    time.sleep(5)

    res = session.get(
        f"{QBIT_URL}/api/v2/search/results",
        params={"id": search_id, "limit": 500, "offset": 0},
    )
    results = res.json().get("results", []) if res.status_code == 200 else []

    session.post(f"{QBIT_URL}/api/v2/search/stop",   data={"id": search_id})
    session.post(f"{QBIT_URL}/api/v2/search/delete", data={"id": search_id})

    results.sort(key=lambda x: x.get("nbSeeders", 0), reverse=True)
    return results


def _upload_ghostbin(text: str) -> str:
    files = {"f": ("results.txt", text.encode("utf-8"), "text/plain")}
    res = requests.post("https://gbin.me", files=files, timeout=15)
    if res.status_code not in [200, 201]:
        raise RuntimeError(f"HTTP {res.status_code}: {res.text[:200]}")
    return res.url if res.url != "https://gbin.me/" else res.text.strip()



@BOT.add_cmd(cmd="qsadd")
async def qbit_search_plugin_add(bot: BOT, message: Message):
    """
    CMD: QSADD
    INFO: Installs a qBittorrent search plugin from a URL and updates all engines.
    USAGE: .qsadd <url>
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "`Usage: .qsadd <url>`\n"
            "`Example: .qsadd https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/1337x.py`"
        )
        return

    plugin_url = args[1].strip()
    response = await message.reply("`Installing search plugin...`")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{QBIT_URL}/api/v2/search/installPlugin",
                data={"sources": plugin_url},
            ) as req:
                if req.status != 200:
                    await response.edit(f"`Installation failed. API Error {req.status}`")
                    return

            await response.edit("`Plugin injected. Triggering engine update...`")

            async with session.post(f"{QBIT_URL}/api/v2/search/updatePlugins") as req:
                if req.status == 200:
                    await response.edit("`Plugin installed and search engines updated.`")
                else:
                    await response.edit(f"`Plugin installed, but update failed. API Error {req.status}`")

        except Exception as e:
            await response.edit(f"`API connection failed: {e}`")


@BOT.add_cmd(cmd="qsearch")
async def qbit_search_cmd(bot: BOT, message: Message):
    """
    CMD: QSEARCH
    INFO: Search qBittorrent for torrents. Results posted to Ghostbin.
    USAGE: .qsearch <query>
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("`Usage: .qsearch <query>`")
        return

    query = args[1].strip()
    response = await message.reply(f"`Searching '{query}'...`")

    try:
        results = await asyncio.to_thread(_execute_search, query)
        if not results:
            await response.edit("`No results found.`")
            return

        text = f"qBittorrent Search: '{query}'\n{'=' * 60}\n\n"
        valid = 0

        for r in results:
            name = r.get("fileName", "Unknown")
            site = r.get("siteUrl", "Unknown")

            if "api key error" in name.lower() or any(b in site.lower() for b in BANNED_TRACKERS):
                continue

            size_mb = round(r.get("fileSize", 0) / (1024 * 1024), 2)
            seeds   = r.get("nbSeeders",  0)
            leechs  = r.get("nbLeechers", 0)
            magnet  = r.get("fileUrl", "")

            valid += 1
            text += (
                f"[{valid}] {name}\n"
                f"Size: {size_mb} MB | Seeders: {seeds} | Leechers: {leechs} | Tracker: {site}\n"
                f"Magnet:\n{magnet}\n"
                f"{'-' * 60}\n\n"
            )

        if valid == 0:
            await response.edit("`No valid torrents found after filtering.`")
            return

        if len(text) > 400_000:
            await response.edit("`Result too large. Try a more specific query.`")
            return

        await response.edit("`Uploading results...`")
        paste_url = await asyncio.to_thread(_upload_ghostbin, text)

        await response.edit(
            f"<b>qBittorrent Search:</b> <code>{query}</code>\n"
            f"└ <b>Found:</b> {valid} torrents (sorted by seeders)\n"
            f"└ <b>Results:</b> <a href='{paste_url}'>View on Ghostbin</a>",
            disable_web_page_preview=True,
        )

    except Exception as e:
        await response.edit(f"`Search failed: {e}`")



