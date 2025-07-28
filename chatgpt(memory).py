import requests
import time
from uuid import uuid4
import os
import warnings
from collections import deque

# Отключаем предупреждения urllib3
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

class GigaChatAuth:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = 0
        self.auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.cert_path = "sberbank.crt"

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
                return False
        except Exception as e:
            print(f"Ошибка при получении токена: {str(e)}")
            return False
    
    def is_token_valid(self):
        if not self.access_token:
            return False
        return time.time() < self.token_expires
    
    def ensure_valid_token(self):
        if not self.is_token_valid():
            print("Получаем новый токен...")
            return self.get_token()
        return True

class GigaChatAPI:
    def __init__(self, auth: GigaChatAuth, history_size=6):
        self.auth = auth
        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        self.cert_path = "sberbank.crt"
        self.message_history = deque(maxlen=history_size)  # Хранит последние 6 сообщений
    
    def _prepare_messages(self, new_message):
        # Добавляем новое сообщение в историю
        self.message_history.append({"role": "user", "content": new_message})
        
        # Формируем список сообщений для отправки
        return list(self.message_history)
    
    def send_message(self, message):
        if not self.auth.ensure_valid_token():
            raise Exception("Не удалось получить токен")
        
        # Подготавливаем сообщения с историей
        messages = self._prepare_messages(message)
        
        headers = {
            'Authorization': f'Bearer {self.auth.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "GigaChat",
            "messages": messages,
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
                # Добавляем ответ ассистента в историю
                assistant_response = response.json()['choices'][0]['message']
                self.message_history.append(assistant_response)
                return response.json()
            else:
                print(f"Ошибка API: {response.status_code}")
                return None
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {str(e)}")
            return None

if __name__ == "__main__":
    auth = GigaChatAuth(
        client_id="cafaab7f-2996-44db-ade8-c095e8f84583",
        client_secret="e7e0ee9e-c93d-4d74-b8fb-a841c117f11b"
    )
    
    giga = GigaChatAPI(auth)
    
    if not auth.get_token():
        print("Не удалось получить токен. Проверьте credentials.")
        exit(1)
    
    print("Чат с GigaChat (введите 'exit' для выхода)")
    while True:
        message = input("Вы: ")
        if message.lower() in ['exit', 'quit']:
            break
            
        response = giga.send_message(message)
        if response:
            print("GigaChat:", response['choices'][0]['message']['content'])
