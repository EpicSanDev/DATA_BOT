# DATA_BOT v2 - Guide d'utilisation

## 🚀 Nouvelles fonctionnalités v2

DATA_BOT v2 apporte de nombreuses améliorations par rapport à la version originale:

### ✅ Interface web de gestion
- Interface moderne et responsive accessible via navigateur
- Tableau de bord avec statistiques en temps réel
- Gestion des ressources via interface graphique
- Recherche avancée dans l'archive

### ✅ Support d'autres modèles IA
- **Ollama** (original) - Modèles locaux comme Llama2, Mistral, etc.
- **OpenAI** - GPT-3.5, GPT-4 (nécessite clé API)
- **LLM locaux** - Support HuggingFace Transformers
- **Fallback** - Réponses prédéfinies si IA indisponible

### ✅ Export en différents formats
- **JSON** - Export structuré complet
- **CSV** - Format tableur compatible Excel
- **HTML** - Page web interactive avec recherche
- **XML** - Format structuré pour intégrations
- **ZIP** - Archive complète avec fichiers téléchargés

### ✅ Détection de doublons
- Détection par **URL normalisée** (suppression paramètres tracking)
- Détection par **hash de contenu** (fichiers identiques)
- Détection par **titre similaire** (normalisation textuelle)
- Détection d'**URLs similaires** (même domaine, chemin proche)

### ✅ Compression intelligente
- **Compression adaptative** selon le type de fichier
- **GZIP** pour texte, HTML, JSON
- **ZIP** pour archives multiples
- **Seuils intelligents** de ratio de compression
- **Auto-compression** des nouveaux fichiers

### ✅ API REST complète
- Endpoints pour toutes les fonctionnalités
- Format JSON standardisé
- Support CORS pour intégrations web
- Documentation interactive via interface

### ✅ Support de proxies
- **Rotation automatique** des proxies
- **Test de santé** et détection de pannes
- **Stratégies** : round-robin, aléatoire, failover
- **Configuration** via variables d'environnement

### ✅ Archivage programmé
- **Scheduler type cron** intégré
- **Tâches prédéfinies** : archivage, export, nettoyage
- **Planification flexible** : horaire, quotidien, hebdomadaire
- **Gestion des erreurs** et retry automatique

## 🎮 Utilisation

### Installation

```bash
# Cloner le projet
git clone https://github.com/EpicSanDev/DATA_BOT
cd DATA_BOT

# Installer les dépendances v2
pip install python-dotenv httpx

# Optionnel : pour toutes les fonctionnalités
pip install -r requirements.txt
```

### Démarrage rapide

```bash
# Mode serveur avec interface web (recommandé)
python main_v2.py --mode server

# Puis ouvrir http://localhost:8080
```

### Modes d'utilisation

#### Mode serveur
```bash
python main_v2.py --mode server --api-port 8080
```
- Interface web complète
- API REST active
- Planificateur automatique
- Idéal pour usage continu

#### Mode export
```bash
# Export JSON
python main_v2.py --mode export --export-format json

# Export ZIP avec fichiers
python main_v2.py --mode export --export-format zip --include-files

# Export filtré
python main_v2.py --mode export --export-format csv --filter-status downloaded
```

#### Mode compression
```bash
# Compression intelligente
python main_v2.py --mode compress

# Forcer recompression
python main_v2.py --mode compress --force-recompress
```

#### Mode doublons
```bash
# Détecter les doublons
python main_v2.py --mode duplicates

# Supprimer les doublons
python main_v2.py --mode duplicates --remove-duplicates --duplicate-strategy keep_best
```

#### Mode nettoyage
```bash
python main_v2.py --mode cleanup --max-exports 5
```

#### Mode planification
```bash
# Lister les tâches
python main_v2.py --mode schedule --schedule-action list

# Ajouter une tâche
python main_v2.py --mode schedule --schedule-action add \
  --task-name "Export hebdomadaire" \
  --task-type export \
  --task-frequency weekly
```

### Configuration

#### Variables d'environnement

```bash
# IA et Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
OPENAI_API_KEY=sk-your-key-here

# Proxies (optionnel)
PROXY_LIST=http://proxy1.com:8080,http://user:pass@proxy2.com:3128

# Chemins
ARCHIVE_PATH=./archive
SCREENSHOTS_PATH=./screenshots
DATABASE_PATH=./data/archive.db

# Limites
MAX_PAGES_PER_DOMAIN=100
CONCURRENT_DOWNLOADS=5
```

#### Fichier .env

