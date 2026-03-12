import os
import platform
import shutil
import time

from app import BOT, Message
from ub_core.utils import run_shell_cmd


def _read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return ""


def _parse_meminfo() -> dict:
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                key, val = line.split(":", 1)
                info[key.strip()] = int(val.strip().split()[0])
    except Exception:
        pass
    return info


def _cpu_freq() -> str:
    try:
        freqs = []
        base = "/sys/devices/system/cpu"
        for cpu in sorted(os.listdir(base)):
            freq_path = f"{base}/{cpu}/cpufreq/scaling_cur_freq"
            if os.path.isfile(freq_path):
                freqs.append(int(_read_file(freq_path)))
        if freqs:
            avg = sum(freqs) / len(freqs)
            return f"{avg / 1e6:.2f} GHz"
    except Exception:
        pass
    try:
        with open("/proc/cpuinfo") as f:
            mhz_vals = [
                float(line.split(":")[1].strip())
                for line in f
                if line.startswith("cpu MHz")
            ]
        if mhz_vals:
            return f"{sum(mhz_vals) / len(mhz_vals) / 1000:.2f} GHz"
    except Exception:
        pass
    return "N/A"


def _cpu_temp() -> str:
    try:
        base = "/sys/class/thermal"
        for zone in sorted(os.listdir(base)):
            if not zone.startswith("thermal_zone"):
                continue
            ttype = _read_file(f"{base}/{zone}/type").lower()
            if any(k in ttype for k in ("cpu", "soc", "pkg", "x86", "acpi", "ps4")):
                temp = int(_read_file(f"{base}/{zone}/temp"))
                return f"{temp / 1000:.1f} °C"
        zone0 = f"{base}/thermal_zone0/temp"
        if os.path.isfile(zone0):
            return f"{int(_read_file(zone0)) / 1000:.1f} °C"
    except Exception:
        pass
    return "N/A"


def _load_avg() -> str:
    try:
        vals = _read_file("/proc/loadavg").split()[:3]
        return " / ".join(vals)
    except Exception:
        return "N/A"


def _net_stats() -> str:
    try:
        results = []
        with open("/proc/net/dev") as f:
            lines = f.readlines()[2:]
        for line in lines:
            parts = line.split()
            iface = parts[0].rstrip(":")
            if iface == "lo":
                continue
            rx = int(parts[1])
            tx = int(parts[9])
            def fmt(b):
                for unit in ("B", "KB", "MB", "GB", "TB"):
                    if b < 1024:
                        return f"{b:.1f} {unit}"
                    b /= 1024
                return f"{b:.1f} PB"
            results.append(f"{iface}: ↓{fmt(rx)} ↑{fmt(tx)}")
        return "  |  ".join(results) if results else "N/A"
    except Exception:
        return "N/A"


def _swap_info(mem: dict) -> str:
    total = mem.get("SwapTotal", 0)
    free = mem.get("SwapFree", 0)
    if total == 0:
        return "None"
    used = total - free
    pct = int(used / total * 100) if total else 0
    return f"{used / 1024**2:.2f} GiB / {total / 1024**2:.2f} GiB ({pct}%)"


def _uptime_str() -> str:
    try:
        secs = float(_read_file("/proc/uptime").split()[0])
        d, rem = divmod(int(secs), 86400)
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        parts = []
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        parts.append(f"{s}s")
        return " ".join(parts)
    except Exception:
        return "N/A"


@BOT.add_cmd(cmd=["specs", "server"])
async def server_specs_cmd(bot: BOT, message: Message):
    """
    CMD: SPECS | SERVER
    INFO: Displays host server hardware and OS specifications.
    USAGE: .specs | .server
    """
    response = await message.reply("`Pulling hardware telemetry...`")

    try:
        os_name = "Unknown"
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    os_name = line.split("=", 1)[1].strip().strip('"')
                    break

        kernel    = platform.release()
        arch      = platform.machine()
        hostname  = platform.node()
        uptime    = _uptime_str()
        load      = _load_avg()

        cpu_name = "Unknown"
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    cpu_name = line.split(":", 1)[1].strip()
                    break
        cores     = os.cpu_count()
        cpu_freq  = _cpu_freq()
        cpu_temp  = _cpu_temp()

        mem = _parse_meminfo()
        mem_total = mem.get("MemTotal", 0)
        mem_avail = mem.get("MemAvailable", 0)
        mem_used  = mem_total - mem_avail
        mem_pct   = int(mem_used / mem_total * 100) if mem_total else 0
        mem_str   = f"{mem_used / 1024**2:.2f} GiB / {mem_total / 1024**2:.2f} GiB ({mem_pct}%)"
        swap_str  = _swap_info(mem)

        total, used, free = shutil.disk_usage("/")
        disk_str  = f"{used / 1024**3:.2f} GiB / {total / 1024**3:.2f} GiB ({int(used/total*100)}%)"

        net_str   = _net_stats()

        text = (
            "<b>Server Telemetry</b>\n"
            "<pre language=shell>\n"
            f"Host     : {hostname}\n"
            f"OS       : {os_name}\n"
            f"Kernel   : {kernel} ({arch})\n"
            f"Uptime   : {uptime}\n"
            f"Load     : {load} (1/5/15 min)\n"
            "────────────────────────\n"
            f"CPU      : {cpu_name}\n"
            f"Cores    : {cores}\n"
            f"Freq     : {cpu_freq}\n"
            f"Temp     : {cpu_temp}\n"
            "────────────────────────\n"
            f"RAM      : {mem_str}\n"
            f"Swap     : {swap_str}\n"
            f"Disk     : {disk_str}\n"
            "────────────────────────\n"
            f"Network  : {net_str}\n"
            "</pre>"
        )

        await response.edit(text=text)

    except Exception as e:
        await response.edit(f"`Hardware read failed: {e}`")
