#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки команд в базе данных
"""

import sqlite3

DATABASE_NAME = 'zkteco_access_control.db'

def check_commands():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    
    print("=== ПРОВЕРКА КОМАНД В БАЗЕ ДАННЫХ ===\n")
    
    # Проверяем команды
    commands = conn.execute("SELECT * FROM pending_commands ORDER BY id").fetchall()
    
    print(f"Всего команд в очереди: {len(commands)}")
    for cmd in commands:
        print(f"ID: {cmd['id']}, Устройство: {cmd['device_sn']}, Команда: {cmd['command_string']}")
    
    print("\n" + "="*50)
    print("ПРОВЕРКА УСТРОЙСТВ:")
    
    devices = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
    
    print(f"Всего устройств: {len(devices)}")
    for device in devices:
        print(f"SN: {device['sn']}, IP: {device['ip_address']}, Последний раз видели: {device['last_seen']}")
    
    conn.close()

if __name__ == "__main__":
    check_commands()
