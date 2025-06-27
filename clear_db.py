#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для очистки базы данных ZKTeco Access Control
"""

import sqlite3

DATABASE_NAME = 'zkteco_access_control.db'

def clear_database():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row

    try:
        print("=== ОЧИСТКА БАЗЫ ДАННЫХ ZKTeco ===\n")

        tables = ['devices', 'users', 'event_logs', 'pending_commands', 'biometrics']
        for table in tables:
            print(f"Очистка таблицы: {table}")
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        print("Все таблицы очищены.")

    except Exception as e:
        print(f"Ошибка при очистке базы данных: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_database()
