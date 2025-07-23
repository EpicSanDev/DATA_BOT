"""
Système de monitoring et alertes pour ArchiveChain

Ce module fournit un monitoring complet de la santé du système,
détection d'anomalies, et système d'alertes automatiques.

SÉCURITÉ: Toutes les métriques sensibles sont automatiquement masquées
"""

import time
import threading
import psutil
import json
import statistics
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
from datetime import datetime, timedelta

from .exceptions import BlockchainError
from .error_handler import RobustnessLogger


class AlertSeverity(Enum):
    """Niveaux de sévérité des alertes"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types de métriques"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """Alerte système"""
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    component: str
    metric_name: str
    current_value: Any
    threshold_value: Any
    triggered_at: float
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = asdict(self)
        data['severity'] = self.severity.value
        return data
    
    def is_resolved(self) -> bool:
        """Vérifie si l'alerte est résolue"""
        return self.resolved_at is not None


@dataclass
class SystemMetric:
    """Métrique système"""
    name: str
    metric_type: MetricType
    value: Union[int, float]
    timestamp: float
    tags: Dict[str, str]
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        return data


class MetricsCollector:
    """Collecteur de métriques système"""
    
    def __init__(self, collection_interval: float = 60.0):
        self.collection_interval = collection_interval
        self.logger = RobustnessLogger("metrics_collector")
        
        # Stockage des métriques
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.current_metrics: Dict[str, SystemMetric] = {}
        self.metrics_lock = threading.RLock()
        
        # Thread de collecte
        self.collection_thread: Optional[threading.Thread] = None
        self.collection_running = False
        
        # Métriques personnalisées
        self.custom_metrics: Dict[str, Callable[[], Union[int, float]]] = {}
    
    def start_collection(self):
        """Démarre la collecte automatique de métriques"""
        if self.collection_running:
            return
        
        self.collection_running = True
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="MetricsCollector"
        )
        self.collection_thread.start()
        
        self.logger.info(
            "Metrics collection started",
            context={"collection_interval": self.collection_interval}
        )
    
    def stop_collection(self):
        """Arrête la collecte automatique"""
        self.collection_running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5.0)
        
        self.logger.info("Metrics collection stopped")
    
    def _collection_loop(self):
        """Boucle de collecte des métriques"""
        while self.collection_running:
            try:
                self.collect_system_metrics()
                self.collect_blockchain_metrics()
                self.collect_custom_metrics()
                
            except Exception as e:
                self.logger.error(
                    "Error in metrics collection",
                    context={"error": str(e)},
                    exception=e
                )
            
            time.sleep(self.collection_interval)
    
    def collect_system_metrics(self):
        """Collecte les métriques système"""
        timestamp = time.time()
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self._store_metric("system.cpu.usage_percent", cpu_percent, MetricType.GAUGE, timestamp)
            
            # Mémoire
            memory = psutil.virtual_memory()
            self._store_metric("system.memory.usage_percent", memory.percent, MetricType.GAUGE, timestamp)
            self._store_metric("system.memory.available_bytes", memory.available, MetricType.GAUGE, timestamp)
            self._store_metric("system.memory.used_bytes", memory.used, MetricType.GAUGE, timestamp)
            
            # Disque
            disk = psutil.disk_usage('/')
            self._store_metric("system.disk.usage_percent", (disk.used / disk.total) * 100, MetricType.GAUGE, timestamp)
            self._store_metric("system.disk.free_bytes", disk.free, MetricType.GAUGE, timestamp)
            
            # Réseau
            network = psutil.net_io_counters()
            self._store_metric("system.network.bytes_sent", network.bytes_sent, MetricType.COUNTER, timestamp)
            self._store_metric("system.network.bytes_recv", network.bytes_recv, MetricType.COUNTER, timestamp)
            
            # Processus
            process_count = len(psutil.pids())
            self._store_metric("system.process.count", process_count, MetricType.GAUGE, timestamp)
            
        except Exception as e:
            self.logger.warning(
                "Failed to collect some system metrics",
                context={"error": str(e)},
                exception=e
            )
    
    def collect_blockchain_metrics(self):
        """Collecte les métriques blockchain (à implémenter selon le contexte)"""
        timestamp = time.time()
        
        # Ces métriques seraient collectées depuis les composants blockchain
        # Pour l'instant, on simule quelques métriques de base
        
        # Simulation de métriques blockchain
        self._store_metric("blockchain.blocks.total", 0, MetricType.GAUGE, timestamp)
        self._store_metric("blockchain.transactions.pending", 0, MetricType.GAUGE, timestamp)
        self._store_metric("blockchain.nodes.active", 0, MetricType.GAUGE, timestamp)
        self._store_metric("blockchain.consensus.score", 0.0, MetricType.GAUGE, timestamp)
    
    def collect_custom_metrics(self):
        """Collecte les métriques personnalisées"""
        timestamp = time.time()
        
        for metric_name, collector_func in self.custom_metrics.items():
            try:
                value = collector_func()
                self._store_metric(f"custom.{metric_name}", value, MetricType.GAUGE, timestamp)
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to collect custom metric: {metric_name}",
                    context={"metric_name": metric_name, "error": str(e)},
                    exception=e
                )
    
    def add_custom_metric(self, name: str, collector_func: Callable[[], Union[int, float]]):
        """Ajoute une métrique personnalisée"""
        self.custom_metrics[name] = collector_func
        
        self.logger.debug(
            f"Custom metric added: {name}",
            context={"metric_name": name}
        )
    
    def _store_metric(self, name: str, value: Union[int, float], 
                     metric_type: MetricType, timestamp: float):
        """Stocke une métrique"""
        with self.metrics_lock:
            metric = SystemMetric(
                name=name,
                metric_type=metric_type,
                value=value,
                timestamp=timestamp,
                tags={},
                description=""
            )
            
            self.current_metrics[name] = metric
            self.metrics_history[name].append(metric)
    
    def get_current_metrics(self) -> Dict[str, SystemMetric]:
        """Retourne les métriques actuelles"""
        with self.metrics_lock:
            return self.current_metrics.copy()
    
    def get_metric_history(self, metric_name: str, 
                          duration_seconds: Optional[float] = None) -> List[SystemMetric]:
        """Retourne l'historique d'une métrique"""
        with self.metrics_lock:
            if metric_name not in self.metrics_history:
                return []
            
            history = list(self.metrics_history[metric_name])
            
            if duration_seconds is not None:
                cutoff_time = time.time() - duration_seconds
                history = [m for m in history if m.timestamp >= cutoff_time]
            
            return history
    
    def get_metric_statistics(self, metric_name: str, 
                            duration_seconds: float = 3600) -> Dict[str, float]:
        """Calcule les statistiques d'une métrique"""
        history = self.get_metric_history(metric_name, duration_seconds)
        
        if not history:
            return {}
        
        values = [m.value for m in history]
        
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "count": len(values),
            "latest": values[-1] if values else 0
        }


