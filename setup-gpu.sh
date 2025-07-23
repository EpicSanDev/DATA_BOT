#!/bin/bash
# DATA_BOT v4 - GPU-enabled Docker Setup Script

set -e  # Exit on any error

echo "🚀 DATA_BOT v4 - Configuration Docker avec support GPU"
echo "=================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Docker on different systems
install_docker() {
    echo "📦 Installation de Docker..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        if command_exists apt-get; then
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
        # CentOS/RHEL
        elif command_exists yum; then
            sudo yum install -y docker
            sudo systemctl start docker
            sudo systemctl enable docker
            sudo usermod -aG docker $USER
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "⚠️  Veuillez installer Docker Desktop depuis https://docker.com/products/docker-desktop"
        exit 1
    fi
}

# Function to install NVIDIA Container Toolkit
install_nvidia_docker() {
    echo "🔧 Installation du support GPU NVIDIA..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Add NVIDIA package repositories
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        
        sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
        sudo systemctl restart docker
        
        echo "✅ Support GPU NVIDIA installé"
    else
        echo "⚠️  Support GPU disponible uniquement sur Linux"
    fi
}

# Function to check GPU availability
check_gpu() {
    echo "🔍 Vérification des GPU disponibles..."
    
    if command_exists nvidia-smi; then
        echo "📊 GPUs NVIDIA détectés:"
        nvidia-smi --list-gpus
        return 0
    else
        echo "⚠️  Aucun GPU NVIDIA détecté ou nvidia-smi non installé"
        return 1
    fi
}

# Function to create optimized docker-compose for GPU
create_gpu_compose() {
    echo "📝 Création de docker-compose-gpu.yml..."
    
    cat > docker-compose-gpu.yml << 'EOF'
version: '3.8'

services:
  # Main DATA_BOT v4 application
  databot-v4:
    build: .
    container_name: databot-v4
    ports:
      - "8080:8080"  # Main web interface
      - "8081:8081"  # Browser plugin server
      - "8082:8082"  # Admin interface
      - "8083:8083"  # GraphQL API
    environment:
      - ENVIRONMENT=docker
      - REDIS_HOST=redis
      - ELASTICSEARCH_HOST=elasticsearch
      - OPENSEARCH_HOST=opensearch
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=databot_v4
      - POSTGRES_USER=databot
      - POSTGRES_PASSWORD=databot_password
      - OLLAMA_HOST=ollama:11434
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./archive:/app/archive
      - ./screenshots:/app/screenshots
      - ./config:/app/config
    depends_on:
      - redis
      - postgres
      - elasticsearch
      - opensearch
      - ollama
    restart: unless-stopped
    networks:
      - databot-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # Ollama AI service with GPU support
  ollama:
    image: ollama/ollama:latest
    container_name: databot-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
      - NVIDIA_VISIBLE_DEVICES=all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - databot-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis for distributed coordination and caching
  redis:
    image: redis:7-alpine
    container_name: databot-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - databot-network
    command: redis-server --appendonly yes

  # PostgreSQL for enhanced database features
  postgres:
    image: postgres:15-alpine
    container_name: databot-postgres
    environment:
      - POSTGRES_DB=databot_v4
      - POSTGRES_USER=databot
      - POSTGRES_PASSWORD=databot_password
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    restart: unless-stopped
    networks:
      - databot-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U databot"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Elasticsearch for search and analytics
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    container_name: databot-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    restart: unless-stopped
    networks:
      - databot-network
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # OpenSearch as alternative to Elasticsearch
  opensearch:
    image: opensearchproject/opensearch:2.11.0
    container_name: databot-opensearch
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
    ports:
      - "9201:9200"
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    restart: unless-stopped
    networks:
      - databot-network

  # Vector database (Qdrant)
  qdrant:
    image: qdrant/qdrant:v1.6.0
    container_name: databot-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    restart: unless-stopped
    networks:
      - databot-network

  # Monitoring with Prometheus
  prometheus:
    image: prom/prometheus:v2.47.0
    container_name: databot-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped
    networks:
      - databot-network
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'

  # Visualization with Grafana
  grafana:
    image: grafana/grafana:10.1.0
    container_name: databot-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_SECURITY_ADMIN_USER=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    restart: unless-stopped
    networks:
      - databot-network

  # Load balancer/reverse proxy
  nginx:
    image: nginx:alpine
    container_name: databot-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - databot-v4
      - ollama
    restart: unless-stopped
    networks:
      - databot-network

volumes:
  redis-data:
  postgres-data:
  elasticsearch-data:
  opensearch-data:
  qdrant-data:
  prometheus-data:
  grafana-data:
  ollama-data:

networks:
  databot-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF

    echo "✅ docker-compose-gpu.yml créé"
}

