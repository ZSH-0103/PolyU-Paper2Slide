#!/bin/zsh
cd "${0:A:h}"
if curl -fsS --max-time 2 http://127.0.0.1:8769/api/templates >/dev/null; then
  open http://127.0.0.1:8769/
  exit
fi
(
  for attempt in {1..50}; do
    if curl -fsS --max-time 1 http://127.0.0.1:8769/api/templates >/dev/null 2>&1; then
      open http://127.0.0.1:8769/
      break
    fi
    sleep 0.2
  done
)&
if [[ -x .venv/bin/python ]]; then exec .venv/bin/python server.py; fi
bundled="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
if [[ -x "$bundled" ]]; then exec "$bundled" server.py; fi
exec python3 server.py
