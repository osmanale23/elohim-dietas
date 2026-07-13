"""
Sistema de Dietas — Centro Médico Elohim
Gestión de alimentación para pacientes internados (Piso 5, Piso 6, UCI)
"""

import os
import json
import sqlite3
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dieta-elohim-2025')
DB_PATH = os.environ.get('DIETA_DB', 'dieta.db')

PASSWORDS = {
    'piso5':       os.environ.get('PASS_PISO5',  'Piso5Elohim'),
    'piso6':       os.environ.get('PASS_PISO6',  'Piso6Elohim'),
    'uci':         os.environ.get('PASS_UCI',    'UCIElohim'),
    'emergencia':  os.environ.get('PASS_EMG',    'EmergenciaElohim'),
    'ucin':        os.environ.get('PASS_UCIN',   'UCINElohim'),
    'cafeteria':   os.environ.get('PASS_CAF',    'CafetElohim'),
    'gerencia':    os.environ.get('PASS_GER',    'GerenciaElohim'),
}

ROLE_NAMES = {
    'piso5':      'Enfermería — Piso 5',
    'piso6':      'Enfermería — Piso 6',
    'uci':        'Enfermería — UCI',
    'emergencia': 'Enfermería — Emergencia',
    'ucin':       'Enfermería — UCIN',
    'cafeteria':  'Cafetería',
    'gerencia':   'Gerencia',
}

FLOOR_LABEL = {
    'piso5':      'Piso 5',
    'piso6':      'Piso 6',
    'uci':        'UCI',
    'emergencia': 'Emergencia',
    'ucin':       'UCIN',
}

NURSES = [
    'YUSMARI LOPEZ',
    'ADALGISA CONCEPCION',
    'KENIA MOORE',
    'SALDYS BENIGNO',
    'ALEXANDER MEJIA',
    'NOEMI GOMEZ',
    'IRIS ABAD',
    'EDITH EVANGELISTA',
    'MILENA FREITES',
    'DECENA DOMINGA',
    'BONIFACIA BELTRAN',
    'KATERIN MEDINA',
    'NARDELIS RODRIGUEZ',
]

DIET_OPTIONS = {
    'corriente': {
        'desayuno': [
            'Avena cocida en leche descremada (250ml)',
            '2 huevos hervidos o revueltos',
            '2 rebanadas de pan integral',
            'Porción de fruta blanda (lechosa, sandía, melón o guineo)',
            'Té o café',
        ],
        'almuerzo': [
            'Sopa de vegetales con pollo',
            '1 taza de arroz blanco o integral / Trigo',
            'Pechuga de pollo a la plancha (120-150g)',
            'Vegetales cocidos (zanahoria, auyama, brócoli, coliflor, repollo)',
            'Ensalada fresca según tolerancia',
            'Jugo natural sin azúcar añadida',
        ],
        'cena': [
            'Pescado al horno o pollo desmenuzado (120g)',
            'Puré de papa / yautía / batata / plátano maduro',
            'Vegetales cocidos',
            'Huevo hervido (alternativa proteica)',
            'Queso mozzarella o Gouda (alternativa proteica)',
        ],
    },
    'blanda': {
        'desayuno': [
            'Avena cocida en leche descremada (250ml)',
            '2 huevos hervidos o revueltos',
            'Porción de fruta blanda (lechosa, melón, guineo, sandía)',
            'Té o café según tolerancia',
            'Yogurt griego',
        ],
        'almuerzo': [
            'Vegetales cocidos (zanahoria, brócoli, auyama, coliflor)',
            'Ensalada fresca según tolerancia',
            'Puré de papa / yautía / auyama / plátano maduro',
            'Pollo desmenuzado (150-200g)',
            'Sopas licuadas',
        ],
        'cena': [
            'Pescado al horno o pollo desmenuzado (120g)',
            'Puré de papa / yautía / batata / plátano maduro',
            'Vegetales cocidos blandos',
            'Sopa de vegetales',
            'Huevo hervido (alternativa proteica)',
            'Queso mozzarella o Gouda (alternativa proteica)',
        ],
    },
    'liquida': {
        'desayuno': [
            'Avena licuada en leche descremada',
            'Jugo natural sin azúcar añadida',
            'Té o infusión sin azúcar',
            'Caldo de pollo liviano',
        ],
        'almuerzo': [
            'Sopa licuada de vegetales con pollo',
            'Caldo de pollo o res desgrasado',
            'Jugo natural sin azúcar',
            'Gelatina sin azúcar',
        ],
        'cena': [
            'Sopa licuada de vegetales',
            'Caldo desgrasado',
            'Jugo natural sin azúcar',
            'Infusión / té sin azúcar',
        ],
    },
}

