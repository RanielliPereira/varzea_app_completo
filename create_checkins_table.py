# create_checkins_table.py
import sqlite3
import os

# Ajuste o caminho do banco se o seu tiver outro nome
DB = os.path.join(os.path.dirname(__file__), "varzea.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    treino TEXT NOT NULL,
    data TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE(user_id, treino, data)
);
""")

conn.commit()
conn.close()

print("Tabela checkins criada / verificada com sucesso.")

