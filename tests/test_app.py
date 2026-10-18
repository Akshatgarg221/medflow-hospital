import pytest
from app import app as flask_app, init_db

@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / 'test.db'
    monkeypatch.setattr('app.DB_PATH', str(db))
    init_db()
    flask_app.config.update(TESTING=True, SECRET_KEY='test-secret')
    with flask_app.test_client() as client:
        yield client

def csrf(client):
    with client.session_transaction() as sess:
        return sess.get('csrf_token')

def login(client, next_url=None):
    url = '/login' + (f'?next={next_url}' if next_url else '')
    return client.post(url, data={
        'username': 'admin', 'password': 'ChangeMe123!', 'csrf_token': csrf(client)
    }, follow_redirects=False)

def test_dashboard_requires_login(client):
    assert client.get('/').status_code == 302

def test_login_and_dashboard(client):
    response = login(client)
    assert response.status_code == 302
    dashboard = client.get('/')
    assert dashboard.status_code == 200
    assert b'Total patients' in dashboard.data

def test_login_rejects_external_redirect(client):
    response = login(client, 'https://evil.example')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')
    assert 'evil.example' not in response.headers['Location']

def test_patient_search(client):
    login(client)
    response = client.get('/patients?q=Aarav')
    assert response.status_code == 200
    assert b'Aarav Sharma' in response.data

def test_patient_search_treats_wildcards_literally(client):
    login(client)
    response = client.get('/patients?q=%25')
    assert response.status_code == 200
    assert b'Aarav Sharma' not in response.data

def test_csrf_blocks_patient_creation(client):
    login(client)
    response = client.post('/patients/new', data={
        'name': 'Test Patient', 'age': '20', 'gender': 'Male',
        'department': 'Cardiology', 'status': 'Outpatient'
    })
    assert response.status_code == 400

def test_assistant_low_stock(client):
    login(client)
    response = client.post('/api/assistant', json={'message': 'Which items are low stock?'},
                           headers={'X-CSRF-Token': csrf(client)})
    assert response.status_code == 200
    assert b'N95 masks' in response.data

def test_assistant_rejects_empty_question(client):
    login(client)
    response = client.post('/api/assistant', json={'message': ' '},
                           headers={'X-CSRF-Token': csrf(client)})
    assert response.status_code == 400

def test_security_headers_present(client):
    response = client.get('/login')
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Cache-Control'] == 'no-store'

def test_logout_requires_csrf(client):
    login(client)
    response = client.post('/logout')
    assert response.status_code == 400

def test_login_rejects_wrong_password(client):
    response = client.post('/login', data={
        'username': 'admin', 'password': 'wrong-password', 'csrf_token': csrf(client)
    })
    assert response.status_code == 200
    assert b'Incorrect username or password' in response.data


def test_login_requires_csrf(client):
    response = client.post('/login', data={'username': 'admin', 'password': 'ChangeMe123!'})
    assert response.status_code == 400


def test_patient_creation_validates_age_and_enum(client):
    login(client)
    response = client.post('/patients/new', data={
        'csrf_token': csrf(client), 'name': 'Invalid Age', 'age': '999',
        'gender': 'Male', 'department': 'Cardiology', 'status': 'Outpatient'
    })
    assert response.status_code == 200
    assert b'Please check the required fields' in response.data


def test_patient_creation_success(client):
    login(client)
    response = client.post('/patients/new', data={
        'csrf_token': csrf(client), 'name': 'Test Patient', 'age': '29',
        'gender': 'Prefer not to say', 'phone': '9000000000',
        'department': 'Cardiology', 'status': 'Outpatient'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Test Patient' in response.data


def test_patient_detail_returns_404_for_missing_record(client):
    login(client)
    assert client.get('/patients/999999').status_code == 404


def test_inventory_rejects_negative_adjustment(client):
    login(client)
    with client.session_transaction() as sess:
        token = sess['csrf_token']
    # Item 4 is seeded with 18 units; this adjustment would make stock negative.
    response = client.post('/inventory/4/adjust', data={'csrf_token': token, 'delta': '-999'})
    assert response.status_code == 302
    with client.application.app_context():
        from flask import g
        from app import connect_db, DB_PATH
        db = connect_db()
        quantity = db.execute('SELECT quantity FROM inventory WHERE id=4').fetchone()['quantity']
        db.close()
    assert quantity >= 0


def test_inventory_creation_rejects_duplicate(client):
    login(client)
    response = client.post('/inventory', data={
        'csrf_token': csrf(client), 'item': 'N95 masks', 'category': 'PPE',
        'quantity': '10', 'reorder_level': '5', 'unit': 'boxes'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'already exists' in response.data


def test_appointment_creation_requires_csrf(client):
    login(client)
    response = client.post('/appointments', data={
        'patient_id': '1', 'doctor': 'Dr Test', 'department': 'Cardiology',
        'appt_date': '2030-01-01', 'appt_time': '10:00'
    })
    assert response.status_code == 400


def test_assistant_rejects_malformed_json_gracefully(client):
    login(client)
    response = client.post('/api/assistant', data='{not-json', content_type='application/json',
                           headers={'X-CSRF-Token': csrf(client)})
    assert response.status_code == 400


def test_all_mutation_routes_require_authentication(client):
    assert client.post('/patients/new').status_code == 302
    assert client.post('/appointments').status_code == 302
    assert client.post('/inventory').status_code == 302
    assert client.post('/inventory/1/adjust').status_code == 302


def test_database_indexes_created(client):
    from app import connect_db
    db = connect_db()
    indexes = {row['name'] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    db.close()
    assert 'idx_appointments_date_status_time' in indexes
    assert 'idx_inventory_reorder' in indexes


def test_patient_page_parameter_is_safe(client):
    login(client)
    response = client.get('/patients?page=not-a-number')
    assert response.status_code == 200
    assert b'Page 1 of 1' in response.data


def test_security_headers_present_on_error(client):
    response = client.get('/not-a-route')
    assert response.status_code == 404
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'


def test_assistant_returns_structured_low_stock_results(client):
    login(client)
    response = client.post('/api/assistant', json={'message': 'Show low stock supplies'},
                           headers={'X-CSRF-Token': csrf(client)})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['intent'] == 'inventory'
    assert payload['count'] >= 1
    assert any(item['item'] == 'N95 masks' for item in payload['data'])
    assert all(item['priority'] in ('out_of_stock', 'reorder') for item in payload['data'])


def test_assistant_overdue_intent_includes_caveat(client):
    login(client)
    response = client.post('/api/assistant', json={'message': 'Show overdue appointments'},
                           headers={'X-CSRF-Token': csrf(client)})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['intent'] == 'overdue_appointments'
    assert 'not proof' in payload['disclaimer']


def test_assistant_unknown_intent_does_not_guess(client):
    login(client)
    response = client.post('/api/assistant', json={'message': 'What is the best treatment for chest pain?'},
                           headers={'X-CSRF-Token': csrf(client)})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['intent'] == 'unknown'
    assert 'could not confidently match' in payload['reply']
    assert payload['data'] == []


def test_assistant_does_not_log_raw_question(client):
    login(client)
    marker = 'CONFIDENTIAL-FREE-TEXT-DO-NOT-LOG'
    client.post('/api/assistant', json={'message': marker}, headers={'X-CSRF-Token': csrf(client)})
    from app import connect_db
    db = connect_db()
    actions = [row['action'] for row in db.execute('SELECT action FROM audit_log').fetchall()]
    db.close()
    assert marker not in ' '.join(actions)
    assert any('operations assistant intent: unknown' == action for action in actions)
