import pytest
import os
import tempfile
from flask import session
from app import create_app
from utils.db_adapter import db_adapter


@pytest.fixture
def app():
    """Cria e configura uma instância de aplicação Flask para testes"""
    # Usar banco de dados SQLite temporário para testes
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'USE_POSTGRES': False,
        'DATABASE_PATH': db_path,
        'SECRET_KEY': 'test_key'
    })
    
    # Inicializar banco de dados para testes
    with app.app_context():
        db_adapter.init_db()
        
        # Criar um usuário de teste
        with db_adapter.get_db_connection() as conn:
            cursor = conn.cursor()
            # Adicionar usuário de teste
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ('testuser', 'pbkdf2:sha256:150000$GFCcFipT$7d3a9f4b78480c0f585739d5103ee76e352c81c3d53cd85ef4c5342dccea7448')
            )
            # Adicionar número WhatsApp de teste
            cursor.execute(
                "INSERT INTO whatsapp_numbers (phone_number, description, user_id) VALUES (?, ?, ?)",
                ('5541999887766', 'Número de teste', 1)
            )
            # Adicionar link personalizado de teste
            cursor.execute(
                "INSERT INTO custom_links (link_name, message_template, user_id, click_count) VALUES (?, ?, ?, ?)",
                ('teste', 'Mensagem de teste', 1, 0)
            )
            conn.commit()
    
    yield app
    
    # Limpar após o teste
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Cria um cliente de teste"""
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Cria um cliente de teste já autenticado"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'testuser'
    return client


def test_redirect_to_login(client):
    """Testa se a página inicial redireciona para login quando não autenticado"""
    response = client.get('/')
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']


def test_login_page(client):
    """Testa se a página de login carrega corretamente"""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower()


def test_login_success(client):
    """Testa login com credenciais corretas"""
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'test_password'  # A senha corresponde ao hash acima
    }, follow_redirects=True)
    assert response.status_code == 200


def test_dashboard_access(authenticated_client):
    """Testa acesso ao dashboard quando autenticado"""
    response = authenticated_client.get('/admin/dashboard')
    assert response.status_code == 200


def test_redirect_whatsapp(client, app):
    """Testa funcionalidade de redirecionamento para WhatsApp com contador de cliques"""
    # Verificar contador inicial
    with app.app_context():
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT click_count FROM custom_links WHERE link_name = 'teste'")
        initial_count = cursor.fetchone()['click_count']
        conn.close()
    
    # Acessar link de redirecionamento
    response = client.get('/teste')
    assert response.status_code == 302
    assert 'https://wa.me/' in response.headers['Location']
    
    # Verificar se o contador foi incrementado
    with app.app_context():
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT click_count FROM custom_links WHERE link_name = 'teste'")
        new_count = cursor.fetchone()['click_count']
        conn.close()
    
    assert new_count == initial_count + 1


def test_user_isolation(authenticated_client, app):
    """Testa o isolamento de dados entre usuários diferentes"""
    # Criar segundo usuário
    with app.app_context():
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        # Adicionar segundo usuário
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ('testuser2', 'pbkdf2:sha256:150000$GFCcFipT$7d3a9f4b78480c0f585739d5103ee76e352c81c3d53cd85ef4c5342dccea7448')
        )
        # Adicionar número WhatsApp para segundo usuário
        cursor.execute(
            "INSERT INTO whatsapp_numbers (phone_number, description, user_id) VALUES (?, ?, ?)",
            ('5541988776655', 'Número do usuário 2', 2)
        )
        conn.commit()
    
    # Obter números do usuário atual (testuser id=1)
    response = authenticated_client.get('/admin/numbers')
    assert response.status_code == 200
    # Verificar se apenas vê seus próprios números (e não do outro usuário)
    assert b'5541999887766' in response.data
    assert b'5541988776655' not in response.data
