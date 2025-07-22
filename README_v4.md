# DATA_BOT v4 - Enterprise Archiving Platform

![DATA_BOT v4](https://img.shields.io/badge/version-4.0.0-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-green.svg)
![Kubernetes](https://img.shields.io/badge/kubernetes-supported-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Une plateforme d'archivage internet de niveau entreprise avec fonctionnalités avancées de ML, clustering, et déploiement cloud-native.

## 🎯 Nouvelles Fonctionnalités v4

### ✅ Implémentées

#### 1. 🔧 Interface d'Administration Complète
- Dashboard en temps réel avec métriques avancées
- Gestion complète des ressources et catégories
- Monitoring système intégré
- Outils d'administration et maintenance
- Interface responsive et intuitive

#### 2. 🔍 Support OpenSearch comme Alternative à Elasticsearch
- Moteur de recherche open-source compatible
- Basculement automatique entre ES et OpenSearch
- API unifiée pour la recherche
- Performance optimisée pour de gros volumes

#### 3. 🧬 Clustering Automatique des Résultats
- Algorithmes multiples (HDBSCAN, K-means, Agglomerative, DBSCAN)
- Clustering intelligent des résultats de recherche
- Visualisation et exploration des clusters
- Recommandations basées sur la similarité

#### 4. 🚀 API GraphQL Complète
- Schema GraphQL pour toutes les fonctionnalités
- Requêtes, mutations et subscriptions
- Interface GraphQL Playground intégrée
- Support des requêtes complexes et relations

#### 5. 🤖 Machine Learning pour Catégorisation Automatique
- Classification automatique du contenu
- Support de modèles multiples (Naive Bayes, Transformers)
- Entraînement et évaluation de modèles
- Catégorisation en temps réel

#### 6. ☸️ Support Kubernetes Complet
- Manifests Kubernetes optimisés
- Déploiement multi-environnement
- Auto-scaling et haute disponibilité
- Monitoring et observabilité

#### 7. 🐳 Dockerisation 100%
- Images Docker optimisées multi-stage
- Docker Compose pour développement
- Orchestration complète des services
- Configuration par variables d'environnement

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Admin Interface│    │  GraphQL API    │
│   (Port 8080)   │    │   (Port 8082)   │    │   (Port 8083)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────┐
                    │     API Server v4       │
                    │    (FastAPI Core)       │
                    └─────────────┬───────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐    ┌──────────▼──────────┐    ┌─────────▼─────────┐
│  ML Categorizer│    │  Result Clusterer   │    │ OpenSearch Manager│
│   (scikit-learn│    │    (HDBSCAN/etc)    │    │  (Alternative ES) │
│   transformers)│    │                     │    │                   │
└────────────────┘    └─────────────────────┘    └───────────────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                    ┌─────────────▼───────────┐
                    │    Database Manager     │
                    │   (PostgreSQL/SQLite)   │
                    └─────────────────────────┘
```

## 🚀 Installation et Déploiement

### Option 1: Docker Compose (Recommandé pour développement)

```bash
# Cloner le repository
git clone https://github.com/EpicSanDev/DATA_BOT.git
cd DATA_BOT

# Démarrer tous les services
docker-compose up -d

# Vérifier le statut
docker-compose ps
```

**Services disponibles:**
- Interface principale: http://localhost:8080
- Interface d'administration: http://localhost:8082
- API GraphQL: http://localhost:8083/graphql
- Monitoring (Grafana): http://localhost:3000

### Option 2: Kubernetes (Production)

```bash
# Déployer sur Kubernetes
python src/kubernetes_deployer.py deploy --environment production

# Vérifier le déploiement
kubectl get pods -n databot-v4

# Accéder aux services
kubectl port-forward -n databot-v4 svc/databot-service 8080:8080
```

### Option 3: Installation locale

```bash
# Installer les dépendances
pip install -r requirements.txt -r requirements_v3.txt -r requirements_v4.txt

# Démarrer v4
python main_v4.py --mode server --enable-admin --enable-graphql --enable-opensearch
```

## 🔧 Configuration

### Variables d'Environnement

```env
# Configuration générale
ENVIRONMENT=development
DEBUG=true

# Base de données
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=databot_v4
POSTGRES_USER=databot
POSTGRES_PASSWORD=your_password

# Moteurs de recherche
USE_OPENSEARCH=true
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9201
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# Machine Learning
ENABLE_ML_CATEGORIZATION=true
ML_MODEL=distilbert-base-uncased
CONFIDENCE_THRESHOLD=0.3

# Clustering
ENABLE_RESULT_CLUSTERING=true
CLUSTERING_ALGORITHM=hdbscan
MIN_CLUSTER_SIZE=3

# Ports des services
API_PORT=8080
ADMIN_PORT=8082
GRAPHQL_PORT=8083

# Kubernetes
KUBERNETES_NAMESPACE=databot-v4
```

## 📚 Utilisation

### 1. Interface d'Administration

```bash
# Accéder au dashboard admin
http://localhost:8082
```

**Fonctionnalités disponibles:**
- 📊 Dashboard avec métriques en temps réel
- 🔍 Recherche et exploration avancée
- 📚 Gestion complète des ressources
- 🏷️ Gestion des catégories et tags
- 🧬 Configuration et lancement de clustering
- 🤖 Entraînement et gestion des modèles ML
- 📈 Monitoring système complet

### 2. API GraphQL

```bash
# Accéder au playground GraphQL
http://localhost:8083/graphql
```

**Exemples de requêtes:**

```graphql
# Recherche avec clustering
query SearchWithClustering {
  search(
    query: "intelligence artificielle"
    enableClustering: true
    limit: 20
  ) {
    results {
      resources {
        id
        title
        url
        categories
      }
      total
    }
    clusters {
      id
      name
      description
      size
      keywords
    }
    executionTime
  }
}

# Catégorisation automatique
mutation CategorizeResource {
  categorizeResource(id: 123) {
    id
    categories
    title
  }
}

# Clustering des ressources
mutation ClusterResources {
  clusterResources(algorithm: "hdbscan") {
    id
    name
    size
    coherenceScore
    keywords
  }
}
```

### 3. API REST v4

```bash
# Recherche avancée
curl -X POST http://localhost:8080/api/v4/search/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "search_engine": "opensearch",
    "enable_clustering": true,
    "clustering_algorithm": "hdbscan",
    "limit": 20
  }'

# Catégorisation ML
curl -X POST http://localhost:8080/api/v4/ml/categorize \
  -H "Content-Type: application/json" \
  -d '{
    "confidence_threshold": 0.3,
    "max_categories": 5,
    "auto_save": true
  }'

