import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
DB = 'estacionamento.db'

# ================= CRIAÇÃO AUTOMÁTICA DO BANCO =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome VARCHAR(30) NOT NULL,
        fone VARCHAR(20) NOT NULL,
        cpf VARCHAR(14) UNIQUE NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS veiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa VARCHAR(10) UNIQUE NOT NULL,
        modelo VARCHAR(50) NOT NULL,
        marca VARCHAR(50) NOT NULL,
        cor VARCHAR(20) NOT NULL,
        cliente_id INTEGER NOT NULL,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS precos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_veiculo VARCHAR(30) NOT NULL,
        valor_hora DECIMAL(10,2) NOT NULL,
        valor_diaria DECIMAL(10,2) NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estadia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        veiculo_id INTEGER NOT NULL,
        horario_entrada DATETIME NOT NULL,
        horario_saida DATETIME,
        valor_total DECIMAL(10,2),
        status VARCHAR(20) DEFAULT 'Aberto',
        FOREIGN KEY (veiculo_id) REFERENCES veiculos(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estadia_id INTEGER NOT NULL,
        forma_pagamento VARCHAR(30) NOT NULL,
        valor_pago DECIMAL(10,2) NOT NULL,
        data_pago DATETIME NOT NULL,
        FOREIGN KEY (estadia_id) REFERENCES estadia(id))''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ================= FUNÇÕES DE DATA/HORA =================
def formatar_data(data_str):
    """Converte '2024-01-15 14:30:00' em '15/01/2024 14:30'"""
    if not data_str:
        return '-'
    try:
        dt = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return data_str

def tempo_decorrido(data_entrada_str):
    """Calcula quanto tempo se passou desde a entrada (ex: '2h 15min')"""
    if not data_entrada_str:
        return '-'
    try:
        entrada = datetime.strptime(data_entrada_str, '%Y-%m-%d %H:%M:%S')
        agora = datetime.now()
        diff = agora - entrada
        horas = diff.seconds // 3600
        minutos = (diff.seconds % 3600) // 60
        return f"{horas}h {minutos}min"
    except:
        return '-'

def calcular_valor(horario_entrada_str, horario_saida_str, valor_hora, valor_diaria):
    """Calcula automaticamente o valor a pagar baseado no tempo decorrido."""
    try:
        entrada = datetime.strptime(horario_entrada_str, '%Y-%m-%d %H:%M:%S')
        saida = datetime.strptime(horario_saida_str, '%Y-%m-%d %H:%M:%S')
        diff = saida - entrada
        horas = diff.seconds / 3600 + diff.days * 24

        # Lógica: se passou mais de 12 horas, cobra diária. Caso contrário, cobra por hora.
        if horas >= 12:
            return round(valor_diaria, 2)
        else:
            # Arredonda para cima (1h30 = 2 horas)
            horas_cobradas = int(horas) + (1 if horas % 1 > 0 else 0)
            return round(horas_cobradas * valor_hora, 2)
    except:
        return 0.0

# Registra as funções no Jinja para usar nos templates HTML
app.jinja_env.globals.update(
    formatar_data=formatar_data,
    tempo_decorrido=tempo_decorrido
)

# ================= LAYOUT BASE =================
BASE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sistema de Estacionamento</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<nav class="navbar navbar-expand-lg navbar-dark bg-dark shadow">
  <div class="container">
    <a class="navbar-brand fw-bold" href="/">🅿️ Estacionamento</a>
    <div class="navbar-nav">
      <a class="nav-link" href="/">Início</a>
      <a class="nav-link" href="/clientes">Clientes</a>
      <a class="nav-link" href="/veiculos">Veículos</a>
      <a class="nav-link" href="/precos">Preços</a>
      <a class="nav-link" href="/estadias">Estadias</a>
      <a class="nav-link" href="/pagamentos">Pagamentos</a>
    </div>
  </div>
