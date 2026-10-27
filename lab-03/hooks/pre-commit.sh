#!/usr/bin/env bash
set -euo pipefail

# Отримуємо список лише доданих/змінених файлів у staged (ігноруємо видалені)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=d)

if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

EXIT_CODE=0

# 1. Перевірка bash-скриптів (.sh)
STAGED_SH=$(echo "$STAGED_FILES" | grep -E '\.sh$' || true)

if [ -n "$STAGED_SH" ]; then
  if command -v shellcheck &> /dev/null; then
    echo "[Pre-commit] Перевірка Shell-скриптів за допомогою shellcheck..."
    for file in $STAGED_SH; do
      if [ -f "$file" ]; then
        shellcheck "$file" || EXIT_CODE=1
      fi
    done
  else
    echo "[Pre-commit WARN] shellcheck не встановлено. Перевірку .sh файлів пропущено."
  fi
fi

# 2. Перевірка Python-файлів (.py)
STAGED_PY=$(echo "$STAGED_FILES" | grep -E '\.py$' || true)

if [ -n "$STAGED_PY" ]; then
  LINTER=""
  if command -v flake8 &> /dev/null; then
    LINTER="flake8"
  elif command -v ruff &> /dev/null; then
    LINTER="ruff check"
  fi

  if [ -n "$LINTER" ]; then
    echo "[Pre-commit] Перевірка Python-файлів за допомогою $LINTER..."
    for file in $STAGED_PY; do
      if [ -f "$file" ]; then
        $LINTER "$file" || EXIT_CODE=1
      fi
    done
  else
    echo "[Pre-commit WARN] Лінтер Python (flake8/ruff) не знайдено. Перевірку .py файлів пропущено."
  fi
fi

# Результат
if [ $EXIT_CODE -ne 0 ]; then
  echo "[Pre-commit ERROR] Лінтер виявив помилки у staged-файлах. Коміт скасовано!"
  exit 1
fi

echo "[Pre-commit SUCCESS] Усі staged-файли успішно пройшли перевірку."
exit 0
