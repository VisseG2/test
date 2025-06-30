# Імпортуємо необхідні бібліотеки
from flask import Flask, request, Response, render_template, redirect, url_for, flash
import sqlite3
import datetime
import base64
import threading
import logging
import os
from werkzeug.utils import secure_filename

# --- Налаштування ---
HOST_IP = '0.0.0.0'
HOST_PORT = 8080
DATABASE_NAME = 'zkteco_access_control.db'
SECRET_KEY = 'my-super-secret-key-change-it'

# Створюємо веб-додаток
app = Flask(__name__)
app.secret_key = SECRET_KEY
db_lock = threading.Lock()

# --- Функції для роботи з базою даних ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    print("Ініціалізація бази даних...")
    with db_lock:
        conn = get_db_connection()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY,
                sn TEXT UNIQUE,
                ip_address TEXT,
                last_seen TIMESTAMP,
                alias TEXT,
                firmware_version TEXT
            );"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS device_params (
                device_sn TEXT,
                param_name TEXT,
                param_value TEXT,
                PRIMARY KEY (device_sn, param_name)
            );"""
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, pin TEXT UNIQUE, name TEXT, card_no TEXT, privilege INTEGER DEFAULT 0, message_to_display TEXT);""")
        conn.execute("""CREATE TABLE IF NOT EXISTS event_logs (id INTEGER PRIMARY KEY, device_sn TEXT, user_pin TEXT, event_time TIMESTAMP, event_type TEXT, verification_mode TEXT, door_id INTEGER);""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pending_commands (id INTEGER PRIMARY KEY, device_sn TEXT, command_string TEXT);""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS biometrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_pin TEXT NOT NULL,
            bio_type INTEGER NOT NULL,
            template_data TEXT NOT NULL,
            finger_id INTEGER,
            version TEXT,
            UNIQUE(user_pin, bio_type, finger_id)
        );""")
        conn.commit()
        conn.close()
    print("База даних успішно ініціалізована.")

def add_pending_command(device_sn, command_string):
    with db_lock:
        conn = get_db_connection()
        conn.execute("INSERT INTO pending_commands (device_sn, command_string) VALUES (?, ?)", (device_sn, command_string))
        conn.commit()
        conn.close()

def parse_pairs(text, sep='\t'):
    """Parse key=value pairs separated by `sep`. Extra '=' characters are kept in values."""
    result = {}
    for part in text.strip().split(sep):
        if '=' in part:
            key, value = part.split('=', 1)
            result[key] = value
    return result

# --- Маршрути для веб-інтерфейсу (Адмін-панель) ---

@app.route('/')
def dashboard():
    with db_lock:
        conn = get_db_connection()
        devices = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
        logs = conn.execute("SELECT l.*, u.name FROM event_logs l LEFT JOIN users u ON l.user_pin = u.pin ORDER BY l.id DESC LIMIT 20").fetchall()
        conn.close()
    return render_template('dashboard.html', devices=devices, logs=logs)

@app.route('/sync_all/<device_sn>')
def sync_all(device_sn):
    add_pending_command(device_sn, "C:1:DATA QUERY tablename=user,fielddesc=*,filter=*")
    add_pending_command(device_sn, "C:2:DATA QUERY tablename=templatev10,fielddesc=*,filter=*")
    flash(f"Запит на повну синхронізацію відправлено на пристрій {device_sn}.", 'info')
    return redirect(url_for('dashboard'))


@app.route('/devices', methods=['GET', 'POST'])
def manage_devices():
    """Перегляд та редагування інформації про пристрої"""
    if request.method == 'POST':
        sn = request.form.get('sn')
        alias = request.form.get('alias', '').strip()
        with db_lock:
            conn = get_db_connection()
            conn.execute("UPDATE devices SET alias = ? WHERE sn = ?", (alias, sn))
            conn.commit()
            conn.close()
        flash(f'Інформацію про пристрій {sn} оновлено.', 'success')
        return redirect(url_for('manage_devices'))

    with db_lock:
        conn = get_db_connection()
        devices = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
        conn.close()
    return render_template('devices.html', devices=devices)



@app.route('/device/<sn>')
def device_detail_page(sn):
    """Детальна інформація про пристрій"""
    with db_lock:
        conn = get_db_connection()
        device = conn.execute("SELECT * FROM devices WHERE sn = ?", (sn,)).fetchone()
        params = conn.execute(
            "SELECT param_name, param_value FROM device_params WHERE device_sn = ? ORDER BY param_name",
            (sn,),
        ).fetchall()
        conn.close()
    if not device:
        return "Пристрій не знайдено", 404
    return render_template('device_detail.html', device=device, params=params)


