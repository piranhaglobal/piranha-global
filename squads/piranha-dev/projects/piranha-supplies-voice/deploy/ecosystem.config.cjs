// PM2 ecosystem — Piranha Supplies Voice
// Usar: pm2 start deploy/ecosystem.config.cjs
// Logs: pm2 logs piranha-voice
module.exports = {
  apps: [
    {
      name: "piranha-voice",
      script: "venv/bin/gunicorn",
      args: [
        "--workers", "2",
        "--bind", "127.0.0.1:5000",
        "--timeout", "30",
        "--access-logfile", "/var/log/piranha-voice/access.log",
        "--error-logfile", "/var/log/piranha-voice/error.log",
        "src.handlers.webhook_handler:create_app()",
      ],
      cwd: "/opt/piranha-supplies-voice",
      interpreter: "none",
      env: {
        PYTHONPATH: "/opt/piranha-supplies-voice",
      },
      watch: false,
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 10,
    },
  ],
};
