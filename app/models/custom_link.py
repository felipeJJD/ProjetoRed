from utils.db_adapter import db_adapter
import logging


class CustomLink:
    """Modelo que representa um link personalizado no sistema"""
    
    def __init__(self, id=None, link_name=None, description=None, is_active=True, 
                 is_rotating=False, user_id=None, owner_id=None, 
                 message_template=None, custom_message=None, click_count=0):
        self.id = id
        self.link_name = link_name
        self.description = description
        self.is_active = is_active
        self.is_rotating = is_rotating
        self.user_id = user_id
        self.owner_id = owner_id
        self.message_template = message_template
        self.custom_message = custom_message
        self.click_count = click_count
    
    @staticmethod
    def get_by_id(link_id):
        """Busca um link pelo ID"""
        result = db_adapter.execute_query(
            'SELECT * FROM custom_links WHERE id = %s', 
            (link_id,)
        )
        return CustomLink._from_db_result(result) if result else None
    
    @staticmethod
    def get_by_name(link_name):
        """Busca um link pelo nome"""
        result = db_adapter.execute_query(
            'SELECT * FROM custom_links WHERE link_name = %s', 
            (link_name,)
        )
        return CustomLink._from_db_result(result) if result else None
    
    @staticmethod
    def get_by_user(user_id):
        """Busca todos os links de um usuário"""
        results = db_adapter.execute_query(
            'SELECT * FROM custom_links WHERE user_id = %s', 
            (user_id,),
            fetch_all=True
        )
        return [CustomLink._from_db_result(result) for result in results] if results else []
    
    def save(self):
        """Salva um link no banco de dados (cria ou atualiza)"""
        if self.id:
            # Atualizar link existente
            query = '''UPDATE custom_links SET 
                link_name = %s, 
                is_active = %s, 
                user_id = %s,
                custom_message = %s,
                click_count = %s
            WHERE id = %s'''
            
            # Converter booleano para inteiro
            is_active_int = 1 if self.is_active else 0
            
            params = (
                self.link_name, is_active_int, 
                self.user_id, self.custom_message, 
                self.click_count, self.id
            )
            
            try:
                db_adapter.execute_query(query, params, commit=True)
                return self.id
            except Exception as e:
                logging.error(f"Erro ao atualizar link: {str(e)}")
                raise
        else:
            # Criar novo link
            conn = db_adapter.get_db_connection()
            try:
                cursor = conn.cursor()
                
                # Converter booleano para inteiro
                is_active_int = 1 if self.is_active else 0
                
                if db_adapter.use_postgres:
                    query = '''INSERT INTO custom_links 
                        (link_name, is_active, user_id, 
                         custom_message, click_count)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id'''
                else:
                    query = '''INSERT INTO custom_links 
                        (link_name, is_active, user_id, 
                         custom_message, click_count)
                    VALUES (?, ?, ?, ?, ?)'''
                
                params = (
                    self.link_name, is_active_int, 
                    self.user_id, self.custom_message, self.click_count
                )
                
                if db_adapter.use_postgres:
                    cursor.execute(query, params)
                    self.id = cursor.fetchone()['id']
                else:
                    cursor.execute(query, params)
                    self.id = cursor.lastrowid
                
                conn.commit()
                return self.id
            except Exception as e:
                conn.rollback()
                logging.error(f"Erro ao criar link: {str(e)}")
                raise
            finally:
                conn.close()
    
    def increment_click_count(self):
        """Incrementa o contador de cliques"""
        if self.id:
            conn = db_adapter.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE custom_links SET click_count = COALESCE(click_count, 0) + 1 WHERE id = %s',
                    (self.id,)
                )
                conn.commit()
                self.click_count += 1
                return True
            except Exception as e:
                conn.rollback()
                logging.error(f"Erro ao incrementar contador de cliques: {str(e)}")
                return False
            finally:
                conn.close()
        return False
    
    def delete(self):
        """Remove um link do banco de dados"""
        if self.id:
            db_adapter.execute_query(
                'DELETE FROM custom_links WHERE id = %s',
                (self.id,),
                commit=True
            )
            return True
        return False
    
    @staticmethod
    def _from_db_result(db_result):
        """Cria uma instância de CustomLink a partir de um resultado do banco de dados"""
        if not db_result:
            return None
        
        # Converter o valor inteiro de is_active para booleano
        is_active_bool = bool(db_result['is_active'])
            
        return CustomLink(
            id=db_result['id'],
            link_name=db_result['link_name'],
            description='',  # Campo não existe na tabela PostgreSQL
            is_active=is_active_bool,
            is_rotating=False,  # Campo não existe na tabela PostgreSQL
            user_id=db_result['user_id'],
            owner_id=db_result.get('user_id'),  # Usar user_id como fallback
            message_template=None,  # Campo não existe na tabela PostgreSQL
            custom_message=db_result.get('custom_message', None),
            click_count=db_result.get('click_count', 0)
        )
