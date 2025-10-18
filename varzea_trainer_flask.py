import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo   # <— importa o fuso horário
import time
import pytz
import random
from flask_login import login_required


tz = pytz.timezone("America/Sao_Paulo")
now_local = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "varzea.db")

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "troca_esse_segredo")

#Lista de frases motivacionais 
FRASES = [
    "A vitória começa no treino 💪🔥",
    "Treine enquanto eles dormem 😎",
    "Na raça, tudo é possível! 👊",
    "Disciplina vence o talento!",
    "Corpo cansado, mente forte 🦾",
    "Foco, força e fé ⚽🔥",
    "A excelência é um hábito diário."
]

# Número total de treinos por plano
TOTAL_AMADOR = 13
TOTAL_SEMI_PRO = 21  # Exemplo — ajuste se for outro número


# Mail config via env vars
app.config["MAIL_SERVER"] = os.environ.get("SMTP_HOST", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("SMTP_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("SMTP_USER", "")
app.config["MAIL_PASSWORD"] = os.environ.get("SMTP_PASS", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("SMTP_FROM", app.config["MAIL_USERNAME"] or "no-reply@example.com")

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)


DB_PATH = "varzea.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Só cria o banco se ele ainda não existir
    if not os.path.exists(DB_PATH):
        print("🔧 Criando banco de dados pela primeira vez...")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Usuários
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Perfil
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                age INTEGER,
                height_m REAL,
                weight_kg REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # Check-ins de treino
        cur.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                treino TEXT,
                plano TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # Tabela alternativa de check-ins
        cur.execute("""
            CREATE TABLE IF NOT EXISTS checkin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plano TEXT NOT NULL,
                data DATE NOT NULL
            )
        """)

        # Histórico de peso diário
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weight_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                log_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # ✅ NOVA TABELA — Medidas corporais
        cur.execute("""
            CREATE TABLE IF NOT EXISTS body_measures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                peso REAL,
                braco REAL,
                perna REAL,
                cintura REAL,
                quadril REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        cur.execute("""
          CREATE TABLE IF NOT EXISTS treino_velocidade (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          dia INTEGER NOT NULL,
          UNIQUE(user_id, dia),
          FOREIGN KEY(user_id) REFERENCES users(id)
          );
      """)

        conn.commit()
        conn.close()
        print("✅ Banco criado com sucesso!")
    else:
        print("📁 Banco já existente — usando o atual.")

# Executa na inicialização
init_db()

def send_reset_email(to_email):
    if not app.config["MAIL_USERNAME"] or not app.config["MAIL_PASSWORD"]:
        print("[WARN] SMTP not configured. Cannot send email.")
        return False, None
    token = serializer.dumps(to_email, salt="reset-salt")
    link = url_for("reset", token=token, _external=True)
    html = f"<p>Você pediu redefinir a senha. Clique no link abaixo (expira em 1h):</p><p><a href='{link}'>{link}</a></p>"
    try:
        msg = Message("Redefinir senha - Na Raça", recipients=[to_email], html=html)
        mail.send(msg)
        return True, link
    except Exception as e:
        print("Mail error:", e)
        return False, None

from functools import wraps
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("uid"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

MOTIVACOES = [
    "Quem corre na raça nunca perde a batalha.",
    "Constância vence talento quando o talento não treina.",
    "Foco, força e fé no gramado.",
    "Várzea é coração: joga simples, joga sério."
]

TREINOS = [
    {
        "id": 1,
        "titulo": "Dia 1 – Base + Condicionamento",
        "exercicios": [
            "Corda: 4x1min (30s descanso)",
            "Circuito 2 voltas: 12 agachamentos, 10 flexões, 20s prancha",
            "5 sprints de 10m (força total)",
            "Extra abdômen: 3x15 abdominal bicicleta"
        ]
    },
    {
        "id": 2,
        "titulo": "Dia 2 – Força",
        "exercicios": [
            "3 séries com galão: 12 agachamento, 12 avanço (cada perna), 12 remada curvada",
            "3x8 burpees",
            "3x25s prancha",
            "Extra abdômen: 3x15 abdominal infra"
        ]
    },
    {
        "id": 3,
        "titulo": "Dia 3 – Explosão",
        "exercicios": [
            "8 sprints curtos de 10m (descanso 40s)",
            "3x12 Skater Jump (saltos laterais)",
            "3x10 agachamento com salto",
            "Extra abdômen: 3x20s prancha lateral (cada lado)"
        ]
    },
    {
        "id": 4,
        "titulo": "Dia 4 – Descanso ativo",
        "exercicios": [
            "Caminhada leve + alongamento/mobilidade"
        ]
    },
    {
        "id": 5,
        "titulo": "Dia 5 – Resistência + Força",
        "exercicios": [
            "Corda 5x1min",
            "3 séries: 12 agachamento com galão",
            "10 avanço cada perna",
            "8 flexões rápidas",
            "3x30s prancha",
            "Extra abdômen: 3x12 abdominal bicicleta"
        ]
    },
    {
        "id": 6,
        "titulo": "Dia 6 – Explosão curta",
        "exercicios": [
            "10 sprints de 10m (máxima explosão)",
            "3x10 burpees",
            "3x12 Skater Jump",
            "Extra abdômen: 3x15 abdominal infra"
        ]
    },
    {
        "id": 7,
        "titulo": "Dia 7 – Descanso ativo",
        "exercicios": [
            "Caminhada leve ou alongamento"
        ]
    },
    {
        "id": 8,
        "titulo": "Dia 8 – Força + Explosão",
        "exercicios": [
            "Corda 3x1min",
            "3 séries: 12 agachamento com galão",
            "12 remada curvada",
            "10 flexão rápida",
            "6 sprints de 10m",
            "Extra abdômen: 3x20s prancha lateral (cada lado)"
        ]
    },
    {
        "id": 9,
        "titulo": "Dia 9 – Condicionamento",
        "exercicios": [
            "Corda 5x1min",
            "Circuito 2 voltas: 12 agachamento",
            "10 burpees, 25s prancha",
            "4 sprints de 15m",
            "Extra abdômen: 3x12 abdominal bicicleta"
        ]
    },
    {
        "id": 10,
        "titulo": "Dia 10 – Leve / Manutenção",
        "exercicios": [
            "Corda 3x1min (leve)",
            "2 séries: 10 agachamento + 8 flexões + 20s prancha",
            "Alongamento"
        ]
    },
    {
        "id": 11,
        "titulo": "Dia 11 – Ativação curta",
        "exercicios": [
            "3 sprints curtos de 10m (70% esforço)",
            "Corda 2x1min leve",
            "Alongamento dinâmico"
        ]
    },
    {
        "id": 12,
        "titulo": "Dia 12 – Descanso total",
        "exercicios": [
            "Apenas alongamento leve"
        ]
    },
    {
        "id": 13,
        "titulo": "Dia de jogo",
        "exercicios": [
            "Aquecimento: 5 min corrida leve ou corda",
            "Alongamento dinâmico (quadril, posterior, adutor)",
            "3 sprints progressivos (leve → médio → forte)"
        ]
    }
]
# Treino Intermediário: 21 dias (estrutura para integrar ao app)
TREINO_SEMI_PRO = [
    {"id": 1, "titulo": "Dia 1 – Base + Força", "exercicios": [
        "Corda: 4x1min (descanso 30s)",
        "3 séries: 15 agachamento, 10 flexões, 20s prancha",
        "5 tiros curtos 10m",
    ]},
    {"id": 2, "titulo": "Dia 2 – Resistência", "exercicios": [
        "Caminhada leve 10min + alongamento dinâmico",
        "Circuito: 12 agachamento + 10 burpees + 20s prancha (3x)",
    ]},
    {"id": 3, "titulo": "Dia 3 – Força", "exercicios": [
        "3 séries com galão: 12 agachamento, 12 avanço, 12 remada curvada",
        "3x25s prancha",
    ]},
    {"id": 4, "titulo": "Dia 4 – Explosão", "exercicios": [
        "8 tiros de 10m (descanso 40s)",
        "3x10 agachamento com salto",
        "3x12 skater jump"
    ]},
    {"id": 5, "titulo": "Dia 5 – Abdômen + Core", "exercicios": [
        "3x20s prancha lateral (cada lado)",
        "3x15 abdominal infra",
        "3x20 bicicleta"
    ]},
    {"id": 6, "titulo": "Dia 6 – Descanso ativo", "exercicios": [
        "Caminhada leve ou alongamento geral"
    ]},
    {"id": 7, "titulo": "Dia 7 – Potência", "exercicios": [
        "5x10m sprint",
        "3x10 burpees",
        "3x10 agachamento explosivo"
    ]},
    {"id": 8, "titulo": "Dia 8 – Força + Corda", "exercicios": [
        "Corda 5x1min",
        "3 séries: 12 avanço + 10 flexões + 20s prancha"
    ]},
    {"id": 9, "titulo": "Dia 9 – Condicionamento", "exercicios": [
        "4 tiros de 20m (máximo)",
        "Corda 3x1min leve",
        "Circuito: 10 agachamento + 10 burpees + 10 abdominais"
    ]},
    {"id": 10, "titulo": "Dia 10 – Recuperação", "exercicios": [
        "Alongamento e mobilidade"
    ]},
    {"id": 11, "titulo": "Dia 11 – Força total", "exercicios": [
        "3 séries com galão: 15 agachamento, 15 remada, 15 avanço",
        "3x30s prancha"
    ]},
    {"id": 12, "titulo": "Dia 12 – Explosão + Sprint", "exercicios": [
        "6 tiros de 15m",
        "3x12 Skater Jump",
        "3x10 burpees"
    ]},
    {"id": 13, "titulo": "Dia 13 – Core + Flexibilidade", "exercicios": [
        "3x20s prancha",
        "3x15 abdominal infra",
        "Alongamento"
    ]},
    {"id": 14, "titulo": "Dia 14 – Condicionamento", "exercicios": [
        "Corda 4x1min",
        "Circuito: 10 burpees, 10 agachamentos, 10 flexões (3x)"
    ]},
    {"id": 15, "titulo": "Dia 15 – Força", "exercicios": [
        "4 séries com galão: 10 agachamento, 10 avanço, 10 remada"
    ]},
    {"id": 16, "titulo": "Dia 16 – Explosão", "exercicios": [
        "5 sprints 10m",
        "3x12 agachamento com salto",
        "3x15 skater jump"
    ]},
    {"id": 17, "titulo": "Dia 17 – Descanso ativo", "exercicios": [
        "Caminhada leve ou alongamento"
    ]},
    {"id": 18, "titulo": "Dia 18 – Força + Core", "exercicios": [
        "3x15 agachamento + 3x20s prancha + 3x12 flexão"
    ]},
    {"id": 19, "titulo": "Dia 19 – Condicionamento final", "exercicios": [
        "Corda 5x1min",
        "5 tiros curtos de 10m"
    ]},
    {"id": 20, "titulo": "Dia 20 – Mobilidade", "exercicios": [
        "Alongamento geral e mobilidade articular"
    ]},
    {"id": 21, "titulo": "Dia 21 – Dia de Jogo", "exercicios": [
        "Aquecimento leve + alongamento + 3 sprints progressivos"
    ]},
]



def table_exists(conn, table_name):
    """Retorna True se a tabela existir no banco SQLite."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None

def atingiu_peso_ideal(peso_atual, peso_min, peso_max):
    return peso_min <= peso_atual <= peso_max
    
@app.route("/")
def home():
    if session.get("uid"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not (name and email and password):
            flash("Preencha todos os campos.", "error")
            return render_template("register.html")
        pw_hash = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute("INSERT INTO users(name,email,password_hash) VALUES (?,?,?)",(name,email,pw_hash))
            conn.commit()
            conn.close()
            flash("Conta criada. Faça login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("E-mail já cadastrado.", "error")
    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # ✅ Cria conexão com suporte a dicionário (row_factory)
        conn = sqlite3.connect("varzea.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 🔍 Busca usuário pelo e-mail
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        # ✅ Valida senha e faz login
        if user and check_password_hash(user["password_hash"], password):
            session["uid"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            flash(f"👋 Bem-vindo, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        # ❌ Caso falhe
        flash("Credenciais inválidas. Tente novamente.", "error")

    # 🧭 Mostra página de login
    return render_template("login.html")
    

@app.route("/forgot", methods=["GET","POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user:
            ok, link = send_reset_email(email)
            if ok:
                flash("Enviamos link para seu e-mail.", "success")
            else:
                flash("Não foi possível enviar e-mail. Veja console e configure SMTP.", "error")
        else:
            flash("Se o e-mail existir, enviaremos um link.", "info")
    return render_template("forgot.html")

@app.route("/reset/<token>", methods=["GET","POST"])
def reset(token):
    try:
        email = serializer.loads(token, salt="reset-salt", max_age=3600)
    except Exception:
        return "Link inválido ou expirado."
    if request.method == "POST":
        new_pw = request.form.get("password","")
        if not new_pw:
            flash("Digite a nova senha.", "error")
        else:
            conn = get_db()
            conn.execute("UPDATE users SET password_hash=? WHERE email=?", (generate_password_hash(new_pw), email))
            conn.commit()
            conn.close()
            flash("Senha alterada. Faça login.", "success")
            return redirect(url_for("login"))
    return render_template("reset.html")
    

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["uid"]

    with get_db() as conn:
        cur = conn.cursor()

        # Conta treinos feitos no plano AMADOR
        cur.execute("""
            SELECT COUNT(*) FROM checkins
            WHERE user_id=? AND plano='amador'
        """, (user_id,))
        feitos_amador = cur.fetchone()[0]

        # Conta treinos feitos no plano SEMI PRO
        cur.execute("""
            SELECT COUNT(*) FROM checkins
            WHERE user_id=? AND plano='semi_pro'
        """, (user_id,))
        feitos_semi = cur.fetchone()[0]

    progresso_amador = (feitos_amador / TOTAL_AMADOR) * 100 if TOTAL_AMADOR > 0 else 0
    progresso_semi = (feitos_semi / TOTAL_SEMI_PRO) * 100 if TOTAL_SEMI_PRO > 0 else 0

    # Frase motivacional aleatória
    frase = random.choice(FRASES)

    name = session.get("name")

    return render_template(
        "dashboard.html",
        name=name,
        frase=frase,
        feitos_amador=feitos_amador,
        total_amador=TOTAL_AMADOR,
        progresso_amador=progresso_amador,
        feitos_semi=feitos_semi,
        total_semi=TOTAL_SEMI_PRO,
        progresso_semi=progresso_semi
    )

#@app.route("/treinos")
#@login_required
#def treinos_view():
   # user_id = session["uid"]
    #db = get_db()
    #cur = db.execute("SELECT treino FROM checkins WHERE user_id = ?", (user_id,))
    #feitos = [row[0] for row in cur.fetchall()]
    #db.close()
    #return render_template("treino.html", treinos=TREINOS, feitos=feitos)

    
#@app.route("/treinos_intermediario")
#@login_required
#def treinos_intermediario():
    #return render_template
# --- TREINO SEMI PRO (21 DIAS) ---
@app.route("/treino_semi_pro", methods=["GET", "POST"])
def treino_semi_pro():
    if "uid" not in session:
        return redirect("/login")

    user_id = session["uid"]
    treino_id = request.args.get("treino_id", default=1, type=int)
    total_dias = len(TREINO_SEMI_PRO)

    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()

    # ✅ Garante que a tabela existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            user_id INTEGER,
            treino TEXT,
            plano TEXT
        )
    """)
    conn.commit()

    # --- 🟢 Quando o usuário faz check-in
    if request.method == "POST":
        treino_id_post = int(request.form.get("treino_id", treino_id))

        # Verifica se já fez check-in
        cur.execute(
            "SELECT 1 FROM checkins WHERE user_id=? AND treino=? AND plano=?",
            (user_id, f"treino_{treino_id_post}", "semi_pro")
        )

        if not cur.fetchone():
            cur.execute(
                "INSERT INTO checkins (user_id, treino, plano) VALUES (?, ?, ?)",
                (user_id, f"treino_{treino_id_post}", "semi_pro")
            )
            conn.commit()

        # ✅ Se for o último treino, redireciona pro vídeo final e reseta
        if treino_id_post >= total_dias:
            cur.execute("DELETE FROM checkins WHERE user_id=? AND plano=?", (user_id, "semi_pro"))
            conn.commit()
            conn.close()
            return redirect(url_for("video_final"))

        return redirect(url_for("treino_semi_pro", treino_id=treino_id_post + 1))

    # --- 📊 Busca os treinos feitos
    cur.execute("SELECT treino FROM checkins WHERE user_id=? AND plano=?", (user_id, "semi_pro"))
    feitos = [row[0] for row in cur.fetchall()]
    conn.close()

    # ✅ Se o treino_id for maior que o total, vai direto pro vídeo final
    if treino_id > total_dias:
        return redirect(url_for("video_final"))

    # --- 📌 Dados do treino atual
    treino = TREINO_SEMI_PRO[treino_id - 1]
    anterior = treino_id - 1 if treino_id > 1 else None
    proximo = treino_id + 1 if treino_id < total_dias else None
    feito = f"treino_{treino_id}" in feitos

    return render_template(
        "treino_semi_pro.html",
        treino=treino,
        anterior=anterior,
        proximo=proximo,
        feito=feito
    )


# --- NOVA ROTA: Vídeo final do Semi-Pro
@app.route("/video_final")
def video_final():
    if "uid" not in session:
        return redirect("/login")

    user_id = session["uid"]

    # Limpa os check-ins do plano semi_pro (reinicia a barra)
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM checkins WHERE user_id=? AND plano=?", (user_id, "semi_pro"))
    conn.commit()
    conn.close()

    return render_template("video_final.html")

   
@app.route("/treino/<int:treino_id>", methods=["GET", "POST"])
@login_required
def treino_individual(treino_id):
    user_id = session["uid"]
    total_dias = len(TREINOS)

    with get_db() as conn:
        cur = conn.cursor()
        
    # ✅ Garante que a tabela existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            user_id INTEGER,
            treino TEXT,
            plano TEXT
        )
    """)
    conn.commit()

    # --- 🟢 Quando o usuário faz check-in
    if request.method == "POST":
        treino_id_post = int(request.form.get("treino_id", treino_id))

        # Verifica se já fez check-in
        cur.execute(
            "SELECT 1 FROM checkins WHERE user_id=? AND treino=? AND plano=?",
            (user_id, f"treino_{treino_id_post}", "amador")
        )

        if not cur.fetchone():
            cur.execute(
                "INSERT INTO checkins (user_id, treino, plano) VALUES (?, ?, ?)",
                (user_id, f"treino_{treino_id_post}", "amador")
            )
            conn.commit()

        # ✅ Se for o último treino, redireciona pro vídeo final e reseta
        if treino_id_post >= total_dias:
            cur.execute("DELETE FROM checkins WHERE user_id=? AND plano=?", (user_id, "amador"))
            conn.commit()
            conn.close()
            return redirect(url_for("video_final_13"))

        return redirect(url_for("treino_individual", treino_id=treino_id_post + 1))

    # --- 📊 Busca os treinos feitos
    cur.execute("SELECT treino FROM checkins WHERE user_id=? AND plano=?", (user_id, "amador"))
    feitos = [row[0] for row in cur.fetchall()]
    conn.close()

    # ✅ Se o treino_id for maior que o total, vai direto pro vídeo final
    if treino_id > total_dias:
        return redirect(url_for("video_final_13"))

    # --- 📌 Dados do treino atual
    treino = TREINOS [treino_id - 1]
    anterior = treino_id - 1 if treino_id > 1 else None
    proximo = treino_id + 1 if treino_id < total_dias else None
    feito = f"treino_{treino_id}" in feitos

    return render_template(
        "treino_individual.html",
        treino=treino,
        anterior=anterior,
        proximo=proximo,
        feito=feito
    )

    
    
@app.route("/video_final_13")
@login_required
def video_final_13():
    user_id = session["uid"]
    with get_db() as conn:
        cur = conn.cursor()
        # 🧹 Garante que os check-ins do plano amador estão limpos
        cur.execute("DELETE FROM checkins WHERE user_id=? AND plano=?", (user_id, "amador"))
        conn.commit()

    return render_template("video_final_13.html")
    

@app.route("/checkin", methods=["POST"])
@login_required
def checkin():
    treino = request.form.get("treino")
    if not treino:
        flash("Treino não informado.", "error")
        return redirect(request.referrer or url_for("treinos_view"))

    user_id = session.get("uid")
    if not user_id:
        flash("Faça login para registrar check-in.", "error")
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO checkins (user_id, treino) VALUES (?, ?)", (user_id, treino))
    db.commit()
    db.close()

    flash(f"✅ Check-in feito para {treino}!", "success")
    return redirect(request.referrer or url_for("treinos_view"))


@app.route("/meus_checkins")
@login_required
def meus_checkins():
    user_id = session.get("uid")
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT treino, created_at FROM checkins WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    registros = cur.fetchall()
    db.close()
    return render_template("meus_checkins.html", checkins=registros)

@app.route("/dieta")
def dieta():
    cardapio = [
("Café da manhã", ["Ovos mexidos + pão integral", "Banana + aveia", "Café/chá sem açúcar"]),
("Almoço", ["Arroz + feijão", "Frango grelhado ou ovos", "Salada/legumes"]),
("Lanche", ["Fruta (banana/maçã)", "Amendoim torrado (pequena porção)"]),
("Jantar", ["Arroz ou batata", "Proteína (frango/ovo)", "Legumes refogados"]),
("Hidratação", ["2–3L de água por dia", "Evitar refrigerante e álcool pré-jogo"])
]

    subs = [
("Proteínas", "Frango → ovos → sardinha enlatada"),
("Carboidratos", "Arroz → batata → mandioca"),
("Legumes", "Cenoura → abobrinha → brócolis"),
("Extras", "Aveia, banana, feijão, tomate, cebola, alho")
]

    macros = [50, 30, 20]  # exemplo: porcentagem de carbo, proteínas e gorduras
    return render_template("dieta.html", cardapio=cardapio, subs=subs, macros=macros)

@app.route("/recuperacao")
@login_required
def recuperacao_view():
    dicas = [
        "Sono: 7–9h por noite.",
        "Pós-treino: alongar 10–15 min e hidratar.",
        "Dia antes do jogo: treinar leve + carboidrato base.",
        "Pós-jogo: água + fruta; 1h depois, proteína magra + carboidrato + legumes."
    ]
    return render_template("recuperacao.html", dicas=dicas)
    
    
    
@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    conn = get_db()
    prof = conn.execute(
        "SELECT * FROM profile WHERE user_id=?", (session["uid"],)
    ).fetchone()

    redirecionar_para_medidas = False  # flag

    if request.method == "POST":
        idade = request.form.get("idade", "").strip()
        altura_raw = request.form.get("altura", "").strip()
        peso_raw = request.form.get("peso", "").strip()

        altura_norm = altura_raw.replace(",", ".") if altura_raw else ""
        peso_norm = peso_raw.replace(",", ".") if peso_raw else ""

        altura_val = None
        peso_val = None
        erro_parse = False

        try:
            if altura_norm:
                altura_val = float(altura_norm)
            if peso_norm:
                peso_val = float(peso_norm)
        except ValueError:
            erro_parse = True
            flash("Altura ou peso inválidos. Use 1.75 e 72.5 (ponto ou vírgula).", "error")

        if not erro_parse:
            if prof:
                conn.execute(
                    "UPDATE profile SET age=?, height_m=?, weight_kg=? WHERE user_id=?",
                    (idade if idade else None, altura_val, peso_val, session["uid"])
                )
            else:
                conn.execute(
                    "INSERT INTO profile(user_id, age, height_m, weight_kg) VALUES (?,?,?,?)",
                    (session["uid"], idade if idade else None, altura_val, peso_val)
                )
                redirecionar_para_medidas = True  # primeira vez -> vai preencher medidas

            conn.commit()
            prof = conn.execute(
                "SELECT * FROM profile WHERE user_id=?", (session["uid"],)
            ).fetchone()

    imc = faixa = peso_ideal = motivacao = None
    mensagem = None

    try:
        if prof and prof["height_m"] and prof["weight_kg"]:
            h = float(str(prof["height_m"]).replace(",", "."))
            w = float(str(prof["weight_kg"]).replace(",", "."))
            if h > 0 and w > 0:
                imc = round(w / (h * h), 1)
                min_w = 18.5 * (h * h)
                max_w = 24.9 * (h * h)
                peso_ideal = (round(min_w, 1), round(max_w, 1))

                if imc < 18.5:
                    faixa = "Abaixo do peso"
                    motivacao = "⚡ Está leve demais! Bora ganhar massa com treinos e alimentação certa."
                elif imc <= 24.9:
                    faixa = "Peso ideal"
                    motivacao = "✅ Tá no ponto, mantenha a disciplina que o jogo é seu!"
                elif imc <= 29.9:
                    faixa = "Sobrepeso"
                    motivacao = "⚽ Força! Com treino e foco você vai chegar no shape ideal rapidinho."
                else:
                    faixa = "Obesidade"
                    motivacao = "🔥 Hora de dar o gás! Cada treino é um passo rumo à evolução."

                if min_w <= w <= max_w:
                    mensagem = "🎉 Parabéns! Você atingiu seu peso ideal."
                    redirecionar_para_medidas = True  # peso ideal -> pedir medidas finais
    except Exception as e:
        print("Erro ao calcular IMC:", e)
        flash("Não foi possível calcular o IMC com os valores fornecidos.", "error")

    pesos = conn.execute(
        "SELECT weight_kg, log_date FROM weight_log WHERE user_id=? ORDER BY log_date DESC",
        (session["uid"],)
    ).fetchall() if table_exists(conn, "weight_log") else []

    # 🔍 Pega última medida para mostrar botão de comparativo
    ultima_medida = conn.execute(
        "SELECT * FROM body_measures WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (session["uid"],)
    ).fetchone() if table_exists(conn, "body_measures") else None

    conn.close()

    # 🚀 Redireciona se for primeira vez OU se atingiu peso ideal
    if redirecionar_para_medidas:
        return redirect(url_for("medidas"))

    return render_template(
        "perfil.html",
        prof=prof,
        imc=imc,
        faixa=faixa,
        peso_ideal=peso_ideal,
        motivacao=motivacao,
        pesos=pesos,
        mensagem=mensagem,
        ultima_medida=ultima_medida  # envia para HTML
    )
    
@app.route("/medidas", methods=["GET", "POST"])
@login_required
def medidas():
    conn = get_db()
    user_id = session["uid"]

    if request.method == "POST":
        barriga = request.form.get("barriga")
        peito = request.form.get("peito")
        braco_dir = request.form.get("braco_dir")
        braco_esq = request.form.get("braco_esq")
        coxa_dir = request.form.get("coxa_dir")
        coxa_esq = request.form.get("coxa_esq")
        pant_dir = request.form.get("pant_dir")
        pant_esq = request.form.get("pant_esq")

        conn.execute("""
            INSERT INTO body_measures
            (user_id, barriga, peito, braco_dir, braco_esq, coxa_dir, coxa_esq, pant_dir, pant_esq, created_at)
            VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))
        """, (user_id, barriga, peito, braco_dir, braco_esq,
              coxa_dir, coxa_esq, pant_dir, pant_esq))
        conn.commit()
        flash("✅ Medidas salvas com sucesso!", "success")
        return redirect(url_for("medidas"))

    # 📊 Pega a primeira e última medida para exibir no comparativo
    inicial = conn.execute("""
        SELECT * FROM body_measures
        WHERE user_id=? ORDER BY created_at ASC LIMIT 1
    """, (user_id,)).fetchone()

    ultima = conn.execute("""
        SELECT * FROM body_measures
        WHERE user_id=? ORDER BY created_at DESC LIMIT 1
    """, (user_id,)).fetchone()

    conn.close()
    return render_template("medidas.html", inicial=inicial, ultima=ultima)
    
    
@app.route("/peso_diario", methods=["POST"])
def peso_diario():
    user_id = session.get("uid")
    if not user_id:
        flash("Faça login para registrar seu peso.")
        return redirect(url_for("login"))

    peso_raw = request.form.get("peso_diario")
    if not peso_raw:
        flash("Informe o peso.", "error")
        return redirect(url_for("perfil"))

    try:
        p = float(peso_raw.replace(",", "."))
    except ValueError:
        flash("Peso inválido.", "error")
        return redirect(url_for("perfil"))

    now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row  # ✅ permite acessar por nome da coluna
        cur = conn.cursor()

        # Salva o peso
        cur.execute(
            "INSERT INTO weight_log (user_id, weight_kg, log_date) VALUES (?, ?, ?)",
            (user_id, p, now_local)
        )
        conn.commit()

        # Busca perfil do usuário
        prof = conn.execute("SELECT * FROM profile WHERE user_id=?", (user_id,)).fetchone()
        if prof and prof["height_m"]:
            h = float(prof["height_m"])
            min_w = 18.5 * (h * h)
            max_w = 24.9 * (h * h)

            if min_w <= p <= max_w:
                flash("🎉 Você atingiu o peso ideal! Agora registre suas medidas finais.")
                return redirect(url_for("medidas"))

    flash("Peso salvo com sucesso!")
    return redirect(url_for("perfil"))
   
@app.route("/comparativo")
@login_required
def comparativo():
    conn = get_db()

    primeira = conn.execute("""
        SELECT * FROM body_measures
        WHERE user_id=? ORDER BY created_at ASC LIMIT 1
    """, (session["uid"],)).fetchone()

    ultima = conn.execute("""
        SELECT * FROM body_measures
        WHERE user_id=? ORDER BY created_at DESC LIMIT 1
    """, (session["uid"],)).fetchone()

    conn.close()

    if not primeira or not ultima:
        flash("Você precisa registrar pelo menos duas medidas para gerar o comparativo.", "warning")
        return redirect(url_for("medidas"))

    campos = {
        "barriga": "Barriga",
        "peito": "Peito",
        "braco_dir": "Braço Direito",
        "braco_esq": "Braço Esquerdo",
        "coxa_dir": "Coxa Direita",
        "coxa_esq": "Coxa Esquerda",
        "pant_dir": "Panturrilha Direita",
        "pant_esq": "Panturrilha Esquerda"
    }

    diferencas = {}
    for key in campos.keys():
        diff = float(ultima[key]) - float(primeira[key])
        diferencas[key] = round(diff, 1)

    return render_template("comparativo.html",
                           primeira=primeira,
                           ultima=ultima,
                           campos=campos,
                           diferencas=diferencas)
                           
    
@app.route("/peso_grafico")
def peso_grafico():
    user_id = session.get("uid")
    if not user_id:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT weight_kg, created_at
        FROM weight_log
        WHERE user_id = ?
        ORDER BY created_at
    """, (user_id,))
    data = cur.fetchall()
    conn.close()

    # Converte em duas listas: datas e pesos
    labels = [row["created_at"] for row in data]
    pesos = [row["weight_kg"] for row in data]

    return render_template("peso_grafico.html", labels=labels, pesos=pesos)
   

    
    
@app.route("/pre_jogo")
@login_required
def pre_jogo():
    dicas = [
        "💧 Hidratação: beba água ao longo do dia anterior e no dia do jogo.",
        "🥗 Alimentação: priorize carboidratos complexos (arroz, batata, macarrão integral) e proteínas leves.",
        "😴 Sono: durma de 7 a 9 horas na noite anterior.",
        "🧘 Alongamento leve e mobilidade, sem exercícios pesados.",
        "⚽ Revisar mentalmente jogadas e posicionamento em campo.",
        "🕑 No dia do jogo: faça um café da manhã/lanche leve 3 h antes e um aquecimento gradual."
    ]
    return render_template("pre_jogo.html", dicas=dicas)
  
@app.route("/treinos_especificos")
@login_required
def treinos_especificos():
    return render_template("treinos_especificos.html")
    
TREINOS_VELOCIDADE = [
    {
        "id": 1,
        "titulo": "Dia 1 - Aceleração Inicial",
        "descricao": "Foca no impulso e na rapidez da primeira passada — essencial para ganhar no arranque.",
        "exercicios": [
            "Sprint estacionário 6x20s",
            "Skipping rápido 4x30s",
            "Agachamento + impulso 4x10",
            "Prancha frontal 3x30s"
        ]
    },
    {
        "id": 2,
        "titulo": "Dia 2 - Passada Rápida",
        "descricao": "Melhora a frequência e coordenação das passadas para atingir máxima velocidade.",
        "exercicios": [
            "Corrida estacionária acelerada 6x20s",
            "Passadas curtas e rápidas 4x15m (ou 5 passos)",
            "Lateral shuffle 4x20s",
            "Core lateral 3x30s"
        ]
    },
    {
        "id": 3,
        "titulo": "Dia 3 - Reação e Arranque",
        "descricao": "Treina a velocidade de reação para ganhar tempo no 1x1 e antecipações.",
        "exercicios": [
            "Sprint reativo (com sinal sonoro ou visual) 6x",
            "Saltos reativos + arranque curto 4x",
            "Skipping explosivo 4x20s",
            "Prancha dinâmica 3x30s"
        ]
    },
    {
        "id": 4,
        "titulo": "Dia 4 - Velocidade Máxima",
        "descricao": "Desenvolve velocidade máxima e melhora a capacidade de manter o ritmo forte.",
        "exercicios": [
            "Corrida estacionária máxima 8x15s",
            "Aceleração curta (3 a 5m) 5x",
            "Saltos alternados + impulso 4x15",
            "Mobilidade ativa"
        ]
    },
    {
        "id": 5,
        "titulo": "Dia 5 - Sprint Repetido",
        "descricao": "Foca em repetir sprints curtos com alta intensidade, simulando situações reais de jogo.",
        "exercicios": [
            "Sprint estacionário 20s ON / 20s OFF (8 rounds)",
            "Passadas rápidas + troca de direção 5x",
            "Skipping + salto 4x30s",
            "Core frontal e lateral 3x30s"
        ]
    },
    {
        "id": 6,
        "titulo": "Dia 6 - Velocidade com Bola ⚽",
        "descricao": "Desenvolve velocidade e controle de bola em alta intensidade, mesmo em espaços pequenos.",
        "exercicios": [
            "Condução curta de bola + aceleração 5x",
            "Passe na parede + arranque 4x",
            "Troca de direção com bola 5x",
            "Mobilidade ativa com bola"
        ]
    },
    {
        "id": 7,
        "titulo": "Dia 7 - Teste de Velocidade 🏁",
        "descricao": "Teste final para avaliar ganho de velocidade e explosão da semana.",
        "exercicios": [
            "Sprint estacionário máximo 10x15s",
            "Passadas rápidas cronometradas",
            "Burpees com arranque curto 3x12",
            "Descompressão muscular"
        ]
    }
]

# ------------------- TREINO DE EXPLOSÃO -------------------

TREINOS_EXPLOSAO = [
    {
        "id": 1,
        "titulo": "Dia 1 - Arranque Explosivo",
        "descricao": "Desenvolve potência nas pernas e reação rápida para sair do lugar com velocidade.",
        "exercicios": [
            "Sprint estacionário 6x20s",
            "Agachamento com salto 4x10",
            "Skipping explosivo 4x20s",
            "Prancha frontal 3x30s"
        ]
    },
    {
        "id": 2,
        "titulo": "Dia 2 - Aceleração Curta",
        "descricao": "Foca em acelerações de curta distância simulando arrancadas de jogo.",
        "exercicios": [
            "Arranque em 3 metros (ida e volta) 6x",
            "Lateral shuffle + sprint curto 4x",
            "Salto vertical com impulso 4x10",
            "Core lateral 3x30s"
        ]
    },
    {
        "id": 3,
        "titulo": "Dia 3 - Potência de Pernas",
        "descricao": "Fortalece e dá explosão às pernas com exercícios funcionais intensos.",
        "exercicios": [
            "Pliometria estacionária (saltos rápidos) 4x20s",
            "Afundo com salto alternado 3x12",
            "Burpees explosivos 3x10",
            "Prancha dinâmica 3x30s"
        ]
    },
    {
        "id": 4,
        "titulo": "Dia 4 - Tempo de Reação",
        "descricao": "Trabalha sua capacidade de reagir rapidamente a estímulos, simulando situações reais.",
        "exercicios": [
            "Sprint reativo (com sinal sonoro ou visual) 6x",
            "Mudança rápida de direção em 2m 5x",
            "Saltos alternados 4x15",
            "Mobilidade ativa"
        ]
    },
    {
        "id": 5,
        "titulo": "Dia 5 - Aceleração Contínua",
        "descricao": "Melhora sua capacidade de manter explosão repetida em pouco tempo.",
        "exercicios": [
            "Sprint estacionário 30s ON / 30s OFF (8 rounds)",
            "Skipping com potência 4x30s",
            "Agachamento + salto 4x10",
            "Core frontal e lateral 3x30s"
        ]
    },
    {
        "id": 6,
        "titulo": "Dia 6 - Explosão com Bola ⚽",
        "descricao": "Simula acelerações e potência com bola, mesmo em espaço pequeno.",
        "exercicios": [
            "Condução de bola curta + arranque 5x",
            "Passe na parede + sprint estacionário 4x",
            "Mudança rápida de direção com bola 5x",
            "Mobilidade ativa com bola"
        ]
    },
    {
        "id": 7,
        "titulo": "Dia 7 - Teste de Explosão 🏁",
        "descricao": "Teste seu nível de potência e velocidade acumulada da semana.",
        "exercicios": [
            "Sprint estacionário máximo 10x15s",
            "Pliometria rápida 5x20s",
            "Burpees explosivos 3x12",
            "Descompressão muscular"
        ]
    }
]

# ------------------- TREINO DE FORÇA -------------------

TREINOS_FORCA = [
    {
        "id": 1,
        "titulo": "Dia 1 - Base de Força 🏋️",
        "descricao": "Foco em construir uma base sólida com exercícios fundamentais.",
        "exercicios": [
            "Agachamento 4x10",
            "Flexão de braço 4x10",
            "Prancha frontal 3x30s",
            "Alongamento dinâmico"
        ]
    },
    {
        "id": 2,
        "titulo": "Dia 2 - Força Funcional",
        "descricao": "Fortalece músculos estabilizadores e movimentos compostos.",
        "exercicios": [
            "Afundo unilateral 3x12",
            "Prancha lateral 3x30s cada lado",
            "Superman 3x15",
            "Abdominal bicicleta 3x20"
        ]
    },
    {
        "id": 3,
        "titulo": "Dia 3 - Core + Pernas",
        "descricao": "Fortalecimento do centro e potência de membros inferiores.",
        "exercicios": [
            "Agachamento com salto 3x10",
            "Ponte de quadril 4x15",
            "Prancha dinâmica 3x30s",
            "Abdominal reto 3x20"
        ]
    },
    {
        "id": 4,
        "titulo": "Dia 4 - Força Explosiva",
        "descricao": "Integra força com velocidade para movimentos potentes.",
        "exercicios": [
            "Pliometria 3x12",
            "Agachamento isométrico 3x30s",
            "Flexão com palmas 3x10",
            "Core lateral 3x30s"
        ]
    },
    {
        "id": 5,
        "titulo": "Dia 5 - Força com Bola ⚽",
        "descricao": "Aplicação prática da força nos movimentos do futebol.",
        "exercicios": [
            "Passe com potência 4x10",
            "Domínio + arranque 4x",
            "Sprint + chute 4x",
            "Mobilidade de quadril"
        ]
    },
    {
        "id": 6,
        "titulo": "Dia 6 - Força Total",
        "descricao": "Treino de corpo inteiro para consolidar ganhos.",
        "exercicios": [
            "Agachamento + flexão 4x10",
            "Prancha frontal 3x40s",
            "Ponte unilateral 3x12",
            "Alongamento ativo"
        ]
    },
    {
        "id": 7,
        "titulo": "Dia 7 - Teste de Força 🏁",
        "descricao": "Avaliação dos ganhos de força e resistência muscular.",
        "exercicios": [
            "Máximo de flexões em 1 minuto",
            "Máximo de agachamentos em 1 minuto",
            "Máximo de prancha (tempo)",
            "Recuperação ativa"
        ]
    }
]


TREINOS_RESISTENCIA = [
    {
        "id": 1,
        "titulo": "Dia 1 - Base Aeróbica",
        "descricao": "Constrói sua base de resistência para manter o ritmo de jogo, mesmo em espaço reduzido.",
        "exercicios": [
            "Corrida estacionária leve - 15 min",
            "Skipping 4x30s",
            "Polichinelo 3x30s",
            "Alongamento dinâmico"
        ]
    },
    {
        "id": 2,
        "titulo": "Dia 2 - Corrida Intervalada",
        "descricao": "Alterna momentos de alta e baixa intensidade simulando sprints, mesmo sem campo.",
        "exercicios": [
            "Corrida estacionária forte 30s + leve 30s (6x)",
            "Skipping explosivo 4x30s",
            "Agachamento com salto 3x10",
            "Core frontal 3x30s"
        ]
    },
    {
        "id": 3,
        "titulo": "Dia 3 - Resistência de Jogo",
        "descricao": "Simula intensidade de jogo com deslocamentos curtos e exercícios funcionais.",
        "exercicios": [
            "Mudança de direção em 2m - 5x",
            "Lateral shuffle estacionário 4x30s",
            "Burpees 3x12",
            "Prancha com movimento 3x30s"
        ]
    },
    {
        "id": 4,
        "titulo": "Dia 4 - Fartlek",
        "descricao": "Treino contínuo com variações de velocidade sem precisar sair de casa.",
        "exercicios": [
            "Corrida estacionária alternando ritmo - 20 min",
            "Acelerações progressivas (skipping) 6x30s",
            "Saltos contínuos 3x30s",
            "Mobilidade geral"
        ]
    },
    {
        "id": 5,
        "titulo": "Dia 5 - Alta Intensidade",
        "descricao": "Trabalha sua capacidade de manter intensidade alta mesmo em pouco espaço.",
        "exercicios": [
            "HIIT 30s ON / 30s OFF (8 rounds)",
            "Corrida estacionária com aceleração 4x30s",
            "Agachamento explosivo 4x10",
            "Core lateral 3x30s"
        ]
    },
    {
        "id": 6,
        "titulo": "Dia 6 - Resistência com Bola ⚽",
        "descricao": "Simula situações reais de jogo com bola, mesmo em espaço pequeno.",
        "exercicios": [
            "Condução de bola em zigue-zague curto - 5x",
            "Passe na parede + desmarque curto - 5x",
            "Sprint estacionário com bola - 4x30s",
            "Mobilidade ativa com bola"
        ]
    },
    {
        "id": 7,
        "titulo": "Dia 7 - Teste Final 🏁",
        "descricao": "Teste sua resistência e finalize a semana com intensidade máxima, em casa.",
        "exercicios": [
            "HIIT 8 rounds 30s forte / 30s leve",
            "Shuttle run indoor (2m ida e volta) 5x",
            "Saltos + sprint estacionário",
            "Descompressão muscular"
        ]
    }
]

TREINOS_MOBILIDADE = [
    {
        "id": 1,
        "titulo": "Dia 1 - Mobilidade de Tornozelo e Quadril",
        "descricao": "Melhora a base da sua movimentação e aceleração.",
        "exercicios": [
            "Mobilidade de tornozelo 3x30s",
            "Alongamento borboleta 3x30s",
            "Rotação de quadril em pé 3x10",
            "Prancha com elevação de perna 3x20s"
        ]
    },
    {
        "id": 2,
        "titulo": "Dia 2 - Mobilidade de Coluna e Posterior",
        "descricao": "Aumenta a flexibilidade e evita lesões lombares.",
        "exercicios": [
            "Gato-camelo 3x10",
            "Toque nos pés com pernas estendidas 3x30s",
            "Alongamento em posição de prancha 3x30s",
            "Respiração profunda com alongamento 3x"
        ]
    },
    {
        "id": 3,
        "titulo": "Dia 3 - Mobilidade de Joelhos e Core",
        "descricao": "Fortalece e estabiliza joelhos, quadril e abdômen.",
        "exercicios": [
            "Agachamento profundo com mobilidade 3x10",
            "Elevação de joelhos no chão 3x12",
            "Prancha lateral 3x20s",
            "Alongamento de isquiotibiais"
        ]
    },
    {
        "id": 4,
        "titulo": "Dia 4 - Mobilidade Total do Corpo",
        "descricao": "Ativa e solta todas as articulações antes do jogo.",
        "exercicios": [
            "Movimento articular completo 2x",
            "Alongamento dinâmico em deslocamento",
            "Mobilidade torácica + quadril",
            "Alongamento em prancha alta 3x20s"
        ]
    },
    {
        "id": 5,
        "titulo": "Dia 5 - Mobilidade Explosiva",
        "descricao": "Foca em amplitude rápida para arranques e giros.",
        "exercicios": [
            "Mobilidade em avanço 3x",
            "Rotação de tronco com passada 3x12",
            "Skips + mobilidade ativa",
            "Alongamento em movimento 3x20s"
        ]
    },
    {
        "id": 6,
        "titulo": "Dia 6 - Mobilidade com Bola ⚽",
        "descricao": "Trabalha controle de bola e amplitude corporal.",
        "exercicios": [
            "Dominadas + giro de quadril 3x",
            "Controle de bola alternando pernas 3x30s",
            "Alongamento dinâmico com bola",
            "Mobilidade leve ativa"
        ]
    },
    {
        "id": 7,
        "titulo": "Dia 7 - Recuperação Ativa 🧘",
        "descricao": "Dia leve de recuperação com foco em respiração e amplitude.",
        "exercicios": [
            "Alongamentos leves (todo corpo) 10 min",
            "Respiração profunda controlada",
            "Mobilidade articular suave",
            "Relaxamento postural"
        ]
    }
]

@app.route("/treino_resistencia", methods=["GET", "POST"])
@login_required
def treino_resistencia():
    user_id = session["uid"]

    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treino_resistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dia INTEGER NOT NULL,
            UNIQUE(user_id, dia)
        )
    """)
    conn.commit()

    cur.execute("SELECT dia FROM treino_resistencia WHERE user_id=?", (user_id,))
    concluidos = [row[0] for row in cur.fetchall()]

    progresso = int((len(concluidos) / len(TREINOS_RESISTENCIA)) * 100)

    conn.close()

    return render_template(
        "treino_resistencia.html",
        treinos=TREINOS_RESISTENCIA,
        concluidos=concluidos,
        progresso=progresso
    )


@app.route("/concluir_treino_resistencia/<int:dia>", methods=["POST"])
@login_required
def concluir_treino_resistencia(dia):
    user_id = session["uid"]
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO treino_resistencia (user_id, dia) VALUES (?, ?)", (user_id, dia))
    conn.commit()

    # Se terminou todos os treinos, reseta
    cur.execute("SELECT COUNT(*) FROM treino_resistencia WHERE user_id=?", (user_id,))
    total = cur.fetchone()[0]
    if total >= len(TREINOS_RESISTENCIA):
        cur.execute("DELETE FROM treino_resistencia WHERE user_id=?", (user_id,))
        conn.commit()

    conn.close()
    return redirect(url_for("treino_resistencia"))

@app.route("/treino_velocidade", methods=["GET", "POST"])
@login_required
def treino_velocidade():
    user_id = session["uid"]

    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treino_velocidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dia INTEGER NOT NULL,
            UNIQUE(user_id, dia)
        )
    """)
    conn.commit()

    cur.execute("SELECT dia FROM treino_velocidade WHERE user_id=?", (user_id,))
    concluidos = [row[0] for row in cur.fetchall()]

    progresso = int((len(concluidos) / len(TREINOS_VELOCIDADE)) * 100)

    return render_template(
        "treino_velocidade.html",
        treinos=TREINOS_VELOCIDADE,
        concluidos=concluidos,
        progresso=progresso
    )


@app.route("/concluir_treino_velocidade/<int:dia>", methods=["POST"])
@login_required
def concluir_treino_velocidade(dia):
    user_id = session["uid"]
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO treino_velocidade (user_id, dia) VALUES (?, ?)", (user_id, dia))
    conn.commit()

    # Se terminou todos os treinos, reseta
    cur.execute("SELECT COUNT(*) FROM treino_velocidade WHERE user_id=?", (user_id,))
    total = cur.fetchone()[0]
    if total >= len(TREINOS_VELOCIDADE):
        cur.execute("DELETE FROM treino_velocidade WHERE user_id=?", (user_id,))
        conn.commit()

    conn.close()
    return redirect(url_for("treino_velocidade"))
    



@app.route("/treino_forca", methods=["GET", "POST"])
@login_required
def treino_forca():
    user_id = session["uid"]

    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treino_forca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dia INTEGER NOT NULL,
            UNIQUE(user_id, dia)
        )
    """)
    conn.commit()

    cur.execute("SELECT dia FROM treino_forca WHERE user_id=?", (user_id,))
    concluidos = [row[0] for row in cur.fetchall()]

    progresso = int((len(concluidos) / len(TREINOS_FORCA)) * 100)

    return render_template(
        "treino_forca.html",
        treinos=TREINOS_FORCA,
        concluidos=concluidos,
        progresso=progresso
    )


@app.route("/concluir_treino_forca/<int:dia>", methods=["POST"])
@login_required
def concluir_treino_forca(dia):
    user_id = session["uid"]
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO treino_forca (user_id, dia) VALUES (?, ?)", (user_id, dia))
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM treino_forca WHERE user_id=?", (user_id,))
    total = cur.fetchone()[0]
    if total >= len(TREINOS_FORCA):
        cur.execute("DELETE FROM treino_forca WHERE user_id=?", (user_id,))
        conn.commit()

    conn.close()
    return redirect(url_for("treino_forca"))



@app.route("/treino_explosao", methods=["GET", "POST"])
@login_required
def treino_explosao():
    user_id = session["uid"]

    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treino_explosao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dia INTEGER NOT NULL,
            UNIQUE(user_id, dia)
        )
    """)
    conn.commit()

    cur.execute("SELECT dia FROM treino_explosao WHERE user_id=?", (user_id,))
    concluidos = [row[0] for row in cur.fetchall()]

    progresso = int((len(concluidos) / len(TREINOS_EXPLOSAO)) * 100)

    return render_template(
        "treino_explosao.html",
        treinos=TREINOS_EXPLOSAO,
        concluidos=concluidos,
        progresso=progresso
    )


@app.route("/concluir_treino_explosao/<int:dia>", methods=["POST"])
@login_required
def concluir_treino_explosao(dia):
    user_id = session["uid"]
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO treino_explosao (user_id, dia) VALUES (?, ?)", (user_id, dia))
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM treino_explosao WHERE user_id=?", (user_id,))
    total = cur.fetchone()[0]
    if total >= len(TREINOS_EXPLOSAO):
        cur.execute("DELETE FROM treino_explosao WHERE user_id=?", (user_id,))
        conn.commit()

    conn.close()
    return redirect(url_for("treino_explosao"))


@app.route("/treino_mobilidade", methods=["GET", "POST"])
@login_required
def treino_mobilidade():
    user_id = session["uid"]
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treino_mobilidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dia INTEGER NOT NULL,
            UNIQUE(user_id, dia)
        )
    """)
    conn.commit()

    # Buscar treinos concluídos atualizados
    cur.execute("SELECT dia FROM treino_mobilidade WHERE user_id=?", (user_id,))
    concluidos = [row[0] for row in cur.fetchall()]

    progresso = int((len(concluidos) / len(TREINOS_MOBILIDADE)) * 100)

    conn.close()

    return render_template(
        "treino_mobilidade.html",
        treinos=TREINOS_MOBILIDADE,
        concluidos=concluidos,
        progresso=progresso
    )

@app.route("/concluir_treino_mobilidade/<int:dia>", methods=["POST"])
@login_required
def concluir_treino_mobilidade(dia):
    user_id = session["uid"]
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO treino_mobilidade (user_id, dia) VALUES (?, ?)", (user_id, dia))
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM treino_mobilidade WHERE user_id=?", (user_id,))
    total = cur.fetchone()[0]
    if total >= len(TREINOS_MOBILIDADE):
        cur.execute("DELETE FROM treino_mobilidade WHERE user_id=?", (user_id,))
        conn.commit()

    conn.close()
    return redirect(url_for("treino_mobilidade"))
    
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
    



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
