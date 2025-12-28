# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
import requests
from datetime import datetime

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

SERVIDOR_LOCAL_URL = "http://192.168.1.248:5000/api/webhook/processar"

@webhook_bp.route('/mercadopago', methods=['POST'])
def webhook_mercadopago():
    try:
        data = request.get_json() or {}
        
        payment_id = None
        if 'data' in data and 'id' in data['data']:
            payment_id = data['data']['id']
        elif 'id' in data:
            payment_id = data['id']
        
        print(f"[WEBHOOK] Recebido: {payment_id}")
        
        if not payment_id:
            return jsonify({'status': 'received', 'warning': 'no payment_id'}), 200
        
        try:
            response = requests.post(
                SERVIDOR_LOCAL_URL,
                json={
                    'payment_id': payment_id,
                    'type': data.get('type'),
                    'action': data.get('action')
                },
                timeout=10
            )
            print(f"[WEBHOOK] Repassado: {response.status_code}")
        except Exception as e:
            print(f"[WEBHOOK] Erro: {e}")
        
        return jsonify({'status': 'received', 'payment_id': payment_id}), 200
        
    except Exception as e:
        print(f"[WEBHOOK] Erro: {e}")
        return jsonify({'status': 'error'}), 200

@webhook_bp.route('/test', methods=['GET'])
def test_webhook():
    return jsonify({
        'status': 'ok',
        'message': 'Webhook online!',
        'servidor_local': SERVIDOR_LOCAL_URL,
        'timestamp': datetime.now().isoformat()
    }), 200