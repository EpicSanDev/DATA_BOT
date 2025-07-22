# DATA_BOT v3 - Documentation

## 🎯 Nouvelles Fonctionnalités v3

### ✅ Implémentées

#### 1. 📱 Interface Mobile Native (PWA)
- Application web progressive avec interface tactile optimisée
- Mode hors ligne avec synchronisation
- Installation sur mobile comme une app native
- Interface responsive adaptée aux petits écrans

**Usage:**
```bash
python main_v3.py --mode mobile
# Accès: http://localhost:8080/mobile
```

#### 2. 🔍 Support Bases Vectorielles
- Support ChromaDB (local) et Qdrant
- Recherche sémantique sur le contenu archivé
- Indexation automatique des nouvelles ressources

**Usage:**
```bash
# Indexer tout le contenu
python main_v3.py --mode vector --vector-action index

# Recherche sémantique
python main_v3.py --mode vector --vector-action search --search-query "intelligence artificielle"
```

#### 3. 🔎 Intégration Elasticsearch
- Recherche full-text avancée
- Agrégations et analytics
- Suggestions de recherche

**Usage:**
```bash
# Indexer dans Elasticsearch
python main_v3.py --mode elasticsearch --es-action index

# Recherche avancée
python main_v3.py --mode elasticsearch --es-action search --search-query "machine learning"
```

#### 4. 🔌 Plugin Navigateur
- Extension Chrome/Firefox
- Archivage en un clic depuis le navigateur
- Notes rapides et capture de sélections

**Installation:**
1. Démarrer le serveur plugin: `python main_v3.py --enable-browser-plugin`
2. Aller sur `chrome://extensions/`
3. Activer "Mode développeur"
4. Charger l'extension depuis `src/browser_plugin/`

#### 5. 🌐 Mode Distribué Multi-machines
- Coordination avec Redis
- Workers distribués pour le traitement
- Répartition automatique des tâches

**Usage:**
```bash
# Coordinateur
python main_v3.py --mode distributed --distributed-action coordinator --enable-distributed

# Worker
python main_v3.py --mode distributed --distributed-action worker --enable-distributed
```

## 🚀 Installation v3

### Dépendances Supplémentaires
```bash
pip install -r requirements_v3.txt
```

### Services Externes (Optionnels)
- **Redis** (pour le mode distribué): `redis-server`
- **Elasticsearch** (pour la recherche avancée): via Docker ou installation locale
- **Qdrant** (alternative ChromaDB): via Docker

### Démarrage Rapide
```bash
# Mode complet avec toutes les fonctionnalités
python main_v3.py --mode mobile \
  --enable-vector-search \
  --enable-elasticsearch \
  --enable-browser-plugin \
  --enable-distributed
```

## 📱 Interface Mobile PWA

### Fonctionnalités
- **Tableau de bord** avec statistiques en temps réel
- **Recherche rapide** avec suggestions
- **Archivage rapide** d'URLs
- **Mode hors ligne** avec synchronisation
- **Notes rapides** et gestion des tags

### Screenshots
L'interface mobile s'adapte automatiquement à tous les écrans et peut être installée comme une app native.

## 🔍 Recherche Avancée

### Recherche Vectorielle (Sémantique)
```python
# API
POST /api/v3/mobile/search
{
  "query": "intelligence artificielle",
  "type": "vector",
  "limit": 10
}
```

### Recherche Elasticsearch (Full-text)
```python
# API
POST /api/v3/mobile/search
{
  "query": "machine learning",
  "type": "elasticsearch", 
  "filters": {"content_type": "web_page"},
  "limit": 20
}
```

## 🔌 Plugin Navigateur

### Fonctionnalités
- **Archivage en un clic** de la page courante
- **Capture d'écran** automatique
- **Notes rapides** sur les pages
- **Recherche** dans l'archive depuis le navigateur
- **Menu contextuel** pour archiver liens et sélections

### API Plugin
```javascript
// Archiver une page
fetch('http://localhost:8081/plugin/archive-page', {
  method: 'POST',
  body: JSON.stringify({
    url: window.location.href,
    title: document.title,
    content: document.body.innerText
  })
});
```

## 🌐 Mode Distribué

### Architecture
- **Coordinateur**: Distribue les tâches aux workers
- **Workers**: Exécutent les tâches (archivage, capture, etc.)
- **Redis**: Communication et coordination
- **Monitoring**: Surveillance de la santé du cluster

### Types de Tâches
- `ARCHIVE`: Téléchargement et archivage
- `SCREENSHOT`: Capture d'écran
- `EXTRACT`: Extraction de contenu
- `INDEX`: Indexation vectorielle/ES
- `COMPRESS`: Compression des fichiers

## 📊 API v3

### Nouveaux Endpoints

#### Mobile
- `GET /mobile/` - Interface PWA
- `POST /api/v3/mobile/search` - Recherche mobile
- `POST /api/v3/mobile/quick-archive` - Archivage rapide
- `GET /api/v3/mobile/status` - Statut système

#### Plugin Navigateur  
- `POST /plugin/archive-page` - Archiver depuis plugin
- `POST /plugin/quick-note` - Note rapide
- `GET /plugin/search` - Recherche plugin

#### Distribué
- `GET /api/v3/cluster/status` - Statut cluster
- `POST /api/v3/cluster/task` - Soumettre tâche

## 🧪 Tests

```bash
# Tests v3
python test_v3.py

# Tests spécifiques
python -m pytest tests/test_vector_manager.py
python -m pytest tests/test_elasticsearch_manager.py
```

## 🔧 Configuration

### Variables d'Environnement
```env
# Bases vectorielles
VECTOR_PROVIDER=chromadb  # ou qdrant
CHROMADB_PERSIST_DIR=./data/vectors
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# Mode distribué
REDIS_HOST=localhost
REDIS_PORT=6379
COORDINATOR_HOST=localhost
COORDINATOR_PORT=8082

# Plugin navigateur
PLUGIN_PORT=8081
```

### Configuration Avancée
```python
# main_v3.py --config config_v3.json
{
  "vector": {
    "provider": "chromadb",
    "chunk_size": 512,
    "dimension": 384
  },
  "elasticsearch": {
    "host": "localhost",
    "port": 9200,
    "index_name": "databot_v3"
  },
  "distributed": {
    "max_workers": 5,
    "task_timeout": 300,
    "heartbeat_interval": 30
  }
}
```

## 📈 Monitoring

### Métriques Disponibles
- Nombre de documents indexés (vectoriel + ES)
- Temps de réponse des recherches
- Statut des workers distribués
- Utilisation de la bande passante
- Tâches en cours/terminées/échouées

### Dashboard
Accessible via l'interface mobile ou l'API `/api/v3/stats`.

## 🚧 Prochaines Améliorations

- [ ] Interface d'administration complète
- [ ] Support OpenSearch comme alternative à ES
- [ ] Clustering automatique des résultats
- [ ] API GraphQL
- [ ] Support Kubernetes pour le déploiement
- [ ] Machine learning pour la catégorisation automatique

## 📄 Migration depuis v2

La v3 est entièrement compatible avec la v2. Les données existantes sont automatiquement disponibles dans les nouvelles fonctionnalités.

```bash
# Migrer les données vers l'index vectoriel
python main_v3.py --mode vector --vector-action index

# Migrer vers Elasticsearch  
python main_v3.py --mode elasticsearch --es-action index
```

---

**🤖 DATA_BOT v3 - L'archivage internet nouvelle génération!**