class AnomalyDetector:
    """Détecteur d'anomalies pour les métriques"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.logger = RobustnessLogger("anomaly_detector")
        
        # Configuration de détection
        self.thresholds = {
            "system.cpu.usage_percent": {"warning": 80, "critical": 95},
            "system.memory.usage_percent": {"warning": 85, "critical": 95},
            "system.disk.usage_percent": {"warning": 80, "critical": 90},
        }
        
        # Détection de tendances
        self.trend_windows = {
            "short": 300,   # 5 minutes
            "medium": 1800, # 30 minutes
            "long": 3600    # 1 heure
        }
        
        # Historique des anomalies
        self.detected_anomalies: List[Dict[str, Any]] = []
    
    def detect_threshold_violations(self) -> List[Dict[str, Any]]:
        """Détecte les violations de seuils"""
        violations = []
        current_metrics = self.metrics_collector.get_current_metrics()
        
        for metric_name, metric in current_metrics.items():
            if metric_name in self.thresholds:
                thresholds = self.thresholds[metric_name]
                
                violation = None
                
                if "critical" in thresholds and metric.value >= thresholds["critical"]:
                    violation = {
                        "type": "threshold_violation",
                        "severity": AlertSeverity.CRITICAL,
                        "metric_name": metric_name,
                        "current_value": metric.value,
                        "threshold_value": thresholds["critical"],
                        "threshold_type": "critical"
                    }
                elif "warning" in thresholds and metric.value >= thresholds["warning"]:
                    violation = {
                        "type": "threshold_violation",
                        "severity": AlertSeverity.WARNING,
                        "metric_name": metric_name,
                        "current_value": metric.value,
                        "threshold_value": thresholds["warning"],
                        "threshold_type": "warning"
                    }
                
                if violation:
                    violations.append(violation)
        
        return violations
    
    def detect_trend_anomalies(self) -> List[Dict[str, Any]]:
        """Détecte les anomalies de tendance"""
        anomalies = []
        
        for metric_name in ["system.cpu.usage_percent", "system.memory.usage_percent"]:
            try:
                # Analyser la tendance sur différentes fenêtres
                short_stats = self.metrics_collector.get_metric_statistics(
                    metric_name, self.trend_windows["short"]
                )
                long_stats = self.metrics_collector.get_metric_statistics(
                    metric_name, self.trend_windows["long"]
                )
                
                if not short_stats or not long_stats:
                    continue
                
                # Détecter une augmentation rapide
                if (short_stats["mean"] > long_stats["mean"] * 1.5 and 
                    short_stats["mean"] > 50):
                    
                    anomalies.append({
                        "type": "rapid_increase",
                        "severity": AlertSeverity.WARNING,
                        "metric_name": metric_name,
                        "short_term_avg": short_stats["mean"],
                        "long_term_avg": long_stats["mean"],
                        "increase_ratio": short_stats["mean"] / long_stats["mean"]
                    })
                
                # Détecter une variance élevée (instabilité)
                if short_stats["std_dev"] > long_stats["mean"] * 0.3:
                    anomalies.append({
                        "type": "high_variance",
                        "severity": AlertSeverity.INFO,
                        "metric_name": metric_name,
                        "variance": short_stats["std_dev"],
                        "mean": short_stats["mean"]
                    })
                    
            except Exception as e:
                self.logger.warning(
                    f"Failed to analyze trends for {metric_name}",
                    context={"metric_name": metric_name, "error": str(e)},
                    exception=e
                )
        
        return anomalies
    
    def detect_all_anomalies(self) -> List[Dict[str, Any]]:
        """Détecte toutes les anomalies"""
        all_anomalies = []
        
        # Violations de seuils
        all_anomalies.extend(self.detect_threshold_violations())
        
        # Anomalies de tendance
        all_anomalies.extend(self.detect_trend_anomalies())
        
        # Stocker l'historique
        for anomaly in all_anomalies:
            anomaly["detected_at"] = time.time()
            self.detected_anomalies.append(anomaly)
        
        # Limiter l'historique
        if len(self.detected_anomalies) > 1000:
            self.detected_anomalies = self.detected_anomalies[-1000:]
        
        return all_anomalies
    
    def add_threshold(self, metric_name: str, warning: Optional[float] = None, 
                     critical: Optional[float] = None):
        """Ajoute un seuil personnalisé"""
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = {}
        
        if warning is not None:
            self.thresholds[metric_name]["warning"] = warning
        if critical is not None:
            self.thresholds[metric_name]["critical"] = critical
        
        self.logger.info(
            f"Threshold added for metric: {metric_name}",
            context={
                "metric_name": metric_name,
                "warning": warning,
                "critical": critical
            }
        )


class AlertManager:
    """Gestionnaire d'alertes"""
    
    def __init__(self, anomaly_detector: AnomalyDetector):
        self.anomaly_detector = anomaly_detector
        self.logger = RobustnessLogger("alert_manager")
        
        # Alertes actives
        self.active_alerts: Dict[str, Alert] = {}
        self.alerts_history: List[Alert] = []
        self.alerts_lock = threading.RLock()
        
        # Configuration
        self.alert_config = {
            "cooldown_period": 300,  # 5 minutes entre alertes similaires
            "auto_resolve_timeout": 1800,  # 30 minutes pour auto-résolution
            "max_alerts_history": 1000
        }
        
        # Callbacks d'alerte
        self.alert_callbacks: List[Callable[[Alert], None]] = []
    
    def check_and_trigger_alerts(self):
        """Vérifie et déclenche les alertes nécessaires"""
        anomalies = self.anomaly_detector.detect_all_anomalies()
        
        for anomaly in anomalies:
            self._process_anomaly(anomaly)
        
        # Auto-résoudre les alertes anciennes
        self._auto_resolve_alerts()
    
    def _process_anomaly(self, anomaly: Dict[str, Any]):
        """Traite une anomalie et déclenche une alerte si nécessaire"""
        # Générer un ID d'alerte unique
        alert_id = self._generate_alert_id(anomaly)
        
        with self.alerts_lock:
            # Vérifier si l'alerte existe déjà
            if alert_id in self.active_alerts:
                # Mettre à jour l'alerte existante
                existing_alert = self.active_alerts[alert_id]
                existing_alert.current_value = anomaly.get("current_value", anomaly.get("short_term_avg", "unknown"))
                return
            
            # Vérifier le cooldown
            if self._is_in_cooldown(anomaly):
                return
            
            # Créer une nouvelle alerte
            alert = Alert(
                alert_id=alert_id,
                severity=anomaly.get("severity", AlertSeverity.WARNING),
                title=self._generate_alert_title(anomaly),
                description=self._generate_alert_description(anomaly),
                component="system",
                metric_name=anomaly["metric_name"],
                current_value=anomaly.get("current_value", anomaly.get("short_term_avg", "unknown")),
                threshold_value=anomaly.get("threshold_value", "N/A"),
                triggered_at=time.time()
            )
            
            # Stocker l'alerte
            self.active_alerts[alert_id] = alert
            self.alerts_history.append(alert)
            
            # Déclencher les callbacks
            self._trigger_alert_callbacks(alert)
            
            self.logger.warning(
                f"Alert triggered: {alert.title}",
                context={
                    "alert_id": alert_id,
                    "severity": alert.severity.value,
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value
                }
            )
    
    def _generate_alert_id(self, anomaly: Dict[str, Any]) -> str:
        """Génère un ID unique pour l'alerte"""
        import hashlib
        
        # Utiliser le nom de métrique et le type d'anomalie
        key_data = f"{anomaly['metric_name']}:{anomaly['type']}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def _generate_alert_title(self, anomaly: Dict[str, Any]) -> str:
        """Génère le titre de l'alerte"""
        metric_name = anomaly["metric_name"]
        anomaly_type = anomaly["type"]
        
        if anomaly_type == "threshold_violation":
            threshold_type = anomaly.get("threshold_type", "unknown")
            return f"{threshold_type.title()} threshold violation: {metric_name}"
        elif anomaly_type == "rapid_increase":
            return f"Rapid increase detected: {metric_name}"
        elif anomaly_type == "high_variance":
            return f"High variance detected: {metric_name}"
        else:
            return f"Anomaly detected: {metric_name}"
    
    def _generate_alert_description(self, anomaly: Dict[str, Any]) -> str:
        """Génère la description de l'alerte"""
        metric_name = anomaly["metric_name"]
        anomaly_type = anomaly["type"]
        
        if anomaly_type == "threshold_violation":
            current = anomaly.get("current_value", "unknown")
            threshold = anomaly.get("threshold_value", "unknown")
            return f"Metric {metric_name} has value {current}, exceeding threshold of {threshold}"
        elif anomaly_type == "rapid_increase":
            short_avg = anomaly.get("short_term_avg", "unknown")
            long_avg = anomaly.get("long_term_avg", "unknown")
            return f"Metric {metric_name} increased rapidly: short-term avg {short_avg} vs long-term avg {long_avg}"
        elif anomaly_type == "high_variance":
            variance = anomaly.get("variance", "unknown")
            return f"Metric {metric_name} shows high variance: {variance}"
        else:
            return f"Anomaly detected in metric {metric_name}"
    
    def _is_in_cooldown(self, anomaly: Dict[str, Any]) -> bool:
        """Vérifie si l'anomalie est en période de cooldown"""
        metric_name = anomaly["metric_name"]
        current_time = time.time()
        cooldown = self.alert_config["cooldown_period"]
        
        # Chercher les alertes récentes pour cette métrique
        for alert in reversed(self.alerts_history[-50:]):  # Vérifier les 50 dernières
            if (alert.metric_name == metric_name and 
                current_time - alert.triggered_at < cooldown):
                return True
        
        return False
    
    def _auto_resolve_alerts(self):
        """Résout automatiquement les alertes anciennes"""
        current_time = time.time()
        timeout = self.alert_config["auto_resolve_timeout"]
        
        with self.alerts_lock:
            alerts_to_resolve = []
            
            for alert_id, alert in self.active_alerts.items():
                if current_time - alert.triggered_at > timeout:
                    alerts_to_resolve.append(alert_id)
            
            for alert_id in alerts_to_resolve:
                self.resolve_alert(alert_id, "Auto-resolved due to timeout")
    
    def resolve_alert(self, alert_id: str, reason: str = "Manual resolution"):
        """Résout une alerte"""
        with self.alerts_lock:
            if alert_id not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_id]
            alert.resolved_at = time.time()
            
            del self.active_alerts[alert_id]
            
            self.logger.info(
                f"Alert resolved: {alert.title}",
                context={
                    "alert_id": alert_id,
                    "reason": reason,
                    "duration": alert.resolved_at - alert.triggered_at
                }
            )
            
            return True
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Ajoute un callback d'alerte"""
        self.alert_callbacks.append(callback)
    
    def _trigger_alert_callbacks(self, alert: Alert):
        """Déclenche les callbacks d'alerte"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(
                    f"Alert callback failed",
                    context={
                        "alert_id": alert.alert_id,
                        "callback": str(callback),
                        "error": str(e)
                    },
                    exception=e
                )
    
    def get_active_alerts(self) -> List[Alert]:
        """Retourne les alertes actives"""
        with self.alerts_lock:
            return list(self.active_alerts.values())
    
    def get_alerts_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des alertes"""
        with self.alerts_lock:
            active_alerts = list(self.active_alerts.values())
            
            severity_counts = {severity.value: 0 for severity in AlertSeverity}
            for alert in active_alerts:
                severity_counts[alert.severity.value] += 1
            
            return {
                "total_active_alerts": len(active_alerts),
                "severity_breakdown": severity_counts,
                "total_alerts_history": len(self.alerts_history),
                "oldest_active_alert": min([a.triggered_at for a in active_alerts]) if active_alerts else None,
                "latest_alert": max([a.triggered_at for a in self.alerts_history]) if self.alerts_history else None
            }


