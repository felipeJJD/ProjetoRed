from utils.db_adapter import db_adapter
from werkzeug.security import generate_password_hash, check_password_hash


class User:
    """Modelo que representa um usuário do sistema"""
    
    def __init__(self, id=None, username=None, password=None, plan_id=None, is_admin=False):
        self.id = id
        self.username = username
        self.password = password
        self.plan_id = plan_id
        self.is_admin = is_admin
    
    @staticmethod
    def get_by_id(user_id):
        """Busca um usuário pelo ID"""
        result = db_adapter.execute_query(
            'SELECT * FROM users WHERE id = %s', 
            (user_id,)
        )
        return User._from_db_result(result) if result else None
    
    @staticmethod
    def get_by_username(username):
        """Busca um usuário pelo nome de usuário"""
        result = db_adapter.execute_query(
            'SELECT * FROM users WHERE username = %s', 
            (username,)
        )
        return User._from_db_result(result) if result else None
    
    @staticmethod
    def authenticate(username, password):
        """Autentica um usuário pelo nome de usuário e senha"""
        user = User.get_by_username(username)
        if user and check_password_hash(user.password, password):
            return user
        return None
    
    def save(self):
        """Salva um usuário no banco de dados (cria ou atualiza)"""
        if self.id:
            # Atualizar usuário existente
            db_adapter.execute_query(
                '''UPDATE users SET 
                    username = %s, 
                    password = %s, 
                    plan_id = %s, 
                    is_admin = %s 
                WHERE id = %s''',
                (self.username, self.password, self.plan_id, self.is_admin, self.id),
                commit=True
            )
            return self.id
        else:
            # Criar novo usuário
            result = db_adapter.execute_query(
                '''INSERT INTO users (username, password, plan_id, is_admin)
                VALUES (%s, %s, %s, %s)''',
                (self.username, self.password, self.plan_id, self.is_admin),
                commit=True
            )
            
            # Recuperar o ID gerado
            if db_adapter.use_postgres:
                self.id = db_adapter.get_last_insert_id('users')
            else:
                conn = db_adapter.get_db_connection()
                try:
                    cursor = conn.cursor()
                    self.id = cursor.lastrowid
                finally:
                    conn.close()
                    
            return self.id
    
    @staticmethod
    def create(username, password, plan_id=1, is_admin=False):
        """Cria um novo usuário com senha hasheada"""
        hashed_password = generate_password_hash(password)
        user = User(
            username=username,
            password=hashed_password,
            plan_id=plan_id,
            is_admin=is_admin
        )
        user.save()
        return user
    
    def get_plan(self):
        """Retorna o plano do usuário"""
        result = db_adapter.execute_query(
            'SELECT * FROM plans WHERE id = %s', 
            (self.plan_id,)
        )
        return result if result else None
    
    def get_numbers(self):
        """Retorna os números de WhatsApp do usuário"""
        return db_adapter.execute_query(
            'SELECT * FROM whatsapp_numbers WHERE user_id = %s', 
            (self.id,),
            fetch_all=True
        ) or []
    
    def get_links(self):
        """Retorna os links personalizados do usuário"""
        return db_adapter.execute_query(
            'SELECT * FROM custom_links WHERE user_id = %s', 
            (self.id,),
            fetch_all=True
        ) or []
    
    @staticmethod
    def _from_db_result(db_result):
        """Cria uma instância de User a partir de um resultado do banco de dados"""
        if not db_result:
            return None
            
        return User(
            id=db_result['id'],
            username=db_result['username'],
            password=db_result['password'],
            plan_id=db_result['plan_id'],
            is_admin=db_result['is_admin']
        )
