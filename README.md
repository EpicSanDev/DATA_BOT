# DATA_BOT v4 - Enhanced Analytics & GPU Support

## 🆕 Nouvelles Fonctionnalités v4

### 🎯 Améliorations Majeures

- **🚀 Support GPU avec Ollama** - Intégration Ollama avec support GPU NVIDIA pour des performances IA optimisées
- **📊 Dashboard Analytics Avancé** - Interface de visualisation complète avec graphiques temps réel
- **📱 Interface Mobile Améliorée** - Application mobile responsive avec visualisations interactives
- **🐳 Configuration Docker Optimisée** - Support GPU complet avec script d'installation automatisé
- **📈 Métriques en Temps Réel** - Monitoring complet avec Prometheus et Grafana

### 🔧 Nouvelles Fonctionnalités Techniques

#### 🤖 Intelligence Artificielle Renforcée
- **Ollama avec GPU** : Utilisation des GPU NVIDIA pour accélérer les tâches d'IA
- **Modèles multiples** : Support pour llama2, mistral, codellama
- **API standardisée** : Interface unifiée pour tous les modèles d'IA

#### 📊 Visualisations Avancées
- **Graphiques interactifs** : Chart.js et D3.js pour des visualisations riches
- **Dashboard temps réel** : Mise à jour automatique des métriques
- **Graphes de réseau** : Visualisation des interconnexions entre sites
- **Analytics mobile** : Interface optimisée pour smartphones et tablettes

#### 🐳 Infrastructure Docker
- **Support GPU natif** : Configuration automatique du support NVIDIA
- **Services orchestrés** : PostgreSQL, Redis, Elasticsearch, OpenSearch
- **Monitoring intégré** : Prometheus, Grafana, alertes automatiques
- **Load balancing** : Nginx configuré pour haute disponibilité

## 🚀 Installation Rapide avec Support GPU

### Prérequis
- Docker et Docker Compose
- GPU NVIDIA (optionnel mais recommandé)
- NVIDIA Container Toolkit (pour GPU)

### Installation Automatisée

```bash
# Cloner le repository
git clone https://github.com/EpicSanDev/DATA_BOT.git
cd DATA_BOT

# Lancer l'installation avec support GPU
./setup-gpu.sh
```

Le script d'installation :
- ✅ Vérifie et installe Docker si nécessaire
- ✅ Configure le support GPU NVIDIA
- ✅ Déploie tous les services
- ✅ Initialise les bases de données
- ✅ Télécharge les modèles Ollama
- ✅ Lance les tests de santé

### Installation Manuelle

```bash
# Copier la configuration
cp .env.example .env

# Construire et démarrer avec GPU
docker-compose -f docker-compose-gpu.yml up -d --build

# Ou sans GPU
docker-compose up -d --build
```

## 📊 Interfaces Utilisateur

### 🖥️ Dashboard Principal
**URL**: `http://localhost:8080/dashboard/analytics`

**Fonctionnalités**:
- 📈 Statistiques temps réel (sites, pages, données, taux de succès)
- 📊 Graphiques d'activité quotidienne
- 🌐 Distribution par domaines
- 📊 Statuts des archives
- ⚡ Métriques de performance
- 🕸️ Graphe de liens inter-sites
- 📋 Activité récente détaillée
- 📤 Export des données

### 📱 Interface Mobile
**URL**: `http://localhost:8080/mobile`

**Fonctionnalités**:
- 📊 Dashboard mobile adaptatif
- 📈 Graphiques optimisés tactile
- 🔍 Recherche avancée
- 📊 Analytics en temps réel
- 💾 Mode hors ligne
- 📤 Export mobile

### 🔧 Interface d'Administration
**URL**: `http://localhost:8082`

**Fonctionnalités**:
- ⚙️ Configuration des services
- 📊 Monitoring des performances
- 🤖 Gestion des modèles IA
- 📋 Gestion des tâches
- 🔍 Logs système

## 📁 Structure du Projet

Le projet a été réorganisé pour une meilleure maintenabilité :

```
DATA_BOT/
├── src/                    # Code source principal
│   ├── core/              # Logique métier centrale
│   │   ├── config.py      # Configuration
│   │   ├── models.py      # Modèles de données
│   │   ├── enhanced_ai_client.py  # Client IA
│   │   └── ...
│   ├── api/               # APIs et interfaces web
│   │   ├── api_server.py  # Serveur API principal
│   │   ├── admin_interface.py  # Interface admin
│   │   └── ...
│   ├── database/          # Gestionnaires de base de données
│   ├── ml/                # Machine Learning et IA
│   ├── utils/             # Utilitaires et helpers
│   ├── web/               # Scraping et capture web
│   └── blockchain/        # Intégration blockchain
├── tests/                 # Tests unitaires et d'intégration
├── scripts/               # Scripts d'installation et utilitaires
├── config/                # Fichiers de configuration
├── docs/                  # Documentation
├── docker/                # Configuration Docker
├── k8s/                   # Configuration Kubernetes
└── security/              # Outils et audits de sécurité
```

## 🎯 Endpoints API v4

### Analytics API
```bash
# Statistiques générales
GET /api/v4/analytics/stats

# Activité récente
GET /api/v4/analytics/recent?limit=50

# Données quotidiennes
GET /api/v4/analytics/daily?days=30

# Distribution des domaines
GET /api/v4/analytics/domains?limit=10

# Distribution des statuts
GET /api/v4/analytics/status

# Métriques de performance
GET /api/v4/analytics/performance?hours=24

# Graphe de réseau
GET /api/v4/analytics/network?limit=50

# Export des données
GET /api/v4/analytics/export
```

