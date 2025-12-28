# -*- coding: utf-8 -*-
from flask import Flask
from webhook import webhook_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp)

@app.route('/')
def index():
    return {
        'status': 'online',
        'server': 'Render',
        'service': 'Webhook Mercado Pago',
        'endpoints': {
            'webhook': 'POST /webhook/mercadopago',
            'test': 'GET /webhook/test'
        }
    }

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)