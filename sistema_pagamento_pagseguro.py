"""
Sistema Karaokê Unificado - Mercado Pago
Suporte para .AGB (Windows) e .MP4 (Android TV Box)
"""

import os
import json
import sqlite3
import hashlib
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
import mercadopago

# Configurações Mercado Pago
MERCADOPAGO_ACCESS_TOKEN = "APP_USR-828706020452811-090212-31de142a389d647842d7cb466b9882be-64322291"  # SUBSTITUIR pelo seu token
MERCADOPAGO_PUBLIC_KEY = "APP_USR-f1658047-f49a-4018-8df2-61d9646b6e68"  # SUBSTITUIR pela sua chave pública

# Inicializar SDK Mercado Pago
sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

app = Flask(__name__)

class SistemaUnificadoMercadoPago:
    def __init__(self):
        self.criar_banco()
        self.configurar_rotas()
        
    def criar_banco(self):
        """Cria banco de dados unificado"""
        self.conn = sqlite3.connect('karaoke_unificado.db', check_same_thread=False)
        c = self.conn.cursor()
        
        # Tabela de clientes expandida
        c.execute('''CREATE TABLE IF NOT EXISTS clientes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      machine_id TEXT UNIQUE,
                      tipo_sistema TEXT,  -- 'windows' ou 'android'
                      extensao TEXT,      -- '.agb' ou '.mp4'
                      nome TEXT,
                      ultimo_acesso TEXT,
                      ultima_atualizacao TEXT,
                      pacotes_atuais TEXT,
                      status TEXT)''')
        
        # Tabela de transações Mercado Pago
        c.execute('''CREATE TABLE IF NOT EXISTS transacoes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      machine_id TEXT,
                      payment_id TEXT UNIQUE,
                      preference_id TEXT,
                      pacotes TEXT,
                      tipo_arquivo TEXT,
                      valor REAL,
                      status TEXT,
                      data_criacao TEXT,
                      data_pagamento TEXT,
                      tipo_pagamento TEXT)''')
        
        # Tabela de liberações
        c.execute('''CREATE TABLE IF NOT EXISTS liberacoes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      machine_id TEXT,
                      pacotes_liberados TEXT,
                      tipo_arquivo TEXT,
                      data_liberacao TEXT,
                      baixado INTEGER DEFAULT 0)''')
        
        self.conn.commit()
    
    def configurar_rotas(self):
        """Configura todas as rotas do sistema"""
        
        @app.route('/')
        def index():
            return self.pagina_inicial()
        
        @app.route('/cliente/<machine_id>')
        def pagina_cliente(machine_id):
            # Detectar tipo de cliente pelo ID
            tipo = 'android' if machine_id.startswith('APK-') else 'windows'
            return self.gerar_pagina_cliente(machine_id, tipo)
        
        @app.route('/api/criar_pagamento', methods=['POST'])
        def criar_pagamento():
            return self.criar_checkout_mercadopago(request.json)
        
        @app.route('/api/webhook_mercadopago', methods=['POST'])
        def webhook_mercadopago():
            return self.processar_webhook_mercadopago(request.json)
        
        @app.route('/api/verificar_liberacao/<machine_id>')
        def verificar_liberacao(machine_id):
            return self.verificar_pacotes_liberados(machine_id)
        
        @app.route('/api/diagnostico_android', methods=['POST'])
        def diagnostico_android():
            """Endpoint específico para APK Android"""
            return self.analisar_cliente_android(request.json)
    
    def pagina_inicial(self):
        """Dashboard do sistema"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sistema Karaokê Unificado - Mercado Pago</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                h1 {
                    color: #333;
                    text-align: center;
                    margin-bottom: 30px;
                    font-size: 32px;
                }
                .status-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }
                .status-card {
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    border-left: 5px solid #00b4d8;
                }
                .status-card.success {
                    border-left-color: #4CAF50;
                }
                .status-card h3 {
                    margin-bottom: 15px;
                    color: #333;
                }
                .info-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }
                .info-box {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 25px;
                    border-radius: 15px;
                    text-align: center;
                    color: white;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                .info-box .number {
                    font-size: 42px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }
                .info-box .label {
                    font-size: 14px;
                    opacity: 0.9;
                }
                .system-type {
                    display: inline-block;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                    margin: 5px;
                }
                .windows { background: #0078d4; color: white; }
                .android { background: #3ddc84; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎤 Sistema Karaokê Unificado</h1>
                <h2 style="text-align: center; color: #666; margin-bottom: 30px;">
                    Mercado Pago + Windows (.agb) + Android (.mp4)
                </h2>
                
                <div class="status-card success">
                    <h3>✅ Sistema Online</h3>
                    <p>Integração Mercado Pago: <strong>ATIVA</strong></p>
                    <p>Servidor: <strong>karaoke-alex.onrender.com</strong></p>
                    <div style="margin-top: 10px;">
                        <span class="system-type windows">Windows .AGB</span>
                        <span class="system-type android">Android .MP4</span>
                    </div>
                </div>
                
                <div class="info-grid">
                    <div class="info-box">
                        <div class="number" id="vendas-hoje">0</div>
                        <div class="label">Vendas Hoje</div>
                    </div>
                    <div class="info-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                        <div class="number" id="clientes-windows">0</div>
                        <div class="label">Clientes Windows</div>
                    </div>
                    <div class="info-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                        <div class="number" id="clientes-android">0</div>
                        <div class="label">Clientes Android</div>
                    </div>
                    <div class="info-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                        <div class="number" id="receita-mes">R$ 0</div>
                        <div class="label">Receita do Mês</div>
                    </div>
                </div>
                
                <div class="status-grid">
                    <div class="status-card">
                        <h3>📊 Estatísticas Windows (.AGB)</h3>
                        <p>Máquinas ativas: <strong id="windows-ativas">0</strong></p>
                        <p>Pacotes vendidos: <strong id="windows-pacotes">0</strong></p>
                        <p>Última atualização: <strong id="windows-ultima">-</strong></p>
                    </div>
                    
                    <div class="status-card">
                        <h3>📱 Estatísticas Android (.MP4)</h3>
                        <p>TV Boxes ativas: <strong id="android-ativas">0</strong></p>
                        <p>Pacotes vendidos: <strong id="android-pacotes">0</strong></p>
                        <p>Última atualização: <strong id="android-ultima">-</strong></p>
                    </div>
                </div>
            </div>
            
            <script>
                // Atualizar estatísticas
                function atualizarStats() {
                    fetch('/api/estatisticas')
                        .then(r => r.json())
                        .then(data => {
                            document.getElementById('vendas-hoje').innerText = data.vendas_hoje || 0;
                            document.getElementById('clientes-windows').innerText = data.clientes_windows || 0;
                            document.getElementById('clientes-android').innerText = data.clientes_android || 0;
                            document.getElementById('receita-mes').innerText = 'R$ ' + (data.receita_mes || 0).toFixed(2);
                        });
                }
                
                setInterval(atualizarStats, 30000);
                atualizarStats();
            </script>
        </body>
        </html>
        """
        return html
    
    def gerar_pagina_cliente(self, machine_id, tipo_sistema):
        """Gera página de pagamento adaptada ao tipo de cliente"""
        
        # Determinar extensão baseado no tipo
        extensao = '.mp4' if tipo_sistema == 'android' else '.agb'
        titulo_sistema = 'TV Box Android' if tipo_sistema == 'android' else 'Windows Professional'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Atualização Karaokê - {titulo_sistema}</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://sdk.mercadopago.com/js/v2"></script>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .system-badge {{
                    display: inline-block;
                    padding: 8px 20px;
                    border-radius: 25px;
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 15px;
                    {'background: #3ddc84; color: white;' if tipo_sistema == 'android' else 'background: #0078d4; color: white;'}
                }}
                .pacotes-section {{
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .pacote-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    margin: 8px 0;
                    background: white;
                    border-radius: 8px;
                    transition: all 0.3s;
                }}
                .pacote-item:hover {{
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }}
                .pacote-item input[type="checkbox"] {{
                    width: 20px;
                    height: 20px;
                    cursor: pointer;
                }}
                .preco {{
                    font-weight: bold;
                    color: #00b4d8;
                    font-size: 18px;
                }}
                .pre-venda {{
                    background: #ffd60a;
                    color: #003566;
                    padding: 3px 10px;
                    border-radius: 15px;
                    font-size: 11px;
                    font-weight: bold;
                    margin-left: 10px;
                }}
                .total-section {{
                    background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
                    color: white;
                    border-radius: 15px;
                    padding: 25px;
                    margin: 20px 0;
                    text-align: center;
                }}
                .total-valor {{
                    font-size: 42px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .btn-pagar {{
                    background: #009ee3;
                    color: white;
                    border: none;
                    padding: 18px 40px;
                    font-size: 18px;
                    font-weight: bold;
                    border-radius: 50px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 20px;
                    transition: all 0.3s;
                    box-shadow: 0 10px 30px rgba(0,158,227,0.3);
                }}
                .btn-pagar:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 15px 40px rgba(0,158,227,0.4);
                }}
                #cho-container {{
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <span class="system-badge">
                        {'📱 Android TV Box - MP4' if tipo_sistema == 'android' else '💻 Windows Professional - AGB'}
                    </span>
                    <h1>🎤 Atualização Karaokê</h1>
                    <p style="color: #666;">Máquina: {machine_id}</p>
                </div>
                
                <div class="pacotes-section">
                    <h3>📦 Pacotes Disponíveis ({extensao})</h3>
                    <div id="lista-pacotes">
                        <!-- Pacotes serão carregados aqui -->
                    </div>
                </div>
                
                <div class="total-section">
                    <div>Total a Pagar:</div>
                    <div class="total-valor" id="valor-total">R$ 0,00</div>
                    <div id="economia" style="font-size: 14px; margin-top: 10px;"></div>
                </div>
                
                <button class="btn-pagar" id="btn-pagar" onclick="processarPagamento()">
                    💳 PAGAR COM MERCADO PAGO
                </button>
                
                <div id="cho-container"></div>
            </div>
            
            <script>
                const mp = new MercadoPago('{MERCADOPAGO_PUBLIC_KEY}');
                const machineId = '{machine_id}';
                const tipoSistema = '{tipo_sistema}';
                const extensao = '{extensao}';
                let pacotesSelecionados = [];
                let valorTotal = 0;
                
                // Carregar pacotes disponíveis
                function carregarPacotes() {{
                    // Simulação - seria uma chamada real à API
                    const pacotes = [
                        {{codigo: '41A', preco: 25.00, preVenda: false}},
                        {{codigo: '41B', preco: 25.00, preVenda: false}},
                        {{codigo: '41C', preco: 15.00, preVenda: true}},
                        {{codigo: '41D', preco: 15.00, preVenda: true}}
                    ];
                    
                    let html = '';
                    pacotes.forEach(p => {{
                        html += `
                            <div class="pacote-item">
                                <label style="display: flex; align-items: center;">
                                    <input type="checkbox" value="${{p.codigo}}" data-preco="${{p.preco}}" onchange="atualizarTotal()">
                                    <span style="margin-left: 10px;">
                                        Pacote ${{p.codigo}} (${{extensao}})
                                        ${{p.preVenda ? '<span class="pre-venda">PRÉ-VENDA</span>' : ''}}
                                    </span>
                                </label>
                                <span class="preco">R$ ${{p.preco.toFixed(2)}}</span>
                            </div>
                        `;
                    }});
                    document.getElementById('lista-pacotes').innerHTML = html;
                }}
                
                function atualizarTotal() {{
                    let total = 0;
                    
                    const checkboxes = document.querySelectorAll('.pacote-item input[type="checkbox"]:checked');
                    pacotesSelecionados = [];
                    checkboxes.forEach(cb => {{
                        pacotesSelecionados.push(cb.value);
                        total += parseFloat(cb.dataset.preco);
                    }});
                    
                    // Aplicar teto de R$ 500
                    const tetoMaximo = 500;
                    let economia = 0;
                    if (total > tetoMaximo) {{
                        economia = total - tetoMaximo;
                        total = tetoMaximo;
                        document.getElementById('economia').innerHTML = 
                            `⭐ Promoção aplicada! Economia de R$ ${{economia.toFixed(2)}}`;
                    }}
                    
                    valorTotal = total;
                    document.getElementById('valor-total').innerText = `R$ ${{total.toFixed(2)}}`;
                    document.getElementById('btn-pagar').disabled = total === 0;
                }}
                
                function processarPagamento() {{
                    if (valorTotal === 0) {{
                        alert('Selecione ao menos um pacote!');
                        return;
                    }}
                    
                    const dados = {{
                        machine_id: machineId,
                        tipo_sistema: tipoSistema,
                        extensao: extensao,
                        pacotes: pacotesSelecionados,
                        valor: valorTotal
                    }};
                    
                    // Criar preferência no Mercado Pago
                    fetch('/api/criar_pagamento', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(dados)
                    }})
                    .then(r => r.json())
                    .then(data => {{
                        if (data.success) {{
                            // Redirecionar para checkout do Mercado Pago
                            window.location.href = data.init_point;
                        }} else {{
                            alert('Erro ao processar pagamento');
                        }}
                    }});
                }}
                
                // Inicializar
                carregarPacotes();
                atualizarTotal();
            </script>
        </body>
        </html>
        """
        return html
    
    def criar_checkout_mercadopago(self, dados):
        """Cria checkout no Mercado Pago"""
        try:
            # Criar preferência de pagamento
            preference_data = {
                "items": [
                    {
                        "title": f"Atualização Karaokê - Pacotes: {', '.join(dados['pacotes'])}",
                        "quantity": 1,
                        "unit_price": dados['valor'],
                        "currency_id": "BRL"
                    }
                ],
                "payer": {
                    "email": "cliente@example.com"
                },
                "back_urls": {
                    "success": f"https://karaoke-alex.onrender.com/pagamento_sucesso",
                    "failure": f"https://karaoke-alex.onrender.com/pagamento_erro",
                    "pending": f"https://karaoke-alex.onrender.com/pagamento_pendente"
                },
                "auto_return": "approved",
                "notification_url": "https://karaoke-alex.onrender.com/api/webhook_mercadopago",
                "external_reference": f"{dados['machine_id']}_{int(datetime.now().timestamp())}"
            }
            
            preference_response = sdk.preference().create(preference_data)
            preference = preference_response["response"]
            
            # Salvar transação no banco
            c = self.conn.cursor()
            c.execute('''INSERT INTO transacoes 
                       (machine_id, preference_id, pacotes, tipo_arquivo, valor, status, data_criacao)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (dados['machine_id'], preference["id"], json.dumps(dados['pacotes']),
                      dados.get('extensao', '.agb'), dados['valor'], 'PENDENTE',
                      datetime.now().isoformat()))
            self.conn.commit()
            
            return jsonify({
                'success': True,
                'init_point': preference["init_point"],  # URL do checkout
                'preference_id': preference["id"]
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def processar_webhook_mercadopago(self, dados):
        """Processa notificação de pagamento do Mercado Pago"""
        try:
            # Mercado Pago envia type e data.id
            if dados.get("type") == "payment":
                payment_id = dados["data"]["id"]
                
                # Buscar detalhes do pagamento
                payment = sdk.payment().get(payment_id)
                payment_info = payment["response"]
                
                if payment_info["status"] == "approved":
                    # Pagamento aprovado - liberar pacotes
                    external_ref = payment_info["external_reference"]
                    machine_id = external_ref.split("_")[0]
                    
                    # Buscar transação
                    c = self.conn.cursor()
                    c.execute("SELECT pacotes, tipo_arquivo FROM transacoes WHERE machine_id = ? ORDER BY id DESC LIMIT 1", 
                             (machine_id,))
                    result = c.fetchone()
                    
                    if result:
                        pacotes, tipo_arquivo = result
                        
                        # Criar liberação
                        c.execute('''INSERT INTO liberacoes 
                                   (machine_id, pacotes_liberados, tipo_arquivo, data_liberacao)
                                   VALUES (?, ?, ?, ?)''',
                                 (machine_id, pacotes, tipo_arquivo, datetime.now().isoformat()))
                        
                        # Atualizar status da transação
                        c.execute('''UPDATE transacoes 
                                   SET status = 'PAGO', payment_id = ?, data_pagamento = ?
                                   WHERE machine_id = ? AND status = 'PENDENTE' ''',
                                 (payment_id, datetime.now().isoformat(), machine_id))
                        
                        self.conn.commit()
            
            return "OK", 200
            
        except Exception as e:
            print(f"Erro webhook: {e}")
            return "ERROR", 500
    
    def verificar_pacotes_liberados(self, machine_id):
        """Verifica pacotes liberados para download"""
        c = self.conn.cursor()
        c.execute('''SELECT pacotes_liberados, tipo_arquivo 
                    FROM liberacoes 
                    WHERE machine_id = ? AND baixado = 0
                    ORDER BY data_liberacao DESC LIMIT 1''', 
                 (machine_id,))
        result = c.fetchone()
        
        if result:
            pacotes, tipo_arquivo = result
            return jsonify({
                'tem_atualizacao': True,
                'pacotes': json.loads(pacotes),
                'tipo_arquivo': tipo_arquivo
            })
        else:
            return jsonify({
                'tem_atualizacao': False
            })
    
    def analisar_cliente_android(self, dados):
        """Analisa cliente Android e retorna pacotes faltantes"""
        machine_id = dados.get('machine_id')
        pacotes_atuais = dados.get('pacotes_atuais', [])
        
        # Aqui você implementaria a lógica real de comparação
        # Por enquanto, vamos simular
        todos_pacotes = ['41A', '41B', '41C', '41D', '41E']
        pacotes_faltantes = [p for p in todos_pacotes if p not in pacotes_atuais]
        
        # Registrar/atualizar cliente
        c = self.conn.cursor()
        c.execute('''INSERT OR REPLACE INTO clientes 
                   (machine_id, tipo_sistema, extensao, ultimo_acesso, pacotes_atuais)
                   VALUES (?, ?, ?, ?, ?)''',
                 (machine_id, 'android', '.mp4', datetime.now().isoformat(), 
                  json.dumps(pacotes_atuais)))
        self.conn.commit()
        
        return jsonify({
            'machine_id': machine_id,
            'pacotes_faltantes': pacotes_faltantes,
            'url_pagamento': f'https://karaoke-alex.onrender.com/cliente/{machine_id}'
        })
    
    def run(self, host='0.0.0.0', port=8000):
        """Inicia o servidor"""
        print(f"""
        ╔════════════════════════════════════════════════════╗
        ║   SISTEMA KARAOKÊ UNIFICADO - MERCADO PAGO         ║
        ╚════════════════════════════════════════════════════╝
        
        ✅ Suporte Windows (.AGB)
        ✅ Suporte Android TV Box (.MP4)
        ✅ Integração Mercado Pago
        
        Servidor rodando em: http://{host}:{port}
        """)
        
        app.run(host=host, port=port, debug=False)

# Inicializar e rodar
if __name__ == "__main__":
    sistema = SistemaUnificadoMercadoPago()
    sistema.run()
