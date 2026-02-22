#!/bin/bash
# BioResearch Assistant — Oracle Cloud ARM Setup
# Einmalig ausführen nach erstem SSH Login

set -e

echo "🚀 BioResearch Assistant Setup — Oracle Cloud ARM"

# System updaten
sudo apt update && sudo apt upgrade -y

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
sudo apt install -y docker-compose-plugin netfilter-persistent

# Firewall für Oracle (wichtig — ohne das sind Ports gesperrt!)
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 3000 -j ACCEPT
sudo netfilter-persistent save

# Swap hinzufügen (hilft bei Ollama)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Caddy für SSL
sudo apt install -y caddy

echo "✅ Setup fertig! Jetzt:"
echo "1. git clone https://github.com/synapticfour/bioresearch-assistant.git"
echo "2. cd bioresearch-assistant"
echo "3. cp .env.example .env && nano .env"
echo "4. docker compose -f docker-compose.prod.yml up -d"
echo "5. docker compose -f docker-compose.prod.yml exec backend alembic upgrade head"
echo "6. ollama pull mistral  (optional, ~4GB)"
