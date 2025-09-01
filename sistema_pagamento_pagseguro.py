"""
Sistema de Pagamento Automático com PagSeguro
Integração completa para Karaokê - Alex
"""

import os
import json
import hashlib
import requests
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from threading import Thread
import time

# Configurações PagSeguro
PAGSEGURO_EMAIL = "alexdorj@gmail.com"  # SUBSTITUIR pelo seu email do PagSeguro
PAGSEGURO_TOKEN = "fc0031b8-b276-40ce-8bed-632df68a537a0462468b4cbc8d6e444443968856e9b7c2c0-0c62-4572-8f5f-64ee6fefd8ac"  # SUBSTITUIR pelo seu token do PagSeguro
PAGSEGURO_SANDBOX = False  # True para testes, False para produção

# URLs do PagSeguro
if PAGSEGURO_SANDBOX:
    PAGSEGURO_URL = "https://sandbox.pagseguro.uol.com.br"
    PAGSEGURO_WS = "https://ws.sandbox.pagseguro.uol.com.br"
else:
    PAGSEGURO_URL = "https://pagseguro.uol.com.br"
    PAGSEGURO_WS = "https://ws.pagseguro.uol.com.br"

app = Flask(__name__)

class SistemaPagamentoPagSeguro:
    def __init__(self):
        self.criar_banco()
        self.configurar_rotas()
        
    def criar_banco(self):
        """Cria banco de dados para controle de pagamentos"""
        self.conn = sqlite3.connect('pagamentos_karaoke.db', check_same_thread=False)
        c = self.conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS transacoes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      machine_id TEXT,
                      codigo_pagseguro TEXT UNIQUE,
                      reference TEXT,
                      pacotes TEXT,
                      valor REAL,
                      status TEXT,
                      data_criacao TEXT,
                      data_pagamento TEXT,
                      tipo_pagamento TEXT,
                      link_pagamento TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS liberacoes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      machine_id TEXT,
                      pacotes_liberados TEXT,
                      data_liberacao TEXT,
                      transacao_id INTEGER,
                      baixado INTEGER DEFAULT 0)''')
        
        self.conn.commit()
    
    def configurar_rotas(self):
        """Configura todas as rotas do servidor"""
        
        @app.route('/')
        def index():
            return self.pagina_inicial()
        
        @app.route('/cliente/<machine_id>')
        def pagina_cliente(machine_id):
            return self.gerar_pagina_cliente(machine_id)
        
        @app.route('/api/criar_pagamento', methods=['POST'])
        def criar_pagamento():
            return self.criar_checkout_pagseguro(request.json)
        
        @app.route('/api/notificacao_pagseguro', methods=['POST'])
        def notificacao_pagseguro():
            return self.processar_notificacao_pagseguro(request.form)
        
        @app.route('/api/verificar_liberacao/<machine_id>')
        def verificar_liberacao(machine_id):
            return self.verificar_pacotes_liberados(machine_id)
        
        @app.route('/api/confirmar_download/<machine_id>', methods=['POST'])
        def confirmar_download(machine_id):
            return self.marcar_como_baixado(machine_id)
    
    def pagina_inicial(self):
        """Página inicial do sistema"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sistema Karaokê - Pagamento Automático</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                }
                .container {
                    max-width: 1200px;
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
                }
                .status-card {
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                    border-left: 5px solid #4CAF50;
                }
                .status-card h3 {
                    margin-top: 0;
                    color: #333;
                }
                .info-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }
                .info-box {
                    background: #f0f0f0;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                }
                .info-box .number {
                    font-size: 36px;
                    font-weight: bold;
                    color: #764ba2;
                }
                .info-box .label {
                    color: #666;
                    margin-top: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎤 Sistema Karaokê - Pagamento Automático</h1>
                
                <div class="status-card">
                    <h3>✅ Sistema Online e Funcionando</h3>
                    <p>Integração PagSeguro: <strong>ATIVA</strong></p>
                    <p>Modo: <strong>""" + ("SANDBOX" if PAGSEGURO_SANDBOX else "PRODUÇÃO") + """</strong></p>
                </div>
                
                <div class="info-grid">
                    <div class="info-box">
                        <div class="number" id="total-vendas">0</div>
                        <div class="label">Vendas Hoje</div>
                    </div>
                    <div class="info-box">
                        <div class="number" id="clientes-ativos">0</div>
                        <div class="label">Clientes Ativos</div>
                    </div>
                    <div class="info-box">
                        <div class="number" id="receita-mes">R$ 0,00</div>
                        <div class="label">Receita do Mês</div>
                    </div>
                </div>
                
                <div class="status-card">
                    <h3>📊 Últimas Transações</h3>
                    <div id="transacoes-recentes">Carregando...</div>
                </div>
            </div>
            
            <script>
                // Atualizar estatísticas a cada 30 segundos
                function atualizarStats() {
                    fetch('/api/estatisticas')
                        .then(r => r.json())
                        .then(data => {
                            document.getElementById('total-vendas').innerText = data.vendas_hoje;
                            document.getElementById('clientes-ativos').innerText = data.clientes_ativos;
                            document.getElementById('receita-mes').innerText = 'R$ ' + data.receita_mes.toFixed(2);
                        });
                }
                
                setInterval(atualizarStats, 30000);
                atualizarStats();
            </script>
        </body>
        </html>
        """
        return html
    
    def gerar_pagina_cliente(self, machine_id):
        """Gera página de pagamento para o cliente"""
        # Buscar dados do cliente e pacotes faltantes
        # Este seria integrado com seu sistema de análise
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Atualização Karaokê - Pagamento</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
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
                    background: white;
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                h1 {
                    color: #333;
                    text-align: center;
                    margin-bottom: 10px;
                    font-size: 24px;
                }
                .machine-id {
                    text-align: center;
                    color: #666;
                    margin-bottom: 30px;
                    font-size: 14px;
                }
                .pacotes-section {
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                }
                .pacote-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 10px;
                    margin: 5px 0;
                    background: white;
                    border-radius: 5px;
                }
                .pacote-item input[type="checkbox"] {
                    width: 20px;
                    height: 20px;
                    cursor: pointer;
                }
                .preco {
                    font-weight: bold;
                    color: #4CAF50;
                }
                .pre-venda {
                    background: #fff3cd;
                    color: #856404;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                }
                .total-section {
                    background: #28a745;
                    color: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: center;
                }
                .total-valor {
                    font-size: 36px;
                    font-weight: bold;
                }
                .btn-pagar {
                    background: #FFC107;
                    color: #333;
                    border: none;
                    padding: 15px 40px;
                    font-size: 18px;
                    font-weight: bold;
                    border-radius: 50px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 20px;
                    transition: all 0.3s;
                }
                .btn-pagar:hover {
                    background: #FFB300;
                    transform: scale(1.05);
                }
                .btn-pagar:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                    transform: scale(1);
                }
                .plano-anual {
                    background: #e3f2fd;
                    border: 2px solid #2196F3;
                    border-radius: 10px;
                    padding: 15px;
                    margin: 20px 0;
                }
                .creditos-box {
                    background: #f3e5f5;
                    border: 2px solid #9c27b0;
                    border-radius: 10px;
                    padding: 15px;
                    margin: 20px 0;
                }
                .loading {
                    display: none;
                    text-align: center;
                    margin: 20px 0;
                }
                .loading.active {
                    display: block;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .spinner {
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #764ba2;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎤 Atualização Karaokê</h1>
                <div class="machine-id">Máquina: """ + machine_id + """</div>
                
                <div class="pacotes-section">
                    <h3>📦 Pacotes Disponíveis</h3>
                    <div id="lista-pacotes">
                        <!-- Pacotes serão carregados aqui -->
                    </div>
                </div>
                
                <div class="creditos-box">
                    <h3>💳 Comprar Créditos</h3>
                    <p>Economize comprando créditos antecipadamente!</p>
                    <select id="pacote-creditos" onchange="atualizarTotal()">
                        <option value="0">Não comprar créditos</option>
                        <option value="10">10 créditos - R$ 120,00 (economia R$ 30)</option>
                        <option value="20">20 créditos - R$ 250,00 (economia R$ 50)</option>
                        <option value="50">50 créditos - R$ 600,00 (economia R$ 150)</option>
                    </select>
                </div>
                
                <div class="plano-anual">
                    <h3>📅 Plano Anual</h3>
                    <label>
                        <input type="checkbox" id="plano-anual" onchange="atualizarTotal()">
                        Contratar Plano Anual - R$ 600,00
                        <br><small>Inclui todos os pacotes do ano!</small>
                    </label>
                </div>
                
                <div class="total-section">
                    <div>Total a Pagar:</div>
                    <div class="total-valor" id="valor-total">R$ 0,00</div>
                    <div id="economia" style="font-size: 14px; margin-top: 10px;"></div>
                </div>
                
                <button class="btn-pagar" id="btn-pagar" onclick="processarPagamento()">
                    PAGAR COM PAGSEGURO
                </button>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Processando pagamento...</p>
                </div>
            </div>
            
            <script>
                const machineId = '""" + machine_id + """';
                let pacotesSelecionados = [];
                let valorTotal = 0;
                
                // Carregar pacotes disponíveis
                function carregarPacotes() {
                    // Simulação - seria uma chamada real à API
                    const pacotes = [
                        {codigo: '41A', preco: 25.00, preVenda: false},
                        {codigo: '41B', preco: 25.00, preVenda: false},
                        {codigo: '41C', preco: 15.00, preVenda: true},
                        {codigo: '41D', preco: 15.00, preVenda: true}
                    ];
                    
                    let html = '';
                    pacotes.forEach(p => {
                        html += `
                            <div class="pacote-item">
                                <label>
                                    <input type="checkbox" value="${p.codigo}" data-preco="${p.preco}" onchange="atualizarTotal()">
                                    Pacote ${p.codigo}
                                    ${p.preVenda ? '<span class="pre-venda">PRÉ-VENDA</span>' : ''}
                                </label>
                                <span class="preco">R$ ${p.preco.toFixed(2)}</span>
                            </div>
                        `;
                    });
                    document.getElementById('lista-pacotes').innerHTML = html;
                }
                
                function atualizarTotal() {
                    let total = 0;
                    let economia = 0;
                    
                    // Calcular pacotes selecionados
                    const checkboxes = document.querySelectorAll('.pacote-item input[type="checkbox"]:checked');
                    pacotesSelecionados = [];
                    checkboxes.forEach(cb => {
                        pacotesSelecionados.push(cb.value);
                        total += parseFloat(cb.dataset.preco);
                    });
                    
                    // Verificar plano anual
                    if (document.getElementById('plano-anual').checked) {
                        total = 600;
                        document.getElementById('economia').innerText = 'Plano Anual - Todos os pacotes incluídos!';
                    }
                    
                    // Verificar créditos
                    const creditos = document.getElementById('pacote-creditos').value;
                    if (creditos > 0) {
                        if (creditos == 10) {
                            total += 120;
                            economia += 30;
                        } else if (creditos == 20) {
                            total += 250;
                            economia += 50;
                        } else if (creditos == 50) {
                            total += 600;
                            economia += 150;
                        }
                    }
                    
                    // Aplicar teto de R$ 500 se necessário
                    const tetoMaximo = 500;
                    if (total > tetoMaximo && !document.getElementById('plano-anual').checked) {
                        economia += total - tetoMaximo;
                        total = tetoMaximo;
                        document.getElementById('economia').innerText = `⭐ Promoção aplicada! Economia de R$ ${economia.toFixed(2)}`;
                    } else if (economia > 0) {
                        document.getElementById('economia').innerText = `Economia de R$ ${economia.toFixed(2)}`;
                    }
                    
                    valorTotal = total;
                    document.getElementById('valor-total').innerText = `R$ ${total.toFixed(2)}`;
                    
                    // Habilitar/desabilitar botão
                    document.getElementById('btn-pagar').disabled = total === 0;
                }
                
                function processarPagamento() {
                    if (valorTotal === 0) {
                        alert('Selecione ao menos um item!');
                        return;
                    }
                    
                    document.getElementById('loading').classList.add('active');
                    document.getElementById('btn-pagar').disabled = true;
                    
                    // Preparar dados
                    const dados = {
                        machine_id: machineId,
                        pacotes: pacotesSelecionados,
                        valor: valorTotal,
                        plano_anual: document.getElementById('plano-anual').checked,
                        creditos: document.getElementById('pacote-creditos').value
                    };
                    
                    // Enviar para criar checkout no PagSeguro
                    fetch('/api/criar_pagamento', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(dados)
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            // Redirecionar para PagSeguro
                            window.location.href = data.checkout_url;
                        } else {
                            alert('Erro ao processar pagamento: ' + data.error);
                            document.getElementById('loading').classList.remove('active');
                            document.getElementById('btn-pagar').disabled = false;
                        }
                    })
                    .catch(error => {
                        alert('Erro de conexão. Tente novamente.');
                        document.getElementById('loading').classList.remove('active');
                        document.getElementById('btn-pagar').disabled = false;
                    });
                }
                
                // Inicializar
                carregarPacotes();
                atualizarTotal();
            </script>
        </body>
        </html>
        """
        return html
    
    def criar_checkout_pagseguro(self, dados):
        """Cria checkout no PagSeguro e retorna link de pagamento"""
        try:
            # Preparar XML para PagSeguro
            xml_checkout = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <checkout>
                <currency>BRL</currency>
                <items>
                    <item>
                        <id>1</id>
                        <description>Atualizacao Karaoke - {', '.join(dados.get('pacotes', []))}</description>
                        <amount>{dados['valor']:.2f}</amount>
                        <quantity>1</quantity>
                    </item>
                </items>
                <reference>{dados['machine_id']}-{int(time.time())}</reference>
                <sender>
                    <email>cliente@example.com</email>
                </sender>
                <shipping>
                    <type>3</type>
                </shipping>
                <notificationURL>https://seu-servidor.com/api/notificacao_pagseguro</notificationURL>
            </checkout>"""
            
            # Fazer requisição ao PagSeguro
            response = requests.post(
                f"{PAGSEGURO_WS}/v2/checkout",
                params={
                    'email': PAGSEGURO_EMAIL,
                    'token': PAGSEGURO_TOKEN
                },
                data=xml_checkout,
                headers={'Content-Type': 'application/xml; charset=UTF-8'}
            )
            
            if response.status_code == 200:
                # Extrair código do checkout
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                checkout_code = root.find('code').text
                
                # Salvar transação no banco
                c = self.conn.cursor()
                c.execute('''INSERT INTO transacoes 
                           (machine_id, codigo_pagseguro, reference, pacotes, valor, status, data_criacao, link_pagamento)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (dados['machine_id'], checkout_code, f"{dados['machine_id']}-{int(time.time())}",
                          json.dumps(dados['pacotes']), dados['valor'], 'AGUARDANDO',
                          datetime.now().isoformat(), f"{PAGSEGURO_URL}/v2/checkout/payment.html?code={checkout_code}"))
                self.conn.commit()
                
                return jsonify({
                    'success': True,
                    'checkout_url': f"{PAGSEGURO_URL}/v2/checkout/payment.html?code={checkout_code}"
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erro ao criar checkout no PagSeguro'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    def processar_notificacao_pagseguro(self, dados):
        """Processa notificação de pagamento do PagSeguro"""
        try:
            notification_code = dados.get('notificationCode')
            notification_type = dados.get('notificationType')
            
            if notification_type == 'transaction':
                # Consultar detalhes da transação
                response = requests.get(
                    f"{PAGSEGURO_WS}/v3/transactions/notifications/{notification_code}",
                    params={
                        'email': PAGSEGURO_EMAIL,
                        'token': PAGSEGURO_TOKEN
                    }
                )
                
                if response.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.text)
                    
                    # Extrair informações
                    status = root.find('status').text
                    reference = root.find('reference').text
                    
                    # Status PagSeguro:
                    # 1 = Aguardando pagamento
                    # 2 = Em análise
                    # 3 = Paga
                    # 4 = Disponível
                    # 5 = Em disputa
                    # 6 = Devolvida
                    # 7 = Cancelada
                    
                    if status in ['3', '4']:  # Paga ou Disponível
                        # Liberar pacotes
                        machine_id = reference.split('-')[0]
                        
                        # Buscar transação
                        c = self.conn.cursor()
                        c.execute("SELECT pacotes FROM transacoes WHERE reference = ?", (reference,))
                        result = c.fetchone()
                        
                        if result:
                            pacotes = result[0]
                            
                            # Criar liberação
                            c.execute('''INSERT INTO liberacoes 
                                       (machine_id, pacotes_liberados, data_liberacao, baixado)
                                       VALUES (?, ?, ?, 0)''',
                                     (machine_id, pacotes, datetime.now().isoformat()))
                            
                            # Atualizar status da transação
                            c.execute('''UPDATE transacoes 
                                       SET status = 'PAGO', data_pagamento = ?
                                       WHERE reference = ?''',
                                     (datetime.now().isoformat(), reference))
                            
                            self.conn.commit()
            
            return "OK", 200
            
        except Exception as e:
            print(f"Erro ao processar notificação: {e}")
            return "ERROR", 500
    
    def verificar_pacotes_liberados(self, machine_id):
        """Verifica se há pacotes liberados para download"""
        c = self.conn.cursor()
        c.execute('''SELECT pacotes_liberados FROM liberacoes 
                    WHERE machine_id = ? AND baixado = 0
                    ORDER BY data_liberacao DESC LIMIT 1''', (machine_id,))
        result = c.fetchone()
        
        if result:
            return jsonify({
                'tem_atualizacao': True,
                'pacotes': json.loads(result[0])
            })
        else:
            return jsonify({
                'tem_atualizacao': False
            })
    
    def marcar_como_baixado(self, machine_id):
        """Marca pacotes como baixados"""
        c = self.conn.cursor()
        c.execute('''UPDATE liberacoes SET baixado = 1 
                    WHERE machine_id = ? AND baixado = 0''', (machine_id,))
        self.conn.commit()
        
        return jsonify({'success': True})
    
    def run(self, host='0.0.0.0', port=8000):
        """Inicia o servidor"""
        print(f"""
        ╔════════════════════════════════════════════════╗
        ║   SERVIDOR KARAOKÊ COM PAGSEGURO - AUTOMÁTICO   ║
        ╚════════════════════════════════════════════════╝
        
        Status: ONLINE
        Endereço: http://{host}:{port}
        PagSeguro: {'SANDBOX' if PAGSEGURO_SANDBOX else 'PRODUÇÃO'}
        
        IMPORTANTE: Configure seu token do PagSeguro!
        """)
        
        app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    sistema = SistemaPagamentoPagSeguro()
    sistema.run()