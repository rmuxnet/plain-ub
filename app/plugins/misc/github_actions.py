import re
import os
import aiohttp
from app import BOT, Message

@BOT.add_cmd(cmd=["gha"])
async def gha_cmd(bot: BOT, message: Message):
    """
    CMD: GHA
    INFO: Fetches GitHub Actions workflow status from a run URL.
    USAGE: .gha status <github_run_url>
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 3 or args[1].lower() != "status":
        await message.reply("`Usage: .gha status <github_run_url>`")
        return

    url = args[2].strip()
    
    match = re.search(r"github\.com/([^/]+)/([^/]+)/actions/runs/(\d+)", url)
    if not match:
        await message.reply("`Error: Invalid GitHub Actions run URL.`")
        return

    owner, repo, run_id = match.groups()
    api_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    response = await message.reply("`Querying GitHub API...`")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, headers=headers) as resp:
                if resp.status == 404:
                    await response.edit("`Error: Run not found. If this is a private repo, add GITHUB_TOKEN to your config.env.`")
                    return
                elif resp.status != 200:
                    await response.edit(f"`API Error: HTTP {resp.status}`")
                    return
                
                data = await resp.json()
        except Exception as e:
            await response.edit(f"`Connection failed: {e}`")
            return
          
    workflow_name = data.get("name", "Unknown Workflow")
    status = data.get("status", "unknown").capitalize()
    
    conclusion = data.get("conclusion")
    conclusion_str = conclusion.capitalize() if conclusion else "Running/Pending"
    
    head_branch = data.get("head_branch", "unknown")
    head_sha = data.get("head_sha", "unknown")[:7]
    commit_msg = data.get("head_commit", {}).get("message", "No commit message").split('\n')[0]
    actor = data.get("actor", {}).get("login", "unknown")

    formatted_text = (
        "<b>GitHub Actions Telemetry</b>\n"
        "<pre language=shell>\n"
        f"Repository : {owner}/{repo}\n"
        f"Workflow   : {workflow_name}\n"
        f"Branch     : {head_branch} ({head_sha})\n"
        f"Commit     : {commit_msg}\n"
        f"Triggered  : {actor}\n"
        "----------------------------\n"
        f"Status     : {status}\n"
        f"Conclusion : {conclusion_str}\n"
        "</pre>\n"
        f"<a href='{url}'>View Run on GitHub</a>"
    )

    await response.edit(text=formatted_text, disable_preview=True)
