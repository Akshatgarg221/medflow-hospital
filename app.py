"""MedFlow: small demo hospital operations dashboard. Not for production PHI."""
import os, sqlite3, secrets
from datetime import date, datetime
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("MEDFLOW_DB", os.path.join(BASE, "medflow.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1", MAX_CONTENT_LENGTH=1_000_000)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin');
CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, mrn TEXT UNIQUE NOT NULL, name TEXT NOT NULL, age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 120), gender TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', department TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Outpatient', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL REFERENCES patients(id), doctor TEXT NOT NULL, department TEXT NOT NULL, appt_date TEXT NOT NULL, appt_time TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Scheduled');
CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT UNIQUE NOT NULL, category TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity >= 0), reorder_level INTEGER NOT NULL CHECK(reorder_level >= 0), unit TEXT NOT NULL DEFAULT 'units');
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL);
"""

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.before_request
def open_db():
    g.db = connect_db()
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(24)

@app.teardown_request
def close_db(exc):
    db = g.pop("db", None)
    if db is not None: db.close()

def init_db():
    db = connect_db(); db.executescript(SCHEMA)
    if not db.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        db.execute(
    "INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
    (
        "admin",
        generate_password_hash(
            os.environ.get("DEMO_PASSWORD", "ChangeMe123!"),
            method="pbkdf2:sha256"
        ),
        "admin"
    )
)
    if db.execute("SELECT COUNT(*) n FROM patients").fetchone()['n'] == 0:
        today = date.today().isoformat()
        sample = [
          ('MF-1001','Aarav Sharma',34,'Male','9000000001','Cardiology','Outpatient'),
          ('MF-1002','Meera Singh',52,'Female','9000000002','Orthopedics','Admitted'),
          ('MF-1003','Kabir Verma',27,'Male','9000000003','General Medicine','Outpatient'),
          ('MF-1004','Ananya Gupta',41,'Female','9000000004','Neurology','Under observation'),
          ('MF-1005','Ishaan Patel',63,'Male','9000000005','Cardiology','Admitted')]
        for mrn,name,age,gender,phone,dept,status in sample:
            db.execute('INSERT INTO patients(mrn,name,age,gender,phone,department,status,created_at) VALUES(?,?,?,?,?,?,?,?)',(mrn,name,age,gender,phone,dept,status,datetime.now().isoformat(timespec='seconds')))
        pids = [r['id'] for r in db.execute('SELECT id FROM patients ORDER BY id').fetchall()]
        doctors = [('Dr. R. Mehta','Cardiology'),('Dr. S. Rao','Orthopedics'),('Dr. A. Khan','General Medicine')]
        for i,pid in enumerate(pids[:4]):
            doctor,dept=doctors[i%len(doctors)]
            db.execute('INSERT INTO appointments(patient_id,doctor,department,appt_date,appt_time,status) VALUES(?,?,?,?,?,?)',(pid,doctor,dept,today,f'{9+i:02d}:30','Scheduled' if i%2==0 else 'Checked in'))
        for item,cat,qty,level,unit in [('Surgical gloves','PPE',120,50,'boxes'),('N95 masks','PPE',28,40,'boxes'),('Saline 500ml','Consumables',75,30,'bottles'),('Syringes 5ml','Consumables',18,25,'packs'),('Bandages','First aid',64,20,'packs')]:
            db.execute('INSERT INTO inventory(item,category,quantity,reorder_level,unit) VALUES(?,?,?,?,?)',(item,cat,qty,level,unit))
    db.commit(); db.close()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('username'): return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def csrf_protect():
    token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    if not token or not secrets.compare_digest(token, session.get('csrf_token','')): abort(400, 'Invalid or missing CSRF token')

def audit(action):
    g.db.execute('INSERT INTO audit_log(username,action,created_at) VALUES(?,?,?)',(session.get('username','anonymous'),action,datetime.now().isoformat(timespec='seconds')))
    g.db.commit()

@app.context_processor
def inject_globals(): return {'csrf_token': session.get('csrf_token','')}

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        csrf_protect(); username=request.form.get('username','').strip(); password=request.form.get('password','')
        user=g.db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        if user and check_password_hash(user['password_hash'],password):
            session.clear(); session['username']=user['username']; session['role']=user['role']; session['csrf_token']=secrets.token_urlsafe(24)
            g.db.execute('INSERT INTO audit_log(username,action,created_at) VALUES(?,?,?)',(username,'login',datetime.now().isoformat(timespec='seconds'))); g.db.commit()
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Incorrect username or password.','error')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    csrf_protect(); session.clear(); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    db=g.db
    metrics={
      'patients':db.execute('SELECT COUNT(*) n FROM patients').fetchone()['n'],
      'appointments':db.execute("SELECT COUNT(*) n FROM appointments WHERE appt_date=? AND status!='Cancelled'",(date.today().isoformat(),)).fetchone()['n'],
      'admitted':db.execute("SELECT COUNT(*) n FROM patients WHERE status='Admitted'").fetchone()['n'],
      'low_stock':db.execute('SELECT COUNT(*) n FROM inventory WHERE quantity<=reorder_level').fetchone()['n']}
    appointments=db.execute('SELECT a.*,p.name patient_name,p.mrn FROM appointments a JOIN patients p ON p.id=a.patient_id ORDER BY a.appt_date,a.appt_time LIMIT 8').fetchall()
    low_stock=db.execute('SELECT * FROM inventory WHERE quantity<=reorder_level ORDER BY quantity ASC').fetchall()
    return render_template('dashboard.html',metrics=metrics,appointments=appointments,low_stock=low_stock,today=date.today().isoformat())

@app.route('/patients')
@login_required
def patients():
    q=request.args.get('q','').strip()
    rows=g.db.execute('SELECT * FROM patients WHERE name LIKE ? OR mrn LIKE ? OR department LIKE ? ORDER BY id DESC', (f'%{q}%',f'%{q}%',f'%{q}%')).fetchall()
    return render_template('patients.html',patients=rows,q=q)

@app.route('/patients/new', methods=['GET','POST'])
@login_required
def new_patient():
    if request.method=='POST':
        csrf_protect()
        name=request.form.get('name','').strip(); age=request.form.get('age',''); gender=request.form.get('gender',''); phone=request.form.get('phone','').strip(); dept=request.form.get('department',''); status=request.form.get('status','Outpatient')
        if not name or not age.isdigit() or not 0<=int(age)<=120 or gender not in ('Female','Male','Non-binary','Prefer not to say') or not dept or status not in ('Outpatient','Admitted','Under observation','Discharged'):
            flash('Please check the required fields and enter a valid age.','error')
            return render_template('patient_form.html',patient=None)
        mrn='MF-'+secrets.token_hex(3).upper()
        try:
            g.db.execute('INSERT INTO patients(mrn,name,age,gender,phone,department,status,created_at) VALUES(?,?,?,?,?,?,?,?)',(mrn,name,int(age),gender,phone,dept,status,datetime.now().isoformat(timespec='seconds')))
            g.db.commit(); audit(f'created patient {mrn}'); flash(f'Patient record created ({mrn}).','success'); return redirect(url_for('patients'))
        except sqlite3.IntegrityError:
            flash('Could not create patient record. Please retry.','error')
    return render_template('patient_form.html',patient=None)

@app.route('/patients/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    p=g.db.execute('SELECT * FROM patients WHERE id=?',(patient_id,)).fetchone()
    if not p: abort(404)
    appts=g.db.execute('SELECT * FROM appointments WHERE patient_id=? ORDER BY appt_date DESC,appt_time DESC',(patient_id,)).fetchall()
    return render_template('patient_detail.html',patient=p,appointments=appts)

@app.route('/appointments', methods=['GET','POST'])
@login_required
def appointments():
    if request.method=='POST':
        csrf_protect(); patient_id=request.form.get('patient_id',''); doctor=request.form.get('doctor','').strip(); dept=request.form.get('department','').strip(); appt_date=request.form.get('appt_date',''); appt_time=request.form.get('appt_time','')
        try:
            datetime.strptime(appt_date,'%Y-%m-%d'); datetime.strptime(appt_time,'%H:%M')
            if not patient_id.isdigit() or not doctor or not dept: raise ValueError()
            g.db.execute('INSERT INTO appointments(patient_id,doctor,department,appt_date,appt_time) VALUES(?,?,?,?,?)',(int(patient_id),doctor,dept,appt_date,appt_time)); g.db.commit(); audit('created appointment'); flash('Appointment scheduled.','success')
        except (ValueError,sqlite3.IntegrityError): flash('Please enter valid appointment details.','error')
        return redirect(url_for('appointments'))
    rows=g.db.execute('SELECT a.*,p.name patient_name,p.mrn FROM appointments a JOIN patients p ON p.id=a.patient_id ORDER BY a.appt_date DESC,a.appt_time').fetchall()
    people=g.db.execute('SELECT id,name,mrn FROM patients ORDER BY name').fetchall()
    return render_template('appointments.html',appointments=rows,patients=people,today=date.today().isoformat())

@app.route('/appointments/<int:appointment_id>/status',methods=['POST'])
@login_required
def appointment_status(appointment_id):
    csrf_protect(); status=request.form.get('status','')
    if status not in ('Scheduled','Checked in','Completed','Cancelled'): abort(400)
    cur=g.db.execute('UPDATE appointments SET status=? WHERE id=?',(status,appointment_id)); g.db.commit()
    if cur.rowcount: audit(f'updated appointment {appointment_id} to {status}')
    return redirect(request.referrer or url_for('appointments'))

@app.route('/inventory',methods=['GET','POST'])
@login_required
def inventory():
    if request.method=='POST':
        csrf_protect(); item=request.form.get('item','').strip(); category=request.form.get('category','').strip(); unit=request.form.get('unit','units').strip(); qty=request.form.get('quantity',''); level=request.form.get('reorder_level','')
        if not item or not category or not qty.isdigit() or not level.isdigit(): flash('Enter a name, category, and non-negative quantities.','error')
        else:
            try:
                g.db.execute('INSERT INTO inventory(item,category,quantity,reorder_level,unit) VALUES(?,?,?,?,?)',(item,category,int(qty),int(level),unit or 'units')); g.db.commit(); audit(f'added inventory item {item}'); flash('Inventory item added.','success')
            except sqlite3.IntegrityError: flash('An item with that name already exists.','error')
        return redirect(url_for('inventory'))
    rows=g.db.execute('SELECT * FROM inventory ORDER BY (quantity<=reorder_level) DESC,item').fetchall()
    return render_template('inventory.html',items=rows)

@app.route('/inventory/<int:item_id>/adjust',methods=['POST'])
@login_required
def adjust_inventory(item_id):
    csrf_protect(); delta=request.form.get('delta','')
    try: delta=int(delta)
    except ValueError: abort(400)
    cur=g.db.execute('UPDATE inventory SET quantity=quantity+? WHERE id=? AND quantity+?>=0',(delta,item_id,delta)); g.db.commit()
    if cur.rowcount: audit(f'adjusted inventory item {item_id} by {delta}')
    else: flash('Adjustment rejected: quantity cannot become negative.','error')
    return redirect(url_for('inventory'))

@app.route('/api/assistant',methods=['POST'])
@login_required
def assistant():
    csrf_protect(); question=request.json.get('message','').strip() if request.is_json else request.form.get('message','').strip()
    if not question or len(question)>500: return jsonify({'reply':'Please enter a question under 500 characters.'}),400
    q=question.lower(); db=g.db
    if any(k in q for k in ('low stock','stock','inventory','reorder','supplies')):
        items=db.execute('SELECT item,quantity,reorder_level,unit FROM inventory WHERE quantity<=reorder_level ORDER BY quantity ASC').fetchall()
        if items:
            lines=[f"• {x['item']}: {x['quantity']} {x['unit']} left (reorder threshold {x['reorder_level']})" for x in items]
            reply='Inventory items at or below their reorder threshold:\n'+'\n'.join(lines)+'\nSuggested action: verify physical counts, then raise a purchase request through your normal approval process.'
        else: reply='No inventory items are currently at or below their reorder threshold. Continue routine checks.'
    elif any(k in q for k in ('appointment','schedule','today','doctor')):
        rows=db.execute("SELECT a.appt_time,p.name,a.department,a.status FROM appointments a JOIN patients p ON p.id=a.patient_id WHERE a.appt_date=? AND a.status!='Cancelled' ORDER BY a.appt_time",(date.today().isoformat(),)).fetchall()
        reply=f"There are {len(rows)} non-cancelled appointments recorded for today.\n"+'\n'.join(f"• {r['appt_time']} — {r['name']} / {r['department']} ({r['status']})" for r in rows) if rows else 'No non-cancelled appointments are recorded for today.'
    elif any(k in q for k in ('admitted','beds','inpatient')):
        n=db.execute("SELECT COUNT(*) n FROM patients WHERE status='Admitted'").fetchone()['n']
        reply=f'The system currently has {n} patient records marked Admitted. This is not a live bed-occupancy feed; confirm with the ward team before operational decisions.'
    elif any(k in q for k in ('patient','find','search','record')):
        reply='To locate a record, open Patients and search by patient name, medical record number (MRN), or department. Access only records needed for your assigned work.'
    else:
        reply='I can help with hospital operations: ask about today’s appointments, low-stock supplies, admitted-patient record counts, or how to find a patient record. I do not diagnose symptoms or recommend treatment.'
    audit('used operations assistant'); return jsonify({'reply':reply})

@app.errorhandler(400)
def bad_request(error):
    if request.path.startswith('/api/'): return jsonify({'error':'Invalid request. Refresh the page and try again.'}),400
    return render_template('error.html',code=400,message='The request could not be validated. Refresh the page and try again.'),400
@app.errorhandler(404)
def not_found(error): return render_template('error.html',code=404,message='The page or record could not be found.'),404

if __name__=='__main__':
    init_db()
    app.run(debug=os.environ.get('FLASK_DEBUG')=='1', host='127.0.0.1', port=int(os.environ.get('PORT','5000')))
