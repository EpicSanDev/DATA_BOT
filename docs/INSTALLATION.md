# 🚀 Guide d'Installation DATA_BOT v4

![Installation](https://img.shields.io/badge/installation-guide-blue.svg)
![Platform](https://img.shields.io/badge/platform-multi--platform-green.svg)

Guide complet d'installation de DATA_BOT v4 avec toutes les options de déploiement disponibles.

## 📋 Table des Matières

- [🎯 Prérequis](#-prérequis)
- [⚡ Installation Express](#-installation-express)
- [🐳 Installation Docker](#-installation-docker)
- [☸️ Installation Kubernetes](#-installation-kubernetes)
- [💻 Installation Locale](#-installation-locale)
- [🔧 Configuration](#-configuration)
- [✅ Vérification](#-vérification)
- [🚨 Dépannage](#-dépannage)

## 🎯 Prérequis

### Système Minimum

| Composant | Minimum | Recommandé | Production |
|-----------|---------|------------|------------|
| **CPU** | 2 cores | 4 cores | 8+ cores |
| **RAM** | 4 GB | 8 GB | 16+ GB |
| **Disque** | 20 GB | 50 GB | 200+ GB |
| **OS** | Linux/macOS/Windows | Ubuntu 20.04+ | Ubuntu 22.04 LTS |

### Logiciels Requis

#### Docker (Recommandé)
- Docker 20.10+ ([Installation Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ ([Installation Compose](https://docs.docker.com/compose/install/))

#### Kubernetes (Production)
- Kubernetes 1.24+ ([Installation K8s](https://kubernetes.io/docs/setup/))
- kubectl ([Installation kubectl](https://kubernetes.io/docs/tasks/tools/))
- Helm 3.0+ (optionnel) ([Installation Helm](https://helm.sh/docs/intro/install/))

#### Installation Locale
- Python 3.11+ ([Installation Python](https://www.python.org/downloads/))
- Node.js 18+ ([Installation Node.js](https://nodejs.org/))
- PostgreSQL 14+ ([Installation PostgreSQL](https://www.postgresql.org/download/))
- Redis 6+ ([Installation Redis](https://redis.io/download))

## ⚡ Installation Express

### 🚀 Démarrage en 30 secondes

```bash
# 1. Cloner le projet
git clone https://github.com/votre-org/DATA_BOT.git
cd DATA_BOT

# 2. Démarrage automatique
make quick-start
# ou
./scripts/quick-start.sh

# 3. Accès immédiat
open http://localhost        # Interface principale
open http://localhost/admin  # Interface admin
```

Cette méthode configure automatiquement Docker avec la configuration par défaut.

## 🐳 Installation Docker

### 📦 Docker Compose (Développement)

#### 1. Préparation

```bash
# Cloner le repository
git clone https://github.com/votre-org/DATA_BOT.git
cd DATA_BOT/docker

# Copier la configuration
cp .env.example .env
```

#### 2. Configuration

Éditez le fichier [`.env`](docker/.env.example) :

```bash
# Configuration de base
ENVIRONMENT=development
TAG=latest
DOMAIN=localhost

# Base de données
POSTGRES_DB=databot_v4
POSTGRES_USER=databot
# Les mots de passe sont générés automatiquement

# Services optionnels
ENABLE_OPENSEARCH=true
ENABLE_VECTOR_SEARCH=true
ENABLE_ML_CATEGORIZATION=true
```

#### 3. Déploiement

```bash
# Démarrage complet
./scripts/deploy.sh deploy

# Ou démarrage manuel
docker-compose up -d

# Vérification
./scripts/monitor.sh status
```

#### 4. Accès aux Services

| Service | URL | Authentification |
|---------|-----|------------------|
| **Interface Web** | http://localhost | - |
| **Admin Dashboard** | http://localhost/admin | - |
| **API REST** | http://localhost:8080 | - |
| **GraphQL Playground** | http://localhost/graphql | - |
| **Grafana** | http://localhost:3000 | admin / voir `secrets/grafana_password.txt` |
| **Prometheus** | http://localhost:9090 | - |

### 🏭 Docker Production

```bash
# Configuration production
export ENVIRONMENT=production
export TAG=v4.0.0
export DOMAIN=votre-domaine.com

# SSL/TLS (automatique avec Let's Encrypt)
export ENABLE_SSL=true
export LETSENCRYPT_EMAIL=admin@votre-domaine.com

# Scaling
export API_REPLICAS=3
export ADMIN_REPLICAS=2

# Déploiement
./scripts/deploy.sh deploy -e production
```

## ☸️ Installation Kubernetes

### 🎡 Cluster Local (Minikube/Kind)

#### 1. Préparation du Cluster

```bash
# Avec Minikube
minikube start --memory=8192 --cpus=4
minikube addons enable ingress

# Avec Kind
kind create cluster --config k8s/kind-config.yaml
```

#### 2. Déploiement

```bash
# Méthode automatique
python src/kubernetes_deployer.py deploy --environment development

# Méthode manuelle
kubectl apply -f k8s/base/
kubectl apply -f k8s/overlays/development/
```

#### 3. Accès aux Services

```bash
# Port-forward pour accès local
kubectl port-forward -n databot svc/databot-service 8080:8080
kubectl port-forward -n databot svc/databot-admin 8082:8082

# Ou via Ingress
echo "127.0.0.1 databot.local" >> /etc/hosts
curl http://databot.local
```

### 🏢 Cluster Production

#### 1. Configuration

```bash
# Variables d'environnement
export K8S_NAMESPACE=databot-prod
export ENVIRONMENT=production
export REPLICAS=5
export REGISTRY=registry.votre-org.com
```

#### 2. Secrets et Configuration

```bash
# Créer les secrets
kubectl create namespace $K8S_NAMESPACE
kubectl create secret generic databot-secrets \
  --from-file=postgres-password=secrets/postgres_password.txt \
  --from-file=redis-password=secrets/redis_password.txt \
  -n $K8S_NAMESPACE

# ConfigMap
kubectl create configmap databot-config \
  --from-env-file=.env \
  -n $K8S_NAMESPACE
```

#### 3. Déploiement avec Helm

```bash
# Ajouter le repository Helm
helm repo add databot https://charts.votre-org.com
helm repo update

# Installation
helm install databot-prod databot/databot \
  --namespace $K8S_NAMESPACE \
  --values k8s/helm/values-production.yaml
```

#### 4. Monitoring et Observabilité

```bash
# Déployer le stack monitoring
kubectl apply -f k8s/monitoring/

# Accès Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

## 💻 Installation Locale

### 🖥️ Installation Native

#### 1. Prérequis Python

```bash
# Installer Python 3.11+
sudo apt update && sudo apt install python3.11 python3.11-venv python3.11-dev
# ou
brew install python@3.11

# Créer environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows
```

#### 2. Dépendances

```bash
# Cloner le projet
git clone https://github.com/votre-org/DATA_BOT.git
cd DATA_BOT

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements_v3.txt
pip install -r requirements_v4.txt
```

#### 3. Services Externes

##### PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS
brew install postgresql
brew services start postgresql

# Créer la base de données
sudo -u postgres createuser -P databot
sudo -u postgres createdb -O databot databot_v4
```

##### Redis

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS
brew install redis
brew services start redis
```

##### Elasticsearch/OpenSearch (Optionnel)

```bash
# Elasticsearch
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install elasticsearch

# OpenSearch
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.0/opensearch-2.11.0-linux-x64.tar.gz
tar -xf opensearch-2.11.0-linux-x64.tar.gz
cd opensearch-2.11.0
./bin/opensearch
```

#### 4. Configuration

```bash
# Copier le fichier de configuration
cp .env.example .env

# Éditer la configuration
nano .env
```

Configuration minimale pour installation locale :

```env
# Base de données
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=databot_v4
POSTGRES_USER=databot
POSTGRES_PASSWORD=votre_mot_de_passe

# Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# API
API_HOST=localhost
API_PORT=8080
ADMIN_PORT=8082
GRAPHQL_PORT=8083

# IA (optionnel)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2

# Moteur de recherche
USE_OPENSEARCH=false
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
```

#### 5. Démarrage

```bash
# Base de données - Migration
python -c "
from src.database import DatabaseManager
import asyncio
async def init_db():
    db = DatabaseManager()
    await db.initialize()
    await db.create_tables()
    print('Base de données initialisée')
asyncio.run(init_db())
"

# Démarrage du serveur
python main_v4.py --mode server --enable-admin --enable-graphql

# Ou démarrage spécialisé
python main_v4.py --mode admin    # Interface admin uniquement
python main_v4.py --mode worker   # Worker de traitement
```

## 🔧 Configuration

### Variables d'Environnement Principales

#### Configuration de Base

```env
# Environnement
ENVIRONMENT=development|staging|production
DEBUG=true|false
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# Base de données
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=databot_v4
POSTGRES_USER=databot
POSTGRES_PASSWORD=generated_password

# Cache et sessions
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=generated_password

# API et services
API_HOST=0.0.0.0
API_PORT=8080
ADMIN_PORT=8082
GRAPHQL_PORT=8083
```

#### Fonctionnalités

```env
# Machine Learning
ENABLE_ML_CATEGORIZATION=true
ML_MODEL=distilbert-base-uncased
CONFIDENCE_THRESHOLD=0.3

# Clustering
ENABLE_RESULT_CLUSTERING=true
CLUSTERING_ALGORITHM=hdbscan
MIN_CLUSTER_SIZE=3

# Recherche
USE_OPENSEARCH=true
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9201
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# Recherche vectorielle
ENABLE_VECTOR_SEARCH=true
VECTOR_PROVIDER=chromadb|qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Blockchain
ENABLE_BLOCKCHAIN=true
BLOCKCHAIN_NETWORK=mainnet|testnet
BLOCKCHAIN_PORT=8334
```

#### Sécurité

```env
# Chiffrement
SECRET_KEY=generated_secret_key
JWT_SECRET=generated_jwt_secret
ENCRYPTION_KEY=generated_encryption_key

# CORS et sécurité
CORS_ORIGINS=http://localhost:3000,https://votre-domaine.com
ALLOWED_HOSTS=localhost,127.0.0.1,votre-domaine.com

# TLS/SSL
ENABLE_SSL=true
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### Configuration par Environnement

#### Développement (`.env.development`)

```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
POSTGRES_HOST=localhost
REDIS_HOST=localhost
CORS_ORIGINS=*
```

#### Staging (`.env.staging`)

```env
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
POSTGRES_HOST=db-staging.internal
REDIS_HOST=redis-staging.internal
ENABLE_SSL=true
```

#### Production (`.env.production`)

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
POSTGRES_HOST=db-cluster.internal
REDIS_HOST=redis-cluster.internal
ENABLE_SSL=true
ENABLE_MONITORING=true
SENTRY_DSN=https://your-sentry-dsn
```

## ✅ Vérification

### 🔍 Tests de Santé

```bash
# Vérification complète
./scripts/health-check.sh

# Vérification manuelle des endpoints
curl http://localhost:8080/health
curl http://localhost:8082/_stcore/health
curl http://localhost:8083/health
```

### 📊 Interface de Monitoring

```bash
# Accès Grafana
open http://localhost:3000
# Login: admin / Password: voir secrets/grafana_password.txt

# Métriques Prometheus
open http://localhost:9090
```

### 🧪 Tests Fonctionnels

```bash
# Tests unitaires
python -m pytest tests/ -v

# Tests d'intégration
python test_v4_integration.py

# Tests de performance
python test_v4_performance.py

# Tests sécurité
python test_security_fixes.py
```

### 📈 Vérification des Fonctionnalités

#### API REST

```bash
# Test de l'API
curl -X POST http://localhost:8080/api/v4/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 10}'
```

#### GraphQL

```bash
# Test GraphQL
curl -X POST http://localhost:8083/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ health { status version } }"}'
```

#### Interface Admin

```bash
# Accès interface admin
open http://localhost:8082
```

## 🚨 Dépannage

### Problèmes Courants

#### Services ne Démarrent Pas

```bash
# Vérifier les logs Docker
docker-compose logs databot-api

# Vérifier les ressources
docker stats

# Redémarrer un service
docker-compose restart databot-api
```

#### Problèmes de Base de Données

```bash
# Vérifier la connexion PostgreSQL
docker exec -it databot-postgres psql -U databot -d databot_v4 -c "SELECT version();"

# Vérifier Redis
docker exec -it databot-redis redis-cli ping

# Réinitialiser les données
./scripts/reset-database.sh
```

#### Problèmes de Performance

```bash
# Monitoring des ressources
./scripts/monitor.sh resources

# Optimisation mémoire
export POSTGRES_SHARED_BUFFERS=256MB
export REDIS_MAXMEMORY=512MB

# Redémarrage avec nouvelles limites
docker-compose down && docker-compose up -d
```

#### Problèmes de Connectivité

```bash
# Vérifier les ports
netstat -tulpn | grep :8080
netstat -tulpn | grep :8082

# Vérifier les réseaux Docker
docker network ls
docker network inspect databot-frontend

# Réinitialiser les réseaux
docker-compose down
docker network prune
docker-compose up -d
```

### Logs et Debugging

```bash
# Logs en temps réel
./scripts/deploy.sh logs

# Logs d'un service spécifique
docker-compose logs -f databot-api

# Logs avec filtrage
docker-compose logs databot-api | grep ERROR

# Logs d'installation locale
tail -f logs/databot_v4.log
```

### Réinitialisation Complète

```bash
# Docker - Réinitialisation complète
./scripts/deploy.sh cleanup --force
docker system prune -a --volumes

# Installation locale - Réinitialisation
rm -rf venv/
rm -rf data/
rm -rf logs/
python3.11 -m venv venv
# Recommencer l'installation
```

## 📞 Support

### Obtenir de l'Aide

1. **📚 Consultez d'abord :**
   - [Guide de dépannage](TROUBLESHOOTING.md)
   - [FAQ](../FAQ.md)
   - Cette documentation

2. **🔍 Diagnostics :**
   ```bash
   # Générer un rapport de diagnostic
   ./scripts/diagnostic-report.sh > diagnostic.txt
   ```

3. **💬 Canaux de support :**
   - GitHub Issues : Problèmes techniques
   - GitHub Discussions : Questions générales
   - Email : support@votre-org.com

### Informations Utiles pour le Support

Lors d'une demande de support, incluez :

```bash
# Version de DATA_BOT
python main_v4.py --version

# Informations système
./scripts/system-info.sh

# Logs récents
docker-compose logs --tail=100 > logs.txt
```

---

## 🎉 Installation Terminée !

Félicitations ! DATA_BOT v4 est maintenant installé et prêt à l'emploi.

### 🚀 Prochaines Étapes

1. **🎯 Configuration :** Consultez le [Guide de Configuration](CONFIGURATION.md)
2. **📚 Utilisation :** Consultez la [Documentation Utilisateur](USER_GUIDE.md)
3. **🔧 Administration :** Consultez le [Guide d'Administration](ADMIN_GUIDE.md)
4. **🚀 Production :** Consultez le [Guide de Déploiement Production](PRODUCTION_GUIDE.md)

**🤖 Bienvenue dans l'écosystème DATA_BOT v4 !**

![Installation Complete](https://img.shields.io/badge/installation-complete-success.svg)