```env
# Copier .env.example vers .env et ajuster
cp .env.example .env
```

## 📊 API REST

### Endpoints principaux

```bash
# Statistiques
GET /api/stats

# Ressources
GET /api/resources?limit=50&offset=0&status=downloaded
POST /api/resources
DELETE /api/resources/{id}

# Recherche
GET /api/search?q=python

# Export
GET /api/export?format=json&include_files=true

# Archive
POST /api/archive/start
```

### Exemples d'utilisation

```javascript
// Récupérer les statistiques
const stats = await fetch('/api/stats').then(r => r.json());

// Ajouter une URL
await fetch('/api/resources', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ url: 'https://example.com', title: 'Example' })
});

// Rechercher
const results = await fetch('/api/search?q=python').then(r => r.json());
```

## 🔧 Architecture technique

### Structure des modules v2

```
src/
├── api_server.py          # Serveur API REST + Interface web
├── enhanced_ai_client.py  # Client IA multi-fournisseurs
├── export_manager.py      # Gestionnaire d'exports
├── duplicate_detector.py  # Détection de doublons
├── compression_manager.py # Compression intelligente
├── proxy_manager.py       # Gestion des proxies
├── task_scheduler.py      # Planificateur de tâches
└── [modules originaux]    # config.py, database.py, etc.
```

### Base de données

La base SQLite est étendue avec:
- Métadonnées de compression
- Marquage des doublons
- Historique des tâches programmées
- Statistiques détaillées

### Intégrations

DATA_BOT v2 peut s'intégrer avec:
- **Webhook** - Notifications via API REST
- **CI/CD** - Archivage automatique de documentation
- **Monitoring** - Métriques via endpoints /api/stats
- **Backup** - Export programmé vers stockage externe

## 🛠️ Développement

### Tests

```bash
# Test rapide des fonctionnalités
python test_v2.py

# Test de l'interface (nécessite navigateur)
python demo_server.py 8080
```

### Extension

Pour ajouter de nouvelles fonctionnalités:

1. **Nouveau fournisseur IA** : Étendre `AIProvider` dans `enhanced_ai_client.py`
2. **Nouveau format d'export** : Ajouter méthode dans `ExportManager`
3. **Nouvelles tâches programmées** : Ajouter handler dans `TaskScheduler`
4. **Nouveaux endpoints API** : Étendre `APIHandler`

### Debug

```bash
# Mode verbose
python main_v2.py --mode server --log-level DEBUG

# Logs détaillés
tail -f logs/archive_bot.log
```

## 📈 Performance

### Optimisations v2

- **Compression intelligente** : Réduction jusqu'à 70% de l'espace
- **Détection de doublons** : Évite les téléchargements redondants
- **Rotation de proxies** : Contourne les limitations de taux
- **Planificateur** : Répartit la charge sur la journée

### Métriques

L'interface web affiche:
- Taux de compression moyen
- Statistiques de doublons
- Performance des proxies
- Historique des tâches

## 🔒 Sécurité

### Bonnes pratiques

- **Variables d'environnement** pour les clés API
- **Validation stricte** des URLs
- **Limitation des tailles** de fichiers
- **Nettoyage** des noms de fichiers
- **Logs sécurisés** sans secrets

### API

- **CORS** configuré pour domaines autorisés
- **Rate limiting** possible via reverse proxy
- **Authentification** extensible via middleware

## 🆘 Dépannage

### Problèmes courants

1. **Port 8080 occupé**
   ```bash
   python main_v2.py --mode server --api-port 8081
   ```

2. **Ollama non disponible**
   - Le système passe automatiquement en mode fallback
   - Vérifier `ollama serve` si Ollama installé

3. **Erreurs de compression**
   - Vérifier l'espace disque disponible
   - Logs détaillés dans `logs/archive_bot.log`

4. **Base de données corrompue**
   ```bash
   # Backup et recréation
   mv data/archive.db data/archive.db.bak
   python main_v2.py --mode server  # Recrée la DB
   ```

### Support

- **Logs** : Consultez `logs/archive_bot.log`
- **Interface** : Vérifiez http://localhost:8080/api/stats
- **Test** : Exécutez `python test_v2.py`

---

## 🎯 Roadmap v3

Fonctionnalités prévues:
- [ ] Interface mobile responsive
- [ ] Support de bases vectorielles (ChromaDB, Pinecone)
- [ ] Intégration Elasticsearch
- [ ] Plugin système pour navigateurs
- [ ] Mode distribué multi-machines
- [ ] IA d'analyse de contenu avancée