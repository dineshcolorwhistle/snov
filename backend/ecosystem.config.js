module.exports = {
  apps: [
    {
      name: "snov-backend",
      script: "./.venv/bin/uvicorn",
      args: "main:app --host 127.0.0.1 --port 8090",
      cwd: "/home/agentwhistle-snov-automation/htdocs/snov-automation.agentwhistle.com/snov/backend",
      watch: false,
      interpreter: "none",
      env: {
        PORT: 8090
      }
    }
  ]
};