class HealthMonitor:
    """Moniteur de santé global du système"""
    
    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self.logger = RobustnessLogger("health_monitor")
        
        # Composants
        self.metrics_collector = MetricsCollector(collection_interval=30.0)
        self.anomaly_detector = AnomalyDetector(self.metrics_collector)
        self.alert_manager = AlertManager(self.anomaly_detector)
        
        # Thread de monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_running = False
        
        # Callbacks de santé
        self.health_callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    def start_monitoring(self):
        """Démarre le monitoring complet"""
        if self.monitoring_running:
            return
        
        # Démarrer les composants
        self.metrics_collector.start_collection()
        
        self.monitoring_running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="HealthMonitor"
        )
        self.monitoring_thread.start()
        
        self.logger.info(
            "Health monitoring started",
            context={"check_interval": self.check_interval}
        )
    
    def stop_monitoring(self):
        """Arrête le monitoring"""
        self.monitoring_running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        
        self.metrics_collector.stop_collection()
        
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Boucle de monitoring principal"""
        while self.monitoring_running:
            try:
                # Vérifier et déclencher les alertes
                self.alert_manager.check_and_trigger_alerts()
                
                # Calculer la santé globale
                health_status = self.get_health_status()
                
                # Déclencher les callbacks de santé
                self._trigger_health_callbacks(health_status)
                
            except Exception as e:
                self.logger.error(
                    "Error in monitoring loop",
                    context={"error": str(e)},
                    exception=e
                )
            
            time.sleep(self.check_interval)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Calcule et retourne le statut de santé global"""
        current_metrics = self.metrics_collector.get_current_metrics()
        active_alerts = self.alert_manager.get_active_alerts()
        alerts_summary = self.alert_manager.get_alerts_summary()
        
        # Calculer le score de santé (0-100)
        health_score = self._calculate_health_score(current_metrics, active_alerts)
        
        # Déterminer le statut global
        if health_score >= 90:
            overall_status = "healthy"
        elif health_score >= 70:
            overall_status = "warning"
        elif health_score >= 50:
            overall_status = "degraded"
        else:
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "health_score": health_score,
            "timestamp": time.time(),
            "active_alerts_count": len(active_alerts),
            "critical_alerts_count": sum(1 for a in active_alerts if a.severity == AlertSeverity.CRITICAL),
            "system_metrics": {
                "cpu_usage": current_metrics.get("system.cpu.usage_percent", {}).value if "system.cpu.usage_percent" in current_metrics else None,
                "memory_usage": current_metrics.get("system.memory.usage_percent", {}).value if "system.memory.usage_percent" in current_metrics else None,
                "disk_usage": current_metrics.get("system.disk.usage_percent", {}).value if "system.disk.usage_percent" in current_metrics else None,
            },
            "alerts_summary": alerts_summary
        }
    
    def _calculate_health_score(self, metrics: Dict[str, SystemMetric], 
                               alerts: List[Alert]) -> int:
        """Calcule le score de santé du système"""
        base_score = 100
        
        # Pénalités pour les alertes
        for alert in alerts:
            if alert.severity == AlertSeverity.CRITICAL:
                base_score -= 20
            elif alert.severity == AlertSeverity.ERROR:
                base_score -= 10
            elif alert.severity == AlertSeverity.WARNING:
                base_score -= 5
        
        # Pénalités pour les métriques système
        if "system.cpu.usage_percent" in metrics:
            cpu_usage = metrics["system.cpu.usage_percent"].value
            if cpu_usage > 95:
                base_score -= 15
            elif cpu_usage > 80:
                base_score -= 5
        
        if "system.memory.usage_percent" in metrics:
            memory_usage = metrics["system.memory.usage_percent"].value
            if memory_usage > 95:
                base_score -= 15
            elif memory_usage > 85:
                base_score -= 5
        
        return max(0, min(100, base_score))
    
    def add_health_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Ajoute un callback de santé"""
        self.health_callbacks.append(callback)
    
    def _trigger_health_callbacks(self, health_status: Dict[str, Any]):
        """Déclenche les callbacks de santé"""
        for callback in self.health_callbacks:
            try:
                callback(health_status)
            except Exception as e:
                self.logger.error(
                    f"Health callback failed",
                    context={
                        "callback": str(callback),
                        "error": str(e)
                    },
                    exception=e
                )
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Retourne un statut complet du système"""
        return {
            "health_status": self.get_health_status(),
            "current_metrics": {
                name: metric.to_dict() 
                for name, metric in self.metrics_collector.get_current_metrics().items()
            },
            "active_alerts": [alert.to_dict() for alert in self.alert_manager.get_active_alerts()],
            "system_info": {
                "monitoring_running": self.monitoring_running,
                "collection_interval": self.metrics_collector.collection_interval,
                "check_interval": self.check_interval,
                "uptime": time.time() - (time.time() if not hasattr(self, '_start_time') else self._start_time)
            }
        }


# Instance globale du moniteur de santé
global_health_monitor = HealthMonitor()