</nav>
<div class="container mt-4 mb-5">{{ conteudo|safe }}</div>
</body>
</html>
"""

def render(conteudo):
    return render_template_string(BASE, conteudo=conteudo)

# ================= ROTAS =================

@app.route('/')
def index():
    conn = get_db()
    hoje = datetime.now().strftime('%Y-%m-%d')
    mes_atual = datetime.now().strftime('%Y-%m')

    total_clientes = conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
    total_veiculos = conn.execute('SELECT COUNT(*) FROM veiculos').fetchone()[0]
    carros_no_patio = conn.execute("SELECT COUNT(*) FROM estadia WHERE status='Aberto'").fetchone()[0]
    
    # Faturamento do dia
    faturamento_dia = conn.execute(
        "SELECT COALESCE(SUM(valor_pago), 0) FROM pagamentos WHERE data_pago LIKE ?",
        (hoje + '%',)
    ).fetchone()[0]
    
    # Faturamento do mês
    faturamento_mes = conn.execute(
        "SELECT COALESCE(SUM(valor_pago), 0) FROM pagamentos WHERE data_pago LIKE ?",
        (mes_atual + '%',)
    ).fetchone()[0]

    conn.close()
    return render(f"""
    <div class="text-center bg-white p-5 rounded shadow-sm">
      <h1 class="display-4">Sistema de Estacionamento</h1>
      <p class="lead">Data e hora atual: <b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b></p>
      <hr>
      <div class="row mt-4">
        <div class="col-md-3"><div class="card bg-primary text-white p-3"><h3>{total_clientes}</h3>Clientes</div></div>
        <div class="col-md-3"><div class="card bg-success text-white p-3"><h3>{total_veiculos}</h3>Veículos</div></div>
        <div class="col-md-3"><div class="card bg-info text-white p-3"><h3>{carros_no_patio}</h3>No Pátio</div></div>
        <div class="col-md-3"><div class="card bg-warning text-dark p-3"><h3>R$ {faturamento_dia:.2f}</h3>Hoje</div></div>
      </div>
      <div class="row mt-3">
        <div class="col-md-12"><div class="card bg-danger text-white p-3"><h3>R$ {faturamento_mes:.2f}</h3>Faturamento do Mês</div></div>
      </div>
      <div class="mt-4 d-flex flex-wrap justify-content-center gap-2">
        <a href="/clientes" class="btn btn-primary">👤 Clientes</a>
        <a href="/veiculos" class="btn btn-success">🚗 Veículos</a>
        <a href="/precos" class="btn btn-warning">💰 Preços</a>
        <a href="/estadias" class="btn btn-info">⏱️ Estadias</a>
        <a href="/pagamentos" class="btn btn-danger">💳 Pagamentos</a>
      </div>
    </div>
    """)

# ---------- CLIENTES ----------
@app.route('/clientes')
def clientes():
    conn = get_db()
    dados = conn.execute('SELECT * FROM clientes').fetchall()
    conn.close()
    html = """
    <div class="row">
      <div class="col-md-4">
        <div class="card shadow-sm">
          <div class="card-header bg-primary text-white">Novo Cliente</div>
          <div class="card-body">
            <form method="POST" action="/cliente/novo">
              <div class="mb-2"><label>Nome</label><input name="nome" maxlength="30" class="form-control" required></div>
              <div class="mb-2"><label>Fone</label><input name="fone" class="form-control" required></div>
              <div class="mb-2"><label>CPF</label><input name="cpf" class="form-control" required></div>
              <button class="btn btn-primary w-100">Salvar</button>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-8">
        <div class="card shadow-sm">
          <div class="card-header bg-secondary text-white">Clientes</div>
          <div class="card-body">
            <table class="table table-striped">
              <thead><tr><th>ID</th><th>Nome</th><th>Fone</th><th>CPF</th><th></th></tr></thead>
              <tbody>
              {% for c in dados %}
                <tr><td>{{c['id']}}</td><td>{{c['nome']}}</td><td>{{c['fone']}}</td><td>{{c['cpf']}}</td>
                <td><a href="/cliente/deletar/{{c['id']}}" class="btn btn-sm btn-danger" onclick="return confirm('Excluir?')">X</a></td></tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    """
    return render_template_string(BASE.replace("{{ conteudo|safe }}", html), dados=dados)

@app.route('/cliente/novo', methods=['POST'])
def cliente_novo():
    conn = get_db()
    try:
        conn.execute('INSERT INTO clientes (nome, fone, cpf) VALUES (?,?,?)',
                     (request.form['nome'], request.form['fone'], request.form['cpf']))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect(url_for('clientes'))

@app.route('/cliente/deletar/<int:id>')
def cliente_del(id):
    conn = get_db()
    conn.execute('DELETE FROM clientes WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('clientes'))

# ---------- VEICULOS ----------
@app.route('/veiculos')
def veiculos():
    conn = get_db()
    dados = conn.execute('''SELECT v.*, c.nome AS dono FROM veiculos v
                            JOIN clientes c ON v.cliente_id = c.id''').fetchall()
    clientes = conn.execute('SELECT * FROM clientes').fetchall()
    conn.close()
    html = """
    <div class="row">
      <div class="col-md-4">
        <div class="card shadow-sm">
          <div class="card-header bg-success text-white">Novo Veículo</div>
          <div class="card-body">
            <form method="POST" action="/veiculo/novo">
              <div class="mb-2"><label>Placa</label><input name="placa" class="form-control" required></div>
              <div class="mb-2"><label>Modelo</label><input name="modelo" class="form-control" required></div>
              <div class="mb-2"><label>Marca</label><input name="marca" class="form-control" required></div>
              <div class="mb-2"><label>Cor</label><input name="cor" class="form-control" required></div>
              <div class="mb-2"><label>Dono</label>
                <select name="cliente_id" class="form-select" required>
                  <option value="">Selecione...</option>
                  {% for c in clientes %}<option value="{{c['id']}}">{{c['nome']}}</option>{% endfor %}
                </select>
              </div>
              <button class="btn btn-success w-100">Salvar</button>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-8">
        <div class="card shadow-sm">
          <div class="card-header bg-secondary text-white">Veículos</div>
          <div class="card-body">
            <table class="table table-striped">
              <thead><tr><th>ID</th><th>Placa</th><th>Modelo</th><th>Marca</th><th>Cor</th><th>Dono</th><th></th></tr></thead>
              <tbody>
              {% for v in dados %}
                <tr><td>{{v['id']}}</td><td>{{v['placa']}}</td><td>{{v['modelo']}}</td><td>{{v['marca']}}</td><td>{{v['cor']}}</td><td>{{v['dono']}}</td>
                <td><a href="/veiculo/deletar/{{v['id']}}" class="btn btn-sm btn-danger" onclick="return confirm('Excluir?')">X</a></td></tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    """
    return render_template_string(BASE.replace("{{ conteudo|safe }}", html), dados=dados, clientes=clientes)

@app.route('/veiculo/novo', methods=['POST'])
def veiculo_novo():
    conn = get_db()
    try:
        conn.execute('INSERT INTO veiculos (placa, modelo, marca, cor, cliente_id) VALUES (?,?,?,?,?)',
                     (request.form['placa'], request.form['modelo'], request.form['marca'],
                      request.form['cor'], request.form['cliente_id']))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect(url_for('veiculos'))

@app.route('/veiculo/deletar/<int:id>')
def veiculo_del(id):
    conn = get_db()
    conn.execute('DELETE FROM veiculos WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('veiculos'))

# ---------- PRECOS ----------
@app.route('/precos')
def precos():
    conn = get_db()
    dados = conn.execute('SELECT * FROM precos').fetchall()
    conn.close()
    html = """
    <div class="row">
      <div class="col-md-4">
        <div class="card shadow-sm">
          <div class="card-header bg-warning">Novo Preço</div>
          <div class="card-body">
            <form method="POST" action="/preco/novo">
              <div class="mb-2"><label>Tipo</label><input name="tipo_veiculo" class="form-control" required></div>
              <div class="mb-2"><label>Valor Hora</label><input type="number" step="0.01" name="valor_hora" class="form-control" required></div>
              <div class="mb-2"><label>Valor Diária</label><input type="number" step="0.01" name="valor_diaria" class="form-control" required></div>
              <button class="btn btn-warning w-100">Salvar</button>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-8">
        <div class="card shadow-sm">
          <div class="card-header bg-secondary text-white">Preços</div>
          <div class="card-body">
            <table class="table table-striped">
              <thead><tr><th>ID</th><th>Tipo</th><th>Hora</th><th>Diária</th><th></th></tr></thead>
              <tbody>
              {% for p in dados %}
                <tr><td>{{p['id']}}</td><td>{{p['tipo_veiculo']}}</td><td>R$ {{'%.2f'|format(p['valor_hora'])}}</td><td>R$ {{'%.2f'|format(p['valor_diaria'])}}</td>
                <td><a href="/preco/deletar/{{p['id']}}" class="btn btn-sm btn-danger" onclick="return confirm('Excluir?')">X</a></td></tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    """
    return render_template_string(BASE.replace("{{ conteudo|safe }}", html), dados=dados)

@app.route('/preco/novo', methods=['POST'])
def preco_novo():
    conn = get_db()
    conn.execute('INSERT INTO precos (tipo_veiculo, valor_hora, valor_diaria) VALUES (?,?,?)',
                 (request.form['tipo_veiculo'], float(request.form['valor_hora']), float(request.form['valor_diaria'])))
    conn.commit()
    conn.close()
    return redirect(url_for('precos'))

@app.route('/preco/deletar/<int:id>')
def preco_del(id):
    conn = get_db()
    conn.execute('DELETE FROM precos WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('precos'))

# ---------- ESTADIAS ----------
@app.route('/estadias')
def estadias():
    conn = get_db()
    dados = conn.execute('''SELECT e.*, v.placa FROM estadia e
                            JOIN veiculos v ON e.veiculo_id = v.id
                            ORDER BY e.id DESC''').fetchall()
    veiculos = conn.execute('SELECT * FROM veiculos').fetchall()
    precos = conn.execute('SELECT * FROM precos').fetchall()
    conn.close()
    html = """
    <div class="row">
      <div class="col-md-4">
        <div class="card shadow-sm">
          <div class="card-header bg-info text-white">Registrar Entrada</div>
          <div class="card-body">
            <p class="small text-muted">Horário de entrada: <b>{{ agora }}</b></p>
            <form method="POST" action="/estadia/nova">
              <div class="mb-2"><label>Veículo</label>
                <select name="veiculo_id" class="form-select" required>
                  <option value="">Selecione...</option>
                  {% for v in veiculos %}<option value="{{v['id']}}">{{v['placa']}} - {{v['modelo']}}</option>{% endfor %}
                </select>
              </div>
              <button class="btn btn-info w-100">Registrar Entrada</button>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-8">
        <div class="card shadow-sm">
          <div class="card-header bg-secondary text-white">Estadias</div>
          <div class="card-body">
            <table class="table table-striped">
              <thead><tr><th>ID</th><th>Placa</th><th>Entrada</th><th>Saída</th><th>Tempo</th><th>Total</th><th>Status</th><th></th></tr></thead>
              <tbody>
              {% for e in dados %}
                <tr>
                  <td>{{e['id']}}</td><td>{{e['placa']}}</td>
                  <td>{{ formatar_data(e['horario_entrada']) }}</td>
                  <td>{{ formatar_data(e['horario_saida']) }}</td>
                  <td>
                    {% if e['status'] == 'Aberto' %}
                      <span class="badge bg-warning text-dark">{{ tempo_decorrido(e['horario_entrada']) }}</span>
                    {% else %}
                      {{ tempo_decorrido(e['horario_entrada']) }}
                    {% endif %}
                  </td>
                  <td>{{'R$ %.2f'|format(e['valor_total']) if e['valor_total'] else '-'}}</td>
                  <td><span class="badge bg-{{'success' if e['status']=='Fechado' else 'warning'}}">{{e['status']}}</span></td>
                  <td>
                    {% if e['status'] == 'Aberto' %}
                    <form method="POST" action="/estadia/fechar/{{e['id']}}" class="d-inline">
                      <input type="number" step="0.01" name="valor_total" placeholder="R$" class="form-control form-control-sm d-inline" style="width:80px" required>
                      <button class="btn btn-sm btn-success">Fechar</button>
                    </form>
                    {% endif %}
                    <a href="/estadia/deletar/{{e['id']}}" class="btn btn-sm btn-danger" onclick="return confirm('Excluir?')">X</a>
                  </td>
                </tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    """
    return render_template_string(BASE.replace("{{ conteudo|safe }}", html), 
                                   dados=dados, veiculos=veiculos, precos=precos,
                                   agora=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))

@app.route('/estadia/nova', methods=['POST'])
def estadia_nova():
    conn = get_db()
    conn.execute('INSERT INTO estadia (veiculo_id, horario_entrada, status) VALUES (?,?,?)',
                 (request.form['veiculo_id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Aberto'))
    conn.commit()
    conn.close()
    return redirect(url_for('estadias'))

@app.route('/estadia/fechar/<int:id>', methods=['POST'])
def estadia_fechar(id):
    conn = get_db()
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('UPDATE estadia SET horario_saida=?, valor_total=?, status=? WHERE id=?',
                 (agora, float(request.form['valor_total']), 'Fechado', id))
    conn.commit()
    conn.close()
    return redirect(url_for('estadias'))

@app.route('/estadia/deletar/<int:id>')
def estadia_del(id):
    conn = get_db()
    conn.execute('DELETE FROM estadia WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('estadias'))

# ---------- PAGAMENTOS ----------
@app.route('/pagamentos')
def pagamentos():
    conn = get_db()
    dados = conn.execute('''SELECT p.*, v.placa FROM pagamentos p
                            JOIN estadia e ON p.estadia_id = e.id
                            JOIN veiculos v ON e.veiculo_id = v.id
                            ORDER BY p.id DESC''').fetchall()
    estadias = conn.execute('SELECT * FROM estadia').fetchall()
    conn.close()
    html = """
    <div class="row">
      <div class="col-md-4">
        <div class="card shadow-sm">
          <div class="card-header bg-danger text-white">Novo Pagamento</div>
          <div class="card-body">
            <p class="small text-muted">Data do pagamento: <b>{{ agora }}</b></p>
            <form method="POST" action="/pagamento/novo">
              <div class="mb-2"><label>Estadia</label>
                <select name="estadia_id" class="form-select" required>
                  <option value="">Selecione...</option>
                  {% for e in estadias %}<option value="{{e['id']}}">#{{e['id']}} ({{e['status']}})</option>{% endfor %}
                </select>
              </div>
              <div class="mb-2"><label>Forma</label>
                <select name="forma_pagamento" class="form-select" required>
                  <option>Dinheiro</option><option>PIX</option><option>Cartão Débito</option><option>Cartão Crédito</option>
                </select>
              </div>
              <div class="mb-2"><label>Valor</label><input type="number" step="0.01" name="valor_pago" class="form-control" required></div>
              <button class="btn btn-danger w-100">Registrar</button>
            </form>
          </div>
        </div>
      </div>
      <div class="col-md-8">
        <div class="card shadow-sm">
          <div class="card-header bg-secondary text-white">Pagamentos</div>
          <div class="card-body">
            <table class="table table-striped">
              <thead><tr><th>ID</th><th>Placa</th><th>Forma</th><th>Valor</th><th>Data</th><th></th></tr></thead>
              <tbody>
              {% for p in dados %}
                <tr><td>{{p['id']}}</td><td>{{p['placa']}}</td><td>{{p['forma_pagamento']}}</td>
                <td>R$ {{'%.2f'|format(p['valor_pago'])}}</td>
                <td>{{ formatar_data(p['data_pago']) }}</td>
                <td><a href="/pagamento/deletar/{{p['id']}}" class="btn btn-sm btn-danger" onclick="return confirm('Excluir?')">X</a></td></tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    """
    return render_template_string(BASE.replace("{{ conteudo|safe }}", html), 
                                   dados=dados, estadias=estadias,
                                   agora=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))

@app.route('/pagamento/novo', methods=['POST'])
def pagamento_novo():
    conn = get_db()
    conn.execute('INSERT INTO pagamentos (estadia_id, forma_pagamento, valor_pago, data_pago) VALUES (?,?,?,?)',
                 (request.form['estadia_id'], request.form['forma_pagamento'],
                  float(request.form['valor_pago']), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return redirect(url_for('pagamentos'))

@app.route('/pagamento/deletar/<int:id>')
def pagamento_del(id):
    conn = get_db()
    conn.execute('DELETE FROM pagamentos WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('pagamentos'))

# ================= INICIALIZAÇÃO =================
if __name__ == '__main__':
    init_db()
    app.run(debug=True)