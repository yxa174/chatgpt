import requests
import time
from uuid import uuid4
import os
import warnings

# Отключаем предупреждения urllib3
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

class GigaChatAuth:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = 0
        self.auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.cert_path = "sberbank.crt"  # Путь к сертификату
        
    def get_auth_header(self):
        return {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid4()),
            'Authorization': f'Basic {self._get_basic_auth()}'
        }
    
    def _get_basic_auth(self):
        import base64
        auth_string = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(auth_string.encode()).decode()
    
    def get_token(self):
        """Получает новый токен доступа"""
        payload = {'scope': 'GIGACHAT_API_PERS'}
        
        try:
            verify_setting = self.cert_path if os.path.exists(self.cert_path) else False
            
            response = requests.post(
                self.auth_url,
                headers=self.get_auth_header(),
                data=payload,
                verify=verify_setting,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access_token']
                self.token_expires = int(data['expires_at'] / 1000) - 300
                return True
            else:
                print(f"Ошибка получения токена: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"Ошибка при получении токена: {str(e)}")
            return False
    
    def is_token_valid(self):
        """Проверяет, действителен ли текущий токен"""
        if not self.access_token:
            return False
        return time.time() < self.token_expires
    
    def ensure_valid_token(self):
        """Гарантирует, что у нас есть действительный токен"""
        if not self.is_token_valid():
            print("Токен недействителен или отсутствует. Получаем новый...")
            return self.get_token()
        return True

class GigaChatAPI:
    def __init__(self, auth: GigaChatAuth):
        self.auth = auth
        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        self.cert_path = "sberbank.crt"
    
    def send_message(self, message):
        """Отправляет сообщение в GigaChat"""
        if not self.auth.ensure_valid_token():
            raise Exception("Не удалось получить действительный токен")
        
        headers = {
            'Authorization': f'Bearer {self.auth.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "GigaChat",
            "messages": [{"role": "user", "content": message}],
            "temperature": 0.7
        }
        
        try:
            verify_setting = self.cert_path if os.path.exists(self.cert_path) else False
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                verify=verify_setting,
                timeout=20
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка API: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {str(e)}")
            return None

# Пример использования
if __name__ == "__main__":
    # Инициализация аутентификации
    auth = GigaChatAuth(
        client_id="cafaab7f-2996-44db-ade8-c095e8f84583",
        client_secret="e7e0ee9e-c93d-4d74-b8fb-a841c117f11b"
    )
    
    # Инициализация API
    giga = GigaChatAPI(auth)
    
    # Проверка соединения
    if not auth.get_token():
        print("Не удалось получить токен. Проверьте credentials.")
        exit(1)
    
    # Чат-цикл
    while True:
        message = input("Вы: ")
        if message.lower() in ['exit', 'quit']:
            break
            
        response = giga.send_message(message)
        if response:
            print("GigaChat:", response['choices'][0]['message']['content'])

