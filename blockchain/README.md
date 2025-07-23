# ArchiveChain - Infrastructure Blockchain Complète

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/databot/archivechain)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](blockchain/docker/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-ready-orange.svg)](blockchain/k8s/)

Infrastructure blockchain décentralisée production-ready pour DATA_BOT, basée sur l'architecture ArchiveChain avec consensus Proof of Archive (PoA).

## 🏗️ Architecture

```
blockchain/
├── deployment/              # Scripts de déploiement automatisés
│   ├── contract_deployer.py # Déployeur de smart contracts
│   ├── migration_manager.py # Gestionnaire de migrations
│   └── verification_manager.py
├── network/                 # Réseau P2P décentralisé
│   ├── p2p_manager.py      # Gestionnaire P2P principal
│   ├── dht_manager.py      # Distributed Hash Table
│   └── node_discovery.py   # Découverte automatique de nœuds
├── api/                    # APIs blockchain étendues
│   ├── rest_api.py         # API REST complète
│   ├── graphql_api.py      # API GraphQL
│   └── websocket_api.py    # WebSocket temps réel
├── tools/                  # Outils développeur
│   ├── python_sdk.py       # SDK Python
│   ├── cli_tool.py         # CLI blockchain
│   └── wallet_manager.py   # Gestionnaire de portefeuilles
├── explorer/               # Explorateur de blocs intégré
├── bridge/                 # Ponts inter-chaînes
├── governance/             # Gouvernance on-chain
├── tests/                  # Tests d'intégration
└── docker/                 # Configuration Docker/Kubernetes
```

## 🚀 Fonctionnalités Implémentées

### ✅ Infrastructure de Base
- **Blockchain ArchiveChain** avec consensus Proof of Archive
- **Tokens ARC** avec économie complète (1 milliard de tokens)
- **Smart Contracts** : ArchiveBounty, PreservationPool, ContentVerification
- **Sécurité renforcée** : Signatures ECDSA, SafeMath, validation stricte

### ✅ Déploiement de Smart Contracts
- **Déployeur automatisé** avec templates pré-configurés
- **Migration et mise à jour** de contrats
- **Vérification automatique** post-déploiement
- **Templates réutilisables** pour contrats courants

### ✅ Réseau P2P Décentralisé
- **Découverte automatique** de nœuds via bootstrap
- **DHT (Distributed Hash Table)** pour routage efficace
- **Propagation optimisée** des blocs et transactions
- **Synchronisation cross-chain** avec autres réseaux

### ✅ APIs Blockchain Complètes
- **API REST** avec 50+ endpoints documentés
- **API GraphQL** pour requêtes flexibles
- **WebSocket** pour mises à jour temps réel
- **Rate limiting** et sécurité intégrés

### ✅ Outils Développeur
- **SDK Python** avec interface intuitive
- **CLI blockchain** pour administration
- **Gestionnaire de portefeuilles** sécurisé
- **Documentation complète** avec exemples

### ✅ Infrastructure Docker/Kubernetes
- **Images Docker optimisées** pour chaque type de nœud
- **Orchestration Kubernetes** avec StatefulSets
- **Monitoring intégré** (Prometheus + Grafana)
- **Load balancing** et haute disponibilité

## 🛠️ Installation et Déploiement

### Prérequis
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Kubernetes 1.24+ (optionnel)

### Déploiement Local avec Docker

```bash
# Cloner le repository
git clone https://github.com/databot/archivechain.git
cd archivechain

# Construire et démarrer les services
cd blockchain/docker
docker-compose -f docker-compose.blockchain.yml up -d

# Vérifier le statut
docker-compose ps
```

### Déploiement Production avec Kubernetes

```bash
# Appliquer les manifests Kubernetes
kubectl apply -f blockchain/k8s/

# Vérifier le déploiement
kubectl get pods -n archivechain
kubectl get services -n archivechain
```

## 🔧 Configuration

### Variables d'Environnement

```bash
# Configuration nœud
NODE_TYPE=archive|storage|bandwidth|consensus
NODE_ID=unique-node-identifier
NETWORK_PORT=8333
API_PORT=5000
P2P_PORT=8334

# Base de données
DATABASE_URL=postgresql://user:pass@host:5432/archivechain
REDIS_URL=redis://host:6379/0

# Sécurité
ENABLE_TLS=true
JWT_SECRET=your-secret-key
API_KEY=your-api-key
```

### Configuration Réseau

