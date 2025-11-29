#!/bin/bash
apt-get update
apt-get install -y docker.io git
systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
