# 📡 Référence API DATA_BOT v4

![API](https://img.shields.io/badge/API-REST%20%2B%20GraphQL-blue.svg)
![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-green.svg)
![WebSocket](https://img.shields.io/badge/WebSocket-supported-orange.svg)

Documentation complète des APIs REST et GraphQL de DATA_BOT v4 pour l'intégration et le développement.

## 📋 Table des Matières

- [🎯 Vue d'ensemble](#-vue-densemble)
- [🔐 Authentification](#-authentification)
- [🌐 API REST v4](#-api-rest-v4)
- [🚀 API GraphQL](#-api-graphql)
- [⚡ WebSocket API](#-websocket-api)
- [🔗 API Blockchain](#-api-blockchain)
- [📊 Codes de Réponse](#-codes-de-réponse)
- [🧪 Exemples d'Intégration](#-exemples-dintégration)

## 🎯 Vue d'ensemble

DATA_BOT v4 expose plusieurs types d'APIs pour différents cas d'usage :

### Types d'APIs Disponibles

| API | Description | Port | Base URL |
|-----|-------------|------|----------|
| **REST v4** | API REST principale pour CRUD et opérations | 8080 | `/api/v4` |
| **GraphQL** | API GraphQL pour requêtes complexes | 8083 | `/graphql` |
| **WebSocket** | API temps réel pour streaming | 8080 | `/ws` |
| **Blockchain RPC** | API RPC pour interactions blockchain | 8334 | `/rpc` |
| **Admin API** | API d'administration système | 8082 | `/admin/api` |

### Formats Supportés

- **Requêtes :** JSON, multipart/form-data
- **Réponses :** JSON, XML (sur demande)
- **Streaming :** Server-Sent Events, WebSocket
- **Documentation :** OpenAPI 3.0, GraphQL Schema

### Versions et Compatibilité

| Version | Statut | Support | Fin de Vie |
|---------|--------|---------|------------|
| **v4** | Actuelle | ✅ Complet | - |
| **v3** | Maintenance | ⚠️ Sécurité uniquement | 2025-06-01 |
| **v2** | Déprécié | ❌ Non supporté | 2024-12-01 |

## 🔐 Authentification

### Méthodes Supportées

#### 1. JWT Bearer Token (Recommandé)

```bash
# Obtenir un token
curl -X POST http://localhost:8080/api/v4/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "secure_password",
    "mfa_code": "123456"
  }'

# Réponse
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "scope": "archives:read archives:create search:execute"
}

# Utilisation du token
curl -X GET http://localhost:8080/api/v4/archives \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 2. API Key

```bash
# Générer une clé API
curl -X POST http://localhost:8080/api/v4/auth/api-keys \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "name": "Production Integration",
    "scopes": ["archives:read", "search:execute"],
    "expires_at": "2025-12-31T23:59:59Z"
  }'

# Utilisation de la clé
curl -X GET http://localhost:8080/api/v4/archives \
  -H "X-API-Key: ak_1234567890abcdef..."
```

#### 3. OAuth2 (Enterprise)

```bash
# Flux d'autorisation
GET http://localhost:8080/api/v4/auth/oauth/authorize?
  client_id=your_client_id&
  response_type=code&
  scope=archives:read+search:execute&
  redirect_uri=https://your-app.com/callback

# Exchange code for token
POST http://localhost:8080/api/v4/auth/oauth/token
Content-Type: application/json

{
  "grant_type": "authorization_code",
  "code": "auth_code_received",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "redirect_uri": "https://your-app.com/callback"
}
```

### Scopes et Permissions

```yaml
# Scopes disponibles
scopes:
  # Archives
  "archives:read": "Lire les archives"
  "archives:create": "Créer des archives"
  "archives:update": "Modifier des archives"
  "archives:delete": "Supprimer des archives"
  
  # Recherche
  "search:execute": "Exécuter des recherches"
  "search:admin": "Administration de la recherche"
  
  # Machine Learning
  "ml:categorize": "Catégorisation automatique"
  "ml:train": "Entraînement de modèles"
  "ml:admin": "Administration ML"
  
  # Clustering
  "clustering:execute": "Exécuter du clustering"
  "clustering:admin": "Administration clustering"
  
  # Blockchain
  "blockchain:read": "Lire la blockchain"
  "blockchain:validate": "Valider des transactions"
  "blockchain:admin": "Administration blockchain"
  
  # Administration
  "admin:users": "Gestion des utilisateurs"
  "admin:system": "Administration système"
  "admin:monitoring": "Accès au monitoring"
```

## 🌐 API REST v4

Base URL: `http://localhost:8080/api/v4`

### Archives Management

#### Créer une Archive

```http
POST /api/v4/archives
Content-Type: application/json
Authorization: Bearer {token}

{
  "url": "https://example.com/article",
  "title": "Titre de l'article",
  "content": "Contenu de l'article...",
  "categories": ["technology", "ai"],
  "tags": ["machine-learning", "automation"],
  "metadata": {
    "author": "John Doe",
    "publish_date": "2024-01-15T10:30:00Z"
  },
  "options": {
    "auto_categorize": true,
    "extract_content": true,
    "take_screenshot": true,
    "blockchain_verify": true
  }
}
```

**Réponse 201 Created :**
```json
{
  "id": 12345,
  "url": "https://example.com/article",
  "title": "Titre de l'article",
  "content_hash": "sha256:a3b2c1d4e5f6...",
  "file_path": "/archives/2024/01/15/article_12345.html",
  "categories": [
    {
      "name": "technology",
      "confidence": 0.95
    },
    {
      "name": "ai",
      "confidence": 0.87
    }
  ],
  "tags": ["machine-learning", "automation"],
  "status": "archived",
  "blockchain_tx": "0x1234567890abcdef...",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:05Z"
}
```

#### Récupérer une Archive

```http
GET /api/v4/archives/{id}
Authorization: Bearer {token}
```

**Paramètres de requête :**
- `include_content` (bool) : Inclure le contenu complet
- `include_metadata` (bool) : Inclure les métadonnées étendues
- `include_blockchain` (bool) : Inclure les informations blockchain

**Réponse 200 OK :**
```json
{
  "id": 12345,
  "url": "https://example.com/article",
  "title": "Titre de l'article",
  "content": "Contenu complet de l'article...",
  "content_hash": "sha256:a3b2c1d4e5f6...",
  "file_path": "/archives/2024/01/15/article_12345.html",
  "screenshot_path": "/screenshots/2024/01/15/article_12345.png",
  "categories": [...],
  "tags": [...],
  "metadata": {
    "size_bytes": 15678,
    "mime_type": "text/html",
    "language": "fr",
    "encoding": "utf-8"
  },
  "blockchain": {
    "transaction_hash": "0x1234567890abcdef...",
    "block_number": 54321,
    "block_hash": "0xabcdef1234567890...",
    "verified": true
  },
  "stats": {
    "view_count": 42,
    "search_count": 15,
    "last_accessed": "2024-01-20T14:30:00Z"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:05Z"
}
```

#### Lister les Archives

```http
GET /api/v4/archives
Authorization: Bearer {token}
```

**Paramètres de requête :**
- `page` (int, default: 1) : Numéro de page
- `limit` (int, default: 20, max: 100) : Nombre d'éléments par page
- `sort` (string, default: "created_at") : Champ de tri
- `order` (string, default: "desc") : Ordre de tri (asc/desc)
- `category` (string) : Filtrer par catégorie
- `tag` (string) : Filtrer par tag
- `status` (string) : Filtrer par statut
- `date_from` (ISO date) : Date de début
- `date_to` (ISO date) : Date de fin
- `search` (string) : Recherche textuelle

**Réponse 200 OK :**
```json
{
  "data": [
    {
      "id": 12345,
      "url": "https://example.com/article",
      "title": "Titre de l'article",
      "categories": [...],
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "filters": {
    "category": "technology",
    "status": "archived",
    "date_range": "2024-01-01 to 2024-01-31"
  }
}
```

#### Mettre à Jour une Archive

```http
PUT /api/v4/archives/{id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "title": "Nouveau titre",
  "categories": ["updated-category"],
  "tags": ["new-tag"],
  "metadata": {
    "updated_field": "new_value"
  }
}
```

#### Supprimer une Archive

```http
DELETE /api/v4/archives/{id}
Authorization: Bearer {token}
```

**Paramètres de requête :**
- `permanent` (bool, default: false) : Suppression définitive
- `remove_files` (bool, default: false) : Supprimer les fichiers associés

### Recherche Avancée

#### Recherche Simple

```http
POST /api/v4/search
Content-Type: application/json
Authorization: Bearer {token}

{
  "query": "intelligence artificielle",
  "limit": 20,
  "offset": 0
}
```

#### Recherche Avancée

```http
POST /api/v4/search/advanced
Content-Type: application/json
Authorization: Bearer {token}

{
  "query": "intelligence artificielle",
  "filters": {
    "categories": ["technology", "ai"],
    "tags": ["machine-learning"],
    "date_range": {
      "from": "2024-01-01T00:00:00Z",
      "to": "2024-12-31T23:59:59Z"
    },
    "content_type": ["text/html", "application/pdf"],
    "language": ["fr", "en"],
    "min_confidence": 0.7
  },
  "sort": {
    "field": "relevance",
    "order": "desc"
  },
  "search_options": {
    "search_engine": "opensearch",
    "enable_clustering": true,
    "clustering_algorithm": "hdbscan",
    "enable_vector_search": true,
    "highlight": true,
    "facets": ["categories", "tags", "date"]
  },
  "limit": 50,
  "offset": 0
}
```

**Réponse 200 OK :**
```json
{
  "query": "intelligence artificielle",
  "results": [
    {
      "id": 12345,
      "title": "Introduction à l'IA",
      "url": "https://example.com/ia-intro",
      "excerpt": "L'<em>intelligence artificielle</em> est...",
      "categories": ["technology", "ai"],
      "relevance_score": 0.95,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "clusters": [
    {
      "id": "cluster_1",
      "name": "Machine Learning Basics",
      "description": "Articles sur les bases du ML",
      "size": 15,
      "coherence_score": 0.82,
      "keywords": ["machine learning", "algorithmes", "données"],
      "members": [12345, 12346, 12347]
    }
  ],
  "facets": {
    "categories": {
      "technology": 45,
      "ai": 32,
      "science": 18
    },
    "tags": {
      "machine-learning": 28,
      "deep-learning": 15,
      "nlp": 12
    }
  },
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true
  },
  "performance": {
    "search_time_ms": 45,
    "clustering_time_ms": 120,
    "total_time_ms": 165
  }
}
```

#### Suggestions de Recherche

```http
GET /api/v4/search/suggestions?q=intel
Authorization: Bearer {token}
```

**Réponse 200 OK :**
```json
{
  "suggestions": [
    {
      "text": "intelligence artificielle",
      "score": 0.95,
      "type": "completion"
    },
    {
      "text": "intel processor",
      "score": 0.87,
      "type": "completion"
    }
  ],
  "categories": [
    {
      "name": "technology",
      "count": 245
    }
  ],
  "tags": [
    {
      "name": "intel",
      "count": 123
    }
  ]
}
```

### Machine Learning

#### Catégorisation Automatique

```http
POST /api/v4/ml/categorize
Content-Type: application/json
Authorization: Bearer {token}

{
  "archive_ids": [12345, 12346, 12347],
  "model": "distilbert-base-uncased",
  "confidence_threshold": 0.3,
  "max_categories": 5,
  "auto_save": true
}
```

**Réponse 202 Accepted :**
```json
{
  "task_id": "ml_categorize_abcdef123456",
  "status": "processing",
  "estimated_completion": "2024-01-15T10:35:00Z",
  "progress_url": "/api/v4/tasks/ml_categorize_abcdef123456"
}
```

#### Entraînement de Modèle

```http
POST /api/v4/ml/train
Content-Type: application/json
Authorization: Bearer {token}

{
  "model_name": "custom_categorizer_v1",
  "model_type": "naive_bayes",
  "training_data": {
    "source": "existing_archives",
    "filters": {
      "categories": ["technology", "science"],
      "min_confidence": 0.8
    }
  },
  "parameters": {
    "test_split": 0.2,
    "validation_split": 0.1,
    "max_features": 10000
  },
  "auto_deploy": false
}
```

#### Liste des Modèles

```http
GET /api/v4/ml/models
Authorization: Bearer {token}
```

**Réponse 200 OK :**
```json
{
  "models": [
    {
      "id": "model_123",
      "name": "distilbert-base-uncased",
      "type": "transformers",
      "status": "active",
      "accuracy": 0.89,
      "f1_score": 0.87,
      "training_date": "2024-01-10T14:30:00Z",
      "version": "1.2.3"
    }
  ]
}
```

### Clustering

#### Lancer un Clustering

```http
POST /api/v4/clustering/run
Content-Type: application/json
Authorization: Bearer {token}

{
  "algorithm": "hdbscan",
  "parameters": {
    "min_cluster_size": 3,
    "min_samples": 2,
    "metric": "euclidean"
  },
  "data_source": {
    "type": "search_results",
    "query": "intelligence artificielle",
    "limit": 1000
  },
  "features": {
    "method": "sentence_transformers",
    "model": "all-MiniLM-L6-v2",
    "dimensions": 384
  }
}
```

#### Résultats de Clustering

```http
GET /api/v4/clustering/results/{task_id}
Authorization: Bearer {token}
```

**Réponse 200 OK :**
```json
{
  "task_id": "clustering_xyz789",
  "status": "completed",
  "algorithm": "hdbscan",
  "clusters": [
    {
      "id": "cluster_1",
      "name": "Deep Learning Fundamentals",
      "size": 25,
      "coherence_score": 0.84,
      "keywords": ["deep learning", "neural networks", "tensorflow"],
      "centroid": [0.1, 0.2, 0.3, ...],
      "members": [12345, 12346, ...]
    }
  ],
  "outliers": [12999, 13000],
  "metrics": {
    "silhouette_score": 0.72,
    "calinski_harabasz_score": 342.5,
    "davies_bouldin_score": 0.45
  },
  "completed_at": "2024-01-15T10:45:00Z"
}
```

### Monitoring et Health

#### Santé du Système

```http
GET /api/v4/health
```

**Réponse 200 OK :**
```json
{
  "status": "healthy",
  "version": "4.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "response_time_ms": 15,
      "connections": {
        "active": 12,
        "idle": 8,
        "max": 100
      }
    },
    "opensearch": {
      "status": "healthy",
      "response_time_ms": 25,
      "cluster_health": "green",
      "indices": 15
    },
    "blockchain": {
      "status": "healthy",
      "last_block": 54321,
      "network_peers": 8,
      "sync_status": "synchronized"
    },
    "redis": {
      "status": "healthy",
      "memory_usage": "45%",
      "hit_ratio": "87%"
    }
  }
}
```

#### Métriques Détaillées

```http
GET /api/v4/monitoring/metrics
Authorization: Bearer {token}
```

**Réponse 200 OK :**
```json
{
  "metrics": {
    "api": {
      "requests_per_second": 150.5,
      "average_response_time_ms": 85,
      "error_rate_percent": 0.2
    },
    "archives": {
      "total_count": 15678,
      "daily_growth": 234,
      "storage_usage_gb": 1250.5
    },
    "search": {
      "queries_per_minute": 45,
      "average_search_time_ms": 120,
      "cache_hit_rate_percent": 72
    },
    "ml": {
      "categorizations_today": 456,
      "model_accuracy": 0.89,
      "processing_queue_size": 23
    },
    "blockchain": {
      "transactions_per_hour": 89,
      "validation_success_rate": 0.998,
      "network_hash_rate": "125.5 TH/s"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🚀 API GraphQL

Base URL: `http://localhost:8083/graphql`

### Schema Principal

```graphql
# Types de base
type Archive {
  id: ID!
  url: String!
  title: String
  content: String
  contentHash: String!
  filePath: String
  screenshotPath: String
  categories: [Category!]!
  tags: [String!]!
  metadata: JSON
  status: ArchiveStatus!
  blockchainTx: String
  createdAt: DateTime!
  updatedAt: DateTime!
  
  # Relations
  clusters: [Cluster!]!
  searchResults: [SearchResult!]!
}

type Category {
  id: ID!
  name: String!
  confidence: Float
  description: String
  color: String
}

type Cluster {
  id: ID!
  name: String!
  description: String
  algorithm: String!
  size: Int!
  coherenceScore: Float!
  keywords: [String!]!
  members: [Archive!]!
  createdAt: DateTime!
}

type SearchResult {
  query: String!
  results: [Archive!]!
  clusters: [Cluster!]!
  facets: JSON
  total: Int!
  executionTime: Int!
}

# Enums
enum ArchiveStatus {
  PENDING
  PROCESSING
  ARCHIVED
  FAILED
  DELETED
}

enum ClusteringAlgorithm {
  HDBSCAN
  KMEANS
  AGGLOMERATIVE
  DBSCAN
}

# Inputs
input CreateArchiveInput {
  url: String!
  title: String
  content: String
  categories: [String!]
  tags: [String!]
  metadata: JSON
  options: ArchiveOptionsInput
}

input ArchiveOptionsInput {
  autoCategorize: Boolean = true
  extractContent: Boolean = true
  takeScreenshot: Boolean = true
  blockchainVerify: Boolean = true
}

input SearchInput {
  query: String!
  filters: SearchFiltersInput
  sort: SortInput
  clustering: ClusteringOptionsInput
  limit: Int = 20
  offset: Int = 0
}

input SearchFiltersInput {
  categories: [String!]
  tags: [String!]
  dateRange: DateRangeInput
  contentType: [String!]
  language: [String!]
  minConfidence: Float
}

input ClusteringOptionsInput {
  enable: Boolean = false
  algorithm: ClusteringAlgorithm = HDBSCAN
  minClusterSize: Int = 3
}
```

### Requêtes (Queries)

#### Recherche avec Clustering

```graphql
query SearchWithClustering($input: SearchInput!) {
  search(input: $input) {
    query
    results {
      id
      title
      url
      categories {
        name
        confidence
      }
      excerpt
      relevanceScore
      createdAt
    }
    clusters {
      id
      name
      description
      size
      coherenceScore
      keywords
      members {
        id
        title
      }
    }
    facets
    total
    executionTime
  }
}
```

**Variables :**
```json
{
  "input": {
    "query": "intelligence artificielle",
    "filters": {
      "categories": ["technology", "ai"],
      "dateRange": {
        "from": "2024-01-01T00:00:00Z",
        "to": "2024-12-31T23:59:59Z"
      }
    },
    "clustering": {
      "enable": true,
      "algorithm": "HDBSCAN",
      "minClusterSize": 5
    },
    "limit": 50
  }
}
```

#### Récupérer une Archive avec Relations

```graphql
query GetArchiveWithRelations($id: ID!) {
  archive(id: $id) {
    id
    url
    title
    content
    categories {
      name
      confidence
      description
    }
    tags
    metadata
    blockchainTx
    clusters {
      id
      name
      size
    }
    createdAt
    updatedAt
  }
}
```

#### Liste des Archives avec Pagination

```graphql
query ListArchives($page: Int!, $limit: Int!, $filters: ArchiveFiltersInput) {
  archives(page: $page, limit: $limit, filters: $filters) {
    data {
      id
      title
      url
      categories {
        name
      }
      tags
      createdAt
    }
    pagination {
      page
      limit
      total
      pages
      hasNext
      hasPrev
    }
  }
}
```

### Mutations

#### Créer une Archive

```graphql
mutation CreateArchive($input: CreateArchiveInput!) {
  createArchive(input: $input) {
    id
    url
    title
    status
    blockchainTx
    categories {
      name
      confidence
    }
    createdAt
  }
}
```

**Variables :**
```json
{
  "input": {
    "url": "https://example.com/article",
    "title": "Titre de l'article",
    "content": "Contenu de l'article...",
    "categories": ["technology"],
    "tags": ["ai", "ml"],
    "options": {
      "autoCategorize": true,
      "blockchainVerify": true
    }
  }
}
```

#### Catégorisation ML

```graphql
mutation CategorizeArchive($id: ID!, $options: CategorizationOptionsInput) {
  categorizeArchive(id: $id, options: $options) {
    id
    categories {
      name
      confidence
    }
    updatedAt
  }
}
```

#### Clustering de Ressources

```graphql
mutation ClusterResources($input: ClusteringInput!) {
  clusterResources(input: $input) {
    taskId
    status
    estimatedCompletion
    clusters {
      id
      name
      size
      coherenceScore
      keywords
    }
  }
}
```

### Subscriptions (Temps Réel)

#### Mises à Jour d'Archives

```graphql
subscription ArchiveUpdates($archiveId: ID) {
  archiveUpdated(archiveId: $archiveId) {
    id
    status
    categories {
      name
      confidence
    }
    updatedAt
  }
}
```

#### Événements Blockchain

```graphql
subscription BlockchainEvents {
  blockchainEvent {
    type
    blockNumber
    transactionHash
    data
    timestamp
  }
}
```

#### Progression de Clustering

```graphql
subscription ClusteringProgress($taskId: ID!) {
  clusteringProgress(taskId: $taskId) {
    taskId
    status
    progress
    currentStep
    estimatedTimeRemaining
    intermediateResults {
      clustersFound
      outliers
    }
  }
}
```

## ⚡ WebSocket API

Base URL: `ws://localhost:8080/ws`

### Connexion et Authentification

```javascript
// Connexion WebSocket avec token
const ws = new WebSocket('ws://localhost:8080/ws', ['bearer', jwt_token]);

// Ou avec API key
const ws = new WebSocket('ws://localhost:8080/ws', ['api-key', api_key]);

ws.onopen = function(event) {
  console.log('Connexion WebSocket établie');
  
  // S'abonner aux mises à jour d'archives
  ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'archives',
    filters: {
      categories: ['technology']
    }
  }));
};
```

### Channels Disponibles

#### 1. Archives (`archives`)

```javascript
// S'abonner aux mises à jour d'archives
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'archives',
  filters: {
    categories: ['technology', 'ai'],
    user_id: 'user_123'  // Optionnel
  }
}));

// Message reçu
{
  "type": "archive_updated",
  "channel": "archives",
  "data": {
    "id": 12345,
    "status": "archived",
    "categories": [{"name": "ai", "confidence": 0.95}],
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

#### 2. Recherche en Temps Réel (`search`)

```javascript
// Recherche en streaming
ws.send(JSON.stringify({
  type: 'search_stream',
  channel: 'search',
  query: 'intelligence artificielle',
  options: {
    real_time: true,
    clustering: true
  }
}));

// Résultats en streaming
{
  "type": "search_result",
  "channel": "search",
  "data": {
    "result": {
      "id": 12345,
      "title": "Nouvel article IA",
      "relevance": 0.95
    },
    "is_final": false
  }
}
```

#### 3. Blockchain (`blockchain`)

```javascript
// S'abonner aux événements blockchain
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'blockchain',
  events: ['new_block', 'new_transaction']
}));

// Nouveau bloc
{
  "type": "new_block",
  "channel": "blockchain",
  "data": {
    "block_number": 54321,
    "block_hash": "0xabcdef...",
    "transaction_count": 15,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### 4. Tâches ML (`ml_tasks`)

```javascript
// Suivre la progression d'une tâche ML
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'ml_tasks',
  task_id: 'ml_categorize_abc123'
}));

// Progression
{
  "type": "task_progress",
  "channel": "ml_tasks",
  "data": {
    "task_id": "ml_categorize_abc123",
    "status": "processing",
    "progress": 0.65,
    "estimated_remaining": 45
  }
}
```

## 🔗 API Blockchain

Base URL: `http://localhost:8334/rpc`

### JSON-RPC 2.0

#### Informations sur la Blockchain

```bash
curl -X POST http://localhost:8334/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "blockchain_info",
    "params": {},
    "id": 1
  }'
```

**Réponse :**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "chain_name": "ArchiveChain",
    "network": "mainnet",
    "latest_block": {
      "number": 54321,
      "hash": "0xabcdef1234567890...",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    "total_transactions": 123456,
    "network_peers": 8,
    "sync_status": "synchronized"
  },
  "id": 1
}
```

#### Soumettre une Transaction

```bash
curl -X POST http://localhost:8334/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "submit_transaction",
    "params": {
      "transaction": {
        "type": "archive",
        "data": {
          "content_hash": "sha256:abc123...",
          "metadata_hash": "sha256:def456...",
          "archive_id": 12345
        },
        "signature": "0x1234567890abcdef..."
      }
    },
    "id": 2
  }'
```

#### Vérifier une Archive

```bash
curl -X POST http://localhost:8334/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "verify_archive",
    "params": {
      "content_hash": "sha256:abc123..."
    },
    "id": 3
  }'
```

**Réponse :**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "verified": true,
    "transaction_hash": "0x1234567890abcdef...",
    "block_number": 54321,
    "timestamp": "2024-01-15T10:30:00Z",
    "validator": "0x742d35Cc6...",
    "confirmations": 156
  },
  "id": 3
}
```

## 📊 Codes de Réponse

### Codes de Succès

| Code | Statut | Description |
|------|--------|-------------|
| 200 | OK | Requête réussie |
| 201 | Created | Ressource créée avec succès |
| 202 | Accepted | Requête acceptée pour traitement asynchrone |
| 204 | No Content | Requête réussie sans contenu de réponse |

### Codes d'Erreur Client

| Code | Statut | Description |
|------|--------|-------------|
| 400 | Bad Request | Requête malformée ou paramètres invalides |
| 401 | Unauthorized | Authentification requise ou invalide |
| 403 | Forbidden | Permissions insuffisantes |
| 404 | Not Found | Ressource introuvable |
| 409 | Conflict | Conflit avec l'état actuel de la ressource |
| 422 | Unprocessable Entity | Données valides mais traitement impossible |
| 429 | Too Many Requests | Limite de taux atteinte |

### Codes d'Erreur Serveur

| Code | Statut | Description |
|------|--------|-------------|
| 500 | Internal Server Error | Erreur interne du serveur |
| 502 | Bad Gateway | Erreur de passerelle |
| 503 | Service Unavailable | Service temporairement indisponible |
| 504 | Gateway Timeout | Timeout de passerelle |

### Format des Erreurs

```json
{
  "error": {
    "code": "ARCHIVE_NOT_FOUND",
    "message": "L'archive avec l'ID 12345 n'existe pas",
    "details": {
      "archive_id": 12345,
      "requested_at": "2024-01-15T10:30:00Z"
    },
    "request_id": "req_abcdef123456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## 🧪 Exemples d'Intégration

### Python SDK

```python
import databot_client

# Initialisation du client
client = databot_client.Client(
    base_url="http://localhost:8080",
    api_key="ak_1234567890abcdef..."
)

# Créer une archive
archive = client.archives.create(
    url="https://example.com/article",
    title="Mon Article",
    categories=["technology"],
    options={
        "auto_categorize": True,
        "blockchain_verify": True
    }
)

print(f"Archive créée: {archive.id}")

# Recherche avancée
results = client.search.advanced(
    query="intelligence artificielle",
    filters={
        "categories": ["technology", "ai"],
        "date_range": {
            "from": "2024-01-01",
            "to": "2024-12-31"
        }
    },
    clustering=True
)

print(f"Trouvé {len(results.results)} résultats")
print(f"Clusters: {len(results.clusters)}")

# WebSocket pour temps réel
import asyncio
import websockets

async def listen_updates():
    uri = "ws://localhost:8080/ws"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        # S'abonner aux mises à jour
        await websocket.send(json.dumps({
            "type": "subscribe",
            "channel": "archives",
            "filters": {"categories": ["technology"]}
        }))
        
        async for message in websocket:
            data = json.loads(message)
            print(f"Mise à jour reçue: {data}")

asyncio.run(listen_updates())
```

### JavaScript/Node.js

```javascript
const { DataBotClient } = require('databot-client');

// Initialisation
const client = new DataBotClient({
  baseURL: 'http://localhost:8080',
  apiKey: 'ak_1234567890abcdef...'
});

// Créer une archive
async function createArchive() {
  try {
    const archive = await client.archives.create({
      url: 'https://example.com/article',
      title: 'Mon Article',
      categories: ['technology'],
      options: {
        autoCategorize: true,
        blockchainVerify: true
      }
    });
    
    console.log(`Archive créée: ${archive.id}`);
    return archive;
  } catch (error) {
    console.error('Erreur:', error);
  }
}

// GraphQL avec Apollo Client
import { ApolloClient, InMemoryCache, gql } from '@apollo/client';

const client = new ApolloClient({
  uri: 'http://localhost:8083/graphql',
  cache: new InMemoryCache(),
  headers: {
    authorization: `Bearer ${jwtToken}`
  }
});

const SEARCH_QUERY = gql`
  query SearchWithClustering($input: SearchInput!) {
    search(input: $input) {
      results {
        id
        title
        url
        categories {
          name
          confidence
        }
      }
      clusters {
        id
        name
        size
        keywords
      }
      total
    }
  }
`;

const { data } = await client.query({
  query: SEARCH_QUERY,
  variables: {
    input: {
      query: 'intelligence artificielle',
      clustering: { enable: true }
    }
  }
});

console.log(`${data.search.total} résultats trouvés`);
```

### cURL Scripts

```bash
#!/bin/bash

# Configuration
BASE_URL="http://localhost:8080/api/v4"
API_KEY="ak_1234567890abcdef..."

# Fonction helper pour les requêtes
api_call() {
  local method=$1
  local endpoint=$2
  local data=$3
  
  curl -s -X "$method" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    ${data:+-d "$data"} \
    "$BASE_URL$endpoint"
}

# Créer une archive
create_archive() {
  local url=$1
  local title=$2
  
  api_call POST "/archives" '{
    "url": "'$url'",
    "title": "'$title'",
    "options": {
      "auto_categorize": true,
      "blockchain_verify": true
    }
  }'
}

# Recherche
search() {
  local query=$1
  
  api_call POST "/search/advanced" '{
    "query": "'$query'",
    "search_options": {
      "enable_clustering": true
    },
    "limit": 20
  }'
}

# Utilisation
echo "Création d'archive..."
ARCHIVE=$(create_archive "https://example.com" "Test Article")
ARCHIVE_ID=$(echo "$ARCHIVE" | jq -r '.id')
echo "Archive créée: $ARCHIVE_ID"

echo "Recherche..."
RESULTS=$(search "intelligence artificielle")
TOTAL=$(echo "$RESULTS" | jq -r '.pagination.total')
echo "Résultats trouvés: $TOTAL"
```

---

## 📚 Ressources Complémentaires

- [Guide d'Installation](INSTALLATION.md) - Configuration des APIs
- [Architecture](ARCHITECTURE.md) - Architecture des APIs
- [Security Handbook](SECURITY_HANDBOOK.md) - Sécurité des APIs
- [Examples](examples/) - Exemples d'intégration complets

## 🆘 Support API

- **Documentation Interactive :** http://localhost:8080/docs (Swagger UI)
- **GraphQL Playground :** http://localhost:8083/graphql
- **Postman Collection :** [Télécharger](./examples/DATA_BOT_v4.postman_collection.json)
- **OpenAPI Spec :** [Télécharger](./examples/openapi.yaml)

**🚀 API DATA_BOT v4 - Puissance et Flexibilité pour tous vos Besoins d'Intégration !**

![API Ready](https://img.shields.io/badge/API-Ready-success.svg)
![GraphQL](https://img.shields.io/badge/GraphQL-Supported-purple.svg)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-orange.svg)