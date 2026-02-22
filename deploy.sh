#!/bin/bash
# ================================================================
# HiveCore v2 — Deployment Script fuer Hetzner Server
# ================================================================
#
# USAGE (auf dem Server ausfuehren):
#   bash deploy.sh
#
# VORAUSSETZUNGEN:
#   - Python 3.11+
#   - pip
#   - git
#   - Screen oder systemd
#
# ERSTER DEPLOY:
#   1. SSH auf den Server:  ssh root@159.69.157.42
#   2. Git klonen:          git clone https://github.com/scafa-assistant/hivecore-v2.git
#   3. In den Ordner:       cd hivecore-v2
#   4. .env erstellen:      nano .env  (API Keys eintragen!)
#   5. Deploy starten:      bash deploy.sh
#
# UPDATE DEPLOY (danach):
#   1. SSH auf den Server:  ssh root@159.69.157.42
#   2. In den Ordner:       cd hivecore-v2
#   3. Deploy starten:      bash deploy.sh
# ================================================================

set -e

echo "================================================"
echo " HiveCore v2 — Deployment"
echo "================================================"

# 1. Git Pull (neuesten Code holen)
echo ""
echo "[1/5] Git Pull..."
git pull origin master
echo "     Code aktualisiert."

# 2. Python Dependencies installieren
echo ""
echo "[2/5] Dependencies installieren..."
pip install -r requirements.txt --quiet 2>&1
echo "     Dependencies installiert."

# 3. Pruefen ob .env existiert
echo ""
echo "[3/5] .env pruefen..."
if [ ! -f .env ]; then
    echo "     FEHLER: .env Datei fehlt!"
    echo "     Erstelle sie mit: nano .env"
    echo "     Vorlage:"
    echo "       MOONSHOT_API_KEY=sk-..."
    echo "       KIMI_API_KEY=sk-..."
    echo "       SONNET_API_KEY=sk-ant-..."
    echo "       BRAIN_VERSION=v2"
    echo "       PULSE_HOUR=8"
    echo "       PULSE_MINUTE=0"
    exit 1
fi
echo "     .env vorhanden."

# 4. Stoppe laufenden Server (screen session)
echo ""
echo "[4/5] Server stoppen..."
# Versuche screen session zu killen
screen -S hivecore -X quit 2>/dev/null || true
# Oder: Kill uvicorn direkt
pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 2
echo "     Alter Server gestoppt."

# 5. Server neu starten (in screen session)
echo ""
echo "[5/5] Server starten..."
screen -dmS hivecore bash -c 'cd /root/hivecore-v2 && python -m uvicorn main:app --host 0.0.0.0 --port 8001 2>&1 | tee server.log'
sleep 3

# Verify
echo ""
echo "================================================"
echo " Verifikation..."
echo "================================================"
RESPONSE=$(curl -s --connect-timeout 5 http://localhost:8001/ 2>/dev/null || echo "FAILED")

if echo "$RESPONSE" | grep -q "HiveCore"; then
    echo ""
    echo " SERVER LAEUFT!"
    echo " $RESPONSE"
    echo ""
    echo " Zugriff:"
    echo "   API:       http://159.69.157.42:8001/api/"
    echo "   Dashboard: http://159.69.157.42:8001/dashboard/"
    echo "   Logs:      screen -r hivecore"
    echo "   Stop:      screen -S hivecore -X quit"
    echo ""
else
    echo ""
    echo " FEHLER: Server antwortet nicht!"
    echo " Checke Logs mit: screen -r hivecore"
    echo ""
fi

echo "================================================"
echo " Deployment fertig."
echo "================================================"
