from flask import Flask, jsonify, request, session, send_from_directory, render_template
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime
import csv
import io
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')

app = Flask(
    __name__,
    static_folder=None,
    template_folder=FRONTEND_DIR
)

app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')
CORS(app, supports_credentials=True)

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'work_tracking_db')
}


def db():
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=(), fetch=True, many=False):
    conn = None
    cur = None

    try:
        conn = db()
        cur = conn.cursor(dictionary=True)

        if many:
            cur.executemany(sql, params)
        else:
            cur.execute(sql, params)

        rows = cur.fetchall() if fetch else []

        conn.commit()

        return rows

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()


def ensure_default_admin():
    try:
        rows = query(
            'SELECT id FROM users WHERE username=%s LIMIT 1',
            ('admin',)
        )

        if not rows:
            query(
                '''
                INSERT INTO users
                (
                    full_name,
                    username,
                    email,
                    password_hash,
                    role,
                    phone,
                    department,
                    address
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (
                    'Jay Maruti Magdum',
                    'admin',
                    'admin@worktrack.com',
                    generate_password_hash('admin123'),
                    'Administrator',
                    '98765 00000',
                    'Administration',
                    'Small Manufacturing Unit'
                ),
                fetch=False
            )

    except Exception:
        pass


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):

        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Please login first.'
            }), 401

        return fn(*args, **kwargs)

    return wrapper


def clean(row):
    if not row:
        return row

    for key, value in list(row.items()):

        if isinstance(value, (date, datetime)):
            row[key] = value.isoformat()

    return row


# ---------- Frontend ----------

@app.route('/production')
@app.route('/production.html')
def production_page():
    return render_template('production.html')


@app.route('/')
def home():
    return send_from_directory(
        FRONTEND_DIR,
        'index.html'
    )


@app.route('/<path:path>')
def frontend(path):

    full = os.path.join(
        FRONTEND_DIR,
        path
    )

    if os.path.isfile(full):
        directory, filename = os.path.split(full)

        return send_from_directory(
            directory,
            filename
        )

    return send_from_directory(
        FRONTEND_DIR,
        'index.html'
    )


# ---------- Auth ----------

@app.post('/api/login')
def login():

    data = request.get_json(silent=True) or {}

    username = (
        data.get('username') or
        data.get('email') or
        ''
    ).strip()

    password = data.get('password') or ''

    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username and password are required.'
        }), 400

    rows = query(
        '''
        SELECT
            id,
            full_name,
            username,
            email,
            password_hash,
            role,
            phone,
            department,
            address
        FROM users
        WHERE username=%s OR email=%s
        LIMIT 1
        ''',
        (username, username)
    )

    if not rows or not check_password_hash(
        rows[0]['password_hash'],
        password
    ):
        return jsonify({
            'success': False,
            'message': 'Invalid username or password.'
        }), 401

    user = rows[0]

    session['user_id'] = user['id']
    session['user_name'] = user['full_name']
    session['role'] = user['role']

    user.pop('password_hash', None)

    return jsonify({
        'success': True,
        'user': clean(user)
    })


@app.post('/api/logout')
def logout():

    session.clear()

    return jsonify({
        'success': True,
        'message': 'Logged out successfully.'
    })


@app.post('/api/forgot-password')
def forgot_password():

    data = request.get_json(silent=True) or {}

    email = str(data.get('email', '')).strip()
    phone = str(data.get('phone', '')).strip()
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not email:
        return jsonify({
            'success': False,
            'message': 'Email is required.'
        }), 400

    if not phone:
        return jsonify({
            'success': False,
            'message': 'Phone number is required.'
        }), 400

    if not new_password:
        return jsonify({
            'success': False,
            'message': 'New password is required.'
        }), 400

    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'message': 'New password must be at least 6 characters.'
        }), 400

    if new_password != confirm_password:
        return jsonify({
            'success': False,
            'message': 'Passwords do not match.'
        }), 400

    try:

        rows = query(
            '''
            SELECT id
            FROM users
            WHERE email=%s
              AND phone=%s
            LIMIT 1
            ''',
            (
                email,
                phone
            )
        )

        if not rows:
            return jsonify({
                'success': False,
                'message': 'Email and phone number do not match our records.'
            }), 400

        password_hash = generate_password_hash(
            new_password
        )

        query(
            '''
            UPDATE users
            SET password_hash=%s
            WHERE id=%s
            ''',
            (
                password_hash,
                rows[0]['id']
            ),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Password reset successfully. You can now login.'
        })

    except Error as e:

        print(
            'FORGOT PASSWORD ERROR:',
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.get('/api/me')
@login_required
def me():

    rows = query(
        '''
        SELECT
            id,
            full_name,
            username,
            email,
            role,
            phone,
            department,
            address
        FROM users
        WHERE id=%s
        ''',
        (session['user_id'],)
    )

    return jsonify({
        'success': True,
        'user': clean(rows[0]) if rows else None
    })


# ---------- Employees ----------

@app.get('/api/employees')
@login_required
def employees():

    rows = query(
        '''
        SELECT
            id,
            employee_code,
            full_name,
            email,
            department,
            role,
            phone,
            status
        FROM employees
        ORDER BY id DESC
        '''
    )

    return jsonify({
        'success': True,
        'data': rows
    })


@app.post('/api/employees')
@login_required
def add_employee():

    data = request.get_json(silent=True) or {}

    required = [
        'full_name',
        'employee_code',
        'department',
        'role',
        'phone'
    ]

    if any(
        not str(data.get(field, '')).strip()
        for field in required
    ):
        return jsonify({
            'success': False,
            'message': 'All employee fields are required.'
        }), 400

    try:

        query(
            '''
            INSERT INTO employees
            (
                employee_code,
                full_name,
                email,
                department,
                role,
                phone,
                status
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            ''',
            (
                data['employee_code'],
                data['full_name'],
                data.get('email'),
                data['department'],
                data['role'],
                data['phone'],
                data.get('status', 'Active')
            ),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Employee added successfully.'
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.put('/api/employees/<int:eid>')
@login_required
def edit_employee(eid):

    data = request.get_json(silent=True) or {}

    query(
        '''
        UPDATE employees
        SET
            employee_code=%s,
            full_name=%s,
            email=%s,
            department=%s,
            role=%s,
            phone=%s,
            status=%s
        WHERE id=%s
        ''',
        (
            data.get('employee_code'),
            data.get('full_name'),
            data.get('email'),
            data.get('department'),
            data.get('role'),
            data.get('phone'),
            data.get('status', 'Active'),
            eid
        ),
        fetch=False
    )

    return jsonify({
        'success': True,
        'message': 'Employee updated.'
    })


@app.delete('/api/employees/<int:eid>')
@login_required
def delete_employee(eid):

    query(
        'DELETE FROM employees WHERE id=%s',
        (eid,),
        fetch=False
    )

    return jsonify({
        'success': True,
        'message': 'Employee deleted.'
    })


# ---------- Employee Import ----------

@app.post('/api/employees/import')
@login_required
def import_employees():

    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': 'CSV file is required.'
        }), 400

    file = request.files['file']

    if not file.filename:
        return jsonify({
            'success': False,
            'message': 'Please select a CSV file.'
        }), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({
            'success': False,
            'message': 'Only CSV files are supported.'
        }), 400

    try:

        content = file.read().decode('utf-8-sig')

        reader = csv.DictReader(
            io.StringIO(content)
        )

        required_columns = [
            'employee_code',
            'full_name',
            'email',
            'department',
            'role',
            'phone',
            'status'
        ]

        if not reader.fieldnames:
            return jsonify({
                'success': False,
                'message': 'CSV file has no headers.'
            }), 400

        headers = [
            str(value).strip().lower()
            for value in reader.fieldnames
        ]

        missing = [
            column
            for column in required_columns
            if column not in headers
        ]

        if missing:
            return jsonify({
                'success': False,
                'message':
                    'Missing CSV columns: ' +
                    ', '.join(missing)
            }), 400

        departments = query(
            '''
            SELECT name
            FROM departments
            '''
        )

        department_names = {
            row['name']
            for row in departments
        }

        imported = 0
        skipped = 0
        errors = []

        for row_number, raw_row in enumerate(
            reader,
            start=2
        ):

            row = {
                str(key).strip().lower():
                (value or '').strip()
                for key, value in raw_row.items()
                if key is not None
            }

            employee_code = row.get(
                'employee_code',
                ''
            )

            full_name = row.get(
                'full_name',
                ''
            )

            email = row.get(
                'email',
                ''
            )

            department = row.get(
                'department',
                ''
            )

            role = row.get(
                'role',
                ''
            )

            phone = row.get(
                'phone',
                ''
            )

            status = row.get(
                'status',
                'Active'
            ) or 'Active'

            if not all([
                employee_code,
                full_name,
                department,
                role,
                phone
            ]):

                errors.append(
                    f'Row {row_number}: Required field missing.'
                )

                skipped += 1
                continue

            if department not in department_names:

                errors.append(
                    f'Row {row_number}: Department '
                    f'"{department}" does not exist.'
                )

                skipped += 1
                continue

            existing = query(
                '''
                SELECT id
                FROM employees
                WHERE employee_code=%s
                LIMIT 1
                ''',
                (employee_code,)
            )

            if existing:

                errors.append(
                    f'Row {row_number}: Employee ID '
                    f'"{employee_code}" already exists.'
                )

                skipped += 1
                continue

            try:

                query(
                    '''
                    INSERT INTO employees
                    (
                        employee_code,
                        full_name,
                        email,
                        department,
                        role,
                        phone,
                        status
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ''',
                    (
                        employee_code,
                        full_name,
                        email or None,
                        department,
                        role,
                        phone,
                        status
                    ),
                    fetch=False
                )

                imported += 1

            except Error as e:

                errors.append(
                    f'Row {row_number}: {str(e)}'
                )

                skipped += 1

        message = (
            f'{imported} employee(s) imported successfully.'
        )

        if skipped:
            message += (
                f' {skipped} row(s) skipped.'
            )

        return jsonify({
            'success': True,
            'message': message,
            'imported': imported,
            'skipped': skipped,
            'errors': errors
        })

    except UnicodeDecodeError:

        return jsonify({
            'success': False,
            'message':
                'Unable to read CSV file. '
                'Please save it as UTF-8 CSV.'
        }), 400

    except Exception as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Departments ----------

@app.get('/api/departments')
@login_required
def departments():

    rows = query(
        '''
        SELECT
            d.id,
            d.name,
            d.description,
            COUNT(e.id) AS employee_count
        FROM departments d
        LEFT JOIN employees e
            ON e.department=d.name
        GROUP BY
            d.id,
            d.name,
            d.description
        ORDER BY d.id
        '''
    )

    return jsonify({
        'success': True,
        'data': rows
    })


@app.post('/api/departments')
@login_required
def add_department():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get('name', '')
    ).strip()

    description = str(
        data.get('description', '')
    ).strip()

    if not name:
        return jsonify({
            'success': False,
            'message': 'Department name is required.'
        }), 400

    try:

        query(
            '''
            INSERT INTO departments
            (name, description)
            VALUES(%s,%s)
            ''',
            (
                name,
                description
            ),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Department added successfully.'
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.put('/api/departments/<int:did>')
@login_required
def update_department(did):

    data = request.get_json(silent=True) or {}

    name = str(
        data.get('name', '')
    ).strip()

    description = str(
        data.get('description', '')
    ).strip()

    if not name:
        return jsonify({
            'success': False,
            'message': 'Department name is required.'
        }), 400

    try:

        old_rows = query(
            '''
            SELECT name
            FROM departments
            WHERE id=%s
            ''',
            (did,)
        )

        if not old_rows:
            return jsonify({
                'success': False,
                'message': 'Department not found.'
            }), 404

        old_name = old_rows[0]['name']

        query(
            '''
            UPDATE departments
            SET
                name=%s,
                description=%s
            WHERE id=%s
            ''',
            (
                name,
                description,
                did
            ),
            fetch=False
        )

        if old_name != name:

            query(
                '''
                UPDATE employees
                SET department=%s
                WHERE department=%s
                ''',
                (
                    name,
                    old_name
                ),
                fetch=False
            )

            query(
                '''
                UPDATE work_assignments
                SET department=%s
                WHERE department=%s
                ''',
                (
                    name,
                    old_name
                ),
                fetch=False
            )

        return jsonify({
            'success': True,
            'message': 'Department updated successfully.'
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.delete('/api/departments/<int:did>')
@login_required
def delete_department(did):

    try:

        rows = query(
            '''
            SELECT
                d.name,
                COUNT(e.id) AS employee_count
            FROM departments d
            LEFT JOIN employees e
                ON e.department=d.name
            WHERE d.id=%s
            GROUP BY d.id,d.name
            ''',
            (did,)
        )

        if not rows:
            return jsonify({
                'success': False,
                'message': 'Department not found.'
            }), 404

        if rows[0]['employee_count'] > 0:
            return jsonify({
                'success': False,
                'message':
                    'This department cannot be deleted because employees are assigned to it.'
            }), 400

        query(
            '''
            DELETE FROM departments
            WHERE id=%s
            ''',
            (did,),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Department deleted successfully.'
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Work ----------

@app.get('/api/work')
@login_required
def work():

    rows = query(
        '''
        SELECT
            w.id,
            w.title,
            w.description,
            w.remark,
            e.full_name employee,
            w.employee_id,
            w.department,
            w.deadline,
            w.priority,
            w.status,
            w.progress
        FROM work_assignments w
        LEFT JOIN employees e
            ON e.id=w.employee_id
        ORDER BY w.id DESC
        '''
    )

    return jsonify({
        'success': True,
        'data': [clean(x) for x in rows]
    })


@app.post('/api/work')
@login_required
def add_work():

    data = request.get_json(silent=True) or {}

    if not data.get('title') or not data.get('employee_id'):
        return jsonify({
            'success': False,
            'message': 'Title and employee are required.'
        }), 400

    try:

        query(
            '''
            INSERT INTO work_assignments
            (
                title,
                description,
                remark,
                employee_id,
                department,
                deadline,
                priority,
                status
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            ''',
            (
                data['title'],
                data.get('description', ''),
                data.get('remark', ''),
                data['employee_id'],
                data.get('department'),
                data.get('deadline'),
                data.get('priority', 'Medium'),
                data.get('status', 'Pending')
            ),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Work assigned successfully.'
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.put('/api/work/<int:wid>')
@login_required
def update_work(wid):

    data = request.get_json(silent=True) or {}

    try:

        query(
            '''
            UPDATE work_assignments
            SET
                title=%s,
                description=%s,
                remark=%s,
                employee_id=%s,
                department=%s,
                deadline=%s,
                priority=%s,
                status=%s,
                progress=%s
            WHERE id=%s
            ''',
            (
                data.get('title'),
                data.get('description', ''),
                data.get('remark', ''),
                data.get('employee_id'),
                data.get('department'),
                data.get('deadline'),
                data.get('priority', 'Medium'),
                data.get('status', 'Pending'),
                data.get('progress', 0),
                wid
            ),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Work assignment updated successfully.'
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.delete('/api/work/<int:wid>')
@login_required
def delete_work(wid):

    try:

        query(
            'DELETE FROM work_assignments WHERE id=%s',
            (wid,),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Work assignment deleted successfully.'
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Progress ----------

@app.get('/api/progress')
@login_required
def progress():

    rows = query(
        '''
        SELECT
            w.id,
            w.title,
            e.full_name employee,
            w.department,
            w.progress,
            w.status,
            w.deadline
        FROM work_assignments w
        LEFT JOIN employees e
            ON e.id=w.employee_id
        ORDER BY w.id DESC
        '''
    )

    return jsonify({
        'success': True,
        'data': [clean(x) for x in rows]
    })


@app.put('/api/progress/<int:wid>')
@login_required
def update_progress(wid):

    data = request.get_json(silent=True) or {}

    try:
        progress_value = int(
            data.get('progress', 0)
        )

    except (TypeError, ValueError):

        return jsonify({
            'success': False,
            'message': 'Progress must be a number.'
        }), 400

    if progress_value < 0 or progress_value > 100:

        return jsonify({
            'success': False,
            'message': 'Progress must be between 0 and 100.'
        }), 400

    if progress_value == 100:
        status = 'Completed'

    elif progress_value > 0:
        status = 'In Progress'

    else:
        status = 'Pending'

    try:

        rows = query(
            '''
            SELECT id
            FROM work_assignments
            WHERE id=%s
            ''',
            (wid,)
        )

        if not rows:
            return jsonify({
                'success': False,
                'message': 'Work assignment not found.'
            }), 404

        query(
            '''
            UPDATE work_assignments
            SET
                progress=%s,
                status=%s
            WHERE id=%s
            ''',
            (
                progress_value,
                status,
                wid
            ),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Progress updated successfully.',
            'progress': progress_value,
            'status': status
        })

    except Error as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Attendance ----------

@app.get('/api/attendance')
@login_required
def attendance():

    attendance_date = request.args.get(
        'date',
        date.today().isoformat()
    )

    try:

        rows = query(
            '''
            SELECT
                a.id,
                a.attendance_date,
                a.employee_id,
                e.full_name AS employee,
                e.department,
                a.check_in,
                a.check_out,
                a.status
            FROM attendance AS a
            INNER JOIN employees AS e
                ON e.id = a.employee_id
            WHERE a.attendance_date = %s
            ORDER BY e.full_name ASC
            ''',
            (attendance_date,)
        )

        data = []

        for row in rows:

            row = clean(row)

            if row.get('check_in') is not None:
                row['check_in'] = str(row['check_in'])

            if row.get('check_out') is not None:
                row['check_out'] = str(row['check_out'])

            data.append(row)

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:

        print(
            "ATTENDANCE GET ERROR:",
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.post('/api/attendance')
@login_required
def mark_attendance():

    data = request.get_json(silent=True) or {}

    employee_id = data.get('employee_id')

    attendance_date = (
        data.get('attendance_date')
        or date.today().isoformat()
    )

    check_in = data.get('check_in') or None

    check_out = data.get('check_out') or None

    status = data.get('status') or 'Present'

    if not employee_id:

        return jsonify({
            'success': False,
            'message': 'Employee is required.'
        }), 400

    if not attendance_date:

        return jsonify({
            'success': False,
            'message': 'Attendance date is required.'
        }), 400

    try:

        employee_rows = query(
            '''
            SELECT id
            FROM employees
            WHERE id = %s
            LIMIT 1
            ''',
            (employee_id,)
        )

        if not employee_rows:

            return jsonify({
                'success': False,
                'message': 'Selected employee does not exist.'
            }), 400

        existing_rows = query(
            '''
            SELECT id
            FROM attendance
            WHERE attendance_date = %s
              AND employee_id = %s
            LIMIT 1
            ''',
            (
                attendance_date,
                employee_id
            )
        )

        if existing_rows:

            query(
                '''
                UPDATE attendance
                SET
                    check_in = %s,
                    check_out = %s,
                    status = %s
                WHERE id = %s
                ''',
                (
                    check_in,
                    check_out,
                    status,
                    existing_rows[0]['id']
                ),
                fetch=False
            )

            message = 'Attendance updated successfully.'

        else:

            query(
                '''
                INSERT INTO attendance
                (
                    attendance_date,
                    employee_id,
                    check_in,
                    check_out,
                    status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                ''',
                (
                    attendance_date,
                    employee_id,
                    check_in,
                    check_out,
                    status
                ),
                fetch=False
            )

            message = 'Attendance marked successfully.'

        return jsonify({
            'success': True,
            'message': message
        })

    except Exception as e:

        print(
            "ATTENDANCE POST ERROR:",
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.delete('/api/attendance/<int:attendance_id>')
@login_required
def delete_attendance(attendance_id):

    try:

        rows = query(
            '''
            SELECT id
            FROM attendance
            WHERE id = %s
            LIMIT 1
            ''',
            (attendance_id,)
        )

        if not rows:

            return jsonify({
                'success': False,
                'message': 'Attendance record not found.'
            }), 404

        query(
            '''
            DELETE FROM attendance
            WHERE id = %s
            ''',
            (attendance_id,),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Attendance deleted successfully.'
        })

    except Exception as e:

        print(
            'ATTENDANCE DELETE ERROR:',
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Production ----------

@app.get('/api/production')
@login_required
def production():

    rows = query(
        '''
        SELECT
            id,
            production_date,
            product,
            department,
            quantity,
            good_units,
            defective,
            status
        FROM production
        ORDER BY production_date DESC, id DESC
        '''
    )

    return jsonify({
        'success': True,
        'data': [clean(x) for x in rows]
    })


@app.post('/api/production')
@login_required
def add_production():

    data = request.get_json(silent=True) or {}

    if (
        not data.get('product')
        or data.get('quantity') is None
    ):

        return jsonify({
            'success': False,
            'message': 'Product and quantity are required.'
        }), 400

    query(
        '''
        INSERT INTO production
        (
            production_date,
            product,
            department,
            quantity,
            good_units,
            defective,
            status
        )
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        ''',
        (
            data.get(
                'production_date',
                date.today().isoformat()
            ),
            data['product'],
            data.get(
                'department',
                'Production'
            ),
            int(data['quantity']),
            int(
                data.get(
                    'good_units',
                    data['quantity']
                )
            ),
            int(
                data.get(
                    'defective',
                    0
                )
            ),
            data.get(
                'status',
                'Completed'
            )
        ),
        fetch=False
    )

    return jsonify({
        'success': True,
        'message': 'Production record added.'
    })


@app.delete('/api/production/<int:production_id>')
@login_required
def delete_production(production_id):

    try:

        existing = query(
            '''
            SELECT id
            FROM production
            WHERE id = %s
            LIMIT 1
            ''',
            (production_id,)
        )

        if not existing:
            return jsonify({
                'success': False,
                'message': 'Production record not found.'
            }), 404

        query(
            '''
            DELETE FROM production
            WHERE id = %s
            ''',
            (production_id,),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Production record deleted successfully.'
        })

    except Exception as e:

        print(
            'PRODUCTION DELETE ERROR:',
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Dashboard / Reports ----------

@app.get('/api/dashboard')
@login_required
def dashboard():

    total = query(
        'SELECT COUNT(*) c FROM employees'
    )[0]['c']

    present = query(
        '''
        SELECT COUNT(*) c
        FROM attendance
        WHERE attendance_date=%s
        AND status IN ('Present','Late')
        ''',
        (date.today().isoformat(),)
    )[0]['c']

    active = query(
        '''
        SELECT COUNT(*) c
        FROM work_assignments
        WHERE status='In Progress'
        '''
    )[0]['c']

    output = query(
        '''
        SELECT COALESCE(SUM(quantity),0) total
        FROM production
        WHERE production_date=%s
        ''',
        (date.today().isoformat(),)
    )[0]['total']

    return jsonify({
        'success': True,
        'data': {
            'employees': total,
            'present': present,
            'active_work': active,
            'today_output': output
        }
    })


@app.get('/api/reports')
@login_required
def reports():

    report_type = request.args.get(
        'type',
        'production'
    )

    start = request.args.get('from')
    end = request.args.get('to')

    try:

        if report_type == 'attendance':

            sql = '''
                SELECT
                    a.attendance_date,
                    e.employee_code,
                    e.full_name,
                    e.department,
                    a.check_in,
                    a.check_out,
                    a.status
                FROM attendance a
                JOIN employees e
                    ON e.id = a.employee_id
                WHERE a.attendance_date
                    BETWEEN COALESCE(%s, a.attendance_date)
                    AND COALESCE(%s, a.attendance_date)
                ORDER BY a.attendance_date DESC
            '''

            params = (start, end)

        elif report_type == 'work':

            sql = '''
                SELECT
                    w.title,
                    e.full_name AS employee,
                    w.department,
                    w.deadline,
                    w.priority,
                    w.status,
                    w.progress
                FROM work_assignments w
                LEFT JOIN employees e
                    ON e.id = w.employee_id
                ORDER BY w.id DESC
            '''

            params = ()

        elif report_type == 'employee':

            sql = '''
                SELECT
                    employee_code,
                    full_name,
                    email,
                    department,
                    role,
                    phone,
                    status
                FROM employees
                ORDER BY id
            '''

            params = ()

        else:

            sql = '''
                SELECT
                    production_date,
                    product,
                    department,
                    quantity,
                    good_units,
                    defective,
                    status
                FROM production
                WHERE production_date
                    BETWEEN COALESCE(%s, production_date)
                    AND COALESCE(%s, production_date)
                ORDER BY production_date DESC
            '''

            params = (start, end)

        rows = query(
            sql,
            params
        )

        data = []

        for row in rows:

            row = clean(row)

            if report_type == 'attendance':

                if row.get('check_in') is not None:
                    row['check_in'] = str(
                        row['check_in']
                    )

                if row.get('check_out') is not None:
                    row['check_out'] = str(
                        row['check_out']
                    )

            data.append(row)

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:

        print(
            'REPORT ERROR:',
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Profile ----------

@app.get('/api/profile')
@login_required
def profile():

    rows = query(
        '''
        SELECT
            id,
            full_name,
            username,
            email,
            role,
            phone,
            department,
            address
        FROM users
        WHERE id=%s
        LIMIT 1
        ''',
        (session['user_id'],)
    )

    if not rows:
        return jsonify({
            'success': False,
            'message': 'Profile not found.'
        }), 404

    return jsonify({
        'success': True,
        'user': clean(rows[0])
    })


@app.put('/api/profile')
@login_required
def update_profile():

    data = request.get_json(silent=True) or {}

    full_name = str(
        data.get('full_name', '')
    ).strip()

    email = str(
        data.get('email', '')
    ).strip()

    phone = str(
        data.get('phone', '')
    ).strip()

    address = str(
        data.get('address', '')
    ).strip()

    if not full_name:
        return jsonify({
            'success': False,
            'message': 'Full name is required.'
        }), 400

    if not email:
        return jsonify({
            'success': False,
            'message': 'Email is required.'
        }), 400

    if '@' not in email:
        return jsonify({
            'success': False,
            'message': 'Enter a valid email address.'
        }), 400

    try:

        existing = query(
            '''
            SELECT id
            FROM users
            WHERE email=%s
              AND id<>%s
            LIMIT 1
            ''',
            (
                email,
                session['user_id']
            )
        )

        if existing:
            return jsonify({
                'success': False,
                'message': 'This email is already in use.'
            }), 400

        query(
            '''
            UPDATE users
            SET
                full_name=%s,
                email=%s,
                phone=%s,
                address=%s
            WHERE id=%s
            ''',
            (
                full_name,
                email,
                phone,
                address,
                session['user_id']
            ),
            fetch=False
        )

        session['user_name'] = full_name

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully.'
        })

    except Error as e:

        print(
            'PROFILE UPDATE ERROR:',
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@app.put('/api/profile/password')
@login_required
def change_password():

    data = request.get_json(silent=True) or {}

    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not current_password:
        return jsonify({
            'success': False,
            'message': 'Current password is required.'
        }), 400

    if not new_password:
        return jsonify({
            'success': False,
            'message': 'New password is required.'
        }), 400

    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'message': 'New password must be at least 6 characters.'
        }), 400

    if new_password != confirm_password:
        return jsonify({
            'success': False,
            'message': 'New password and confirm password do not match.'
        }), 400

    try:

        rows = query(
            '''
            SELECT password_hash
            FROM users
            WHERE id=%s
            LIMIT 1
            ''',
            (session['user_id'],)
        )

        if not rows:
            return jsonify({
                'success': False,
                'message': 'User account not found.'
            }), 404

        if not check_password_hash(
            rows[0]['password_hash'],
            current_password
        ):
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect.'
            }), 400

        new_password_hash = generate_password_hash(
            new_password
        )

        query(
            '''
            UPDATE users
            SET password_hash=%s
            WHERE id=%s
            ''',
            (
                new_password_hash,
                session['user_id']
            ),
            fetch=False
        )

        return jsonify({
            'success': True,
            'message': 'Password changed successfully.'
        })

    except Error as e:

        print(
            'PASSWORD CHANGE ERROR:',
            repr(e)
        )

        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ---------- Health ----------

@app.get('/api/health')
def health():

    try:

        query(
            'SELECT 1',
            fetch=True
        )

        return jsonify({
            'success': True,
            'message':
                'WorkTrack backend and MySQL are connected.'
        })

    except Exception as e:

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


if __name__ == '__main__':

    ensure_default_admin()

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )