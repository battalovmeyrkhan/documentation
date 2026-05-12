import urequests as requests

class TelegramBot:
    def __init__(self, token, chat_id, topic_id=None):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.topic_id = topic_id    

    def send_message(self, message):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message
        }
        if self.topic_id is not None:
            payload["message_thread_id"] = self.topic_id
        response = requests.post(url, json=payload)
        print("Message sent:", response)
        # return response.json()

    def request_data(self):
        request = requests.get(f"{self.base_url}/getUpdates?offset={self.offset}").json()
        data = request['result']
        if not data:
            return False
        data = data[0]
        self.offset = data['update_id'] + 1
        text = data['message']['text']
        return text
        
    

    
