#!/data/data/com.termux/files/usr/bin/bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT=587
export SMTP_USER="seuemail@gmail.com"
export SMTP_PASS="SUA_SENHA_DE_APP"
export SMTP_FROM="$SMTP_USER"
export APP_SECRET="troca_esse_segredo"
export BASE_URL="http://127.0.0.1:5000"
python3 varzea_trainer_flask.py
