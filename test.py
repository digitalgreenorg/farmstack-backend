# import requests

# # Replace 'YOUR_API_TOKEN' with the token you received from BotFather
# API_TOKEN = '6050100534:AAGvbJtylfiL2rO2qW8Nzx6XUwcVEihuX8M'
# BASE_URL = f'https://api.telegram.org/bot{API_TOKEN}/'


# def get_updates(offset=None):
#     method = 'getUpdates'
#     url = BASE_URL + method
#     params = {'offset': offset, 'timeout': 60}
#     response = requests.get(url, params=params)
#     return response.json()

# def send_message(chat_id, text):
#     method = 'sendMessage'
#     url = BASE_URL + method
#     data = {'chat_id': chat_id, 'text': text}
#     response = requests.post(url, data=data)
#     return response.json()

# if __name__ == '__main__':
#     last_update_id = None

#     while True:
#         updates = get_updates(offset=last_update_id)
        
#         if updates['ok']:
#             for update in updates['result']:
#                 message = update['message']
#                 chat_id = message['chat']['id']
#                 user_message = message.get('text', '')

#                 # Respond to the user's message
#                 if user_message.lower() == 'hello':
#                     send_message(chat_id, 'Hello! How can I assist you?')

#                 # Update the last_update_id to avoid processing the same update again
#                 last_update_id = update['update_id'] + 1

import secrets


def generate_api_key(length=32):
    api_key = secrets.token_hex(length)
    return api_key

# Generate an API key
api_key = generate_api_key()
print("Generated API Key:", api_key)
