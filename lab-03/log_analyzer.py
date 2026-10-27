#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime

# Регулярний вираз для розбору Nginx/Apache Combined Log Format:
# IP - - [Timestamp] "Method Request Protocol" Status Bytes "Referer" "User-Agent"
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<request>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<bytes>\d+|-)'
)


def parse_line(line: str) -> dict | None:
    """
    Розбирає один рядок журналу.
    Повертає словник із полями (ip, timestamp, status, hour) або None, якщо рядок пошкоджений.
    """
    line = line.strip()
    if not line:
        return None

    match = LOG_PATTERN.match(line)
    if not match:
        return None

    data = match.groupdict()

    # Парсинг години з часової мітки (наприклад: 10/Oct/2000:13:55:36 +0200 -> 13)
    try:
        raw_ts = data["timestamp"].split()[0]  # "10/Oct/2000:13:55:36"
        dt = datetime.strptime(raw_ts, "%d/%b/%Y:%H:%M:%S")
        hour_str = dt.strftime("%H:00")
    except (ValueError, IndexError):
        return None

    try:
        status_code = int(data["status"])
    except ValueError:
        return None

    return {
        "ip": data["ip"],
        "status": status_code,
        "hour": hour_str,
    }


def get_status_class(status: int) -> str:
    """Повертає клас HTTP-коду (1xx, 2xx, 3xx, 4xx, 5xx)."""
    first_digit = status // 100
    if 1 <= first_digit <= 5:
        return f"{first_digit}xx"
    return "Other"


def analyze_log(file_path: str, top_n: int) -> dict:
    """Зчитує файл і будує підсумкову статистику."""
    ip_counter = Counter()
    status_classes = Counter({"1xx": 0, "2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "Other": 0})
    hour_counter = Counter()

    total_lines = 0
    corrupted_lines = 0

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            total_lines += 1
            parsed = parse_line(line)
            if parsed is None:
                corrupted_lines += 1
                continue

            ip_counter[parsed["ip"]] += 1
            status_cls = get_status_class(parsed["status"])
            status_classes[status_cls] += 1
            hour_counter[parsed["hour"]] += 1

    # Видаляємо класи з 0 запитів для охайності
    status_classes_filtered = {k: v for k, v in status_classes.items() if v > 0}

    return {
        "total_lines": total_lines,
        "corrupted_lines": corrupted_lines,
        "valid_lines": total_lines - corrupted_lines,
        "top_ips": dict(ip_counter.most_common(top_n)),
        "status_distribution": status_classes_filtered,
        "peak_hours": dict(hour_counter.most_common(top_n)),
    }


def format_text_report(stats: dict, top_n: int) -> str:
    """Форматує результат у людиночитаний текстовий звіт."""
    lines = [
        "=== ЗВІТ АНАЛІЗУ ВЕБ-ЖУРНАЛУ ===",
        f"Оброблено рядків:  {stats['total_lines']}",
        f"Успішно розібрано: {stats['valid_lines']}",
        f"Пошкоджених:       {stats['corrupted_lines']}",
        "",
        f"--- ТОП-{top_n} IP-адрес за кількістю запитів ---",
    ]
    for ip, count in stats["top_ips"].items():
        lines.append(f"  {ip:<16} : {count} запитів")

    lines.append("\n--- Розподіл кодів відповідей за класами ---")
    for st_cls, count in stats["status_distribution"].items():
        lines.append(f"  {st_cls:<5} : {count}")

    lines.append(f"\n--- ТОП-{top_n} годин пікового навантаження ---")
    for hour, count in stats["peak_hours"].items():
        lines.append(f"  {hour:<5} : {count} запитів")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Аналізатор веб-журналів (Combined Log Format)")
    parser.add_argument("--log", "-l", required=True, help="Шлях до вхідного лог-файлу")
    parser.add_argument("--output", "-o", help="Шлях до файлу результату (за замовчуванням: stdout)")
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Формат виводу: text або json (типово: text)",
    )
    parser.add_argument(
        "--top", "-t", type=int, default=5, help="Кількість позицій у топі (типово: 5)"
    )

    args = parser.parse_args()

    try:
        stats = analyze_log(args.log, args.top)
    except FileNotFoundError:
        print(f"Помилка: Файл '{args.log}' не знайдено.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Критична помилка при читанні файлу: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        output_content = json.dumps(stats, ensure_ascii=False, indent=2)
    else:
        output_content = format_text_report(stats, args.top)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_content + "\n")
        print(f"Звіт успішно збережено у файл: {args.output}")
    else:
        print(output_content)


if __name__ == "__main__":
    main()