# Lancement de clustering
curl -X POST http://localhost:8080/api/v4/clustering/run \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "hdbscan",
    "min_cluster_size": 3
  }'
```

## 🤖 Machine Learning

### Catégorisation Automatique

Le système utilise plusieurs approches pour la catégorisation:

1. **Naive Bayes + TF-IDF** pour la classification rapide
2. **Transformers** (zero-shot) pour la précision
3. **Règles heuristiques** pour les domaines spécialisés

```python
# Exemple d'utilisation
await ml_categorizer.categorize_resource(resource)
# → ['Technology', 'AI/ML', 'Programming']
```

### Clustering Intelligent

Algorithmes supportés:
- **HDBSCAN**: Clustering basé sur la densité (recommandé)
- **K-means**: Clustering par centroïdes
- **Agglomerative**: Clustering hiérarchique
- **DBSCAN**: Clustering par densité avec paramètres fixes

```python
# Clustering automatique des résultats de recherche
clustering_result = await result_clusterer.cluster_search_results(
    search_results, query="intelligence artificielle"
)
```

## 🔍 Moteurs de Recherche

### OpenSearch vs Elasticsearch

Le système supporte automatiquement:
- **OpenSearch** (recommandé): Open source, performant
- **Elasticsearch**: Support complet avec fallback
- **Base de données**: Recherche basique en fallback

Configuration automatique:
```python
# Le système choisit automatiquement le meilleur moteur disponible
search_engine = await determine_search_engine("auto")
# → "opensearch" | "elasticsearch" | "database"
```

## ☸️ Déploiement Kubernetes

### Manifests Inclus

- `k8s/01-namespace-config.yaml`: Namespace et configuration
- `k8s/02-databot-deployment.yaml`: Application principale
- `k8s/03-databases.yaml`: PostgreSQL et Redis
- `k8s/04-search-engines.yaml`: ES, OpenSearch, Qdrant

### Commandes Utiles

```bash
# Déploiement complet
python src/kubernetes_deployer.py deploy --environment production

