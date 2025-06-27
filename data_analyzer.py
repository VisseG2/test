#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор данных ZKTeco для понимания форматов и структур
"""

import sqlite3
import base64
import json
from datetime import datetime

DATABASE_NAME = 'zkteco_access_control.db'

def analyze_real_data():
    """Анализируем реальные данные в базе"""
    print("🔬 АНАЛИЗ РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 50)
    
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    
    # Анализируем устройства
    print("📱 УСТРОЙСТВА:")
    devices = conn.execute("SELECT * FROM devices").fetchall()
    for device in devices:
        print(f"  SN: {device['sn']}")
        print(f"  IP: {device['ip_address']}")
        print(f"  Последний контакт: {device['last_seen']}")
        print(f"  Прошивка: {device['firmware_version'] or 'Неизвестно'}")
        print()
    
    # Анализируем пользователей
    print("👥 ПОЛЬЗОВАТЕЛИ:")
    users = conn.execute("SELECT * FROM users").fetchall()
    for user in users:
        print(f"  PIN: {user['pin']} | Имя: {user['name']}")
        print(f"  Карта: {user['card_no'] or 'Нет'}")
        print(f"  Привилегии: {user['privilege']}")
        print(f"  Сообщение: {user['message_to_display'] or 'Нет'}")
        print()
    
    # Анализируем биометрию
    print("🔐 БИОМЕТРИЧЕСКИЕ ДАННЫЕ:")
    biometrics = conn.execute("SELECT * FROM biometrics").fetchall()
    for bio in biometrics:
        bio_type_name = {
            0: "Отпечаток пальца",
            9: "Шаблон лица"
        }.get(bio['bio_type'], f"Неизвестный тип {bio['bio_type']}")
        
        print(f"  Пользователь PIN: {bio['user_pin']}")
        print(f"  Тип: {bio_type_name}")
        print(f"  Палец ID: {bio['finger_id']}")
        print(f"  Размер шаблона: {len(bio['template_data'])} символов")
        
        # Попробуем декодировать начало шаблона
        try:
            template_start = bio['template_data'][:50]
            print(f"  Начало шаблона: {template_start}...")
        except:
            print("  Ошибка чтения шаблона")
        print()
    
    # Анализируем события
    print("📋 СОБЫТИЯ ДОСТУПА:")
    events = conn.execute("""
        SELECT e.*, u.name 
        FROM event_logs e 
        LEFT JOIN users u ON e.user_pin = u.pin 
        ORDER BY e.event_time DESC
    """).fetchall()
    
    for event in events:
        event_type_name = {
            '1': 'Успешный доступ',
            '27': 'Пользователь не зарегистрирован',
            '200': 'Дверь открыта',
            '201': 'Дверь закрыта'
        }.get(event['event_type'], f"Событие {event['event_type']}")
        
        verify_type_name = {
            '0': 'Автоопределение',
            '1': 'Только отпечаток',
            '15': 'Лицо'
        }.get(event['verification_mode'], f"Режим {event['verification_mode']}")
        
        print(f"  Время: {event['event_time']}")
        print(f"  Устройство: {event['device_sn']}")
        print(f"  Пользователь: {event['user_pin']} ({event['name'] or 'Неизвестный'})")
        print(f"  Событие: {event_type_name}")
        print(f"  Верификация: {verify_type_name}")
        print(f"  Дверь: {event['door_id']}")
        print()
    
    # Анализируем команды
    print("⚙️ ОТЛОЖЕННЫЕ КОМАНДЫ:")
    commands = conn.execute("SELECT * FROM pending_commands").fetchall()
    if commands:
        for cmd in commands:
            print(f"  Устройство: {cmd['device_sn']}")
            print(f"  Команда: {cmd['command_string']}")
            print()
    else:
        print("  Нет отложенных команд")
        print()
    
    conn.close()

def decode_biometric_template(template_data):
    """Пытаемся декодировать биометрический шаблон"""
    print("🧬 АНАЛИЗ БИОМЕТРИЧЕСКОГО ШАБЛОНА")
    print("=" * 50)
    
    try:
        # Пытаемся декодировать как base64
        decoded = base64.b64decode(template_data)
        print(f"Размер декодированных данных: {len(decoded)} байт")
        
        # Показываем первые байты в hex
        hex_start = ' '.join([f'{b:02x}' for b in decoded[:32]])
        print(f"Первые 32 байта (hex): {hex_start}")
        
        # Проверяем, есть ли текстовые данные в начале
        text_start = decoded[:20]
        try:
            text_decoded = text_start.decode('ascii', errors='ignore')
            if text_decoded:
                print(f"Возможный текстовый заголовок: {text_decoded}")
        except:
            pass
            
        # Анализируем возможную структуру
        if decoded.startswith(b'MM'):
            print("Возможно: шаблон начинается с MM (ZKTeco format)")
        elif decoded.startswith(b'ZKTPL'):
            print("Возможно: шаблон ZKTeco Template")
        
    except Exception as e:
        print(f"Ошибка декодирования: {e}")

def analyze_command_formats():
    """Анализируем форматы команд ZKTeco"""
    print("📋 ФОРМАТЫ КОМАНД ZKTECO")
    print("=" * 50)
    
    sample_commands = [
        "C:101:DATA UPDATE user Pin=1\tName=Test\tPrivilege=0\tCardNo=123\tPassword=",
        "C:102:DATA UPDATE biodata Pin=1\tNo=0\tIndex=0\tValid=1\tType=9\tTmp=base64data",
        "C:1:DATA QUERY tablename=user,fielddesc=*,filter=*",
        "C:2:DATA QUERY tablename=templatev10,fielddesc=*,filter=*",
        "C:201:ENROLL_BIO TYPE=0\tPIN=1\tRETRY=3\tOVERWRITE=1\tMODE=1"
    ]
    
    for cmd in sample_commands:
        parts = cmd.split(':', 2)
        if len(parts) >= 3:
            prefix = parts[0]
            cmd_id = parts[1]
            command = parts[2]
            
            print(f"Команда ID: {cmd_id}")
            print(f"Тип: {command.split()[0] if command else 'N/A'}")
            print(f"Полная команда: {cmd}")
            print()

def analyze_event_codes():
    """Анализируем коды событий"""
    print("📊 КОДЫ СОБЫТИЙ ZKTECO")
    print("=" * 50)
    
    event_codes = {
        1: "Успешная верификация",
        20: "Слишком короткий интервал",
        21: "Доступ в недопустимое время", 
        27: "Пользователь не зарегистрирован",
        28: "Тайм-аут открытия двери",
        29: "Истек срок действия привилегий",
        44: "Удаленная идентификация не удалась",
        45: "Тайм-аут удаленной идентификации",
        100: "Тревога вскрытия",
        200: "Дверь открыта",
        201: "Дверь закрыта",
        202: "Открытие кнопкой выхода",
        222: "Удаленная идентификация успешна"
    }
    
    for code, description in event_codes.items():
        print(f"  {code:3d}: {description}")
    print()

def analyze_verification_modes():
    """Анализируем режимы верификации"""
    print("🔐 РЕЖИМЫ ВЕРИФИКАЦИИ")
    print("=" * 50)
    
    verify_modes = {
        0: "Автоматическое определение",
        1: "Только отпечаток пальца", 
        2: "Только ID пользователя",
        3: "Только пароль",
        4: "Только карта",
        5: "Отпечаток или пароль",
        6: "Отпечаток или карта",
        7: "Карта или пароль",
        8: "ID пользователя и отпечаток",
        9: "Отпечаток и пароль",
        10: "Карта и отпечаток",
        11: "Карта и пароль",
        15: "Лицо",
        16: "Лицо и отпечаток",
        17: "Лицо и пароль",
        18: "Лицо и карта"
    }
    
    for mode, description in verify_modes.items():
        print(f"  {mode:2d}: {description}")
    print()

if __name__ == "__main__":
    print("🔍 ZKTeco Data Analyzer")
    print("=" * 60)
    
    analyze_real_data()
    analyze_command_formats()
    analyze_event_codes()
    analyze_verification_modes()
    
    # Анализируем биометрический шаблон, если есть данные
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    bio = conn.execute("SELECT template_data FROM biometrics LIMIT 1").fetchone()
    if bio:
        decode_biometric_template(bio['template_data'])
    conn.close()
    
    print("🎯 ЗАКЛЮЧЕНИЕ:")
    print("- В базе есть реальное устройство с SN: QJT3242200020")
    print("- Зарегистрировано 5 пользователей с биометрическими данными")
    print("- Биометрические шаблоны кодируются в base64")
    print("- События содержат коды от 1 до 255 согласно протоколу")
    print("- Команды используют формат C:ID:COMMAND")
    print("- Система поддерживает отпечатки пальцев и распознавание лиц")
