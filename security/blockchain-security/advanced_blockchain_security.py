#!/usr/bin/env python3
"""
🛡️ Sécurité Blockchain Avancée - DATA_BOT Enterprise
Protection contre attaques blockchain spécialisées et circuit breakers
"""

import asyncio
import logging
import time
import hashlib
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
from decimal import Decimal

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Niveaux de menace blockchain"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AttackType(Enum):
    """Types d'attaques blockchain"""
    FIFTY_ONE_PERCENT = "51_percent_attack"
    DOUBLE_SPENDING = "double_spending"
    ECLIPSE = "eclipse_attack"
    SYBIL = "sybil_attack"
    SELFISH_MINING = "selfish_mining"
    LONG_RANGE = "long_range_attack"
    NOTHING_AT_STAKE = "nothing_at_stake"
    SMART_CONTRACT_EXPLOIT = "smart_contract_exploit"
    CONSENSUS_MANIPULATION = "consensus_manipulation"
    NETWORK_PARTITION = "network_partition"

@dataclass
class SecurityMetrics:
    """Métriques de sécurité blockchain"""
    hash_rate_distribution: Dict[str, float] = field(default_factory=dict)
    network_connectivity: Dict[str, int] = field(default_factory=dict)
    transaction_patterns: Dict[str, Any] = field(default_factory=dict)
    consensus_participation: Dict[str, float] = field(default_factory=dict)
    anomaly_scores: Dict[str, float] = field(default_factory=dict)
    threat_indicators: List[Dict] = field(default_factory=list)
    
@dataclass
class ThreatAlert:
    """Alerte de menace blockchain"""
    alert_id: str
    attack_type: AttackType
    threat_level: ThreatLevel
    source_address: Optional[str]
    affected_components: List[str]
    evidence: Dict[str, Any]
    timestamp: datetime
    auto_response_triggered: bool = False
    resolved: bool = False

class CircuitBreakerState(Enum):
    """États du circuit breaker"""
    CLOSED = "closed"      # Fonctionnement normal
    OPEN = "open"          # Bloqué, protection active
    HALF_OPEN = "half_open"  # Test de récupération

@dataclass
class CircuitBreaker:
    """Circuit breaker pour protection automatique"""
    name: str
    component: str
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: int = 300  # 5 minutes
    last_failure_time: Optional[datetime] = None
    half_open_max_calls: int = 3
    half_open_call_count: int = 0
    
