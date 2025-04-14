from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import requests
import os

app = Flask(__name__)
CORS(app)

ORDERS_FILE = 'orders.json'
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def save_order(order):
    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            orders = json.load(f)
    except FileNotFoundError:
        orders = []

    order['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    orders.append(order)

    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

def send_telegram_notification(order):
    items_text = '\n'.join([f"{item['count']} x {item['name']} — {item['price']}₽" for item in order['items']])
    text = f"""📦 *Новый заказ!*

👤 *Имя:* {order['name']}
📞 *Телефон:* {order['phone']}
📍 *Адрес:* {order['address']}
💬 *Комментарий:* {order.get('comment', '-') or '-'}
💳 *Оплата:* {order['payment']}
🍔 *Заказ:*
{items_text}

💰 *Итого:* {order['total']}₽
"""

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
        'reply_markup': {
            'inline_keyboard': [[
                {
                    'text': '✅ Принять заказ',
                    'callback_data': 'accept_order'
                }
            ]]
        }
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("❌ Ошибка отправки в Telegram:", e)

@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            orders = json.load(f)
    except FileNotFoundError:
        orders = []
    return jsonify(orders)

@app.route('/order', methods=['POST'])
def handle_order():
    order = request.get_json()
    name = order.get('name') or order.get('tg_user', {}).get('first_name', 'Telegram User')
    phone = order.get('phone', 'не указан')
    address = order.get('address', 'Telegram WebApp')
    comment = order.get('comment', '')
    payment = order.get('payment', 'не выбрано')
    items = order.get('items')
    total = order.get('total')

    if not items or total is None:
        return jsonify({'status': 'error', 'message': 'Пустой заказ'}), 400

    final_order = {
        'name': name,
        'phone': phone,
        'address': address,
        'comment': comment,
        'payment': payment,
        'items': items,
        'total': total
    }

    save_order(final_order)
    send_telegram_notification(final_order)

    return jsonify({'status': 'ok', 'message': 'Заказ принят'}), 200

@app.route(f'/bot{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if 'callback_query' in data:
        chat_id = data['callback_query']['message']['chat']['id']
        message_id = data['callback_query']['message']['message_id']
        callback_data = data['callback_query']['data']
        if callback_data == 'accept_order':
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
            payload = {
                'chat_id': chat_id,
                'text': '✅ Заказ принят. Готовим доставку!',
                'reply_to_message_id': message_id
            }
            requests.post(url, json=payload)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run()
