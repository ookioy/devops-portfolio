#!/usr/bin/env bash
set -euo pipefail

# Завантажуємо конфігураційний файл, якщо він існує
CONFIG_FILE="${CONFIG_FILE:-config/monitor.env}"
if [ -f "$CONFIG_FILE" ]; then
  # Read variables from env file
  set -a
  source "$CONFIG_FILE"
  set +a
fi

# Значення за замовчуванням (якщо змінні не задані ні в env, ні в файлі)
CPU_THRESHOLD="${CPU_THRESHOLD:-80}"
MEM_THRESHOLD="${MEM_THRESHOLD:-80}"
DISK_THRESHOLD="${DISK_THRESHOLD:-80}"
CHECK_SERVICES="${CHECK_SERVICES:-cron ssh}"
LOG_FILE="${LOG_FILE:-monitor.log}"

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
HAS_ERROR=0

log() {
  local level="$1"
  local message="$2"
  local entry="[$TIMESTAMP] [$level] $message"

  echo "$entry"
  if [ -n "$LOG_FILE" ]; then
    echo "$entry" >> "$LOG_FILE"
  fi
}

# 1. Перевірка CPU
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | awk '{for(i=1;i<=NF;i++) if($i ~ /id/) print $(i-1)}' | cut -d. -f1 | head -n1)
if [ -n "$CPU_IDLE" ]; then
  CPU_USAGE=$(( 100 - CPU_IDLE ))
else
  # Запасний варіант обчислення через ps
  CPU_USAGE=$(ps -eo %cpu | awk 'NR>1 {s+=$1} END {print int(s)}')
fi

if [ "$CPU_USAGE" -gt "$CPU_THRESHOLD" ]; then
  log "ERROR" "CPU usage high: ${CPU_USAGE}% (Threshold: ${CPU_THRESHOLD}%)"
  HAS_ERROR=1
else
  log "INFO" "CPU usage OK: ${CPU_USAGE}% (Threshold: ${CPU_THRESHOLD}%)"
fi

# 2. Перевірка RAM
MEM_USAGE=$(free -m | awk '/Mem:/ { printf("%d", $3/$2*100) }')
if [ "$MEM_USAGE" -gt "$MEM_THRESHOLD" ]; then
  log "ERROR" "Memory usage high: ${MEM_USAGE}% (Threshold: ${MEM_THRESHOLD}%)"
  HAS_ERROR=1
else
  log "INFO" "Memory usage OK: ${MEM_USAGE}% (Threshold: ${MEM_THRESHOLD}%)"
fi

# 3. Перевірка диска (кореневий розділ /)
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
  log "ERROR" "Disk usage high: ${DISK_USAGE}% (Threshold: ${DISK_THRESHOLD}%)"
  HAS_ERROR=1
else
  log "INFO" "Disk usage OK: ${DISK_USAGE}% (Threshold: ${DISK_THRESHOLD}%)"
fi

# 4. Перевірка сервісів та процесів
for service in $CHECK_SERVICES; do
  if systemctl is-active --quiet "$service" 2>/dev/null || pgrep -x "$service" >/dev/null 2>&1; then
    log "INFO" "Service/Process '$service' is RUNNING"
  else
    log "ERROR" "Service/Process '$service' is NOT RUNNING"
    HAS_ERROR=1
  fi
done

# Ненульовий код виходу при наявності проблем
if [ "$HAS_ERROR" -eq 1 ]; then
  exit 1
fi

exit 0
