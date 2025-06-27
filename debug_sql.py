#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отладки SQL запроса пользователей с биометрией
"""

import sqlite3

DATABASE_NAME = 'zkteco_access_control.db'

def debug_users_query():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    
    print("=== ОТЛАДКА SQL ЗАПРОСА ПОЛЬЗОВАТЕЛЕЙ ===\n")
    
    # Текущий запрос из server.py
    current_query = """
        SELECT u.*, 
               COUNT(CASE WHEN b.bio_type = 0 THEN 1 END) as fingerprint_count,
               COUNT(CASE WHEN b.bio_type = 9 THEN 1 END) as face_count,
               GROUP_CONCAT(CASE WHEN b.bio_type = 0 THEN b.finger_id END) as registered_fingers
        FROM users u 
        LEFT JOIN biometrics b ON u.pin = b.user_pin 
        GROUP BY u.pin 
        ORDER BY u.name
    """
    
    print("Текущий запрос:")
    print(current_query)
    print("\nРезультат:")
    
    users = conn.execute(current_query).fetchall()
    for user in users:
        print(f"PIN: {user['pin']}, Имя: {user['name']}, Отпечатки: {user['fingerprint_count']}, Лица: {user['face_count']}, Пальцы: {user['registered_fingers']}")
    
    print("\n" + "="*50)
    print("ПРОВЕРКА БИОМЕТРИЧЕСКИХ ДАННЫХ:")
    
    # Проверяем биометрические данные напрямую
    bio_query = "SELECT user_pin, bio_type, finger_id FROM biometrics ORDER BY user_pin, bio_type, finger_id"
    biometrics = conn.execute(bio_query).fetchall()
    
    print(f"Всего биометрических записей: {len(biometrics)}")
    for bio in biometrics:
        bio_type_name = "Отпечаток" if bio['bio_type'] == 0 else ("Лицо" if bio['bio_type'] == 9 else f"Тип {bio['bio_type']}")
        print(f"PIN: {bio['user_pin']}, Тип: {bio_type_name}, Палец ID: {bio['finger_id']}")
    
    print("\n" + "="*50)
    print("ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ:")
    
    # Проверяем пользователей
    users_query = "SELECT pin, name FROM users ORDER BY pin"
    users_simple = conn.execute(users_query).fetchall()
    
    for user in users_simple:
        print(f"PIN: {user['pin']}, Имя: {user['name']}")
    
    conn.close()

if __name__ == "__main__":
    debug_users_query()
