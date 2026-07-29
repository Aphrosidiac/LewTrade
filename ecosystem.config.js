module.exports = {
  apps: [{
    name: 'lewtrade-api',
    cwd: '/home/ubuntu/LewTrade/backend',
    script: '/home/ubuntu/.local/bin/uv',
    // --proxy-headers: without it, every request behind nginx looks like it
    // comes from 127.0.0.1, which turns ratelimit.py's per-IP limiter into a
    // site-wide limiter shared by every visitor (including you). Safe to trust
    // here since uvicorn only accepts connections from localhost anyway.
    args: 'run uvicorn lewtrade.app:app --host 127.0.0.1 --port 3108 --app-dir src --workers 1 --proxy-headers',
    interpreter: 'none',
    max_memory_restart: '300M',
  }]
}
