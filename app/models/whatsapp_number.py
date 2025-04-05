from utils.db_adapter import db_adapter


class WhatsAppNumber:
    """Modelo que representa um número de WhatsApp no sistema"""
    
    def __init__(self, id=None, phone_number=None, description=None, 
                 is_active=True, user_id=None, redirect_count=0):
        self.id = id
        self.phone_number = phone_number
        self.description = description
        self.is_active = is_active
        self.user_id = user_id
        self.redirect_count = redirect_count
    
    @staticmethod
    def get_by_id(number_id):
        """Busca um número pelo ID"""
        result = db_adapter.execute_query(
            'SELECT * FROM whatsapp_numbers WHERE id = %s', 
            (number_id,)
        )
        return WhatsAppNumber._from_db_result(result) if result else None
    
    @staticmethod
    def get_active_by_user(user_id):
        """Busca todos os números ativos de um usuário"""
        results = db_adapter.execute_query(
            'SELECT * FROM whatsapp_numbers WHERE user_id = %s AND is_active = %s', 
            (user_id, 1),
            fetch_all=True
        )
        return [WhatsAppNumber._from_db_result(result) for result in results] if results else []
    
    @staticmethod
    def get_by_phone(phone_number, user_id=None):
        """Busca um número pelo número de telefone, opcionalmente filtrando por usuário"""
        query = 'SELECT * FROM whatsapp_numbers WHERE phone_number = %s'
        params = [phone_number]
        
        if user_id is not None:
            query += ' AND user_id = %s'
            params.append(user_id)
        
        result = db_adapter.execute_query(query, tuple(params))
        return WhatsAppNumber._from_db_result(result) if result else None
    
    def save(self):
        """Salva um número no banco de dados (cria ou atualiza)"""
        # Converter booleano para inteiro para compatibilidade com PostgreSQL
        is_active_int = 1 if self.is_active else 0
        
        if self.id:
            # Atualizar número existente
            db_adapter.execute_query(
                '''UPDATE whatsapp_numbers SET 
                    phone_number = %s, 
                    description = %s, 
                    is_active = %s, 
                    user_id = %s,
                    redirect_count = %s
                WHERE id = %s''',
                (self.phone_number, self.description, is_active_int, 
                 self.user_id, self.redirect_count, self.id),
                commit=True
            )
            return self.id
        else:
            # Criar novo número
            conn = db_adapter.get_db_connection()
            try:
                cursor = conn.cursor()
                
                if db_adapter.use_postgres:
                    cursor.execute(
                        '''INSERT INTO whatsapp_numbers 
                            (phone_number, description, is_active, user_id, redirect_count)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id''',
                        (self.phone_number, self.description, is_active_int, 
                         self.user_id, self.redirect_count)
                    )
                    self.id = cursor.fetchone()['id']
                else:
                    cursor.execute(
                        '''INSERT INTO whatsapp_numbers 
                            (phone_number, description, is_active, user_id, redirect_count)
                        VALUES (?, ?, ?, ?, ?)''',
                        (self.phone_number, self.description, self.is_active, 
                         self.user_id, self.redirect_count)
                    )
                    self.id = cursor.lastrowid
                
                conn.commit()
                return self.id
            finally:
                conn.close()
    
    def increment_redirect_count(self):
        """Incrementa o contador de redirecionamentos"""
        if self.id:
            conn = db_adapter.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE whatsapp_numbers SET redirect_count = redirect_count + 1 WHERE id = %s',
                    (self.id,)
                )
                conn.commit()
                self.redirect_count += 1
            finally:
                conn.close()
    
    def delete(self):
        """Remove um número do banco de dados"""
        if self.id:
            db_adapter.execute_query(
                'DELETE FROM whatsapp_numbers WHERE id = %s',
                (self.id,),
                commit=True
            )
            return True
        return False
    
    @staticmethod
    def _from_db_result(db_result):
        """Cria uma instância de WhatsAppNumber a partir de um resultado do banco de dados"""
        if not db_result:
            return None
        
        # Converter is_active de inteiro para booleano
        is_active_bool = bool(db_result['is_active'])
            
        return WhatsAppNumber(
            id=db_result['id'],
            phone_number=db_result['phone_number'],
            description=db_result.get('description', ''),
            is_active=is_active_bool,
            user_id=db_result['user_id'],
            redirect_count=db_result.get('redirect_count', 0)
        )