CONDITION_NOTES = {
    'normal':      None,
    'diabetico':   'Sin azúcar refinada · Frutas bajo índice glucémico · Carbohidratos en porciones controladas · NO jugos azucarados · Proteína en cada comida',
    'renal':       'Limitar potasio y fósforo · Proteínas controladas · Evitar exceso de lácteos · Sin sal añadida',
    'disfagia':    'Consistencia licuada o puré · Evitar sólidos duros · Espesar líquidos según indicación médica',
    'cardiopatia': 'Bajo sodio · Bajo en grasa saturada · Sin sal añadida · Evitar fritos y embutidos',
}

CONDITION_LABEL = {
    'normal':      'Normal',
    'diabetico':   'Diabético',
    'renal':       'Insuf. Renal',
    'disfagia':    'Disfagia',
    'cardiopatia': 'Cardiopatía',
}

MEAL_TIMES = [
    ('desayuno', 'Desayuno', '7:30 AM'),
    ('almuerzo', 'Almuerzo', '12:30 PM'),
    ('cena',     'Cena',     '6:30 PM'),
]


# ─── DATABASE ───────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS patients (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            floor         TEXT NOT NULL,
            room          TEXT NOT NULL,
            diet_type     TEXT NOT NULL DEFAULT 'corriente',
            condition     TEXT NOT NULL DEFAULT 'normal',
            edad          INTEGER,
            sexo          TEXT DEFAULT 'masculino',
            notes         TEXT DEFAULT '',
            active        INTEGER DEFAULT 1,
            registered_by TEXT,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS meal_orders (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            order_date       TEXT NOT NULL,
            meal_date        TEXT,
            meal_time        TEXT NOT NULL,
            options_selected TEXT DEFAULT '[]',
            confirmed        INTEGER DEFAULT 0,
            confirmed_by     TEXT,
            confirmed_at     TEXT,
            extra_notes      TEXT DEFAULT '',
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
    ''')
    conn.commit()
    # Migraciones: agregar columnas nuevas si no existen
    for col, defn in [('edad', 'INTEGER'), ('sexo', "TEXT DEFAULT 'masculino'")]:
        try:
            conn.execute(f'ALTER TABLE patients ADD COLUMN {col} {defn}')
            conn.commit()
        except Exception:
            pass
    try:
        conn.execute('ALTER TABLE meal_orders ADD COLUMN meal_date TEXT')
        conn.commit()
    except Exception:
        pass
    conn.close()


# ─── AUTH ────────────────────────────────────────────────────────────────────
@app.route('/', methods=['GET'])
def root():
    return redirect(url_for('dieta_login'))


@app.route('/login', methods=['GET', 'POST'])
def dieta_login():
    error = None
    if request.method == 'POST':
        pwd = request.form.get('password', '').strip()
        for role, secret in PASSWORDS.items():
            if pwd == secret:
                session['dieta_role'] = role
                if role == 'cafeteria':
                    return redirect(url_for('dieta_cafeteria'))
                elif role == 'gerencia':
                    return redirect(url_for('dieta_gerencia'))
                else:
                    return redirect(url_for('dieta_nurse'))
        error = 'Contraseña incorrecta'
    return render_template('dieta_login.html', error=error)


@app.route('/logout')
def dieta_logout():
    session.pop('dieta_role', None)
    return redirect(url_for('dieta_login'))


NURSE_ROLES = ('piso5', 'piso6', 'uci', 'emergencia', 'ucin')

def nurse_required():
    role = session.get('dieta_role')
    if role not in NURSE_ROLES:
        return redirect(url_for('dieta_login'))
    return None


# ─── NURSE VIEW ───────────────────────────────────────────────────────────────
@app.route('/api/nurse/select', methods=['POST'])
def select_nurse():
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'error': 'invalid'}), 400
    session['nurse_name'] = name
    return jsonify({'ok': True})


@app.route('/nurse')
def dieta_nurse():
    redir = nurse_required()
    if redir: return redir
    role = session['dieta_role']
    conn = get_db()
    patients = conn.execute(
        'SELECT * FROM patients WHERE floor=? AND active=1 ORDER BY room', (role,)
    ).fetchall()
    conn.close()
    today = date.today().strftime('%Y-%m-%d')
    return render_template('dieta_nurse.html',
                           patients=patients,
                           role=role,
                           role_name=ROLE_NAMES[role],
                           floor_label=FLOOR_LABEL[role],
                           today=today,
                           diet_options=DIET_OPTIONS,
                           condition_notes=CONDITION_NOTES,
                           condition_label=CONDITION_LABEL,
                           nurses=NURSES,
                           active_nurse=session.get('nurse_name', ''))


@app.route('/api/patient/add', methods=['POST'])
def add_patient():
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    role = session['dieta_role']
    conn = get_db()
    nurse_name = session.get('nurse_name', role)
    cur = conn.execute(
        'INSERT INTO patients (name, floor, room, diet_type, condition, edad, sexo, notes, registered_by) VALUES (?,?,?,?,?,?,?,?,?)',
        (d['name'].strip(), role, d['room'].strip(), d['diet_type'], d.get('condition', 'normal'),
         d.get('edad'), d.get('sexo', 'masculino'), d.get('notes', ''), nurse_name)
    )
    pid = cur.lastrowid
    meal_time = d.get('meal_time', 'desayuno')
    today_str = date.today().strftime('%Y-%m-%d')
    meal_date = d.get('meal_date', today_str)
    conn.execute(
        'INSERT INTO meal_orders (patient_id, order_date, meal_date, meal_time, options_selected, confirmed, extra_notes) VALUES (?,?,?,?,?,0,?)',
        (pid, today_str, meal_date, meal_time, '[]', d.get('notes', ''))
    )
    conn.commit()
    conn.close()
    # Auto-limpiar sesión de enfermera para obligar re-selección
    session.pop('nurse_name', None)
    return jsonify({'ok': True, 'id': pid})


@app.route('/api/patient/<int:pid>/update', methods=['POST'])
def update_patient(pid):
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    conn = get_db()
    conn.execute(
        'UPDATE patients SET diet_type=?, condition=?, notes=?, updated_at=? WHERE id=?',
        (d['diet_type'], d.get('condition', 'normal'), d.get('notes', ''), datetime.now().isoformat(), pid)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/patient/<int:pid>/discharge', methods=['POST'])
def discharge_patient(pid):
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    conn = get_db()
    conn.execute('UPDATE patients SET active=0, updated_at=? WHERE id=?', (datetime.now().isoformat(), pid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── CAFETERÍA VIEW ──────────────────────────────────────────────────────────
@app.route('/cafeteria')
def dieta_cafeteria():
    if session.get('dieta_role') != 'cafeteria':
        return redirect(url_for('dieta_login'))
    today = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    conn = get_db()
    patients = conn.execute(
        'SELECT * FROM patients WHERE active=1 ORDER BY floor, room'
    ).fetchall()
    orders = conn.execute(
        'SELECT * FROM meal_orders WHERE order_date=?', (today,)
    ).fetchall()
    conn.close()
    orders_map = {(o['patient_id'], o['meal_time']): dict(o) for o in orders}
    return render_template('dieta_cafeteria.html',
                           patients=patients,
                           orders_map=orders_map,
                           today=today,
                           meal_times=MEAL_TIMES,
                           diet_options=DIET_OPTIONS,
                           condition_notes=CONDITION_NOTES,
                           condition_label=CONDITION_LABEL,
                           floor_label=FLOOR_LABEL)


@app.route('/api/order/save', methods=['POST'])
def save_order():
    if session.get('dieta_role') != 'cafeteria':
        return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    now = datetime.now().isoformat()
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM meal_orders WHERE patient_id=? AND order_date=? AND meal_time=?',
        (d['patient_id'], d['date'], d['meal_time'])
    ).fetchone()
    if existing:
        conn.execute(
            'UPDATE meal_orders SET options_selected=?, confirmed=1, confirmed_by=?, confirmed_at=?, extra_notes=? WHERE id=?',
            (json.dumps(d['options']), 'cafeteria', now, d.get('notes', ''), existing['id'])
        )
    else:
        conn.execute(
            'INSERT INTO meal_orders (patient_id, order_date, meal_time, options_selected, confirmed, confirmed_by, confirmed_at, extra_notes) VALUES (?,?,?,?,1,?,?,?)',
            (d['patient_id'], d['date'], d['meal_time'], json.dumps(d['options']), 'cafeteria', now, d.get('notes', ''))
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── GERENCIA VIEW ────────────────────────────────────────────────────────────
@app.route('/gerencia')
def dieta_gerencia():
    if session.get('dieta_role') != 'gerencia':
        return redirect(url_for('dieta_login'))
    today = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    floor_filter = request.args.get('floor', 'all')
    conn = get_db()
    if floor_filter == 'all':
        patients = conn.execute('SELECT * FROM patients WHERE active=1 ORDER BY floor, room').fetchall()
    else:
        patients = conn.execute('SELECT * FROM patients WHERE active=1 AND floor=? ORDER BY room', (floor_filter,)).fetchall()
    orders = conn.execute('SELECT * FROM meal_orders WHERE order_date=?', (today,)).fetchall()
    # Stats
    all_active = conn.execute('SELECT COUNT(*) FROM patients WHERE active=1').fetchone()[0]
    confirmed_today = conn.execute('SELECT COUNT(*) FROM meal_orders WHERE order_date=? AND confirmed=1', (today,)).fetchone()[0]
    pending_today = (all_active * 3) - confirmed_today
    conn.close()
    orders_map = {(o['patient_id'], o['meal_time']): dict(o) for o in orders}
    return render_template('dieta_gerencia.html',
                           patients=patients,
                           orders_map=orders_map,
                           today=today,
                           floor_filter=floor_filter,
                           all_active=all_active,
                           confirmed_today=confirmed_today,
                           pending_today=max(0, pending_today),
                           meal_times=MEAL_TIMES,
                           diet_options=DIET_OPTIONS,
                           condition_notes=CONDITION_NOTES,
                           condition_label=CONDITION_LABEL,
                           floor_label=FLOOR_LABEL)


# ─── REPORTE GERENCIA ─────────────────────────────────────────────────────────
@app.route('/gerencia/reporte')
def gerencia_reporte():
    if session.get('dieta_role') != 'gerencia':
        return redirect(url_for('dieta_login'))
    today_str = date.today().strftime('%Y-%m-%d')
    inicio = request.args.get('inicio', today_str)
    fin    = request.args.get('fin',    today_str)
    conn = get_db()
    patients = conn.execute(
        "SELECT * FROM patients WHERE DATE(created_at) BETWEEN ? AND ? ORDER BY floor, created_at",
        (inicio, fin)
    ).fetchall()
    orders = conn.execute(
        '''SELECT mo.*, p.name as patient_name, p.floor, p.room, p.diet_type,
                  p.condition, p.edad, p.sexo, p.registered_by
           FROM meal_orders mo
           JOIN patients p ON mo.patient_id = p.id
           WHERE mo.order_date BETWEEN ? AND ?
           ORDER BY mo.order_date, p.floor, mo.meal_time''',
        (inicio, fin)
    ).fetchall()
    # Estadísticas
    total_pacientes = len(patients)
    total_pedidos   = len(orders)
    confirmados     = sum(1 for o in orders if o['confirmed'])
    conn.close()
    return render_template('dieta_reporte.html',
                           patients=patients,
                           orders=orders,
                           inicio=inicio,
                           fin=fin,
                           total_pacientes=total_pacientes,
                           total_pedidos=total_pedidos,
                           confirmados=confirmados,
                           now=datetime.now().strftime('%Y-%m-%d %H:%M'),
                           floor_label=FLOOR_LABEL,
                           condition_label=CONDITION_LABEL,
                           MEAL_TIMES=MEAL_TIMES)


# Inicializar DB al arrancar (gunicorn o directo)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
