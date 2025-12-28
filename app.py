# 🎤 GUEDES-OKÊ AUTO+ - SERVIDOR RENDER
# Arquivo: app.py (para deploy no Render)
# URL: https://karaoke-alex.onrender.com

from flask import Flask, request, jsonify, render_template_string, redirect
import requests
import os
import json
import hashlib
import hmac
from datetime import datetime

app = Flask(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

SERVIDOR_LOCAL = "http://192.168.1.248:5000"  # Servidor do Alex
MERCADOPAGO_TOKEN = os.environ.get('MERCADOPAGO_TOKEN', '')  # Configurar no Render

# ============================================================================
# PÁGINA INICIAL (teste)
# ============================================================================

@app.route('/')
def home():
    """Página inicial - mostra status dos endpoints"""
    
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Guedes-Okê AUTO+ - API</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .card {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 100%;
            }
            h1 { color: #667eea; margin-bottom: 10px; }
            .status { color: #27ae60; font-size: 18px; margin-bottom: 30px; }
            .endpoint {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                border-left: 4px solid #667eea;
            }
            .endpoint code {
                background: #e9ecef;
                padding: 2px 8px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎤 Guedes-Okê AUTO+</h1>
            <p class="status">✅ Servidor Online</p>
            
            <div class="endpoint">
                <strong>📱 Checkout</strong><br>
                <code>GET /checkout/{session_id}</code>
            </div>
            
            <div class="endpoint">
                <strong>🔔 Webhook Teste</strong><br>
                <code>GET /webhook/test</code>
            </div>
            
            <div class="endpoint">
                <strong>💳 Webhook Mercado Pago</strong><br>
                <code>POST /webhook/mercadopago</code>
            </div>
            
            <p style="margin-top: 30px; color: #666; font-size: 14px;">
                <strong>Servidor Local:</strong> """ + SERVIDOR_LOCAL + """<br>
                <strong>Timestamp:</strong> """ + datetime.now().isoformat() + """
            </p>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html)

# ============================================================================
# PÁGINA DE CHECKOUT
# ============================================================================

@app.route('/checkout/<session_id>')
def checkout(session_id):
    """Página de checkout para o cliente"""
    
    # Busca dados da sessão no servidor local
    try:
        response = requests.get(f"{SERVIDOR_LOCAL}/api/checkout/{session_id}", timeout=5)
        
        if response.status_code != 200:
            return render_template_string(erro_page("Sessão não encontrada"))
        
        data = response.json()
        
    except Exception as e:
        return render_template_string(erro_page(f"Erro ao conectar com servidor: {e}"))
    
    # HTML da página de checkout
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Checkout - Guedes-Okê</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
            }
            .card {
                background: white;
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            .header h1 {
                color: #667eea;
                font-size: 28px;
                margin-bottom: 5px;
            }
            .header p {
                color: #666;
                font-size: 14px;
            }
            .machine-info {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .machine-info strong {
                color: #667eea;
            }
            .pacotes-list {
                margin: 20px 0;
            }
            .pacote-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: #f8f9fa;
                border-radius: 8px;
                margin-bottom: 8px;
            }
            .pacote-item.pre-venda {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
            }
            .pacote-codigo {
                font-weight: bold;
                color: #333;
            }
            .pacote-tipo {
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }
            .pacote-preco {
                font-size: 18px;
                font-weight: bold;
                color: #27ae60;
            }
            .total-section {
                background: #667eea;
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin: 20px 0;
            }
            .total-section .label {
                font-size: 14px;
                opacity: 0.9;
            }
            .total-section .value {
                font-size: 36px;
                font-weight: bold;
                margin-top: 5px;
            }
            .btn-pagar {
                display: block;
                width: 100%;
                padding: 18px;
                background: #27ae60;
                color: white;
                text-align: center;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                text-decoration: none;
                transition: all 0.3s;
            }
            .btn-pagar:hover {
                background: #229954;
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(39, 174, 96, 0.4);
            }
            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
            }
            .status-pendente {
                background: #fff3cd;
                color: #856404;
            }
            .status-aprovado {
                background: #d4edda;
                color: #155724;
            }
            .loading {
                text-align: center;
                padding: 40px;
                display: none;
            }
            .loading.active {
                display: block;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .footer {
                text-align: center;
                color: white;
                margin-top: 20px;
                font-size: 14px;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="header">
                    <h1>🎤 Guedes-Okê AUTO+</h1>
                    <p>Atualização de Músicas</p>
                </div>
                
                <div class="machine-info">
                    <p><strong>Máquina:</strong> {{ apelido_maquina or machine_id }}</p>
                    {% if nome_cliente %}
                    <p><strong>Cliente:</strong> {{ nome_cliente }}</p>
                    {% endif %}
                    <p><span class="status-badge status-{{ status }}">{{ status }}</span></p>
                </div>
                
                <h3 style="margin: 20px 0 10px; color: #333;">📦 Pacotes Disponíveis</h3>
                
                <div class="pacotes-list">
                    {% for pacote in pacotes_detalhados %}
                    <div class="pacote-item {% if pacote.pre_venda %}pre-venda{% endif %}">
                        <div>
                            <div class="pacote-codigo">{{ pacote.codigo }}</div>
                            <div class="pacote-tipo">
                                {{ pacote.tipo }} • {{ pacote.quantidade }} músicas
                                {% if pacote.pre_venda %}<span style="color: #ffc107;">⭐ PRÉ-VENDA</span>{% endif %}
                            </div>
                        </div>
                        <div class="pacote-preco">R$ {{ "%.2f"|format(pacote.preco) }}</div>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="total-section">
                    <div class="label">VALOR TOTAL</div>
                    <div class="value">R$ {{ "%.2f"|format(valor_total) }}</div>
                    <p style="font-size: 12px; margin-top: 10px; opacity: 0.9;">
                        {{ pacotes_detalhados|length }} pacotes • 
                        {{ (pacotes_detalhados|sum(attribute='quantidade')) }} músicas
                    </p>
                </div>
                
                {% if status == 'pendente' %}
                <button class="btn-pagar" onclick="iniciarPagamento()">
                    💳 PAGAR AGORA
                </button>
                {% else %}
                <div style="text-align: center; padding: 20px; background: #d4edda; border-radius: 10px; color: #155724;">
                    <h3>✅ PAGAMENTO CONFIRMADO!</h3>
                    <p style="margin-top: 10px;">Sua máquina será atualizada automaticamente</p>
                </div>
                {% endif %}
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p style="color: #667eea; font-weight: bold;">Processando pagamento...</p>
                    <p style="color: #666; font-size: 14px; margin-top: 10px;">
                        Aguarde a confirmação
                    </p>
                </div>
            </div>
            
            <div class="footer">
                <p>🔒 Pagamento seguro via Mercado Pago</p>
                <p style="font-size: 12px; margin-top: 5px;">Session: {{ session_id[:8] }}...</p>
            </div>
        </div>
        
        <script>
            const SESSION_ID = '{{ session_id }}';
            const API_URL = 'https://karaoke-alex.onrender.com';
            
            async function iniciarPagamento() {
                try {
                    // Mostra loading
                    document.getElementById('loading').classList.add('active');
                    
                    // Cria preferência de pagamento
                    const response = await fetch(`${API_URL}/api/criar-pagamento`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: SESSION_ID,
                            valor: {{ valor_total }},
                            descricao: '{{ pacotes_detalhados|length }} pacotes de músicas'
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.init_point) {
                        // Redireciona para Mercado Pago
                        window.location.href = data.init_point;
                    } else {
                        alert('Erro ao criar pagamento. Tente novamente.');
                        document.getElementById('loading').classList.remove('active');
                    }
                    
                } catch (error) {
                    console.error('Erro:', error);
                    alert('Erro ao processar pagamento. Verifique sua conexão.');
                    document.getElementById('loading').classList.remove('active');
                }
            }
            
            // Verifica status de pagamento a cada 5 segundos
            {% if status == 'pendente' %}
            setInterval(async () => {
                try {
                    const response = await fetch(`${API_URL}/api/status/${SESSION_ID}`);
                    const data = await response.json();
                    
                    if (data.status === 'pago') {
                        location.reload();
                    }
                } catch (error) {
                    console.error('Erro ao verificar status:', error);
                }
            }, 5000);
            {% endif %}
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html, **data)

def erro_page(mensagem):
    """Página de erro"""
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Erro - Guedes-Okê</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .erro-card {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                text-align: center;
                max-width: 500px;
            }}
            h1 {{ color: #e74c3c; }}
        </style>
    </head>
    <body>
        <div class="erro-card">
            <h1>❌ Erro</h1>
            <p>{mensagem}</p>
            <p style="margin-top: 20px; color: #666; font-size: 14px;">
                Se o problema persistir, entre em contato com o suporte.
            </p>
        </div>
    </body>
    </html>
    """

# ============================================================================
# API: CRIAR PAGAMENTO MERCADO PAGO
# ============================================================================

@app.route('/api/criar-pagamento', methods=['POST'])
def criar_pagamento():
    """Cria preferência de pagamento no Mercado Pago"""
    
    try:
        data = request.json
        session_id = data.get('session_id')
        valor = data.get('valor')
        descricao = data.get('descricao')
        
        # Cria preferência no Mercado Pago
        preference_data = {
            "items": [
                {
                    "title": f"Guedes-Okê - {descricao}",
                    "quantity": 1,
                    "unit_price": float(valor),
                    "currency_id": "BRL"
                }
            ],
            "back_urls": {
                "success": f"https://karaoke-alex.onrender.com/checkout/{session_id}",
                "failure": f"https://karaoke-alex.onrender.com/checkout/{session_id}",
                "pending": f"https://karaoke-alex.onrender.com/checkout/{session_id}"
            },
            "auto_return": "approved",
            "external_reference": session_id,
            "notification_url": "https://karaoke-alex.onrender.com/webhook/mercadopago",
            "payment_methods": {
                "excluded_payment_types": [
                    {"id": "ticket"},  # Exclui boleto
                    {"id": "atm"}      # Exclui pagamento em caixa eletrônico
                ],
                "installments": 1  # Apenas à vista
            }
        }
        
        headers = {
            "Authorization": f"Bearer {MERCADOPAGO_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://api.mercadopago.com/checkout/preferences",
            json=preference_data,
            headers=headers
        )
        
        if response.status_code == 201:
            preference = response.json()
            return jsonify({
                "init_point": preference['init_point'],
                "preference_id": preference['id']
            })
        else:
            return jsonify({"error": "Erro ao criar preferência"}), 500
            
    except Exception as e:
        print(f"❌ Erro ao criar pagamento: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# API: STATUS DO PAGAMENTO
# ============================================================================

@app.route('/api/status/<session_id>')
def verificar_status(session_id):
    """Verifica status do pagamento"""
    
    try:
        response = requests.get(f"{SERVIDOR_LOCAL}/api/checkout/{session_id}")
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({"status": data.get('status')})
        else:
            return jsonify({"error": "Sessão não encontrada"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# WEBHOOK MERCADO PAGO
# ============================================================================

@app.route('/webhook/mercadopago', methods=['POST'])
def webhook_mercadopago():
    """Recebe notificação do Mercado Pago"""
    
    try:
        # Log da requisição
        print(f"📬 Webhook recebido: {datetime.now()}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {request.json}")
        
        data = request.json
        
        # Verifica se é notificação de pagamento
        if data.get('type') == 'payment':
            payment_id = data['data']['id']
            
            # Busca detalhes do pagamento
            headers = {"Authorization": f"Bearer {MERCADOPAGO_TOKEN}"}
            response = requests.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                payment = response.json()
                
                # Verifica se foi aprovado
                if payment['status'] == 'approved':
                    session_id = payment.get('external_reference')
                    
                    # Notifica servidor local
                    requests.post(
                        f"{SERVIDOR_LOCAL}/api/webhook/confirmar-pagamento",
                        json={
                            "session_id": session_id,
                            "payment_id": payment_id,
                            "status": "approved"
                        }
                    )
                    
                    print(f"✅ Pagamento confirmado: {payment_id}")
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# WEBHOOK TESTE
# ============================================================================

@app.route('/webhook/test')
def webhook_test():
    """Endpoint de teste do webhook"""
    
    try:
        # Testa conexão com servidor local
        response = requests.get(f"{SERVIDOR_LOCAL}/admin", timeout=5)
        
        return jsonify({
            "message": "Webhook online!",
            "servidor_local": SERVIDOR_LOCAL,
            "servidor_local_status": "ok" if response.status_code == 200 else "offline",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "message": "Webhook online!",
            "servidor_local": SERVIDOR_LOCAL,
            "servidor_local_status": f"erro: {e}",
            "timestamp": datetime.now().isoformat()
        })

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
