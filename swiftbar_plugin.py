#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# <swiftbar.title>Google AI Pro Limits</swiftbar.title>
# <swiftbar.author>Antigravity Agent</swiftbar.author>
# <swiftbar.author.github>antigravity-ide</swiftbar.author.github>
# <swiftbar.desc>Показывает оставшиеся лимиты для аккаунтов Google AI Pro в Antigravity.</swiftbar.desc>
# <swiftbar.version>1.3</swiftbar.version>

import os
import sys
import json
import time
import re

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
QUOTAS_PATH = os.path.join(PROJECT_DIR, "quotas.json")
ACCOUNTS_PATH = os.path.join(PROJECT_DIR, "accounts.json")
FETCHER_PATH = os.path.join(PROJECT_DIR, "fetcher.py")
AUTH_PATH = os.path.join(PROJECT_DIR, "auth.py")
SWITCH_PATH = os.path.join(PROJECT_DIR, "switch_account.py")

# Находим подходящий интерпретатор Python, в котором установлена библиотека requests
python_bin = "python3"
for candidate in [
    os.path.join(PROJECT_DIR, ".venv", "bin", "python3"),
    os.path.join(PROJECT_DIR, "venv", "bin", "python3"),
    "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
    "/opt/homebrew/bin/python3",
    "/usr/local/bin/python3",
]:
    if os.path.exists(candidate):
        python_bin = candidate
        break

def make_progress_bar(percent):
    # Делаем прогресс-бар шире (25 символов) и толще, используя полные блоки █ и штриховку ░
    filled = min(25, max(0, int(round(percent * 25 / 100))))
    empty = 25 - filled
    bar = "█" * filled + "░" * empty
    
    # Цветовое кодирование в зависимости от доступного лимита (Available)
    if percent < 15:
        color = "#FF453A" # Apple System Red
    elif percent < 40:
        color = "#FFD60A" # Apple System Yellow
    else:
        color = "#30D158" # Apple System Green
        
    return f"{bar} {percent}%", color

def make_average_progress_bar(percent):
    # Широкий и толстый прогресс-бар для общего баланса (█ и ░), но с фиолетовым цветом
    filled = min(25, max(0, int(round(percent * 25 / 100))))
    empty = 25 - filled
    bar = "█" * filled + "░" * empty
    
    if percent < 15:
        color = "#FF453A" # Apple System Red
    elif percent < 40:
        color = "#FFD60A" # Apple System Yellow
    else:
        color = "#BF5AF2" # Apple System Purple (фирменный цвет AI/сводки)
        
    return f"{bar} {percent}%", color

def format_time_remaining(description):
    if not description:
        return ""
    # Ищем фразу "refresh in " или "refresh in..."
    match = re.search(r"refresh in (.+)\.?", description)
    if match:
        time_str = match.group(1).rstrip('.')
        time_str = time_str.replace(",", "") # Убираем запятые
        # Заменяем английские слова на короткие русские обозначения
        time_str = time_str.replace("days", "дн.").replace("day", "дн.")
        time_str = time_str.replace("hours", "ч.").replace("hour", "ч.")
        time_str = time_str.replace("minutes", "мин.").replace("minute", "мин.")
        time_str = time_str.replace("seconds", "сек.").replace("second", "сек.")
        return f"Сброс через: {time_str}"
    return ""

def get_active_ide_email():
    db_path = os.path.expanduser("~/Library/Application Support/Antigravity IDE/User/globalStorage/state.vscdb")
    if not os.path.exists(db_path):
        return None
    try:
        import sqlite3
        import base64
        import re
        import json
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.oauthToken'")
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        val = row[0]
        try:
            decoded = base64.b64decode(val)
        except Exception:
            decoded = val
        text = decoded.decode('utf-8', errors='ignore')
        
        # Сначала извлекаем refresh_token из сессии
        candidates = re.findall(r"[a-zA-Z0-9+/=_-]{80,}", text)
        active_refresh_token = None
        for cand in candidates:
            cand_norm = cand.replace('-', '+').replace('_', '/')
            cand_norm += "=" * ((4 - len(cand_norm) % 4) % 4)
            try:
                dec_cand = base64.b64decode(cand_norm)
                idx = dec_cand.find(b"1//")
                if idx != -1:
                    token_part = dec_cand[idx:]
                    clean_token = bytearray()
                    for b in token_part:
                        if 32 <= b <= 126:
                            clean_token.append(b)
                        else:
                            break
                    raw_token = clean_token.decode('utf-8')
                    active_refresh_token = re.sub(r'[^a-zA-Z0-9_/\.-]', '', raw_token).rstrip('.')
                    break
            except Exception:
                pass
                
        if active_refresh_token and os.path.exists(ACCOUNTS_PATH):
            with open(ACCOUNTS_PATH, "r", encoding="utf-8") as f:
                accounts = json.load(f)
            for acc in accounts:
                if acc.get("refresh_token") == active_refresh_token:
                    return acc.get("email")
                    
        # Резервный вариант, если токен не распарсился
        match = re.search(r'"email":"([^"]+)"', text)
        if match:
            return match.group(1)
        match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def sort_key(account):
    email = account.get("email", "").lower()
    if "@" in email:
        user, domain = email.split("@", 1)
    else:
        user, domain = email, ""
    
    # Разделяем имя пользователя на текстовую часть и число
    match = re.match(r"([a-zA-Z_.-]+)(\d*)", user)
    if match:
        text_part = match.group(1)
        num_part = match.group(2)
        num = int(num_part) if num_part else 0
        return (text_part, num, domain)
    return (email, 0, "")

