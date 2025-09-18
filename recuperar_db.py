import sqlite3
import os
import shutil

# Caminhos
db_corrompido = "/storage/emulated/0/Download/varzea_app_complete/varzea.db"
db_novo = "/storage/emulated/0/Download/varzea_app_complete/varzea_novo.db"
backup_path = "/storage/emulated/0/Download/varzea_app_complete/varzea_corrompido_backup.db"

# Passo 1: criar backup do banco corrompido
if os.path.exists(db_corrompido):
    shutil.move(db_corrompido, backup_path)
    print(f"Banco corrompido movido para backup: {backup_path}")

# Passo 2: criar novo banco limpo
con_novo = sqlite3.connect(db_novo)
cur_novo = con_novo.cursor()

# Criar tabelas essenciais
cur_novo.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL
)
""")

cur_novo.execute("""
CREATE TABLE IF NOT EXISTS treinos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    data TEXT,
    descricao TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

con_novo.commit()

# Passo 3: tentar recuperar dados do banco corrompido
try:
    con_old = sqlite3.connect(f'file:{backup_path}?mode=ro', uri=True)
    cur_old = con_old.cursor()

    # Recuperar usuários
    cur_old.execute("SELECT id, nome, email, senha FROM users")
    users = cur_old.fetchall()
    cur_novo.executemany("INSERT OR IGNORE INTO users (id, nome, email, senha) VALUES (?, ?, ?, ?)", users)

    # Recuperar treinos
    cur_old.execute("SELECT id, user_id, data, descricao FROM treinos")
    treinos = cur_old.fetchall()
    cur_novo.executemany("INSERT OR IGNORE INTO treinos (id, user_id, data, descricao) VALUES (?, ?, ?, ?)", treinos)

    con_novo.commit()
    con_old.close()
    print(f"Recuperação concluída. Novo banco com dados recuperados: {db_novo}")

except sqlite3.DatabaseError:
    print("Falha ao recuperar dados. Novo banco criado vazio.")

con_novo.close()
