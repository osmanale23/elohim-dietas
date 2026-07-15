"""
Sistema de Dietas — Centro Médico Elohim
Gestión de alimentación para pacientes internados (Piso 5, Piso 6, UCI)
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dieta-elohim-2025')

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
    'ISAUL ROMERO',
    'BELKIS PORTES',
    'EMMANUEL MORETA',
    'CRISARDI PORTOLATIN',
    'RODDYS TEJADA RODRIGUEZ',
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

# ─── MENÚS POR DÍA ──────────────────────────────────────────────────────────
DAY_NAMES = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
DAY_NAMES_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MONTH_NAMES_ES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

def today_label_es(d=None):
    d = d or date.today()
    return f"{DAY_NAMES_ES[d.weekday()]}, {d.day} de {MONTH_NAMES_ES[d.month - 1]} {d.year}"

MENU_NORMAL = {
    'lunes':     {
        'desayuno': ['Avena con galletas de soda'],
        'almuerzo': ['Pescado a la plancha con mangú y ensalada hervida'],
        'cena':     ['Quesadilla con jugo de lechosa y avena'],
    },
    'martes':    {
        'desayuno': ['Cereal y leche'],
        'almuerzo': ['Sopa de pollo con arroz'],
        'cena':     ['Sandwich con jugo de lechosa'],
    },
    'miercoles': {
        'desayuno': ['Desayuno de frutas'],
        'almuerzo': ['Trigo con pollo desmenuzado y ensalada hervida'],
        'cena':     ['Jugo de pera/piña con tortilla de huevo'],
    },
    'jueves':    {
        'desayuno': ['Avena con galletas'],
        'almuerzo': ['Carne molida con yautía'],
        'cena':     ['Sopa de pollo'],
    },
    'viernes':   {
        'desayuno': ['Maicena'],
        'almuerzo': ['Moro con pollo desmenuzado y ensalada'],
        'cena':     ['Sandwich con jugo'],
    },
    'sabado':    {
        'desayuno': ['Pan con huevo hervido y jugo de lechosa'],
        'almuerzo': ['Guineo, carne molida y ensalada verde'],
        'cena':     ['Quesadilla con jugo de piña'],
    },
    'domingo':   {
        'desayuno': ['Avena con galletas de soda'],
        'almuerzo': ['Sopa de pollo con arroz'],
        'cena':     ['Sandwich con jugo'],
    },
}

MENU_DIABETICO = {
    'lunes':     {
        'desayuno': ['Pan integral con huevo revuelto y jugo'],
        'almuerzo': ['Mangú, ensalada hervida y carne molida'],
        'cena':     ['Mangú con queso'],
    },
    'martes':    {
        'desayuno': ['Guineos y huevos hervidos'],
        'almuerzo': ['Sopa de pollo'],
        'cena':     ['Yautía con queso mozzarella'],
    },
    'miercoles': {
        'desayuno': ['Auyama y huevo revuelto'],
        'almuerzo': ['Trigo con pollo desmenuzado y ensalada'],
        'cena':     ['Guineo con huevo hervido'],
    },
    'jueves':    {
        'desayuno': ['Pan integral con huevo hervido'],
        'almuerzo': ['Guineo con pollo'],
        'cena':     ['Sopa de pollo'],
    },
    'viernes':   {
        'desayuno': ['Pan integral con jamón y jugo de lechosa'],
        'almuerzo': ['Guinéitos con pollo desmenuzado'],
        'cena':     ['Yautía y huevo hervido'],
    },
    'sabado':    {
        'desayuno': ['Pan con huevo hervido'],
        'almuerzo': ['Puré de guineo con carne molida y ensalada verde'],
        'cena':     ['Auyama con jamón y jugo de piña'],
    },
    'domingo':   {
        'desayuno': ['Guineo con jamón'],
        'almuerzo': ['Sopa de pollo con arroz'],
        'cena':     ['Quesadilla con jugo de lechosa'],
    },
}


# ─── TEMPLATE FILTERS ───────────────────────────────────────────────────────
@app.template_filter('fmt_time')
def fmt_time(value):
    """'2026-07-14T02:13:45' → '2:13 AM'"""
    if not value:
        return '—'
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value))
        return dt.strftime('%-I:%M %p')
    except Exception:
        return str(value)[11:16]

@app.template_filter('fmt_datetime')
def fmt_datetime(value):
    """'2026-07-14T02:13:45' → '2026-07-14  2:13 AM'"""
    if not value:
        return '—'
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value))
        return dt.strftime('%Y-%m-%d  %-I:%M %p')
    except Exception:
        return str(value)[:16].replace('T', ' ')


# ─── DATABASE ───────────────────────────────────────────────────────────────
def get_db():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id            SERIAL PRIMARY KEY,
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
            created_at    TEXT,
            updated_at    TEXT
        )
    ''')
    # Agregar columnas nuevas si no existen (para BD ya creada con esquema viejo)
    for stmt in [
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS edad INTEGER",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS sexo TEXT DEFAULT 'masculino'",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS active INTEGER DEFAULT 1",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS registered_by TEXT",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS updated_at TEXT",
    ]:
        cur.execute(stmt)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS meal_orders (
            id               SERIAL PRIMARY KEY,
            patient_id       INTEGER NOT NULL REFERENCES patients(id),
            order_date       TEXT NOT NULL,
            meal_date        TEXT,
            meal_time        TEXT NOT NULL,
            diet_type        TEXT DEFAULT 'corriente',
            condition        TEXT DEFAULT 'normal',
            meal_notes       TEXT DEFAULT '',
            dieta_cero       INTEGER DEFAULT 0,
            options_selected TEXT DEFAULT '[]',
            confirmed        INTEGER DEFAULT 0,
            confirmed_by     TEXT,
            confirmed_at     TEXT,
            extra_notes      TEXT DEFAULT '',
            delivery_status  TEXT DEFAULT 'pendiente',
            nurse_received   INTEGER DEFAULT 0
        )
    ''')
    # Agregar columnas nuevas a meal_orders si no existen
    for stmt in [
        "ALTER TABLE meal_orders ADD COLUMN IF NOT EXISTS diet_type TEXT DEFAULT 'corriente'",
        "ALTER TABLE meal_orders ADD COLUMN IF NOT EXISTS condition TEXT DEFAULT 'normal'",
        "ALTER TABLE meal_orders ADD COLUMN IF NOT EXISTS meal_notes TEXT DEFAULT ''",
        "ALTER TABLE meal_orders ADD COLUMN IF NOT EXISTS dieta_cero INTEGER DEFAULT 0",
        "ALTER TABLE meal_orders ADD COLUMN IF NOT EXISTS updated_at TEXT",
        "ALTER TABLE meal_orders ADD COLUMN IF NOT EXISTS updated_by TEXT",
    ]:
        cur.execute(stmt)
    conn.commit()
    cur.close()
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
    today_str = date.today().strftime('%Y-%m-%d')
    today_day = DAY_NAMES[date.today().weekday()]
    today_lbl = today_label_es()
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT * FROM patients WHERE floor=%s AND active=1 ORDER BY room', (role,)
    )
    patients = cur.fetchall()
    cur.execute(
        '''SELECT mo.* FROM meal_orders mo
           JOIN patients p ON mo.patient_id = p.id
           WHERE p.floor=%s AND p.active=1
           ORDER BY COALESCE(mo.meal_date, mo.order_date), mo.meal_time''',
        (role,)
    )
    orders = cur.fetchall()
    # Pacientes transferibles (solo para piso5 y piso6)
    transferable = []
    if role in ('piso5', 'piso6'):
        cur.execute(
            "SELECT * FROM patients WHERE floor IN ('emergencia','uci','ucin') AND active=1 ORDER BY floor, created_at DESC"
        )
        transferable = cur.fetchall()
    cur.close()
    conn.close()
    # orders_map: {patient_id: {date_str: {meal_time: order_dict}}}
    orders_map = {}
    for o in orders:
        row = dict(o)
        try:
            row['options_list'] = json.loads(row.get('options_selected') or '[]')
        except Exception:
            row['options_list'] = []
        meal_d = row.get('meal_date') or row.get('order_date') or today_str
        # Calcular el día de semana CORRECTO para esta comida específica
        try:
            meal_d_obj = date.fromisoformat(meal_d)
            row['meal_day'] = DAY_NAMES[meal_d_obj.weekday()]
        except Exception:
            row['meal_day'] = today_day
        pid = o['patient_id']
        if pid not in orders_map:
            orders_map[pid] = {}
        if meal_d not in orders_map[pid]:
            orders_map[pid][meal_d] = {}
        orders_map[pid][meal_d][o['meal_time']] = row
    # Construir etiquetas de fecha para todas las fechas únicas en orders_map
    date_labels = {}
    for pid_map in orders_map.values():
        for d_str in pid_map.keys():
            if d_str not in date_labels:
                try:
                    d_obj = date.fromisoformat(d_str)
                    date_labels[d_str] = today_label_es(d_obj)
                except Exception:
                    date_labels[d_str] = d_str
    return render_template('dieta_nurse.html',
                           patients=patients,
                           orders_map=orders_map,
                           date_labels=date_labels,
                           transferable=transferable,
                           role=role,
                           role_name=ROLE_NAMES[role],
                           floor_label=FLOOR_LABEL[role],
                           today=today_str,
                           today_day=today_day,
                           today_label=today_lbl,
                           menu_normal=MENU_NORMAL,
                           menu_diabetico=MENU_DIABETICO,
                           diet_options=DIET_OPTIONS,
                           condition_notes=CONDITION_NOTES,
                           condition_label=CONDITION_LABEL,
                           condition_label_full=CONDITION_LABEL,
                           nurses=NURSES,
                           active_nurse=session.get('nurse_name', ''))


@app.route('/api/floor/status')
def floor_status():
    redir = nurse_required()
    if redir: return jsonify({'error': 'unauthorized'}), 403
    role = session['dieta_role']
    today_str = date.today().strftime('%Y-%m-%d')
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        '''SELECT mo.patient_id, mo.meal_time, mo.delivery_status
           FROM meal_orders mo
           JOIN patients p ON mo.patient_id = p.id
           WHERE p.floor=%s AND p.active=1 AND mo.order_date=%s''',
        (role, today_str)
    )
    orders = cur.fetchall()
    cur.close()
    conn.close()
    result = {f"{o['patient_id']}_{o['meal_time']}": (o['delivery_status'] or 'pendiente') for o in orders}
    return jsonify(result)


@app.route('/api/patient/add', methods=['POST'])
def add_patient():
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    role = session['dieta_role']
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    nurse_name = session.get('nurse_name', role)
    now_str = datetime.now().isoformat(timespec='seconds')
    cur.execute(
        '''INSERT INTO patients (name, floor, room, diet_type, condition, edad, sexo, notes, registered_by, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
        (d['name'].strip(), role, d['room'].strip(), d['diet_type'], d.get('condition', 'normal'),
         d.get('edad'), d.get('sexo', 'masculino'), d.get('notes', ''), nurse_name, now_str)
    )
    pid = cur.fetchone()['id']
    meal_time = d.get('meal_time', 'desayuno')
    today_str = date.today().strftime('%Y-%m-%d')
    meal_date = d.get('meal_date', today_str)
    cur.execute(
        '''INSERT INTO meal_orders (patient_id, order_date, meal_date, meal_time, diet_type, condition, meal_notes, dieta_cero, options_selected, confirmed, extra_notes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s)''',
        (pid, today_str, meal_date, meal_time,
         d.get('diet_type', 'corriente'), d.get('condition', 'normal'),
         d.get('meal_notes', ''), 1 if d.get('dieta_cero') else 0,
         '[]', d.get('notes', ''))
    )
    conn.commit()
    cur.close()
    conn.close()
    session.pop('nurse_name', None)
    return jsonify({'ok': True, 'id': pid})


@app.route('/api/patient/<int:pid>/update', methods=['POST'])
def update_patient(pid):
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'UPDATE patients SET diet_type=%s, condition=%s, notes=%s, updated_at=%s WHERE id=%s',
        (d['diet_type'], d.get('condition', 'normal'), d.get('notes', ''), datetime.now().isoformat(), pid)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/patient/<int:pid>/add-meal', methods=['POST'])
def add_meal(pid):
    """Agregar un pedido de comida a un paciente ya registrado (sin duplicar el paciente)."""
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    today_str = date.today().strftime('%Y-%m-%d')
    meal_time = d.get('meal_time', 'almuerzo')
    meal_date = d.get('meal_date', today_str)
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Solo crear si no existe ya para este tiempo
    cur.execute(
        'SELECT id FROM meal_orders WHERE patient_id=%s AND order_date=%s AND meal_time=%s',
        (pid, today_str, meal_time)
    )
    if not cur.fetchone():
        cur.execute(
            '''INSERT INTO meal_orders (patient_id, order_date, meal_date, meal_time, diet_type, condition, meal_notes, dieta_cero, options_selected, confirmed, extra_notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s)''',
            (pid, today_str, meal_date, meal_time,
             d.get('diet_type', 'corriente'), d.get('condition', 'normal'),
             d.get('meal_notes', ''), 1 if d.get('dieta_cero') else 0,
             '[]', d.get('meal_notes', ''))
        )
        conn.commit()
        result = {'ok': True, 'created': True}
    else:
        result = {'ok': True, 'created': False, 'msg': 'Ya existe un pedido para ese tiempo de comida'}
    cur.close()
    conn.close()
    return jsonify(result)


@app.route('/api/patient/<int:pid>/discharge', methods=['POST'])
def discharge_patient(pid):
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE patients SET active=0, updated_at=%s WHERE id=%s', (datetime.now().isoformat(), pid))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/meal/<int:order_id>/delete', methods=['DELETE'])
def delete_meal_order(order_id):
    redir = nurse_required()
    if redir: return jsonify({'error': 'unauthorized'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM meal_orders WHERE id=%s', (order_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/transferable-patients')
def transferable_patients():
    """Pacientes en emergencia/UCI/UCIN disponibles para transferir a piso."""
    redir = nurse_required()
    if redir: return jsonify({'error': 'unauthorized'}), 403
    role = session['dieta_role']
    if role not in ('piso5', 'piso6'):
        return jsonify({'patients': []})
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM patients WHERE floor IN ('emergencia','uci','ucin') AND active=1 ORDER BY floor, created_at DESC"
    )
    patients = [dict(p) for p in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({'patients': patients})


@app.route('/api/patient/<int:pid>/transfer', methods=['POST'])
def transfer_patient(pid):
    """Transferir paciente de emergencia/UCI/UCIN a piso."""
    redir = nurse_required()
    if redir: return jsonify({'error': 'unauthorized'}), 403
    role = session['dieta_role']
    if role not in ('piso5', 'piso6'):
        return jsonify({'error': 'Solo enfermeras de piso pueden recibir transferencias'}), 403
    d = request.json
    new_room = d.get('room', '').strip()
    if not new_room:
        return jsonify({'error': 'Habitación requerida'}), 400
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Verificar que el paciente está en una unidad transferible
    cur.execute('SELECT * FROM patients WHERE id=%s AND active=1', (pid,))
    patient = cur.fetchone()
    if not patient or patient['floor'] not in ('emergencia', 'uci', 'ucin'):
        cur.close(); conn.close()
        return jsonify({'error': 'Paciente no transferible'}), 400
    origin_floor = patient['floor']
    cur.execute(
        'UPDATE patients SET floor=%s, room=%s, updated_at=%s WHERE id=%s',
        (role, new_room, datetime.now().isoformat(), pid)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True, 'from': origin_floor, 'to': role, 'room': new_room})


# ─── CAFETERÍA VIEW ──────────────────────────────────────────────────────────
@app.route('/cafeteria')
def dieta_cafeteria():
    if session.get('dieta_role') != 'cafeteria':
        return redirect(url_for('dieta_login'))
    today = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    today_date_obj = datetime.strptime(today, '%Y-%m-%d').date()
    today_day = DAY_NAMES[today_date_obj.weekday()]
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM patients WHERE active=1 ORDER BY floor, room')
    patients = cur.fetchall()
    cur.execute("SELECT * FROM meal_orders WHERE COALESCE(meal_date, order_date)=%s", (today,))
    orders = cur.fetchall()
    cur.close()
    conn.close()
    orders_map = {(o['patient_id'], o['meal_time']): dict(o) for o in orders}
    return render_template('dieta_cafeteria.html',
                           patients=patients,
                           orders_map=orders_map,
                           today=today,
                           today_day=today_day,
                           menu_normal=MENU_NORMAL,
                           menu_diabetico=MENU_DIABETICO,
                           meal_times=MEAL_TIMES,
                           diet_options=DIET_OPTIONS,
                           condition_notes=CONDITION_NOTES,
                           condition_label=CONDITION_LABEL,
                           floor_label=FLOOR_LABEL)


@app.route('/api/order/nurse-received', methods=['POST'])
def nurse_received():
    redir = nurse_required()
    if redir: return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    today_str = date.today().strftime('%Y-%m-%d')
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT id FROM meal_orders WHERE patient_id=%s AND order_date=%s AND meal_time=%s',
        (d['patient_id'], today_str, d['meal_time'])
    )
    existing = cur.fetchone()
    if existing:
        # Solo actualizar — nunca crear pedidos automáticos
        cur.execute('UPDATE meal_orders SET nurse_received=1 WHERE id=%s', (existing['id'],))
        conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/order/delivery-status', methods=['POST'])
def update_delivery_status():
    if session.get('dieta_role') != 'cafeteria':
        return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    status = d['status']  # recibido, en_proceso, en_camino, entregado
    confirmed = 1 if status == 'entregado' else 0
    now = datetime.now().isoformat()
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT id FROM meal_orders WHERE patient_id=%s AND order_date=%s AND meal_time=%s',
        (d['patient_id'], d['date'], d['meal_time'])
    )
    existing = cur.fetchone()
    if existing:
        # Solo actualizar — nunca crear pedidos automáticos desde cafetería
        cur.execute(
            'UPDATE meal_orders SET delivery_status=%s, confirmed=%s, confirmed_by=%s, confirmed_at=%s WHERE id=%s',
            (status, confirmed, 'cafeteria', now, existing['id'])
        )
        conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/meal/<int:order_id>/edit', methods=['POST'])
def edit_meal_order(order_id):
    if nurse_required(): return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    nurse = session.get('nurse_name') or session.get('dieta_role', 'enfermería')
    now_str = datetime.now().isoformat(timespec='seconds')
    dieta_cero = bool(d.get('dieta_cero'))
    diet_type = 'cero' if dieta_cero else d.get('diet_type', 'corriente')
    conn = get_db()
    cur = conn.cursor()
    meal_date = d.get('meal_date') or None
    cur.execute(
        '''UPDATE meal_orders
           SET diet_type=%s, condition=%s, meal_notes=%s, dieta_cero=%s,
               meal_date=%s, updated_at=%s, updated_by=%s
           WHERE id=%s''',
        (diet_type, d.get('condition', 'normal'), d.get('meal_notes', ''),
         1 if dieta_cero else 0, meal_date, now_str, nurse, order_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True, 'updated_at': now_str, 'updated_by': nurse})


@app.route('/api/order/save', methods=['POST'])
def save_order():
    if session.get('dieta_role') != 'cafeteria':
        return jsonify({'error': 'unauthorized'}), 403
    d = request.json
    now = datetime.now().isoformat()
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT id FROM meal_orders WHERE patient_id=%s AND COALESCE(meal_date, order_date)=%s AND meal_time=%s",
        (d['patient_id'], d['date'], d['meal_time'])
    )
    existing = cur.fetchone()
    if existing:
        # Solo actualizar — nunca crear pedidos automáticos desde cafetería
        cur.execute(
            'UPDATE meal_orders SET options_selected=%s, confirmed=1, confirmed_by=%s, confirmed_at=%s, extra_notes=%s WHERE id=%s',
            (json.dumps(d['options']), 'cafeteria', now, d.get('notes', ''), existing['id'])
        )
        conn.commit()
    cur.close()
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
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if floor_filter == 'all':
        cur.execute('SELECT * FROM patients WHERE active=1 ORDER BY floor, room')
    else:
        cur.execute('SELECT * FROM patients WHERE active=1 AND floor=%s ORDER BY room', (floor_filter,))
    patients = cur.fetchall()
    cur.execute("SELECT * FROM meal_orders WHERE COALESCE(meal_date, order_date)=%s", (today,))
    orders = cur.fetchall()
    # Pacientes activos por piso
    floor_counts = {}
    for fk in FLOOR_LABEL:
        cur.execute('SELECT COUNT(*) as cnt FROM patients WHERE active=1 AND floor=%s', (fk,))
        floor_counts[fk] = cur.fetchone()['cnt']
    # Conteos por estado de entrega (basados en meal_date del día seleccionado)
    status_counts = {}
    for st in ('recibido', 'en_proceso', 'en_camino', 'entregado'):
        cur.execute(
            "SELECT COUNT(*) as cnt FROM meal_orders WHERE COALESCE(meal_date, order_date)=%s AND delivery_status=%s", (today, st)
        )
        status_counts[st] = cur.fetchone()['cnt']
    cur.execute(
        "SELECT COUNT(*) as cnt FROM meal_orders WHERE COALESCE(meal_date, order_date)=%s AND nurse_received=1", (today,)
    )
    status_counts['nurse_received'] = cur.fetchone()['cnt']
    cur.execute(
        "SELECT COUNT(*) as cnt FROM meal_orders WHERE COALESCE(meal_date, order_date)=%s AND dieta_cero=1", (today,)
    )
    status_counts['dieta_cero'] = cur.fetchone()['cnt']
    cur.execute(
        "SELECT COUNT(*) as cnt FROM meal_orders WHERE COALESCE(meal_date, order_date)=%s AND diet_type='otra'", (today,)
    )
    status_counts['dieta_otra'] = cur.fetchone()['cnt']
    cur.execute(
        "SELECT COUNT(*) as cnt FROM meal_orders WHERE COALESCE(meal_date, order_date)=%s", (today,)
    )
    status_counts['total_orders'] = cur.fetchone()['cnt']
    cur.close()
    conn.close()
    orders_map = {}
    for o in orders:
        row = dict(o)
        meal_d = row.get('meal_date') or row.get('order_date') or today
        try:
            meal_d_obj = date.fromisoformat(meal_d)
            row['meal_day'] = DAY_NAMES[meal_d_obj.weekday()]
        except Exception:
            row['meal_day'] = today_day
        orders_map[(o['patient_id'], o['meal_time'])] = row
    today_day = DAY_NAMES[datetime.strptime(today, '%Y-%m-%d').weekday()]
    return render_template('dieta_gerencia.html',
                           patients=patients,
                           orders_map=orders_map,
                           today=today,
                           today_day=today_day,
                           floor_filter=floor_filter,
                           floor_counts=floor_counts,
                           status_counts=status_counts,
                           meal_times=MEAL_TIMES,
                           diet_options=DIET_OPTIONS,
                           menu_normal=MENU_NORMAL,
                           menu_diabetico=MENU_DIABETICO,
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
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Use LEFT(created_at, 10) for safe date-string comparison
    cur.execute(
        "SELECT * FROM patients WHERE LEFT(created_at, 10) BETWEEN %s AND %s ORDER BY floor, created_at",
        (inicio, fin)
    )
    patients = cur.fetchall()
    cur.execute(
        '''SELECT mo.*, p.name as patient_name, p.floor, p.room, p.diet_type,
                  p.condition, p.edad, p.sexo, p.registered_by
           FROM meal_orders mo
           JOIN patients p ON mo.patient_id = p.id
           WHERE mo.order_date BETWEEN %s AND %s
           ORDER BY mo.order_date, p.floor, mo.meal_time''',
        (inicio, fin)
    )
    orders = cur.fetchall()
    cur.close()
    conn.close()
    # Estadísticas
    total_pacientes = len(patients)
    total_pedidos   = len(orders)
    confirmados     = sum(1 for o in orders if o['confirmed'])
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
