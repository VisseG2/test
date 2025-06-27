#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для изучения базы данных ZKTeco Access Control
"""

import sqlite3
import json
from datetime import datetime

DATABASE_NAME = 'zkteco_access_control.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def explore_database():
    print("=== ИССЛЕДОВАНИЕ БАЗЫ ДАННЫХ ZKTeco ===\n")
    
    conn = get_db_connection()
    
    # Получаем список всех таблиц
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"📊 Найдено таблиц: {len(tables)}")
    for table in tables:
        print(f"  - {table['name']}")
    print()
    
    # Изучаем каждую таблицу
    for table in tables:
        table_name = table['name']
        print(f"🔍 ТАБЛИЦА: {table_name}")
        print("-" * 50)
        
        # Получаем структуру таблицы
        schema = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        print("Структура:")
        for column in schema:
            print(f"  {column['name']} ({column['type']}) {'NOT NULL' if column['notnull'] else ''} {'PRIMARY KEY' if column['pk'] else ''}")
        
        # Получаем количество записей
        count = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()
        print(f"Записей: {count['count']}")
        
        # Показываем несколько примеров записей
        if count['count'] > 0:
            print("Примеры записей:")
            examples = conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchall()
            for i, row in enumerate(examples, 1):
                print(f"  Запись {i}: {dict(row)}")
        
        print("\n")
    
    conn.close()

def simulate_device_request():
    """Симулируем запросы от терминала"""
    print("=== СИМУЛЯЦИЯ ЗАПРОСОВ ОТ ТЕРМИНАЛА ===\n")
    
    # Симулируем запрос на регистрацию
    print("1. Симуляция регистрации устройства:")
    print("POST /iclock/registry?SN=TEST123456")
    print("Ответ: RegistryCode=GeneratedCode123")
    
    # Добавляем тестовое устройство в БД
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO devices (sn, ip_address, last_seen) VALUES (?, ?, ?)", 
                    ('TEST123456', '192.168.1.100', datetime.now()))
        conn.commit()
        print("✅ Устройство добавлено в базу")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Симулируем запрос команд
    print("\n2. Симуляция запроса команд:")
    print("GET /iclock/getrequest?SN=TEST123456")
    
    # Проверяем есть ли команды для устройства
    commands = conn.execute("SELECT * FROM pending_commands WHERE device_sn = ?", ('TEST123456',)).fetchall()
    if commands:
        print(f"Найдено команд: {len(commands)}")
        for cmd in commands:
            print(f"  Команда: {cmd['command_string']}")
    else:
        print("Команд нет, ответ: OK")
    
    # Симулируем отправку данных пользователя
    print("\n3. Симуляция отправки данных пользователя:")
    print("POST /iclock/cdata?SN=TEST123456&table=user")
    
    # Добавляем тестового пользователя
    try:
        conn.execute("INSERT OR REPLACE INTO users (pin, name, card_no) VALUES (?, ?, ?)", 
                    ('1001', 'Тестовый Пользователь', '12345'))
        conn.commit()
        print("✅ Пользователь добавлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Симулируем событие доступа
    print("\n4. Симуляция события доступа:")
    print("POST /iclock/cdata?SN=TEST123456&table=rtlog")
    
    try:
        conn.execute("INSERT INTO event_logs (device_sn, user_pin, event_time, event_type, verification_mode, door_id) VALUES (?, ?, ?, ?, ?, ?)", 
                    ('TEST123456', '1001', datetime.now(), '1', '1', '1'))
        conn.commit()
        print("✅ Событие записано")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    conn.close()
    print()

def add_test_commands():
    """Добавляем тестовые команды для эксперимента"""
    print("=== ДОБАВЛЕНИЕ ТЕСТОВЫХ КОМАНД ===\n")
    
    conn = get_db_connection()
    
    test_commands = [
        "C:101:DATA UPDATE user Pin=1002\tName=Новый Пользователь\tPrivilege=0\tCardNo=67890\tPassword=",
        "C:1:DATA QUERY tablename=user,fielddesc=*,filter=*",
        "C:2:DATA QUERY tablename=templatev10,fielddesc=*,filter=*",
        "C:201:ENROLL_BIO TYPE=0\tPIN=1002\tRETRY=3\tOVERWRITE=1\tMODE=1"
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        try:
            conn.execute("INSERT INTO pending_commands (device_sn, command_string) VALUES (?, ?)", 
                        ('TEST123456', cmd))
            print(f"✅ Команда {i} добавлена: {cmd[:50]}...")
        except Exception as e:
            print(f"❌ Ошибка команды {i}: {e}")
    
    conn.commit()
    conn.close()
    print()

def show_device_communication_flow():
    """Показываем как происходит общение с устройством"""
    print("=== ПОТОК КОММУНИКАЦИИ С УСТРОЙСТВОМ ===\n")
    
    flow = [
        ("1. Регистрация", "POST /iclock/registry?SN=DEVICE123", "RegistryCode=Generated123"),
        ("2. Первый запрос", "GET /iclock/cdata?SN=DEVICE123", "registry=ok\\nServerVersion=3.0.1\\nRealtime=1\\nRequestDelay=10"),
        ("3. Запрос команд", "GET /iclock/getrequest?SN=DEVICE123", "C:1:DATA QUERY tablename=user..."),
        ("4. Отправка данных", "POST /iclock/cdata?SN=DEVICE123&table=user", "OK"),
        ("5. Событие доступа", "POST /iclock/cdata?SN=DEVICE123&table=rtlog", "OK"),
        ("6. Удаленная авторизация", "POST /iclock/cdata?SN=DEVICE123&AuthType=device", "AUTH=SUCCESS\\nTIPS=Welcome!"),
    ]
    
    for step, request, response in flow:
        print(f"📱 {step}")
        print(f"   Запрос:  {request}")
        print(f"   Ответ:   {response}")
        print()

if __name__ == "__main__":
    explore_database()
    simulate_device_request()
    add_test_commands()
    show_device_communication_flow()
    
    print("🎯 ЗАКЛЮЧЕНИЕ:")
    print("- База данных содержит 5 основных таблиц")
    print("- Устройства регистрируются через /iclock/registry") 
    print("- Команды передаются через pending_commands таблицу")
    print("- События сохраняются в event_logs")
    print("- Пользователи и биометрия управляются через DATA UPDATE команды")
    print("- Система поддерживает удаленную авторизацию")
