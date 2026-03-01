#!/bin/bash
set -e
apt update && apt install -y docker.io docker-compose-plugin
usermod -aG docker ubuntu
systemctl enable docker
git clone https://github.com/SynapticFour/bioresearch-assistant.git /opt/bioresearch
cd /opt/bioresearch
docker compose -f docker-compose.prod.yml up -d