@app.route('/enroll_fingerprint/<device_sn>/<pin>/<int:finger_id>')
def enroll_fingerprint(device_sn, pin, finger_id=0):
    """Удаленная регистрация отпечатка пальца"""
    print(f"👆 Начинаем регистрацию отпечатка для PIN {pin}, палец {finger_id}, устройство {device_sn}")
    
    command = f"C:201:ENROLL_BIO TYPE=0\tPIN={pin}\tNO={finger_id}\tRETRY=3\tOVERWRITE=1\tMODE=1"
    print(f"📝 Сформирована команда: {command}")
    
    try:
        with db_lock:
            conn = get_db_connection()
            conn.execute("INSERT INTO pending_commands (device_sn, command_string) VALUES (?, ?)", 
                       (device_sn, command))
            conn.commit()
            conn.close()
        print(f"✅ Команда регистрации отпечатка добавлена в очередь для {device_sn}")
        
        finger_names = {
            0: "Большой палец (правая рука)",
            1: "Указательный палец (правая рука)", 
            2: "Средний палец (правая рука)",
            3: "Безымянный палец (правая рука)",
            4: "Мизинец (правая рука)",
            5: "Большой палец (левая рука)",
            6: "Указательный палец (левая рука)",
            7: "Средний палец (левая рука)", 
            8: "Безымянный палец (левая рука)",
            9: "Мизинец (левая рука)"
        }
        
        finger_name = finger_names.get(finger_id, f"Палец #{finger_id}")
        flash(f"Команда на регистрацию отпечатка ({finger_name}) для пользователя PIN {pin} отправлена на устройство {device_sn}. Приложите палец к сканеру.", 'info')
        
    except Exception as e:
        print(f"💥 Ошибка при добавлении команды регистрации отпечатка: {e}")
        flash(f"Ошибка при отправке команды регистрации: {e}", 'danger')
    
    return redirect(url_for('user_detail', pin=pin))

@app.route('/delete_user/<pin>')
def delete_user(pin):
    """Удаление пользователя"""
    print(f"🗑️ Начинаем удаление пользователя PIN {pin}")
    try:
        with db_lock:
            conn = get_db_connection()
            try:
                print(f"📝 Удаляем пользователя {pin} из базы данных...")
                # Удаляем пользователя
                conn.execute("DELETE FROM users WHERE pin = ?", (pin,))
                # Удаляем его биометрические данные
                conn.execute("DELETE FROM biometrics WHERE user_pin = ?", (pin,))
                conn.commit()
                print(f"✅ Пользователь {pin} удален из локальной базы")
                
                # Получаем устройства для отправки команд
                devices = conn.execute("SELECT sn FROM devices").fetchall()
                print(f"📡 Найдено устройств для синхронизации: {len(devices)}")
                
                # Отправляем команды удаления на устройства
                for device in devices:
                    command = f"C:103:DATA DELETE user Pin={pin}"
                    conn.execute("INSERT INTO pending_commands (device_sn, command_string) VALUES (?, ?)", 
                               (device['sn'], command))
                    print(f"📤 Команда удаления отправлена на {device['sn']}")
                
                conn.commit()
                print(f"✅ Все команды добавлены в очередь")
                
            except Exception as db_error:
                conn.rollback()
                print(f"❌ Ошибка базы данных: {db_error}")
                raise db_error
            finally:
                conn.close()
                print(f"🔒 Соединение с базой закрыто")
            
        flash(f"Пользователь PIN {pin} успешно удален из системы и с устройств.", 'success')
        print(f"🎉 Удаление пользователя {pin} завершено успешно")
        
    except Exception as e:
        print(f"💥 Критическая ошибка при удалении пользователя {pin}: {e}")
        flash(f"Ошибка при удалении пользователя: {e}", 'danger')
    
    return redirect(url_for('manage_users'))

@app.route('/delete_biometric/<pin>/<int:bio_type>/<int:finger_id>')
def delete_biometric(pin, bio_type, finger_id):
    """Удаление биометрических данных"""
    try:
        with db_lock:
            conn = get_db_connection()
            conn.execute(
                "DELETE FROM biometrics WHERE user_pin = ? AND bio_type = ? AND finger_id = ?",
                (pin, bio_type, finger_id),
            )
            devices = conn.execute("SELECT sn FROM devices").fetchall()
            conn.commit()
            conn.close()

        for device in devices:
            if bio_type == 0:  # Отпечаток
                add_pending_command(
                    device["sn"],
                    f"C:104:DATA DELETE template Pin={pin}\tNo={finger_id}",
                )
            elif bio_type == 9:  # Лицо
                add_pending_command(
                    device["sn"], f"C:105:DATA DELETE face Pin={pin}"
                )
            
        bio_name = "отпечатка пальца" if bio_type == 0 else "лица"
        flash(f"Биометрические данные ({bio_name}) для PIN {pin} успешно удалены.", 'success')
    except Exception as e:
        flash(f"Ошибка при удалении биометрических данных: {e}", 'danger')
    
    return redirect(url_for('user_detail', pin=pin))

