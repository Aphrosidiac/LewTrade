module.exports = {
  apps: [{
    name: 'lewtrade-api',
    cwd: '/home/ubuntu/LewTrade/backend',
    script: '/home/ubuntu/.local/bin/uv',
    args: 'run uvicorn lewtrade.app:app --host 127.0.0.1 --port 3108 --app-dir src --workers 1',
    interpreter: 'none',
    max_memory_restart: '300M',
  }]
}