# Function to create initialization scripts
create_init_scripts() {
    echo "📝 Création des scripts d'initialisation..."
    
    mkdir -p init-scripts monitoring/grafana nginx
    
    # PostgreSQL init script
    cat > init-scripts/01-init.sql << 'EOF'
-- DATA_BOT v4 Database Initialization
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_web_resources_url ON web_resources USING gin(url gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_web_resources_domain ON web_resources(domain);
CREATE INDEX IF NOT EXISTS idx_web_resources_status ON web_resources(status);
CREATE INDEX IF NOT EXISTS idx_web_resources_discovered_at ON web_resources(discovered_at);
EOF

    # Prometheus config
    cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'databot-v4'
    static_configs:
      - targets: ['databot-v4:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'ollama'
    static_configs:
      - targets: ['ollama:11434']
    metrics_path: '/api/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF

    # Basic nginx config
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream databot {
        server databot-v4:8080;
    }
    
    upstream ollama {
        server ollama:11434;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://databot;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /ollama/ {
            proxy_pass http://ollama/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /grafana/ {
            proxy_pass http://grafana:3000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
}

# Function to setup Ollama models
setup_ollama() {
    echo "🤖 Configuration des modèles Ollama..."
    
    # Wait for Ollama to be ready
    echo "⏳ Attente du démarrage d'Ollama..."
    until curl -f http://localhost:11434/api/tags >/dev/null 2>&1; do
        sleep 5
        echo "⏳ Ollama pas encore prêt..."
    done
    
    echo "📥 Téléchargement des modèles Ollama..."
    docker exec databot-ollama ollama pull llama2
    docker exec databot-ollama ollama pull mistral
    docker exec databot-ollama ollama pull codellama
    
    echo "✅ Modèles Ollama installés"
}

# Function to run health checks
health_check() {
    echo "🏥 Vérification de l'état des services..."
    
    services=("databot-v4:8080" "ollama:11434" "redis:6379" "postgres:5432" "elasticsearch:9200")
    
    for service in "${services[@]}"; do
        host=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        
        if docker exec databot-v4 nc -z $host $port 2>/dev/null; then
            echo "✅ $service - OK"
        else
            echo "❌ $service - NOK"
        fi
    done
}

# Main execution
main() {
    echo "🔍 Vérification des prérequis..."
    
    # Check if Docker is installed
    if ! command_exists docker; then
        echo "❌ Docker n'est pas installé"
        read -p "Voulez-vous installer Docker ? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
            echo "🔄 Veuillez redémarrer votre session et relancer ce script"
            exit 0
        else
            echo "❌ Docker est requis pour continuer"
            exit 1
        fi
    fi
    
    # Check if docker-compose is available
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        echo "❌ Docker Compose n'est pas disponible"
        exit 1
    fi
    
    # Check for GPU support
    GPU_AVAILABLE=false
    if check_gpu; then
        GPU_AVAILABLE=true
        
        # Check if NVIDIA Docker is installed
        if ! docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi >/dev/null 2>&1; then
            echo "⚠️  Support GPU NVIDIA non configuré"
            read -p "Voulez-vous installer le support GPU ? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                install_nvidia_docker
            fi
        else
            echo "✅ Support GPU NVIDIA configuré"
        fi
    fi
    
    # Create GPU-optimized compose file
    create_gpu_compose
    create_init_scripts
    
    echo "🏗️  Construction et démarrage des services..."
    
    # Build and start services
    if $GPU_AVAILABLE; then
        docker-compose -f docker-compose-gpu.yml up -d --build
    else
        echo "⚠️  Démarrage sans support GPU"
        # Remove GPU-specific configurations
        sed -i '/deploy:/,/capabilities: \[gpu\]/d' docker-compose-gpu.yml
        sed -i '/NVIDIA_VISIBLE_DEVICES/d' docker-compose-gpu.yml
        docker-compose -f docker-compose-gpu.yml up -d --build
    fi
    
    echo "⏳ Attente de l'initialisation des services..."
    sleep 30
    
    # Setup Ollama models
    if $GPU_AVAILABLE; then
        setup_ollama
    fi
    
    # Run health checks
    health_check
    
    echo ""
    echo "🎉 DATA_BOT v4 déployé avec succès !"
    echo "=================================================="
    echo "📊 Dashboard principal: http://localhost:8080"
    echo "📱 Interface mobile: http://localhost:8080/mobile"
    echo "📈 Analytics: http://localhost:8080/dashboard/analytics"
    echo "🤖 Ollama API: http://localhost:11434"
    echo "📊 Grafana: http://localhost:3000 (admin/admin123)"
    echo "🔍 Prometheus: http://localhost:9090"
    echo "🔍 Elasticsearch: http://localhost:9200"
    echo ""
    
    if $GPU_AVAILABLE; then
        echo "🚀 Support GPU activé - Performance optimisée"
    else
        echo "⚠️  Fonctionnement en mode CPU uniquement"
    fi
    
    echo ""
    echo "📖 Commandes utiles:"
    echo "  - Voir les logs: docker-compose -f docker-compose-gpu.yml logs -f"
    echo "  - Arrêter: docker-compose -f docker-compose-gpu.yml down"
    echo "  - Redémarrer: docker-compose -f docker-compose-gpu.yml restart"
    echo "  - Status: docker-compose -f docker-compose-gpu.yml ps"
}

# Run main function
main "$@"