@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if request.method == 'POST':
        try:
            pin = request.form.get('pin', '').strip()
            name = request.form.get('name', '').strip()
            card_no = request.form.get('card_no', '').strip()
            device_sn = request.form.get('device_sn', '').strip()
            privilege = int(request.form.get('privilege', 0))
            
            # Валидация данных
            if not pin or not name:
                flash('PIN и имя обязательны для заполнения.', 'danger')
                return redirect(url_for('manage_users'))
            
            if not pin.isdigit():
                flash('PIN должен содержать только цифры.', 'danger')
                return redirect(url_for('manage_users'))
            
            # Сохраняем пользователя в локальной базе
            with db_lock:
                conn = get_db_connection()
                if conn.execute("SELECT 1 FROM users WHERE pin = ?", (pin,)).fetchone():
                    conn.execute("UPDATE users SET name = ?, card_no = ?, privilege = ? WHERE pin = ?", 
                               (name, card_no, privilege, pin))
                    flash(f"Пользователь {name} успешно обновлен.", 'success')
                else:
                    conn.execute("INSERT INTO users (pin, name, card_no, privilege) VALUES (?, ?, ?, ?)", 
                               (pin, name, card_no, privilege))
                    flash(f"Пользователь {name} успешно создан.", 'success')
                conn.commit()
                conn.close()
            
            # Отправляем команду на все устройства если указано
            if device_sn:
                user_cmd_body = f"Pin={pin}\tName={name}\tPrivilege={privilege}\tCardNo={card_no}\tPassword="
                add_pending_command(device_sn, f"C:101:DATA UPDATE user {user_cmd_body}")
                flash(f"Команда на добавление пользователя отправлена на устройство {device_sn}.", 'info')
                
        except Exception as e:
            flash(f"Ошибка при добавлении пользователя: {e}", 'danger')
        return redirect(url_for('manage_users'))

    # Получаем данные для отображения
    with db_lock:
        conn = get_db_connection()
        
        # Получаем пользователей с информацией о биометрии
        users_query = """
            SELECT u.*, 
                   COUNT(CASE WHEN b.bio_type = 0 THEN 1 END) as fingerprint_count,
                   COUNT(CASE WHEN b.bio_type = 9 THEN 1 END) as face_count,
                   GROUP_CONCAT(CASE WHEN b.bio_type = 0 THEN b.finger_id END) as registered_fingers
            FROM users u 
            LEFT JOIN biometrics b ON u.pin = b.user_pin 
            GROUP BY u.pin 
            ORDER BY u.name
        """
        users = conn.execute(users_query).fetchall()
        devices = conn.execute("SELECT sn FROM devices ORDER BY last_seen DESC").fetchall()
        conn.close()
    
    return render_template('users.html', users=users, devices=devices)

@app.route('/user/<pin>', methods=['GET', 'POST'])
def user_detail(pin):
    if request.method == 'POST':
        pending_cmd = None
        device_sn = request.form.get('device_sn')
        if 'face_photo' in request.files and request.files['face_photo'].filename != '':
            print(f"📸 Начинаем загрузку фото для пользователя PIN {pin}")
            try:
                face_file = request.files['face_photo']
                face_data = face_file.read()
                print(f"📁 Размер файла: {len(face_data)} байт")

                print("🔄 Кодируем фото в base64...")
                face_template = base64.b64encode(face_data).decode('utf-8')
                print(f"✅ Фото закодировано, размер base64: {len(face_template)} символов")

                bio_cmd_body = (
                    f"Pin={pin}\tNo=0\tIndex=0\tValid=1\tDuress=0\tType=9\tFormat=0\tTmp={face_template}"
                )
                pending_cmd = f"C:102:DATA UPDATE biodata {bio_cmd_body}"
            except Exception as e:
                print(f"💥 Ошибка при подготовке фото: {e}")
                flash(f"Ошибка при загрузке фото: {e}", 'danger')

        if 'message' in request.form:
            with db_lock:
                conn = get_db_connection()
                conn.execute("UPDATE users SET message_to_display = ? WHERE pin = ?", (request.form['message'], pin))
                conn.commit()
                conn.close()
            flash(f"Повідомлення для користувача {pin} успішно встановлено.", 'success')

        if pending_cmd and device_sn:
            add_pending_command(device_sn, pending_cmd)
            print(f"✅ Команда добавлена в очередь для устройства {device_sn}")
            flash(
                f"Команда на загрузку фото лица для PIN {pin} отправлена на устройство {device_sn}.",
                'success',
            )
        return redirect(url_for('user_detail', pin=pin))

    with db_lock:
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE pin = ?", (pin,)).fetchone()
        biometrics = conn.execute("SELECT * FROM biometrics WHERE user_pin = ?", (pin,)).fetchall()
        devices = conn.execute("SELECT sn FROM devices").fetchall()
        conn.close()
    if not user:
        return "Користувач не знайдений", 404
    return render_template('user_detail.html', user=user, biometrics=biometrics, devices=devices)