def main():
    # 1. Проверяем наличие конфигурации
    if not os.path.exists(ACCOUNTS_PATH):
        print(" | sfimage=speedometer")
        print("---")
        print("Аккаунты не настроены | sfimage=person.badge.plus size=12 style=bold")
        print(f"Запустить авторизацию... | bash={python_bin} param1={AUTH_PATH} terminal=true sfimage=arrow.up.right")
        return

    # Читаем аккаунты
    try:
        with open(ACCOUNTS_PATH, "r", encoding="utf-8") as f:
            accounts = json.load(f)
    except Exception as e:
        print(" | sfimage=speedometer sfcolor=#FF453A")
        print("---")
        print(f"Ошибка чтения accounts.json: {e} | sfimage=xmark.octagon sfcolor=#FF453A")
        return

    if not accounts:
        print(" | sfimage=speedometer")
        print("---")
        print("Список аккаунтов пуст | sfimage=person.crop.circle.badge.questionmark size=12 style=bold")
        print(f"Добавить аккаунт... | bash={python_bin} param1={AUTH_PATH} terminal=true sfimage=arrow.up.right")
        return

    # 2. Читаем кэш квот
    quotas_data = None
    cache_age = 999999
    
    if os.path.exists(QUOTAS_PATH):
        try:
            cache_age = time.time() - os.path.getmtime(QUOTAS_PATH)
            with open(QUOTAS_PATH, "r", encoding="utf-8") as f:
                quotas_data = json.load(f)
        except Exception:
            pass

    # Если кэша нет или он устарел (более 3 минут), запускаем fetcher в фоне.
    if cache_age > 180: # 3 минуты
        os.system(f"'{python_bin}' '{FETCHER_PATH}' > /dev/null 2>&1 &")

    # Если данных в кэше нет совсем, показываем загрузку
    if not quotas_data:
        print(" | sfimage=speedometer sfcolor=gray")
        print("---")
        print("Получение данных о лимитах... | sfimage=arrow.clockwise.circle")
        print(f"Обновить вручную | bash={python_bin} param1={FETCHER_PATH} terminal=false refresh=true sfimage=arrow.clockwise")
        print(f"Авторизовать еще аккаунт | bash={python_bin} param1={AUTH_PATH} terminal=true sfimage=person.badge.plus")
        return

    # 3. Заголовок статус-бара: чистый системный стиль, только иконка спидометра
    print(" | sfimage=speedometer")
    
    # 4. Формируем выпадающее меню
    print("---")
    
    # Вычисляем средние лимиты по всем аккаунтам
    total_5h = 0
    total_weekly = 0
    valid_accounts_count = 0
    
    for account in quotas_data:
        status = account.get("status")
        if status != "ok":
            continue
        q = account.get("quotas")
        limits = {}
        if q and q.get("groups"):
            gemini_groups = [g for g in q["groups"] if "gemini" in g.get("displayName", "").lower()]
            if gemini_groups:
                limits = gemini_groups[0].get("limits", {})
                
        if not limits:
            limits = {
                "weekly": {"used_percent": 0},
                "5h": {"used_percent": 0}
            }
            
        weekly_percent = limits.get("weekly", {}).get("used_percent", 0)
        five_hour_percent = limits.get("5h", {}).get("used_percent", 0)
        
        # Корректируем 5-часовой лимит, если недельный исчерпан (< 10%)
        if weekly_percent < 10:
            five_hour_percent = 0
            
        total_weekly += weekly_percent
        total_5h += five_hour_percent
        valid_accounts_count += 1
        
    if valid_accounts_count > 0:
        avg_weekly = int(round(total_weekly / valid_accounts_count))
        avg_5h = int(round(total_5h / valid_accounts_count))
        
        print("ОБЩИЕ ЛИМИТЫ | sfimage=chart.bar.fill sfcolor=#BF5AF2 size=11 style=bold color=#BF5AF2")
        bar_5h, color_5h = make_average_progress_bar(avg_5h)
        bar_wk, color_wk = make_average_progress_bar(avg_weekly)
        
        print(f"  Five Hour Limit: {bar_5h} | color={color_5h} font=Menlo size=10 sfimage=clock sfcolor=#BF5AF2")
        print(f"  Weekly Limit: {bar_wk} | color={color_wk} font=Menlo size=10 sfimage=calendar sfcolor=#BF5AF2")
        print("---")
    
    # Сортируем аккаунты в нужном порядке
    quotas_data.sort(key=sort_key)
    
    email_to_db_value = {acc["email"].lower(): acc.get("db_value") for acc in accounts}
    
    active_email = get_active_ide_email()
    active_email_lower = active_email.lower() if active_email else None

    for idx, account in enumerate(quotas_data):
        email = account["email"]
        status = account["status"]
        q = account.get("quotas")
        
        # Разделитель между аккаунтами
        if idx > 0:
            print("---")
            
        # Заголовок аккаунта (подсвечиваем активный в IDE)
        is_active = (active_email_lower == email.lower())
        if is_active:
            print(f"{email} | sfimage=checkmark.circle.fill sfcolor=green size=13 style=bold color=#30D158 badge=Активен")
        else:
            db_value = email_to_db_value.get(email.lower())
            if db_value:
                print(f"{email} | sfimage=person.crop.circle.fill size=13 style=bold badge=Войти bash={python_bin} param1={SWITCH_PATH} param2={email} terminal=false refresh=true")
            else:
                print(f"{email} | sfimage=person.crop.circle.fill size=13 style=bold")
        
        if status == "auth_error":
            print("  Ошибка авторизации. Обновите токен | sfimage=exclamationmark.octagon.fill sfcolor=#FF453A color=#FF453A size=11")
            print(f"  Реавторизовать аккаунт... | sfimage=arrow.triangle.2.circlepath bash={python_bin} param1={AUTH_PATH} terminal=true size=11")
            continue
            
        # Извлекаем лимиты Gemini. Если данных нет, показываем 0% как заглушку.
        limits = {}
        if q and q.get("groups"):
            gemini_groups = [g for g in q["groups"] if "gemini" in g.get("displayName", "").lower()]
            if gemini_groups:
                limits = gemini_groups[0].get("limits", {})
                
        if not limits:
            limits = {
                "weekly": {
                    "displayName": "Weekly Limit",
                    "used_percent": 0,
                    "description": ""
                },
                "5h": {
                    "displayName": "Five Hour Limit",
                    "used_percent": 0,
                    "description": ""
                }
            }
            
        # Выводим лимиты: сначала 5-часовой, затем недельный
        sorted_keys = sorted(limits.keys(), key=lambda k: 0 if "5h" in k.lower() else 1)
        
        # Получаем процент недельного лимита для проверки
        weekly_percent = limits.get("weekly", {}).get("used_percent", 100)
        
        for k in sorted_keys:
            limit_info = limits[k]
            display_name = limit_info.get("displayName", k)
            used_percent = limit_info.get("used_percent", 0)
            desc = limit_info.get("description", "")
            
            # Корректируем 5-часовой лимит, если недельный исчерпан (< 10%)
            if k == "5h" and weekly_percent < 10:
                used_percent = 0
                desc = "Недельный лимит исчерпан"
                
            limit_sf = "clock" if "5h" in k.lower() else "calendar"
            bar_str, bar_color = make_progress_bar(used_percent)
            
            print(f"  {display_name}: {bar_str} | color={bar_color} font=Menlo size=11 sfimage={limit_sf} sfcolor=#AEAEB2")
            
            # Время сброса лимита (если есть)
            time_remaining = format_time_remaining(desc)
            if time_remaining:
                print(f"    {time_remaining} | size=10 color=#8E8E93 sfimage=timer sfcolor=#8E8E93")
                
        # Кнопка переключения аккаунта
        if not is_active:
            db_value = email_to_db_value.get(email.lower())
            if not db_value:
                print("  Сессия не импортирована (войдите под ним в IDE один раз) | size=10 color=gray sfimage=exclamationmark.triangle")
                    
    # Системное меню в самом низу
    print("---")
    last_update_str = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(QUOTAS_PATH)))
    print(f"Последнее обновление: {last_update_str} | size=10 color=gray sfimage=arrow.clockwise.circle sfcolor=gray")
    print(f"Обновить квоты сейчас | bash={python_bin} param1={FETCHER_PATH} terminal=false refresh=true sfimage=arrow.clockwise sfcolor=#30D158")
    print(f"Добавить/Обновить аккаунт | bash={python_bin} param1={AUTH_PATH} terminal=true sfimage=person.badge.plus sfcolor=#0A84FF")
    print(f"Открыть папку проекта | bash=/usr/bin/open param1={PROJECT_DIR} terminal=false sfimage=folder sfcolor=#FFD60A")

if __name__ == "__main__":
    main()
