# 🚀 Deployment Guide (AWS EC2)

This guide explains how to deploy the **Luna Mediator Agent** to a single AWS EC2 instance.

## Prerequisites

1.  **AWS Account**
2.  **Domain Name** (Optional, but recommended for SSL)
3.  **Environment Variables** (See `.env.example`)

## Step 1: Launch EC2 Instance

1.  Go to AWS Console > EC2 > Launch Instance.
2.  **Name**: `serene-mediator`
3.  **OS**: Ubuntu 22.04 LTS (x86)
4.  **Instance Type**: `t3.medium` (2 vCPU, 4GB RAM) - *Required for AI/ML libs*
5.  **Key Pair**: Create or select an existing key pair (e.g., `serene-key.pem`).
6.  **Network Settings**:
    *   Allow SSH traffic from Anywhere (0.0.0.0/0)
    *   Allow HTTP traffic from the internet
    *   Allow HTTPS traffic from the internet
7.  **Storage**: 30GB gp3 (Default is 8GB, which is too small for Docker images)

## Step 2: Server Setup

SSH into your instance:
```bash
ssh -i serene-key.pem ubuntu@3.236.8.180
```

Run the following commands to install Docker & Git:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Logout and log back in to apply group changes
exit
```

## Step 3: Deploy Application

1.  **Clone Repository**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/serene.git
    cd serene/backend
    ```

2.  **Configure Environment**:
    Create the `.env` file with your production keys:
    ```bash
    nano .env
    ```
    Paste your keys:
    ```env
    LIVEKIT_URL=wss://...
    LIVEKIT_API_KEY=...
    LIVEKIT_API_SECRET=...
    OPENAI_API_KEY=...
    DEEPGRAM_API_KEY=...
    ELEVENLABS_API_KEY=...
    SUPABASE_URL=...
    SUPABASE_KEY=...
    ```

3.  **Start Services**:
    ```bash
    docker compose up -d --build
    ```

## Step 4: Verify Deployment

1.  **Check Logs**:
    ```bash
    docker compose logs -f agent
    ```
    You should see: `🚀 Starting Luna Mediator Agent`

2.  **Test API**:
    Visit `http://<EC2_PUBLIC_IP>:8000` in your browser. You should see `{"message": "HeartSync API is running"}`.

## Updating the App

To deploy new changes, simply run:
```bash
./deploy.sh
```
