import pytest
from app import create_app
from utils.db_adapter import db_adapter
import os
import tempfile

@pytest.fixture
def app():
    """Cria e configura uma instância de aplicação Flask para testes do contador de cliques"""
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
        
        # Configurar dados de teste
        with db_adapter.get_db_connection() as conn:
            cursor = conn.cursor()
            # Adicionar dois usuários
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ('user1', 'pbkdf2:sha256:150000$GFCcFipT$7d3a9f4b78480c0f585739d5103ee76e352c81c3d53cd85ef4c5342dccea7448')
            )
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ('user2', 'pbkdf2:sha256:150000$GFCcFipT$7d3a9f4b78480c0f585739d5103ee76e352c81c3d53cd85ef4c5342dccea7448')
            )
            
            # Adicionar números WhatsApp para ambos os usuários
            cursor.execute(
                "INSERT INTO whatsapp_numbers (phone_number, description, user_id) VALUES (?, ?, ?)",
                ('5541999887766', 'Número user1', 1)
            )
            cursor.execute(
                "INSERT INTO whatsapp_numbers (phone_number, description, user_id) VALUES (?, ?, ?)",
                ('5541988776655', 'Número user2', 2)
            )
            
            # Adicionar links para ambos os usuários com contagem inicial
            cursor.execute(
                "INSERT INTO custom_links (link_name, message_template, user_id, click_count) VALUES (?, ?, ?, ?)",
                ('link1', 'Mensagem user1', 1, 5)  # Começa com 5 cliques
            )
            cursor.execute(
                "INSERT INTO custom_links (link_name, message_template, user_id, click_count) VALUES (?, ?, ?, ?)",
                ('link2', 'Mensagem user2', 2, 10)  # Começa com 10 cliques
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
def user1_client(client):
    """Cliente autenticado como user1"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'user1'
    return client


@pytest.fixture
def user2_client(client):
    """Cliente autenticado como user2"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['username'] = 'user2'
    return client


def test_click_counter_increment(client, app):
    """Testa se o contador de cliques é incrementado ao acessar o link"""
    # Acessar link1 várias vezes
    for _ in range(3):
        response = client.get('/link1')
        assert response.status_code == 302
    
    # Verificar se o contador foi incrementado corretamente
    with app.app_context():
        conn = db_adapter.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT click_count FROM custom_links WHERE link_name = 'link1'")
        count = cursor.fetchone()['click_count']
        conn.close()
    
    # Deveria ser 5 (inicial) + 3 (novos cliques) = 8
    assert count == 8


def test_click_counter_isolation(user1_client, user2_client, app):
    """Testa se os contadores de cliques são isolados por usuário"""
    # Verificar se o usuário 1 só vê seus próprios contadores
    response = user1_client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'link1' in response.data
    assert b'link2' not in response.data
    
    # Verificar se o usuário 2 só vê seus próprios contadores
    response = user2_client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'link1' not in response.data
    assert b'link2' in response.data


def test_admin_interface_displays_counters(user1_client, app):
    """Testa se a interface administrativa exibe os contadores de cliques"""
    response = user1_client.get('/admin/dashboard')
    assert response.status_code == 200
    
    # Verificar se o contador de cliques é exibido
    assert b'5' in response.data  # contador inicial do link1
    
    # Adicionar mais um clique
    client_anon = app.test_client()
    client_anon.get('/link1')
    
    # Verificar se a atualização é refletida na interface
    response = user1_client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'6' in response.data  # contador incremental
