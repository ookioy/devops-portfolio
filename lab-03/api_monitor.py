#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime
import requests
from requests.exceptions import SSLError, Timeout, ConnectionError, RequestException

CONFIG_FILE = "config/config.json"
RESULTS_FILE = "results.json"
WEBHOOK_URL = "https://discord.com/api/webhooks/1562124872258420847/XoLYVPD_s4cuvm0Q5SczKuS_2hWRz2Z_cokKl8eNemInwx01lnd-LInq2iy08_4pGO-b"


def classify_connection_error(error: Exception) -> str:
    """Визначає конкретний тип мережевої помилки (DNS чи Connection Refused)."""
    err_str = str(error).lower()

    dns_keywords = [
        "nameresolutionerror", "getaddrinfo failed",
        "name or service not known", "nodename nor servname provided",
        "failed to resolve"
    ]
    refused_keywords = [
        "connection refused", "errno 111", "winerror 10061", "refused"
    ]

    for kw in dns_keywords:
        if kw in err_str:
            return "DNS"

    for kw in refused_keywords:
        if kw in err_str:
            return "З'єднання відхилено"

    return "Збій з'єднання"


def check_target(target: dict) -> dict:
    """
    Перевіряє ціль з виконаннням однієї повторної спроби при мережевій помилці.
    """
    url = target["url"]
    expected_status = target.get("expected_status", 200)
    timeout = target.get("timeout", 5)
    threshold = target.get("response_time_threshold", 2.0)

    max_attempts = 2  # 1 основна + 1 повторна спроба при збої

    for attempt in range(1, max_attempts + 1):
        start_time = time.time()
        try:
            response = requests.get(url, timeout=timeout, verify=True)
            elapsed = time.time() - start_time

            # 1. Перевірка коду відповіді
            if response.status_code != expected_status:
                return {
                    "url": url,
                    "status": "FAILED",
                    "failure_type": "Несподіваний код",
                    "details": f"Отримано status {response.status_code}, очікувався {expected_status}",
                    "response_time": round(elapsed, 3)
                }

            # 2. Перевірка порогу часу відповіді
            if elapsed > threshold:
                return {
                    "url": url,
                    "status": "FAILED",
                    "failure_type": "Повільна відповідь",
                    "details": f"Час відповіді {elapsed:.3f}s перевищив поріг {threshold}s",
                    "response_time": round(elapsed, 3)
                }

            # Успішна перевірка
            return {
                "url": url,
                "status": "SUCCESS",
                "failure_type": None,
                "details": "OK",
                "response_time": round(elapsed, 3)
            }

        except SSLError as e:
            elapsed = time.time() - start_time
            # Помилка SSL не потребує повторної спроби (сертифікат не виправиться за секунду)
            return {
                "url": url,
                "status": "FAILED",
                "failure_type": "Помилка сертифіката",
                "details": "Невалідний або прострочений SSL/TLS сертифікат",
                "response_time": round(elapsed, 3)
            }

        except Timeout:
            elapsed = time.time() - start_time
            if attempt < max_attempts:
                time.sleep(1)
                continue
            return {
                "url": url,
                "status": "FAILED",
                "failure_type": "Тайм-аут",
                "details": f"Сервер не відповів протягом {timeout} секунд",
                "response_time": round(elapsed, 3)
            }

        except ConnectionError as e:
            elapsed = time.time() - start_time
            failure_type = classify_connection_error(e)
            if attempt < max_attempts:
                time.sleep(1)
                continue
            return {
                "url": url,
                "status": "FAILED",
                "failure_type": failure_type,
                "details": str(e),
                "response_time": round(elapsed, 3)
            }

        except RequestException as e:
            elapsed = time.time() - start_time
            if attempt < max_attempts:
                time.sleep(1)
                continue
            return {
                "url": url,
                "status": "FAILED",
                "failure_type": "Невідома помилка",
                "details": str(e),
                "response_time": round(elapsed, 3)
            }


def send_webhook_notification(failed_targets: list):
    """Надсилає сповіщення у вебхук (Slack / Discord / Telegram)."""
    if not WEBHOOK_URL:
        print("[INFO] Змінна WEBHOOK_URL не встановлена. Сповіщення пропущено.")
        return

    lines = ["🚨 **Звіт про проблеми доступності API**\n"]
    for item in failed_targets:
        lines.append(
            f"• **Ціль**: `{item['url']}`\n"
            f"  **Тип збою**: `{item['failure_type']}`\n"
            f"  **Деталі**: {item['details']}\n"
            f"  **Час відповіді**: {item['response_time']}s\n"
        )

    text_payload = "\n".join(lines)
    # Формат підходить для Discord та Slack
    payload = {
        "content": text_payload,
        "text": text_payload
    }

    try:
        res = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if res.status_code in (200, 204):
            print("[INFO] Сповіщення успішно надіслано у месенджер.")
        else:
            print(f"[WARN] Вебхук повернув код {res.status_code}")
    except Exception as e:
        print(f"[ERROR] Не вдалося надіслати сповіщення: {e}")


def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"[ERROR] Файл конфігурації '{CONFIG_FILE}' не знайдено.")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        targets = json.load(f)

    print(f"--- Запуск перевірки API ({len(targets)} цілей) ---")

    results = []
    failed_targets = []
    timestamp = datetime.utcnow().isoformat() + "Z"

    for target in targets:
        res = check_target(target)
        res_record = {
            "timestamp": timestamp,
            "name": target.get("name"),
            **res
        }
        results.append(res_record)

        status_symbol = "✅" if res["status"] == "SUCCESS" else "❌"
        fail_info = f" [{res['failure_type']}]" if res['failure_type'] else ""
        print(f"{status_symbol} {target['url']} — {res['status']}{fail_info} ({res['response_time']}s)")

        if res["status"] == "FAILED":
            failed_targets.append(res_record)

    # Збереження результатів у структурований файл
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] Результати збережено у '{RESULTS_FILE}'")

    # Відправка сповіщень
    if failed_targets:
        send_webhook_notification(failed_targets)
        print(f"\n[RESULT] Виявлено проблем: {len(failed_targets)}. Завершення з кодом 1.")
        sys.exit(1)
    else:
        print("\n[RESULT] Усі цілі працюють штатно. Завершення з кодом 0.")
        sys.exit(0)


if __name__ == "__main__":
    main()