# --- Маршрути для взаємодії з терміналами ZKTeco ---

@app.route('/iclock/cdata', methods=['GET', 'POST'])
def handle_cdata():
    serial_number = request.args.get('SN')
    if not serial_number: return Response("Error: SN not provided.", status=400)
    
    with db_lock:
        conn = get_db_connection()
        conn.execute("UPDATE devices SET last_seen = ? WHERE sn = ?", (datetime.datetime.now(), serial_number))
        conn.commit()
        conn.close()

    if request.args.get('type') == 'BioData':
        body = request.get_data().decode('utf-8')

        bio_data = parse_pairs(body)

        pin, bio_type = bio_data.get('PIN'), int(bio_data.get('TYPE'))
        template, finger_id = bio_data.get('TMP'), int(bio_data.get('NO', 0))
        with db_lock:
            conn = get_db_connection()
            conn.execute("""INSERT INTO biometrics (user_pin, bio_type, template_data, finger_id) VALUES (?, ?, ?, ?)
                          ON CONFLICT(user_pin, bio_type, finger_id) DO UPDATE SET template_data=excluded.template_data;""",
                          (pin, bio_type, template, finger_id))
            conn.commit()
            conn.close()
        print(f"Успішно зареєстровано біометрію (тип: {bio_type}) для PIN {pin}")
        return Response("OK", content_type="text/plain")

    if request.args.get('AuthType') == 'device':
        body = request.get_data().decode('utf-8')

        auth_data = parse_pairs(body)

        user_pin = auth_data.get('pin')
        print(f"Запит на віддалену ідентифікацію для PIN: {user_pin}")
        with db_lock:
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM users WHERE pin = ?", (user_pin,)).fetchone()
            if user:
                message = user['message_to_display'] or "Welcome!"
                if user['message_to_display']:
                    conn.execute("UPDATE users SET message_to_display = NULL WHERE pin = ?", (user_pin,))
                    conn.commit()
                response_body = f"AUTH=SUCCESS\r\nCONTROL DEVICE 01010105\r\nTIPS={message}\r\n"
            else:
                response_body = "AUTH=FAILED\r\nTIPS=Access Denied\r\n"
            conn.close()
        return Response(response_body, content_type="text/plain")

    if request.args.get('table') == 'rtlog':
        with db_lock:
            conn = get_db_connection()
            for line in request.get_data().decode('utf-8').strip().split('\n'):
                try:

                    log_dict = parse_pairs(line)

                    conn.execute("INSERT INTO event_logs (device_sn, user_pin, event_time, event_type, verification_mode, door_id) VALUES (?, ?, ?, ?, ?, ?)",
                               (serial_number, log_dict.get('pin'), log_dict.get('time'), log_dict.get('event'), log_dict.get('verifytype'), log_dict.get('eventaddr')))
                    conn.commit()
                except Exception as e: print(f"Помилка обробки логу: {e}")
            conn.close()
        return Response("OK", content_type="text/plain")
        
    return Response("registry=ok\nServerVersion=3.0.1\nRealtime=1\nRequestDelay=10\n", content_type="text/plain")

