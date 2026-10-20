#!/usr/bin/env bash
set -euo pipefail

SOURCE=""
DEST=""
KEEP=5
DRY_RUN=0

# 1. Парсинг аргументів
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)  SOURCE="$2"; shift 2 ;;
    --dest)    DEST="$2"; shift 2 ;;
    --keep)    KEEP="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help)
      echo "Використання: $0 --source <шлях> --dest <шлях> [--keep <N>] [--dry-run] [--help]"
      exit 0
      ;;
    *) shift ;;
  esac
done

# 2. Перевірка теки-джерела
if [ -z "$SOURCE" ] || [ ! -d "$SOURCE" ] || [ ! -r "$SOURCE" ]; then
  echo "Помилка: Тека-джерело '$SOURCE' не існує або недоступна для читання." >&2
  exit 1
fi

if [ -z "$DEST" ]; then
  echo "Помилка: Не вказано параметр --dest." >&2
  exit 1
fi

# 3. Перевірка та створення теки призначення
if [ ! -d "$DEST" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[DRY-RUN] Створення теки призначення: $DEST"
  else
    mkdir -p "$DEST"
  fi
fi

# Отримуємо абсолютні шляхи
REAL_SOURCE_PATH=$(cd "$SOURCE" && pwd)
SOURCE_NAME=$(basename "$REAL_SOURCE_PATH")
DEST_NAME=$(basename "$DEST")

TIMESTAMP=$(date +"%Y-%m-%d-%H%M%S")
ARCHIVE_NAME="${SOURCE_NAME}-${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="${DEST}/${ARCHIVE_NAME}"

# 4. Створення архіву (виключаємо теку бекапів)
ARCHIVE_SIZE="0B"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "[DRY-RUN] Створення архіву: $ARCHIVE_PATH"
else
  tar --exclude="$DEST_NAME" -czf "$ARCHIVE_PATH" -C "$(dirname "$REAL_SOURCE_PATH")" "$SOURCE_NAME"
  ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
fi

# 5. Ротація архівів
declare -a ARCHIVES=()

if [ -d "$DEST" ]; then
  while IFS= read -r -d '' file; do
    ARCHIVES+=("$file")
  done < <(find "$DEST" -maxdepth 1 -type f -name "${SOURCE_NAME}-*.tar.gz" -print0 | sort -z)
fi

if [ "$DRY_RUN" -eq 1 ]; then
  ARCHIVES+=("$ARCHIVE_PATH")
fi

DELETED_COUNT=0
TOTAL=${#ARCHIVES[@]}

if [ "$TOTAL" -gt "$KEEP" ]; then
  REMOVE_COUNT=$(( TOTAL - KEEP ))
  for (( i=0; i<REMOVE_COUNT; i++ )); do
    FILE_TO_DEL="${ARCHIVES[i]}"
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "[DRY-RUN] Видалення старого архіву: $FILE_TO_DEL"
    else
      rm -f "$FILE_TO_DEL"
    fi
    DELETED_COUNT=$(( DELETED_COUNT + 1 ))
  done
fi

# 6. Вивід результату
echo "Заархівовано: 1"
echo "Видалено: $DELETED_COUNT"
echo "Розмір архіву: $ARCHIVE_SIZE"
