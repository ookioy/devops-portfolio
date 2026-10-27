#!/usr/bin/env bash
set -euo pipefail

echo "[Pre-push] Запуск тестів перед git push..."

EXIT_CODE=0

if command -v pytest &> /dev/null; then
  pytest || EXIT_CODE=1
elif command -v python3 &> /dev/null; then
  python3 -m unittest discover -s . -p "*test*.py" || EXIT_CODE=1
else
  echo "[Pre-push WARN] Інструмент для запуску тестів не знайдено."
  exit 0
fi

if [ $EXIT_CODE -ne 0 ]; then
  echo "[Pre-push ERROR] Тести не пройшли! Відправку (git push) скасовано."
  exit 1
fi

echo "[Pre-push SUCCESS] Усі тести пройдено."
exit 0