@app.route('/iclock/querydata', methods=['POST'])
def handle_querydata():
    serial_number, table_name = request.args.get('SN'), request.args.get('tablename')
    cmd_id = request.args.get('cmdid')
    print(f"Отримано дані від {serial_number} для таблиці '{table_name}'...")
    
    with db_lock:
        conn = get_db_connection()
        if table_name == 'user':
            for line in request.get_data().decode('utf-8').strip().split('\n'):
                try:

                    user_dict = parse_pairs('\t'.join(line.split('\t')[1:]))

                    pin, name, card_no = user_dict.get('pin'), user_dict.get('name', 'N/A'), user_dict.get('cardno', '')
                    if not conn.execute("SELECT 1 FROM users WHERE pin = ?", (pin,)).fetchone():
                        conn.execute("INSERT INTO users (pin, name, card_no) VALUES (?, ?, ?)", (pin, name, card_no))
                    else:
                        conn.execute("UPDATE users SET name = ?, card_no = ? WHERE pin = ?", (name, card_no, pin))
                    conn.commit()
                except Exception as e: print(f"Помилка парсингу користувача: {e}")
        
        elif table_name == 'templatev10':
            for line in request.get_data().decode('utf-8').strip().split('\n'):
                try:

                    fp_dict = parse_pairs('\t'.join(line.split('\t')[1:]))

                    pin, finger_id = fp_dict.get('pin'), int(fp_dict.get('fingerid'))
                    template = fp_dict.get('template')
                    conn.execute("""INSERT INTO biometrics (user_pin, bio_type, finger_id, template_data) VALUES (?, 0, ?, ?)
                                  ON CONFLICT(user_pin, bio_type, finger_id) DO UPDATE SET template_data=excluded.template_data;""",
                                  (pin, finger_id, template))
                    conn.commit()
                except Exception as e: print(f"Помилка парсингу відбитка: {e}")
        conn.close()

    add_pending_command(serial_number, f"ID={cmd_id}&Return=0&CMD=DATA")
    return Response("OK", content_type="text/plain")

@app.route('/iclock/registry', methods=['POST'])
def handle_registry():
    serial_number, device_ip = request.args.get('SN'), request.remote_addr
    body = request.get_data(as_text=True)
    params = parse_pairs(body, sep=',')
    with db_lock:
        conn = get_db_connection()
        if conn.execute("SELECT 1 FROM devices WHERE sn = ?", (serial_number,)).fetchone():
            conn.execute(
                "UPDATE devices SET ip_address = ?, last_seen = ?, firmware_version = ? WHERE sn = ?",
                (device_ip, datetime.datetime.now(), params.get('FirmVer'), serial_number),
            )
        else:
            conn.execute(
                "INSERT INTO devices (sn, ip_address, last_seen, firmware_version) VALUES (?, ?, ?, ?)",
                (serial_number, device_ip, datetime.datetime.now(), params.get('FirmVer')),
            )
        for key, value in params.items():
            conn.execute(
                "REPLACE INTO device_params (device_sn, param_name, param_value) VALUES (?, ?, ?)",
                (serial_number, key, value),
            )
        conn.commit()
        conn.close()
    return Response("RegistryCode=GeneratedCode123", content_type="text/plain")

@app.route('/iclock/getrequest', methods=['GET'])
def handle_getrequest():
    serial_number = request.args.get('SN')
    print(f"🔍 Устройство {serial_number} запрашивает команды...")
    command_to_send = None
    with db_lock:
        conn = get_db_connection()
        command_row = conn.execute("SELECT * FROM pending_commands WHERE device_sn = ? ORDER BY id LIMIT 1", (serial_number,)).fetchone()
        if command_row:
            command_to_send = command_row['command_string']
            conn.execute("DELETE FROM pending_commands WHERE id = ?", (command_row['id'],))
            conn.commit()
            print(f"📤 Отправляем команду ID {command_row['id']} для {serial_number}: {command_to_send}")
        else:
            print(f"⭕ Нет команд для устройства {serial_number}")
        conn.close()
    return Response(command_to_send, content_type="text/plain") if command_to_send else Response("OK", content_type="text/plain")

@app.route('/iclock/push', methods=['POST'])
def handle_push(): return Response("OK", content_type="text/plain")

@app.route('/iclock/devicecmd', methods=['POST'])
def handle_devicecmd(): return Response("OK", content_type="text/plain")

@app.route('/ping', methods=['GET'])
@app.route('/iclock/ping', methods=['GET'])
def handle_ping(): return Response("OK", content_type="text/plain")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zkteco_server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Обработчик ошибок
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Внутренняя ошибка сервера: {error}")
    return "Внутренняя ошибка сервера", 500

@app.errorhandler(404)
def not_found(error):
    return "Страница не найдена", 404

if __name__ == '__main__':
    try:
        init_database()
        logger.info(f"Сервер запущено. Админ-панель доступна по адресу http://127.0.0.1:{HOST_PORT}")
        print(f"Сервер запущено. Админ-панель доступна за адресою http://127.0.0.1:{HOST_PORT}")
        app.run(host=HOST_IP, port=HOST_PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске сервера: {e}")
        print(f"Критична помилка при запуску сервера: {e}")
