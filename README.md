# Bot d'Archivage Internet Automatique

Un bot intelligent qui explore et archive automatiquement Internet en utilisant Ollama pour la prise de décision.

## 🎯 Fonctionnalités

- **Exploration autonome** : Génère automatiquement des requêtes de recherche intelligentes avec Ollama
- **Téléchargement intelligent** : Télécharge et classe les sites web automatiquement
- **Screenshots de secours** : Capture des screenshots quand le téléchargement n'est pas possible
- **Classification automatique** : Utilise Ollama pour catégoriser et évaluer le contenu
- **Base de données** : Stockage et recherche des ressources archivées
- **Limitation respectueuse** : Respecte les robots.txt et limite le taux de requêtes

## 🚀 Installation

1. **Cloner le projet**
```bash
cd /Users/bastienjavaux/Desktop/DATA_BOT
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Installer Ollama** (si pas déjà fait)
```bash
# Sur macOS
brew install ollama

# Démarrer Ollama
ollama serve

# Télécharger un modèle (ex: llama2)
ollama pull llama2
```

4. **Configuration**
Ajustez les paramètres dans `.env` selon vos besoins.

## 🎮 Utilisation

### Mode Exploration
Découvre de nouvelles URLs à partir de requêtes générées par Ollama :
```bash
python main.py --mode explore
```

### Mode Traitement
Traite les URLs en attente de téléchargement/screenshot :
```bash
python main.py --mode process
```

### Mode Continu (Recommandé)
Explore et traite en continu :
```bash
python main.py --mode continuous
```

### Avec URLs de départ
```bash
python main.py --mode continuous --urls https://news.ycombinator.com https://reddit.com/r/technology
```

## 🛠️ Outils

### Statistiques
```bash
python tools.py stats
```

### Recherche dans l'archive
```bash
python tools.py search "intelligence artificielle"
```

### Ressources récentes
```bash
python tools.py recent
```

## 📁 Structure du Projet

```
DATA_BOT/
├── main.py              # Point d'entrée principal
├── tools.py             # Outils de gestion
├── requirements.txt     # Dépendances Python
├── .env                 # Configuration
├── src/
│   ├── config.py        # Configuration et paramètres
│   ├── models.py        # Modèles de données
│   ├── ollama_client.py # Client Ollama pour IA
│   ├── explorer.py      # Exploration web intelligente
│   ├── downloader.py    # Téléchargement de ressources
│   ├── screenshot.py    # Capture de screenshots
│   └── database.py      # Gestion base de données
├── archive/             # Fichiers téléchargés (créé auto)
├── screenshots/         # Screenshots (créé auto)
├── logs/                # Logs d'exécution (créé auto)
└── data/                # Base de données SQLite (créé auto)
```

## ⚙️ Configuration

Principales options dans `.env` :

```env
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2

# Limites
MAX_DEPTH=3
MAX_PAGES_PER_DOMAIN=50
CONCURRENT_DOWNLOADS=5

# Délais
DELAY_BETWEEN_REQUESTS=1
SCREENSHOT_TIMEOUT=30
```

## 🤖 Intelligence Ollama

Le bot utilise Ollama pour :

1. **Génération de requêtes** : Crée des requêtes de recherche variées et intéressantes
2. **Évaluation d'URLs** : Détermine si une URL vaut la peine d'être archivée
3. **Catégorisation** : Classe automatiquement le contenu découvert
4. **Priorisation** : Assigne des priorités aux ressources

## 📊 Fonctionnement

1. **Phase d'exploration** :
   - Ollama génère des requêtes de recherche intelligentes
   - Recherche sur Google/DuckDuckGo/Bing
   - Évalue chaque URL trouvée avec Ollama
   - Découvre de nouveaux liens depuis les pages visitées

2. **Phase de traitement** :
   - Télécharge les ressources approuvées
   - Si échec, capture un screenshot
   - Catégorise le contenu avec Ollama
   - Extrait les liens pour futures explorations

3. **Phase de classification** :
   - Analyse le contenu téléchargé
   - Assigne catégories, tags et priorités
   - Stocke les métadonnées dans la base

## 🔒 Respect des Serveurs

- Délais configurables entre requêtes
- Respect des robots.txt (optionnel)
- User-Agent personnalisable
- Limitation par domaine
- Headers respectueux

## 📈 Monitoring

Les logs détaillés permettent de suivre :
- Découvertes d'URLs
- Succès/échecs de téléchargement
- Décisions d'Ollama
- Statistiques par domaine
- Performance globale

## 🛡️ Sécurité

- Validation stricte des URLs
- Filtrage de contenu malveillant
- Limitation de taille des fichiers
- Nettoyage des noms de fichiers
- Gestion d'erreurs robuste

## 🎯 Cas d'Usage

- **Veille technologique** : Archive automatiquement les dernières actualités tech
- **Recherche académique** : Collecte des ressources éducatives
- **Backup web** : Sauvegarde de sites importants
- **Documentation** : Archive de documentation technique
- **Culture numérique** : Préservation de contenu culturel

## 🔧 Développement

Pour contribuer ou personnaliser :

1. **Tests** :
```bash
python -m pytest tests/
```

2. **Linting** :
```bash
flake8 src/
```

3. **Ajout de nouveaux moteurs de recherche** :
Modifiez `src/explorer.py`

4. **Personnalisation Ollama** :
Ajustez les prompts dans `src/ollama_client.py`

## 🚀 Prochaines Fonctionnalités

### ✅ VERSION 2.0 - DISPONIBLE MAINTENANT!

Toutes les fonctionnalités v2 ont été implémentées:

- [x] **Interface web de gestion** - Interface moderne accessible sur http://localhost:8080
- [x] **Support d'autres modèles IA** - OpenAI, LLM locaux, fallback automatique  
- [x] **Export en différents formats** - JSON, CSV, HTML, XML, ZIP avec fichiers
- [x] **Détection de doublons** - URL, contenu, titre, similarité intelligente
- [x] **Compression intelligente** - GZIP/ZIP adaptatif selon type de fichier
- [x] **API REST complète** - Endpoints pour toutes les fonctionnalités
- [x] **Support de proxies** - Rotation, test, failover automatique
- [x] **Archivage programmé** - Scheduler type cron intégré

### 🎮 Démarrage rapide v2

```bash
# Démarrer l'interface web v2
python main_v2.py --mode server

# Ouvrir http://localhost:8080
```

### 📱 Interface Web v2

![DATA_BOT v2 Interface](https://github.com/user-attachments/assets/c856c8c0-0fce-4b27-b0e7-4187bf7091de)

L'interface v2 offre:
- 📊 Tableau de bord avec statistiques temps réel
- 🔍 Recherche avancée dans l'archive
- 📤 Export en un clic vers multiple formats
- ⚙️ Gestion des tâches programmées
- 🖥️ Interface responsive et moderne

### 📖 Documentation v2

Consultez [GUIDE_V2.md](GUIDE_V2.md) pour la documentation complète des nouvelles fonctionnalités.

---

## 🎯 Roadmap v3 (Futur)

- [ ] Interface mobile native
- [ ] Support bases vectorielles (ChromaDB, Pinecone)
- [ ] Intégration Elasticsearch  
- [ ] Plugin navigateur
- [ ] Mode distribué multi-machines

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs dans `logs/`
2. Consultez la configuration `.env`
3. Testez la connexion Ollama
4. Vérifiez les permissions de fichiers

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails.

---

**🤖 Happy Archiving!**
