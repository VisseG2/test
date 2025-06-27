#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование команд регистрации отпечатков
"""

import sqlite3

DATABASE_NAME = 'zkteco_access_control.db'

def test_enroll_commands():
    print("=== ТЕСТИРОВАНИЕ КОМАНД РЕГИСТРАЦИИ ===\n")
    
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    
    # Добавляем тестовые команды с разными форматами
    test_commands = [
        # Стандартная команда ENROLL_BIO
        "C:201:ENROLL_BIO TYPE=0\tPIN=1\tNO=1\tRETRY=3\tOVERWRITE=1\tMODE=1",
        
        # Альтернативные форматы
        "C:1:ENROLL_FP pin=1\tfpno=1",
        "C:1:START_ENROLL pin=1\tfid=1",
        
        # Команда включения режима регистрации
        "C:1:SET MODE=ENROLL\tPIN=1\tFINGER=1",
        
        # Команда для терминала перейти в режим регистрации биометрии
        "C:1:ENROLL pin=1\tfid=1\tmode=fp"
    ]
    
    # Очищаем старые команды
    conn.execute("DELETE FROM pending_commands")
    conn.commit()
    
    print("Добавляем тестовые команды:")
    for i, cmd in enumerate(test_commands, 1):
        conn.execute("INSERT INTO pending_commands (device_sn, command_string) VALUES (?, ?)", 
                   ('QJT3242200020', cmd))
        print(f"{i}. {cmd}")
    
    conn.commit()
    
    print(f"\nДобавлено {len(test_commands)} команд в очередь.")
    print("Теперь на терминале должны появиться команды для регистрации.")
    print("Проверьте на терминале реакцию на каждую команду.")
    
    conn.close()

if __name__ == "__main__":
    test_enroll_commands()
