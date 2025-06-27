#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Симулятор терминала ZKTeco для тестирования сервера
"""

import requests
import time
import json
from datetime import datetime

SERVER_URL = "http://127.0.0.1:8080"
DEVICE_SN = "SIM1234567890"
DEVICE_IP = "192.168.1.101"

def simulate_device_registration():
    """Симулируем регистрацию устройства"""
    print("🔌 Регистрируем устройство...")
    
    url = f"{SERVER_URL}/iclock/registry"
    params = {"SN": DEVICE_SN}
    
    try:
        response = requests.post(url, params=params, timeout=5)
        print(f"Ответ сервера: {response.text}")
        print(f"Статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
    print()

def simulate_initial_handshake():
    """Симулируем первоначальное рукопожатие"""
    print("🤝 Выполняем первоначальное рукопожатие...")
    
    url = f"{SERVER_URL}/iclock/cdata"
    params = {"SN": DEVICE_SN, "options": "all"}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"Ответ сервера: {response.text}")
        print(f"Статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка рукопожатия: {e}")
    print()

def simulate_command_request():
    """Симулируем запрос команд от сервера"""
    print("📥 Запрашиваем команды с сервера...")
    
    url = f"{SERVER_URL}/iclock/getrequest"
    params = {"SN": DEVICE_SN}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"Команда от сервера: {response.text}")
        print(f"Статус: {response.status_code}")
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"❌ Ошибка запроса команд: {e}")
        return None
    print()

def simulate_user_data_upload():
    """Симулируем отправку данных пользователей"""
    print("👥 Отправляем данные пользователей...")
    
    # Данные в формате ZKTeco для таблицы user
    user_data = """1\tpin=101\tname=Симулированный Пользователь\tcardno=123456\tprivilege=0\tpassword=\tgroup=0\tstarttime=\tendtime=
2\tpin=102\tname=Тестовый Админ\tcardno=789012\tprivilege=14\tpassword=\tgroup=0\tstarttime=\tendtime="""
    
    url = f"{SERVER_URL}/iclock/cdata"
    params = {"SN": DEVICE_SN, "table": "user", "stamp": int(time.time())}
    
    try:
        response = requests.post(url, params=params, data=user_data, timeout=5)
        print(f"Ответ сервера: {response.text}")
        print(f"Статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка отправки пользователей: {e}")
    print()

def simulate_access_events():
    """Симулируем события доступа"""
    print("🚪 Отправляем события доступа...")
    
    # Симулируем несколько событий
    events = [
        "pin=101\ttime=2025-06-26 15:30:00\tevent=1\tverifytype=1\teventaddr=1",  # Успешный доступ
        "pin=102\ttime=2025-06-26 15:31:00\tevent=1\tverifytype=15\teventaddr=1", # Доступ по лицу
        "pin=999\ttime=2025-06-26 15:32:00\tevent=27\tverifytype=1\teventaddr=1", # Пользователь не зарегистрирован
    ]
    
    event_data = "\n".join(events)
    
    url = f"{SERVER_URL}/iclock/cdata"
    params = {"SN": DEVICE_SN, "table": "rtlog", "stamp": int(time.time())}
    
    try:
        response = requests.post(url, params=params, data=event_data, timeout=5)
        print(f"Ответ сервера: {response.text}")
        print(f"Статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка отправки событий: {e}")
    print()

def simulate_remote_verification():
    """Симулируем удаленную верификацию"""
    print("🔐 Симулируем удаленную верификацию...")
    
    # Запрос на удаленную верификацию
    auth_data = "pin=101\tpassword=\tcardno="
    
    url = f"{SERVER_URL}/iclock/cdata"
    params = {"SN": DEVICE_SN, "AuthType": "device"}
    
    try:
        response = requests.post(url, params=params, data=auth_data, timeout=5)
        print(f"Результат верификации: {response.text}")
        print(f"Статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка верификации: {e}")
    print()

def simulate_biometric_upload():
    """Симулируем отправку биометрических данных"""
    print("👁️ Отправляем биометрические данные...")
    
    # Симулируем шаблон отпечатка пальца (base64)
    bio_data = "PIN=101\tTYPE=0\tNO=0\tIndex=0\tValid=1\tTMP=VGVzdCBmaW5nZXJwcmludCB0ZW1wbGF0ZSBkYXRh"
    
    url = f"{SERVER_URL}/iclock/cdata"
    params = {"SN": DEVICE_SN, "type": "BioData"}
    
    try:
        response = requests.post(url, params=params, data=bio_data, timeout=5)
        print(f"Ответ сервера: {response.text}")
        print(f"Статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка отправки биометрии: {e}")
    print()

def test_server_connectivity():
    """Проверяем доступность сервера"""
    print("🌐 Проверяем доступность сервера...")
    
    try:
        response = requests.get(f"{SERVER_URL}/ping", timeout=5)
        if response.status_code == 200:
            print("✅ Сервер доступен")
            return True
        else:
            print(f"❌ Сервер недоступен (статус: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Сервер недоступен: {e}")
        return False

def run_full_simulation():
    """Запускаем полную симуляцию работы терминала"""
    print("🚀 Запускаем полную симуляцию терминала ZKTeco")
    print("=" * 60)
    
    if not test_server_connectivity():
        print("❌ Симуляция прервана - сервер недоступен")
        return
    
    # Последовательность типичного взаимодействия терминала с сервером
    simulate_device_registration()
    time.sleep(1)
    
    simulate_initial_handshake()
    time.sleep(1)
    
    # Запрашиваем команды несколько раз
    for i in range(3):
        print(f"📋 Проверка команд #{i+1}")
        command = simulate_command_request()
        if command and command.strip() != "OK":
            print(f"Получена команда: {command}")
        time.sleep(1)
    
    simulate_user_data_upload()
    time.sleep(1)
    
    simulate_biometric_upload()
    time.sleep(1)
    
    simulate_access_events()
    time.sleep(1)
    
    simulate_remote_verification()
    
    print("✅ Симуляция завершена!")

if __name__ == "__main__":
    print("ZKTeco Terminal Simulator")
    print("=" * 40)
    print("Этот скрипт симулирует работу терминала ZKTeco")
    print("и отправляет различные типы запросов к серверу.")
    print()
    
    choice = input("Запустить полную симуляцию? (y/n): ").strip().lower()
    
    if choice == 'y':
        run_full_simulation()
    else:
        print("Симуляция отменена")
