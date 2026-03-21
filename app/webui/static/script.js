// UI Flow
const loginContainer = document.getElementById('login-container');
const dashboard = document.getElementById('dashboard-content');
const loginError = document.getElementById('login-error');

// Auth check
async function checkAuth() {
    try {
        const res = await fetch("/api/plugins/manifest");
        if (res.ok) {
            initDashboard();
        } else {
            loginContainer.classList.remove('hidden');
        }
    } catch {
        loginContainer.classList.remove('hidden');
    }
}

// Login
const loginForm = document.getElementById('totp-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = document.getElementById('totp-code').value;
        const btn = loginForm.querySelector('button');
        const orig = btn.innerText;
        btn.innerText = 'WAIT...';

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });
            if (res.ok) {
                initDashboard();
            } else {
                loginError.classList.remove('hidden');
            }
        } catch {
            loginError.classList.remove('hidden');
        } finally {
            btn.innerText = orig;
        }
    });
}

function initDashboard() {
    loginContainer.classList.add('hidden');
    dashboard.classList.remove('hidden');

    fetchWebUIPlugins();
    initWebSockets();
    fetchSystemInfo();
    fetchBotInfo();
    fetchCorePlugins();

    setInterval(fetchSystemInfo, 3000);
    setInterval(fetchBotInfo, 3000);
}

async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    location.reload();
}

/* --- TELEMETRY CORE --- */
function parseUptime(seconds) {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    let str = "";
    if (d > 0) str += d + "d ";
    if (h > 0) str += h + "h ";
    if (m > 0) str += m + "m ";
    str += s + "s";
    return str || "0s";
}

async function fetchSystemInfo() {
    try {
        const res = await fetch('/api/system/info');
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('sys-cpu').innerText = `${data.cpu}%`;
        document.getElementById('sys-ram').innerText = `${data.ram}%`;
        document.getElementById('sys-disk').innerText = `${data.disk}%`;
    } catch (e) { }
}

async function fetchBotInfo() {
    try {
        const res = await fetch('/api/bot/status');
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('bot-uptime').innerText = parseUptime(data.uptime);
        if (data.ping > 0) document.getElementById('bot-ping').innerText = `${data.ping} ms`;
        document.getElementById('bot-msgs').innerText = data.messages || '0';
    } catch (e) { }
}

async function fetchCorePlugins() {
    try {
        const res = await fetch('/api/bot/plugins');
        if (!res.ok) return;
        const data = await res.json();
        const list = document.getElementById('plugin-list');
        list.innerHTML = "";

        data.plugins.forEach(plug => {
            const name = plug.replace('app.plugins.', '');
            const div = document.createElement('div');
            div.className = "flex justify-between items-center border-b border-border pb-1 mb-1 last:border-0";
            div.innerHTML = `
                <span class="truncate pr-2 w-3/4">${name}</span>
                <div class="flex gap-2 w-1/4 justify-end">
                    <button onclick="managePlugin('${plug}', 'reload')" class="text-dim hover:text-white transition">[R]</button>
                    <button onclick="managePlugin('${plug}', 'unload')" class="text-dim hover:text-red-500 transition">[X]</button>
                </div>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        document.getElementById('plugin-list').innerHTML = '<span class="text-red-900 border-l-2 border-red-900 pl-2">Error.</span>';
    }
}

async function managePlugin(name, action) {
    try {
        const res = await fetch(`/api/bot/plugins/${name}/${action}`, { method: 'POST' });
        if (res.ok) fetchCorePlugins();
    } catch (e) {
        alert(`Failed to execute ${action} on ${name}`);
    }
}

/* --- DYNAMIC WEBUI WIDGETS --- */
async function fetchWebUIPlugins() {
    try {
        const res = await fetch('/api/plugins/manifest');
        if (!res.ok) return;
        const data = await res.json();
        const grid = document.getElementById("dashboard-grid");

        if (data.status === "success" && grid && data.plugins.length > 0) {
            document.getElementById("widgets-header").classList.remove('hidden');
            data.plugins.forEach(plugin => {
                if (plugin.html) {
                    const div = document.createElement("div");
                    div.id = `plugin-ui-${plugin.name}`;
                    div.innerHTML = plugin.html;
                    grid.appendChild(div);
                }
                if (plugin.script) {
                    const script = document.createElement("script");
                    script.textContent = plugin.script;
                    document.body.appendChild(script);
                }
            });
        }
    } catch (e) { }
}

/* --- WEBSOCKETS --- */
function initWebSockets() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/logs`;
    const ws = new WebSocket(wsUrl);
    const logsDiv = document.getElementById("live-bot-logs");

    ws.onmessage = (event) => {
        if (logsDiv) {
            logsDiv.textContent += event.data + "\\n";
            // Buffer limit to prevent DOM memory leaks
            if (logsDiv.textContent.length > 15000) {
                logsDiv.textContent = logsDiv.textContent.slice(-5000);
            }
            // Auto scroll
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }
    };

    ws.onerror = (e) => {
        if (logsDiv) logsDiv.innerHTML += `<span class="text-red-900">\\n[!] Socket Connection Offline...</span>\\n`;
    };

    ws.onclose = () => {
        setTimeout(initWebSockets, 5000);
    };
}

document.addEventListener("DOMContentLoaded", checkAuth);