### Recherche Avancée
```bash
# Recherche avec clustering
POST /api/v4/search/advanced
{
  "query": "intelligence artificielle",
  "search_engine": "auto",
  "enable_clustering": true,
  "clustering_algorithm": "hdbscan",
  "limit": 20
}
```

### Gestion ML
```bash
# Catégorisation automatique
POST /api/v4/ml/categorize
{
  "resource_ids": [1, 2, 3],
  "confidence_threshold": 0.3,
  "auto_save": true
}

# Clustering des résultats
POST /api/v4/clustering/run
{
  "algorithm": "hdbscan",
  "min_cluster_size": 3
}
```

## 🐳 Architecture Docker

### Services Déployés

| Service | Port | Description |
|---------|------|-------------|
| **DATA_BOT v4** | 8080 | Application principale |
| **Ollama** | 11434 | Service IA avec GPU |
| **PostgreSQL** | 5432 | Base de données principale |
| **Redis** | 6379 | Cache et coordination |
| **Elasticsearch** | 9200 | Recherche et indexation |
| **OpenSearch** | 9201 | Alternative à Elasticsearch |
| **Qdrant** | 6333 | Base vectorielle |
| **Prometheus** | 9090 | Métriques et monitoring |
| **Grafana** | 3000 | Visualisation des métriques |
| **Nginx** | 80/443 | Load balancer |

### 🚀 Support GPU

Le support GPU est automatiquement détecté et configuré :

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

**Avantages du GPU** :
- ⚡ **10x plus rapide** pour l'analyse de contenu
- 🧠 **Modèles plus complexes** utilisables
- 🔄 **Traitement concurrent** amélioré
- 💾 **Utilisation mémoire optimisée**

## 📈 Monitoring et Métriques

### Prometheus Metrics
- `databot_sites_total` - Nombre total de sites archivés
- `databot_processing_duration_seconds` - Temps de traitement
- `databot_errors_total` - Nombre d'erreurs
- `databot_gpu_utilization` - Utilisation GPU

### Grafana Dashboards
- **Overview** : Vue d'ensemble système
- **Performance** : Métriques de performance
- **AI/ML** : Utilisation des modèles IA
- **Storage** : Utilisation du stockage

### Alertes Automatiques
- 🚨 Erreurs critiques
- ⚡ Performance dégradée
- 💾 Espace disque faible
- 🔥 Surchauffe GPU

## 🔧 Configuration Avancée

### Variables d'Environnement

```bash
# Support GPU
NVIDIA_VISIBLE_DEVICES=all
CUDA_VISIBLE_DEVICES=0

# Base de données
DATABASE_URL=postgresql://databot:password@postgres:5432/databot_v4
REDIS_URL=redis://redis:6379/0

# Recherche
ELASTICSEARCH_HOST=http://elasticsearch:9200
OPENSEARCH_HOST=http://opensearch:9201

# IA
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama2

# Monitoring
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=9090
```

### Optimisation GPU

```bash
# Vérifier l'utilisation GPU
docker exec databot-ollama nvidia-smi

# Monitoring GPU en temps réel
watch -n 1 'docker exec databot-ollama nvidia-smi'

# Logs Ollama
docker logs -f databot-ollama
```

## 🚨 Dépannage

### Problèmes Courants

**1. GPU non détecté**
```bash
# Vérifier NVIDIA driver
nvidia-smi

# Réinstaller NVIDIA Container Toolkit
sudo apt-get install nvidia-container-toolkit
sudo systemctl restart docker
```

**2. Ollama ne démarre pas**
```bash
# Vérifier les logs
docker logs databot-ollama

# Redémarrer le service
docker-compose restart ollama
```

**3. Dashboard ne charge pas**
```bash
# Vérifier l'état des services
docker-compose ps

# Redémarrer l'application
docker-compose restart databot-v4
```

### Commandes de Diagnostic

```bash
# État de tous les services
docker-compose ps

# Logs en temps réel
docker-compose logs -f

# Utilisation des ressources
docker stats

# Tests de santé
curl http://localhost:8080/health
curl http://localhost:11434/api/tags
```

## 📚 Documentation API

### Authentification
Toutes les API utilisent l'authentification par token :

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/v4/analytics/stats
```

### Exemples d'Utilisation

**Recherche avancée** :
```python
import requests

response = requests.post('http://localhost:8080/api/v4/search/advanced', 
    json={
        'query': 'machine learning',
        'enable_clustering': True,
        'limit': 50
    }
)
results = response.json()
```

**Analytics** :
```javascript
fetch('/api/v4/analytics/stats')
    .then(response => response.json())
    .then(data => {
        console.log('Sites:', data.totalSites);
        console.log('Success rate:', data.successRate);
    });
```

## 🎯 Feuille de Route

### 🔄 Prochaines Versions

**v4.1** (Q1 2024)
- [ ] Support AMD GPU
- [ ] Interface vocale
- [ ] API GraphQL complète
- [ ] Clustering temps réel

**v4.2** (Q2 2024)
- [ ] Multi-tenancy
- [ ] Federated search
- [ ] Advanced ML pipelines
- [ ] Mobile app native

**v5.0** (Q3 2024)
- [ ] Kubernetes native
- [ ] Edge computing
- [ ] Blockchain integration
- [ ] AR/VR visualization

## 🤝 Contribution

1. **Fork** le repository
2. **Créer** une branche feature
3. **Implémenter** les changements
4. **Tester** avec GPU et sans GPU
5. **Soumettre** une pull request

### Standards de Code
- Python 3.11+
- Type hints obligatoires
- Tests unitaires requis
- Documentation complète

## 📄 Licence

MIT License - Voir [LICENSE](LICENSE) pour plus de détails.

---

**🚀 DATA_BOT v4 - L'avenir de l'archivage intelligent avec IA et GPU !**