class AdvancedBlockchainSecurity:
    """Système de sécurité blockchain avancé enterprise-grade"""
    
    def __init__(self, blockchain_instance=None):
        self.blockchain = blockchain_instance
        self.security_metrics = SecurityMetrics()
        self.active_alerts: Dict[str, ThreatAlert] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Configuration de sécurité
        self.config = {
            'hash_rate_threshold': 0.45,  # 45% maximum pour un mineur
            'double_spend_window': 6,     # 6 blocks de confirmation
            'eclipse_detection_threshold': 0.8,  # 80% des connexions suspectes
            'sybil_node_threshold': 100,  # Maximum nouveaux nœuds par heure
            'consensus_anomaly_threshold': 3.0,  # Écarts-types
            'smart_contract_gas_limit': 1000000,
            'transaction_rate_limit': 1000,  # TPS maximum
            'network_partition_threshold': 0.3,  # 30% de nœuds déconnectés
        }
        
        # Initialiser les circuit breakers
        self._initialize_circuit_breakers()
        
        # Historique pour détection d'anomalies
        self.transaction_history = deque(maxlen=10000)
        self.block_history = deque(maxlen=1000)
        self.network_metrics_history = deque(maxlen=1000)
        
        # Patterns d'attaque connus
        self.attack_patterns = self._load_attack_patterns()
        
        # Lock pour thread-safety
        self._lock = threading.RLock()
        
    def _initialize_circuit_breakers(self):
        """Initialise les circuit breakers pour chaque composant critique"""
        components = [
            "consensus_engine",
            "transaction_pool", 
            "smart_contracts",
            "p2p_networking",
            "block_validation",
            "token_transfers",
            "mining_operations",
            "archive_operations"
        ]
        
        for component in components:
            self.circuit_breakers[component] = CircuitBreaker(
                name=f"{component}_breaker",
                component=component,
                failure_threshold=5,
                recovery_timeout=300
            )
    
    def _load_attack_patterns(self) -> Dict[AttackType, Dict]:
        """Charge les patterns d'attaque connus"""
        return {
            AttackType.FIFTY_ONE_PERCENT: {
                'indicators': [
                    'hash_rate_concentration > 45%',
                    'consistent_mining_advantage',
                    'fork_creation_pattern'
                ],
                'detection_window': 600,  # 10 minutes
                'confidence_threshold': 0.8
            },
            AttackType.DOUBLE_SPENDING: {
                'indicators': [
                    'same_utxo_multiple_transactions',
                    'conflicting_transactions',
                    'rapid_confirmation_attempts'
                ],
                'detection_window': 300,  # 5 minutes  
                'confidence_threshold': 0.9
            },
            AttackType.ECLIPSE: {
                'indicators': [
                    'connection_monopolization',
                    'information_isolation',
                    'controlled_peer_set'
                ],
                'detection_window': 1800,  # 30 minutes
                'confidence_threshold': 0.7
            },
            AttackType.SYBIL: {
                'indicators': [
                    'rapid_node_registration',
                    'ip_address_clustering',
                    'identical_node_behaviors'
                ],
                'detection_window': 3600,  # 1 hour
                'confidence_threshold': 0.8
            },
            AttackType.SMART_CONTRACT_EXPLOIT: {
                'indicators': [
                    'reentrancy_patterns',
                    'overflow_attempts', 
                    'gas_manipulation',
                    'unauthorized_state_changes'
                ],
                'detection_window': 60,   # 1 minute
                'confidence_threshold': 0.95
            }
        }
    
    async def start_monitoring(self):
        """Démarre la surveillance de sécurité blockchain"""
        if self.monitoring_active:
            logger.warning("Surveillance blockchain déjà active")
            return
            
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info("🛡️ Surveillance sécurité blockchain démarrée")
    
    def stop_monitoring(self):
        """Arrête la surveillance de sécurité"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        logger.info("🛡️ Surveillance sécurité blockchain arrêtée")
    
    def _monitoring_loop(self):
        """Boucle principale de surveillance"""
        while self.monitoring_active:
            try:
                # Collecter métriques
                self._collect_security_metrics()
                
                # Analyser menaces
                self._analyze_threats()
                
                # Vérifier circuit breakers
                self._check_circuit_breakers()
                
                # Mettre à jour métriques
                self._update_anomaly_detection()
                
                # Attendre avant prochaine itération
                time.sleep(10)  # Surveillance toutes les 10 secondes
                
            except Exception as e:
                logger.error(f"Erreur dans boucle surveillance: {e}")
                time.sleep(30)  # Pause plus longue en cas d'erreur
    
    def _collect_security_metrics(self):
        """Collecte les métriques de sécurité blockchain"""
        if not self.blockchain:
            return
            
        try:
            with self._lock:
                # Hash rate distribution
                self.security_metrics.hash_rate_distribution = \
                    self._calculate_hash_rate_distribution()
                
                # Connectivité réseau
                self.security_metrics.network_connectivity = \
                    self._analyze_network_connectivity()
                
                # Patterns de transactions
                self.security_metrics.transaction_patterns = \
                    self._analyze_transaction_patterns()
                
                # Participation au consensus
                self.security_metrics.consensus_participation = \
                    self._analyze_consensus_participation()
                
        except Exception as e:
            logger.error(f"Erreur collecte métriques: {e}")
    
    def _calculate_hash_rate_distribution(self) -> Dict[str, float]:
        """Calcule la distribution du hash rate"""
        if not hasattr(self.blockchain, 'get_miners_stats'):
            return {}
            
        try:
            miners_stats = self.blockchain.get_miners_stats()
            total_hash_rate = sum(miners_stats.values())
            
            if total_hash_rate == 0:
                return {}
                
            distribution = {
                miner: hash_rate / total_hash_rate 
                for miner, hash_rate in miners_stats.items()
            }
            
            return distribution
            
        except Exception as e:
            logger.error(f"Erreur calcul distribution hash rate: {e}")
            return {}
    
    def _analyze_network_connectivity(self) -> Dict[str, int]:
        """Analyse la connectivité réseau"""
        try:
            if not hasattr(self.blockchain, 'get_network_stats'):
                return {}
                
            network_stats = self.blockchain.get_network_stats()
            return {
                'total_nodes': network_stats.get('total_nodes', 0),
                'active_connections': network_stats.get('active_connections', 0),
                'peer_diversity': network_stats.get('peer_diversity', 0),
                'network_latency': network_stats.get('average_latency', 0)
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse connectivité: {e}")
            return {}
    
    def _analyze_transaction_patterns(self) -> Dict[str, Any]:
        """Analyse les patterns de transactions"""
        try:
            if not hasattr(self.blockchain, 'get_recent_transactions'):
                return {}
                
            recent_txs = self.blockchain.get_recent_transactions(limit=1000)
            
            # Analyser patterns
            patterns = {
                'transaction_rate': len(recent_txs),
                'average_value': self._calculate_average_transaction_value(recent_txs),
                'unique_addresses': len(set(tx.get('from_address', '') for tx in recent_txs)),
                'gas_usage_pattern': self._analyze_gas_usage(recent_txs),
                'suspicious_patterns': self._detect_suspicious_patterns(recent_txs)
            }
            
            # Stocker dans historique
            self.transaction_history.extend(recent_txs)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Erreur analyse patterns transactions: {e}")
            return {}
    
    def _analyze_consensus_participation(self) -> Dict[str, float]:
        """Analyse la participation au consensus"""
        try:
            if not hasattr(self.blockchain, 'get_consensus_stats'):
                return {}
                
            consensus_stats = self.blockchain.get_consensus_stats()
            return {
                'participation_rate': consensus_stats.get('participation_rate', 0.0),
                'validator_distribution': consensus_stats.get('validator_distribution', 0.0),
                'consensus_time': consensus_stats.get('average_consensus_time', 0.0),
                'failed_consensus_ratio': consensus_stats.get('failed_consensus_ratio', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse consensus: {e}")
            return {}
    
    def _analyze_threats(self):
        """Analyse les menaces potentielles"""
        try:
            # Détecter attaque 51%
            self._detect_51_percent_attack()
            
            # Détecter double spending
            self._detect_double_spending()
            
            # Détecter attaque Eclipse
            self._detect_eclipse_attack()
            
            # Détecter attaque Sybil
            self._detect_sybil_attack()
            
            # Détecter exploitation smart contracts
            self._detect_smart_contract_exploits()
            
            # Détecter partition réseau
            self._detect_network_partition()
            
        except Exception as e:
            logger.error(f"Erreur analyse menaces: {e}")
    
    def _detect_51_percent_attack(self):
        """Détecte les tentatives d'attaque 51%"""
        hash_distribution = self.security_metrics.hash_rate_distribution
        
        for miner, percentage in hash_distribution.items():
            if percentage > self.config['hash_rate_threshold']:
                self._create_threat_alert(
                    attack_type=AttackType.FIFTY_ONE_PERCENT,
                    threat_level=ThreatLevel.CRITICAL,
                    source_address=miner,
                    evidence={
                        'hash_rate_percentage': percentage,
                        'threshold': self.config['hash_rate_threshold'],
                        'risk_level': 'imminent_51_percent_attack'
                    }
                )
    
    def _detect_double_spending(self):
        """Détecte les tentatives de double spending"""
        recent_txs = list(self.transaction_history)[-1000:]  # 1000 dernières transactions
        
        # Grouper par UTXO
        utxo_usage = defaultdict(list)
        for tx in recent_txs:
            if 'inputs' in tx:
                for input_utxo in tx['inputs']:
                    utxo_id = f"{input_utxo.get('tx_id')}:{input_utxo.get('output_index')}"
                    utxo_usage[utxo_id].append(tx)
        
        # Détecter utilisation multiple
        for utxo_id, transactions in utxo_usage.items():
            if len(transactions) > 1:
                self._create_threat_alert(
                    attack_type=AttackType.DOUBLE_SPENDING,
                    threat_level=ThreatLevel.CRITICAL,
                    evidence={
                        'utxo_id': utxo_id,
                        'conflicting_transactions': [tx.get('tx_id') for tx in transactions],
                        'transaction_count': len(transactions)
                    }
                )
    
    def _detect_eclipse_attack(self):
        """Détecte les attaques Eclipse"""
        network_stats = self.security_metrics.network_connectivity
        
        if 'peer_diversity' in network_stats:
            peer_diversity = network_stats['peer_diversity']
            
            if peer_diversity < self.config['eclipse_detection_threshold']:
                self._create_threat_alert(
                    attack_type=AttackType.ECLIPSE,
                    threat_level=ThreatLevel.HIGH,
                    evidence={
                        'peer_diversity': peer_diversity,
                        'threshold': self.config['eclipse_detection_threshold'],
                        'isolation_risk': 'high'
                    }
                )
    
    def _detect_sybil_attack(self):
        """Détecte les attaques Sybil"""
        # Cette détection nécessiterait l'accès aux métriques de registration de nœuds
        # Implémentation simplifiée basée sur les patterns détectés
        pass
    
    def _detect_smart_contract_exploits(self):
        """Détecte les exploitations de smart contracts"""
        try:
            if not hasattr(self.blockchain, 'get_smart_contract_events'):
                return
                
            recent_events = self.blockchain.get_smart_contract_events(limit=100)
            
            # Analyser patterns suspects
            failed_calls = [event for event in recent_events if event.get('status') == 'failed']
            
            if len(failed_calls) > 10:  # Seuil d'échecs suspects
                # Grouper par signature de méthode
                method_failures = defaultdict(list)
                for event in failed_calls:
                    method_sig = event.get('method_signature', 'unknown')
                    method_failures[method_sig].append(event)
                
                for method_sig, failures in method_failures.items():
                    if len(failures) > 5:  # Seuil pour méthode spécifique
                        self._create_threat_alert(
                            attack_type=AttackType.SMART_CONTRACT_EXPLOIT,
                            threat_level=ThreatLevel.HIGH,
                            evidence={
                                'method_signature': method_sig,
                                'failure_count': len(failures),
                                'pattern': 'repeated_method_exploitation_attempt'
                            }
                        )
                        
        except Exception as e:
            logger.error(f"Erreur détection exploits smart contracts: {e}")
    
    def _detect_network_partition(self):
        """Détecte les partitions réseau"""
        network_stats = self.security_metrics.network_connectivity
        
        total_nodes = network_stats.get('total_nodes', 0)
        active_connections = network_stats.get('active_connections', 0)
        
        if total_nodes > 0:
            connectivity_ratio = active_connections / total_nodes
            
            if connectivity_ratio < (1 - self.config['network_partition_threshold']):
                self._create_threat_alert(
                    attack_type=AttackType.NETWORK_PARTITION,
                    threat_level=ThreatLevel.HIGH,
                    evidence={
                        'connectivity_ratio': connectivity_ratio,
                        'total_nodes': total_nodes,
                        'active_connections': active_connections,
                        'partition_detected': True
                    }
                )
    
    def _create_threat_alert(self, attack_type: AttackType, threat_level: ThreatLevel, 
                           source_address: Optional[str] = None, evidence: Dict = None):
        """Crée une alerte de menace"""
        alert_id = hashlib.sha256(
            f"{attack_type.value}_{threat_level.value}_{time.time()}".encode()
        ).hexdigest()[:16]
        
        alert = ThreatAlert(
            alert_id=alert_id,
            attack_type=attack_type,
            threat_level=threat_level,
            source_address=source_address,
            affected_components=self._get_affected_components(attack_type),
            evidence=evidence or {},
            timestamp=datetime.now()
        )
        
        # Stocker l'alerte
        with self._lock:
            self.active_alerts[alert_id] = alert
        
        # Déclencher réponse automatique si nécessaire
        if threat_level in [ThreatLevel.CRITICAL, ThreatLevel.EMERGENCY]:
            self._trigger_automated_response(alert)
        
        logger.warning(f"🚨 MENACE DÉTECTÉE: {attack_type.value} - Niveau: {threat_level.value}")
        
        return alert_id
    
    def _get_affected_components(self, attack_type: AttackType) -> List[str]:
        """Détermine les composants affectés par type d'attaque"""
        component_mapping = {
            AttackType.FIFTY_ONE_PERCENT: ["consensus_engine", "mining_operations"],
            AttackType.DOUBLE_SPENDING: ["transaction_pool", "block_validation"],
            AttackType.ECLIPSE: ["p2p_networking"],
            AttackType.SYBIL: ["p2p_networking", "consensus_engine"],
            AttackType.SMART_CONTRACT_EXPLOIT: ["smart_contracts"],
            AttackType.NETWORK_PARTITION: ["p2p_networking", "consensus_engine"]
        }
        
        return component_mapping.get(attack_type, ["unknown"])
    
    def _trigger_automated_response(self, alert: ThreatAlert):
        """Déclenche la réponse automatique à une menace"""
        try:
            # Activer circuit breakers pour composants affectés
            for component in alert.affected_components:
                self._trigger_circuit_breaker(component, f"Threat: {alert.attack_type.value}")
            
            # Actions spécifiques par type d'attaque
            if alert.attack_type == AttackType.FIFTY_ONE_PERCENT:
                self._respond_to_51_percent_attack(alert)
            elif alert.attack_type == AttackType.DOUBLE_SPENDING:
                self._respond_to_double_spending(alert)
            elif alert.attack_type == AttackType.SMART_CONTRACT_EXPLOIT:
                self._respond_to_smart_contract_exploit(alert)
            
            alert.auto_response_triggered = True
            logger.info(f"Réponse automatique déclenchée pour alerte {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Erreur réponse automatique: {e}")
    
    def _respond_to_51_percent_attack(self, alert: ThreatAlert):
        """Réponse spécifique à une attaque 51%"""
        # Emergency checkpoint
        if hasattr(self.blockchain, 'create_emergency_checkpoint'):
            self.blockchain.create_emergency_checkpoint()
        
        # Notification d'urgence
        self._send_emergency_notification(alert)
    
    def _respond_to_double_spending(self, alert: ThreatAlert):
        """Réponse spécifique au double spending"""
        # Augmenter le nombre de confirmations requis
        if hasattr(self.blockchain, 'increase_confirmation_requirements'):
            self.blockchain.increase_confirmation_requirements(confirmations=12)
    
    def _respond_to_smart_contract_exploit(self, alert: ThreatAlert):
        """Réponse spécifique à l'exploitation de smart contracts"""
        # Pause d'urgence des smart contracts
        if hasattr(self.blockchain, 'emergency_pause_contracts'):
            self.blockchain.emergency_pause_contracts()
    
    def _trigger_circuit_breaker(self, component: str, reason: str):
        """Déclenche un circuit breaker"""
        if component in self.circuit_breakers:
            breaker = self.circuit_breakers[component]
            breaker.state = CircuitBreakerState.OPEN
            breaker.last_failure_time = datetime.now()
            breaker.failure_count += 1
            
            logger.warning(f"🔴 Circuit breaker OUVERT pour {component}: {reason}")
    
    def _check_circuit_breakers(self):
        """Vérifie l'état des circuit breakers"""
        current_time = datetime.now()
        
        for component, breaker in self.circuit_breakers.items():
            if breaker.state == CircuitBreakerState.OPEN:
                # Vérifier si assez de temps s'est écoulé pour tenter la récupération
                if (breaker.last_failure_time and 
                    (current_time - breaker.last_failure_time).total_seconds() > breaker.recovery_timeout):
                    breaker.state = CircuitBreakerState.HALF_OPEN
                    breaker.half_open_call_count = 0
                    logger.info(f"🟡 Circuit breaker SEMI-OUVERT pour {component}")
            
            elif breaker.state == CircuitBreakerState.HALF_OPEN:
                # En mode test, vérifier la santé du composant
                if self._test_component_health(component):
                    breaker.state = CircuitBreakerState.CLOSED
                    breaker.failure_count = 0
                    logger.info(f"🟢 Circuit breaker FERMÉ pour {component} - Récupération réussie")
                else:
                    breaker.state = CircuitBreakerState.OPEN
                    breaker.last_failure_time = current_time
                    logger.warning(f"🔴 Circuit breaker RE-OUVERT pour {component} - Test échoué")
    
    def _test_component_health(self, component: str) -> bool:
        """Teste la santé d'un composant"""
        # Implémentation simplifiée - à adapter selon les composants réels
        try:
            if component == "consensus_engine":
                return hasattr(self.blockchain, 'consensus') and self.blockchain.consensus is not None
            elif component == "transaction_pool":
                return hasattr(self.blockchain, 'pending_transactions')
            elif component == "smart_contracts":
                return hasattr(self.blockchain, 'smart_contracts')
            # Autres composants...
            return True
        except:
            return False
    
    def _update_anomaly_detection(self):
        """Met à jour la détection d'anomalies basée sur l'historique"""
        try:
            # Analyser les tendances récentes
            self._analyze_transaction_rate_anomalies()
            self._analyze_consensus_time_anomalies()
            self._analyze_network_latency_anomalies()
            
        except Exception as e:
            logger.error(f"Erreur mise à jour détection anomalies: {e}")
    
    def _analyze_transaction_rate_anomalies(self):
        """Analyse les anomalies du taux de transactions"""
        if len(self.transaction_history) < 100:
            return
            
        # Calculer le taux de transactions par fenêtre temporelle
        rates = []
        window_size = 60  # 1 minute
        
        for i in range(0, len(self.transaction_history), window_size):
            window_txs = list(self.transaction_history)[i:i+window_size]
            rates.append(len(window_txs))
        
        if len(rates) >= 10:
            mean_rate = statistics.mean(rates)
            std_rate = statistics.stdev(rates) if len(rates) > 1 else 0
            current_rate = rates[-1]
            
            # Détecter anomalie (> 3 écarts-types)
            if std_rate > 0 and abs(current_rate - mean_rate) > 3 * std_rate:
                anomaly_score = abs(current_rate - mean_rate) / std_rate
                self.security_metrics.anomaly_scores['transaction_rate'] = anomaly_score
                
                if anomaly_score > 5:  # Seuil critique
                    self._create_threat_alert(
                        attack_type=AttackType.CONSENSUS_MANIPULATION,
                        threat_level=ThreatLevel.HIGH,
                        evidence={
                            'anomaly_type': 'transaction_rate',
                            'anomaly_score': anomaly_score,
                            'current_rate': current_rate,
                            'expected_rate': mean_rate
                        }
                    )
    
    def _send_emergency_notification(self, alert: ThreatAlert):
        """Envoie une notification d'urgence"""
        # Implémentation simplifiée - intégrer avec système de notification réel
        logger.critical(f"🚨 NOTIFICATION D'URGENCE: {alert.attack_type.value}")
        logger.critical(f"Niveau de menace: {alert.threat_level.value}")
        logger.critical(f"Preuves: {alert.evidence}")
    
    # Méthodes utilitaires
    def _calculate_average_transaction_value(self, transactions: List[Dict]) -> float:
        """Calcule la valeur moyenne des transactions"""
        if not transactions:
            return 0.0
            
        values = [float(tx.get('amount', 0)) for tx in transactions if 'amount' in tx]
        return statistics.mean(values) if values else 0.0
    
    def _analyze_gas_usage(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyse l'utilisation du gas"""
        if not transactions:
            return {}
            
        gas_values = [tx.get('gas_used', 0) for tx in transactions if 'gas_used' in tx]
        
        if not gas_values:
            return {}
            
        return {
            'average_gas': statistics.mean(gas_values),
            'max_gas': max(gas_values),
            'min_gas': min(gas_values),
            'gas_efficiency': len([g for g in gas_values if g < 100000]) / len(gas_values)
        }
    
    def _detect_suspicious_patterns(self, transactions: List[Dict]) -> List[str]:
        """Détecte les patterns suspects dans les transactions"""
        patterns = []
        
        # Détecter transactions de très petite valeur (dust attacks)
        dust_threshold = 0.001
        dust_count = len([tx for tx in transactions 
                         if float(tx.get('amount', 0)) < dust_threshold])
        
        if dust_count > len(transactions) * 0.5:  # Plus de 50% sont du dust
            patterns.append("potential_dust_attack")
        
        # Détecter transactions avec gas price anormalement bas/élevé
        gas_prices = [float(tx.get('gas_price', 0)) for tx in transactions 
                     if 'gas_price' in tx]
        
        if gas_prices:
            avg_gas_price = statistics.mean(gas_prices)
            anomalous_gas = [gp for gp in gas_prices 
                           if gp < avg_gas_price * 0.1 or gp > avg_gas_price * 10]
            
            if len(anomalous_gas) > len(gas_prices) * 0.2:  # Plus de 20% anormaux
                patterns.append("anomalous_gas_pricing")
        
        return patterns
    
    def _analyze_consensus_time_anomalies(self):
        """Analyse les anomalies du temps de consensus"""
        # Implémentation simplifiée
        pass
    
    def _analyze_network_latency_anomalies(self):
        """Analyse les anomalies de latence réseau"""
        # Implémentation simplifiée
        pass
    
    # API publique
    def get_security_status(self) -> Dict[str, Any]:
        """Retourne le statut de sécurité actuel"""
        with self._lock:
            return {
                'monitoring_active': self.monitoring_active,
                'active_alerts_count': len(self.active_alerts),
                'critical_alerts': [
                    alert.alert_id for alert in self.active_alerts.values() 
                    if alert.threat_level == ThreatLevel.CRITICAL
                ],
                'circuit_breakers_open': [
                    name for name, breaker in self.circuit_breakers.items()
                    if breaker.state == CircuitBreakerState.OPEN
                ],
                'security_metrics': {
                    'hash_rate_concentration': max(
                        self.security_metrics.hash_rate_distribution.values(), 
                        default=0
                    ),
                    'network_connectivity_score': self.security_metrics.network_connectivity.get(
                        'peer_diversity', 0
                    ),
                    'anomaly_scores': dict(self.security_metrics.anomaly_scores)
                }
            }
    
    def get_threat_alerts(self, resolved: bool = False) -> List[ThreatAlert]:
        """Retourne les alertes de menace"""
        with self._lock:
            return [
                alert for alert in self.active_alerts.values()
                if alert.resolved == resolved
            ]
    
    def resolve_alert(self, alert_id: str, resolution_notes: str = ""):
        """Marque une alerte comme résolue"""
        with self._lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].resolved = True
                logger.info(f"Alerte {alert_id} marquée comme résolue: {resolution_notes}")
    
    def force_circuit_breaker_reset(self, component: str):
        """Force la réinitialisation d'un circuit breaker"""
        if component in self.circuit_breakers:
            breaker = self.circuit_breakers[component]
            breaker.state = CircuitBreakerState.CLOSED
            breaker.failure_count = 0
            breaker.last_failure_time = None
            logger.info(f"Circuit breaker forcé FERMÉ pour {component}")
    
    def update_security_config(self, config_updates: Dict[str, Any]):
        """Met à jour la configuration de sécurité"""
        self.config.update(config_updates)
        logger.info(f"Configuration sécurité mise à jour: {config_updates}")


# Exemple d'utilisation
if __name__ == "__main__":
    # Configuration de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Créer instance du système de sécurité
    security_system = AdvancedBlockchainSecurity()
    
    # Démarrer la surveillance
    asyncio.run(security_system.start_monitoring())
    
    try:
        # Simulation de fonctionnement
        time.sleep(60)  # Surveiller pendant 1 minute
    except KeyboardInterrupt:
        pass
    finally:
        security_system.stop_monitoring()