```yaml
# blockchain/config/network.yml
bootstrap_nodes:
  - "bootstrap1.archivechain.io:8333"
  - "bootstrap2.archivechain.io:8333"
  - "bootstrap3.archivechain.io:8333"

p2p:
  max_peers: 50
  heartbeat_interval: 30
  peer_timeout: 300

consensus:
  block_time_target: 600  # 10 minutes
  difficulty_adjustment: 2016  # blocs
  min_validators: 3
```

## 📚 Utilisation du SDK

### Installation

```bash
pip install archivechain-sdk
```

### Exemples d'Utilisation

```python
from blockchain.tools import create_sdk

# Créer une instance SDK
sdk = create_sdk(api_url="http://localhost:5000")

# Créer une archive
tx_id = sdk.create_archive(
    url="https://example.com",
    archiver_address="0x123...",
    metadata={"tags": ["important", "news"]}
)

# Transférer des tokens
sdk.transfer_tokens(
    from_address="0x123...",
    to_address="0x456...",
    amount="100.0",
    fee="0.01"
)

# Déployer un contrat bounty
contract_id = sdk.deploy_bounty_contract(
    target_url="https://target.com",
    reward="500.0",
    deadline=time.time() + 86400,  # 24h
    creator="0x123..."
)

# Rechercher des archives
archives = sdk.search_archives("crypto blockchain")
```

## 🔍 Monitoring et Observabilité

### Métriques Disponibles

- **Blockchain** : Hauteur, TPS, temps de bloc, difficulté
- **Réseau P2P** : Nombre de peers, latence, bande passante
- **Smart Contracts** : Déploiements, exécutions, gas utilisé
- **Tokens** : Supply, transfers, staking, burning

### Dashboards Grafana

Accédez aux dashboards : `http://localhost:3000`
- Dashboard blockchain principal
- Métriques réseau P2P
- Statistiques smart contracts
- Performance système

### Logs Structurés

```bash
# Consulter les logs
docker-compose logs -f archivechain-node-1

# Logs spécifiques
kubectl logs -f deployment/archivechain-node -n archivechain
```

## 🧪 Tests et Qualité

### Exécution des Tests

```bash
# Tests unitaires
python -m pytest blockchain/tests/unit/

# Tests d'intégration
python -m pytest blockchain/tests/integration/

# Tests de performance
python -m pytest blockchain/tests/performance/

# Tests de sécurité
python -m pytest blockchain/tests/security/
```

### Couverture de Code

```bash
# Générer le rapport de couverture
coverage run -m pytest blockchain/tests/
coverage report
coverage html
```

## 🔐 Sécurité

### Fonctionnalités de Sécurité Implémentées

- **Signatures ECDSA obligatoires** pour toutes les transactions
- **SafeMath** pour éviter les overflow/underflow
- **Validation stricte** des entrées et paramètres
- **Rate limiting** sur les APIs
- **TLS/SSL** pour communications chiffrées
- **Isolation des conteneurs** Docker
- **RBAC Kubernetes** pour contrôle d'accès

### Audit de Sécurité

Consultez le [rapport d'audit de sécurité](../SECURITY_AUDIT_REPORT.md) pour les détails des vulnérabilités corrigées.

## 🤝 Contribution

### Guide de Contribution

1. Fork le repository
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

### Standards de Code

- **Python** : PEP 8, type hints, docstrings
- **Tests** : Couverture > 80%
- **Documentation** : Markdown, exemples pratiques
- **Commit** : Messages descriptifs, atomic commits

## 📈 Roadmap

### Version 1.1 (Q2 2024)
- [ ] Sharding pour scalabilité
- [ ] Layer 2 solutions
- [ ] Cross-chain bridges avancés
- [ ] DAO governance complet

### Version 1.2 (Q3 2024)
- [ ] zkSNARKs pour privacy
- [ ] IPFS integration native
- [ ] Mobile SDKs (iOS/Android)
- [ ] Advanced analytics

## 🆘 Support

### Documentation
- [Guide d'installation](docs/installation.md)
- [API Reference](docs/api-reference.md)
- [SDK Documentation](docs/sdk.md)
- [Troubleshooting](docs/troubleshooting.md)

### Communauté
- Discord : [https://discord.gg/archivechain](https://discord.gg/archivechain)
- Telegram : [https://t.me/archivechain](https://t.me/archivechain)
- Twitter : [@ArchiveChain](https://twitter.com/archivechain)

### Issues et Bugs
Reportez les bugs sur [GitHub Issues](https://github.com/databot/archivechain/issues)

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

**Développé avec ❤️ par l'équipe DATA_BOT**

*ArchiveChain - Préservation décentralisée du web pour les générations futures*