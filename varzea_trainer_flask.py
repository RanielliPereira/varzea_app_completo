import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo   # <— importa o fuso horário
import time
import pytz



tz = pytz.timezone("America/Sao_Paulo")
now_local = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "varzea.db")

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "troca_esse_segredo")

# Mail config via env vars
app.config["MAIL_SERVER"] = os.environ.get("SMTP_HOST", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("SMTP_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("SMTP_USER", "")
app.config["MAIL_PASSWORD"] = os.environ.get("SMTP_PASS", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("SMTP_FROM", app.config["MAIL_USERNAME"] or "no-reply@example.com")

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


DB_PATH = "varzea.db"

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
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

        conn.commit()
        conn.close()
        print("✅ Banco criado com sucesso!")
    else:
        print("📁 Banco já existente — usando o atual.")
        
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

CARDAPIO = [
("Café da manhã", ["Ovos mexidos + pão integral", "Banana + aveia", "Café/chá sem açúcar"]),
("Almoço", ["Arroz + feijão", "Frango grelhado ou ovos", "Salada/legumes"]),
("Lanche", ["Fruta (banana/maçã)", "Amendoim torrado (pequena porção)"]),
("Jantar", ["Arroz ou batata", "Proteína (frango/ovo)", "Legumes refogados"]),
("Hidratação", ["2–3L de água por dia", "Evitar refrigerante e álcool pré-jogo"])
]

SUBS = [
("Proteínas", "Frango → ovos → sardinha enlatada"),
("Carboidratos", "Arroz → batata → mandioca"),
("Legumes", "Cenoura → abobrinha → brócolis"),
("Extras", "Aveia, banana, feijão, tomate, cebola, alho")
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

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["uid"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            return redirect(url_for("dashboard"))
        flash("Credenciais inválidas.", "error")
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
    import random
    frase = random.choice(MOTIVACOES)
    checkins_count = 0
    uid = session.get("uid")
    if uid:
        conn = get_db()
        row = conn.execute("SELECT COUNT(*) as c FROM checkins WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        checkins_count = row["c"] if row else 0
    return render_template("dashboard.html", nome=session.get("name","Jogador"), frase=frase, checkins_count=checkins_count)

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

    # Cria tabela se não existir
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treino_checkin (
            user_id INTEGER,
            treino_id INTEGER
        )
    """)
    conn.commit()

    # --- Quando o usuário faz check-in
    if request.method == "POST":
        treino_id_post = int(request.form.get("treino_id", treino_id))

        cur.execute(
            "SELECT 1 FROM treino_checkin WHERE user_id=? AND treino_id=?",
            (user_id, treino_id_post)
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO treino_checkin (user_id, treino_id) VALUES (?, ?)",
                (user_id, treino_id_post)
            )
            conn.commit()

        # ✅ Se for o último treino, vai direto para o vídeo final
        if treino_id_post >= total_dias:
            return redirect(url_for("video_final"))

        return redirect(url_for("treino_semi_pro", treino_id=treino_id_post))

    # --- Busca os treinos feitos
    cur.execute("SELECT treino_id FROM treino_checkin WHERE user_id=?", (user_id,))
    feitos = [row[0] for row in cur.fetchall()]
    conn.close()

    # --- Dados do treino atual
    treino = TREINO_SEMI_PRO[treino_id - 1]
    anterior = treino_id - 1 if treino_id > 1 else None
    proximo = treino_id + 1 if treino_id < total_dias else None
    feito = treino_id in feitos

    return render_template(
        "treino_semi_pro.html",
        treino=treino,
        anterior=anterior,
        proximo=proximo,
        feito=feito
    )


# --- NOVA ROTA: Vídeo final motivacional
@app.route("/video_final")
def video_final():
    if "uid" not in session:
        return redirect("/login")

    user_id = session["uid"]

    # Limpa os check-ins (reinicia os treinos)
    conn = sqlite3.connect("varzea.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM treino_checkin WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    return render_template("video_final.html")

    

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
@login_required
def dieta_view():
    return render_template("dieta.html", cardapio=CARDAPIO, subs=SUBS)

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
            (user_id, barriga, peito, braco_dir, braco_esq, coxa_dir, coxa_esq, pant_dir, pant_esq)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (user_id, barriga, peito, braco_dir, braco_esq, coxa_dir, coxa_esq, pant_dir, pant_esq))
        conn.commit()
        flash("✅ Medidas salvas com sucesso!", "success")
        return redirect(url_for("medidas"))

    # Pega a primeira e a última medida para exibir no comparativo
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
   

@app.route("/treino/<int:treino_id>", methods=["GET", "POST"])
@login_required
def treino_individual(treino_id):
    user_id = session["uid"]
    total_dias = len(TREINOS)

    with get_db() as conn:
        cur = conn.cursor()

        # ✅ Check-in
        if request.method == "POST":
            cur.execute(
                "INSERT INTO checkins (user_id, treino) VALUES (?, ?)",
                (user_id, f"treino_{treino_id}")
            )
            conn.commit()
            flash("✅ Check-in salvo com sucesso!", "success")
            return redirect(url_for("treino_individual", treino_id=treino_id))

        # ✅ Treinos feitos
        feitos = cur.execute(
            "SELECT treino FROM checkins WHERE user_id=?",
            (user_id,)
        ).fetchall()
        feitos = [f[0] for f in feitos]
        feito = f"treino_{treino_id}" in feitos

        # ✅ Se completou todos os 13 dias, redireciona pro vídeo motivacional
        if len(feitos) >= total_dias:
            # limpa os check-ins
            cur.execute("DELETE FROM checkins WHERE user_id=?", (user_id,))
            conn.commit()

            # redireciona direto pro vídeo
            flash("🏁 Parabéns! Você concluiu os 13 dias de treino. Assista o vídeo de motivação 👊", "success")
            return redirect(url_for("video_final_13"))

    # ✅ Treino atual
    treino = next((t for t in TREINOS if t["id"] == treino_id), None)
    if not treino:
        abort(404)

    anterior = treino_id - 1 if treino_id > 1 else None
    proximo = treino_id + 1 if treino_id < total_dias else None

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
    return render_template("video_final_13.html")
  
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
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
    



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