# Vérification du statut
python src/kubernetes_deployer.py status

# Scaling
python src/kubernetes_deployer.py scale --deployment databot-v4 --replicas 5

# Suppression
python src/kubernetes_deployer.py delete
```

### Monitoring

Services de monitoring inclus:
- **Prometheus**: Collecte de métriques
- **Grafana**: Visualisation des données
- **Health checks**: Vérification automatique de santé

## 📊 Monitoring et Observabilité

### Métriques Disponibles

- Utilisation CPU/Mémoire/Disque
- Nombre de requêtes par seconde
- Temps de réponse des API
- Statut des composants
- Performance des algorithmes ML

### Endpoints de Monitoring

```bash
# Santé générale
GET /health

# Santé détaillée de tous les composants
GET /api/v4/health/detailed

# Métriques système
GET /api/v4/monitoring/metrics

# Logs système
GET /api/v4/monitoring/logs?level=INFO&limit=100
```

## 🔧 Développement

### Structure du Projet v4

```
DATA_BOT/
├── main_v4.py                 # Point d'entrée principal v4
├── requirements_v4.txt        # Dépendances v4
├── Dockerfile                 # Image Docker multi-stage
├── docker-compose.yml         # Orchestration complète
├── src/
│   ├── api_server_v4.py      # Serveur API étendu
│   ├── admin_interface.py    # Interface d'administration
│   ├── opensearch_manager.py # Gestionnaire OpenSearch
│   ├── ml_categorizer.py     # Catégoriseur ML
│   ├── result_clusterer.py   # Clustering automatique
│   ├── graphql_server.py     # Serveur GraphQL
│   └── kubernetes_deployer.py # Déployeur K8s
├── k8s/                      # Manifests Kubernetes
│   ├── 01-namespace-config.yaml
│   ├── 02-databot-deployment.yaml
│   ├── 03-databases.yaml
│   └── 04-search-engines.yaml
└── monitoring/               # Configuration monitoring
    ├── prometheus.yml
    └── grafana/
```

### Tests

```bash
# Tests unitaires
python -m pytest tests/

# Tests d'intégration
python test_v4_integration.py

# Tests de performance
python test_v4_performance.py
```

## 📈 Performance

### Benchmarks v4

- **Recherche**: 50-200ms (selon moteur et taille index)
- **Catégorisation ML**: 100-500ms par ressource
- **Clustering**: 1-30s (selon algorithme et taille dataset)
- **GraphQL**: 10-100ms par requête

### Optimisations

- Cache Redis pour requêtes fréquentes
- Indexation asynchrone en arrière-plan
- Batch processing pour operations ML
- Connection pooling pour bases de données

## 🚧 Roadmap Futur

### Version 4.1 (Q2 2024)
- [ ] Support multi-tenancy
- [ ] API de webhooks
- [ ] Intégration LangChain avancée
- [ ] Support des modèles custom

### Version 4.2 (Q3 2024)
- [ ] Interface mobile native
- [ ] Support streaming en temps réel
- [ ] Intégration cloud providers (AWS, GCP, Azure)
- [ ] Analytics avancées

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit les changements (`git commit -am 'Ajout nouvelle fonctionnalité'`)
4. Push la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Créer une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 💬 Support

- **Documentation**: [Wiki du projet](https://github.com/EpicSanDev/DATA_BOT/wiki)
- **Issues**: [GitHub Issues](https://github.com/EpicSanDev/DATA_BOT/issues)
- **Discussions**: [GitHub Discussions](https://github.com/EpicSanDev/DATA_BOT/discussions)

## 🎯 Migration depuis v3

La v4 est entièrement compatible avec la v3. Les données existantes sont automatiquement migrées:

```bash
# Migration automatique depuis v3
python main_v4.py --mode migrate-from-v3

# Vérification post-migration
python main_v4.py --mode verify-migration
```

---

**🤖 DATA_BOT v4 - L'avenir de l'archivage internet intelligent!**

![Enterprise Ready](https://img.shields.io/badge/Enterprise-Ready-success.svg)
![Cloud Native](https://img.shields.io/badge/Cloud-Native-blue.svg)
![AI Powered](https://img.shields.io/badge/AI-Powered-purple.svg)