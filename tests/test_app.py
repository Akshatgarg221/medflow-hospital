import os
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

def login(client):
    with client.session_transaction() as sess: token = sess.get('csrf_token')
    return client.post('/login', data={'username':'admin','password':'ChangeMe123!','csrf_token':token}, follow_redirects=True)

def test_dashboard_requires_login(client):
    assert client.get('/').status_code == 302

def test_login_and_dashboard(client):
    response=login(client)
    assert response.status_code == 200
    assert b'Total patients' in response.data

def test_patient_search(client):
    login(client)
    response=client.get('/patients?q=Aarav')
    assert response.status_code == 200
    assert b'Aarav Sharma' in response.data

def test_csrf_blocks_patient_creation(client):
    login(client)
    response=client.post('/patients/new',data={'name':'Test Patient','age':'20','gender':'Male','department':'Cardiology','status':'Outpatient'})
    assert response.status_code == 400

def test_assistant_low_stock(client):
    login(client)
    with client.session_transaction() as sess: token=sess['csrf_token']
    response=client.post('/api/assistant',json={'message':'Which items are low stock?'},headers={'X-CSRF-Token':token})
    assert response.status_code == 200
    assert b'N95 masks' in response.data
