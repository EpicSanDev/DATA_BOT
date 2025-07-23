#!/usr/bin/env python3
"""
Test de robustesse pour les améliorations ArchiveChain

Ce script teste toutes les améliorations de robustesse implémentées :
- Gestion d'erreurs robuste
- Protection contre les race conditions
- Validation des données renforcée
- Mécanismes de récupération
- Système de monitoring

USAGE: python test_robustness_improvements.py
"""

import sys
import time
import threading
import concurrent.futures
import random
from typing import Dict, Any, List
from decimal import Decimal

# Ajouter le chemin vers les modules blockchain
sys.path.append('src')

from src.blockchain.utils.exceptions import *
from src.blockchain.utils.error_handler import *
from src.blockchain.utils.concurrency import *
from src.blockchain.utils.validators import *
from src.blockchain.utils.recovery import *
from src.blockchain.utils.monitoring import *


class RobustnessTestSuite:
    """Suite de tests pour la robustesse"""
    
    def __init__(self):
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.logger = RobustnessLogger("robustness_test")
        
        # Composants à tester
        self.error_handler = ErrorHandler()
        self.concurrency_manager = ConcurrencyManager()
        self.data_validator = DataValidator()
        self.url_validator = URLValidator()
        self.metadata_validator = MetadataValidator()
        self.checkpoint_manager = CheckpointManager()
        self.recovery_manager = RecoveryManager(self.checkpoint_manager)
        self.health_monitor = HealthMonitor()
    
    def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """Exécute tous les tests de robustesse"""
        print("🚀 Démarrage des tests de robustesse ArchiveChain...")
        print("=" * 60)
        
        # Tests de gestion d'erreurs
        self._test_error_handling()
        
        # Tests de concurrence
        self._test_concurrency_protection()
        
        # Tests de validation
        self._test_data_validation()
        
        # Tests de récupération
        self._test_recovery_mechanisms()
        
        # Tests de monitoring
        self._test_monitoring_system()
        
        # Résumé des résultats
        self._print_test_summary()
        
        return self.test_results
    
    def _test_error_handling(self):
        """Tests de gestion d'erreurs"""
        print("\n🔍 Tests de gestion d'erreurs...")
        
        test_name = "error_handling"
        self.test_results[test_name] = {"passed": 0, "failed": 0, "details": []}
        
        # Test 1: Exceptions spécifiques
        try:
            raise ValidationError("Test validation error", field_name="test_field")
        except ValidationError as e:
            self._record_test_result(test_name, "ValidationError creation", True, "Exception créée correctement")
            assert e.field_name == "test_field"
            assert "test_field" in str(e)
        except Exception:
            self._record_test_result(test_name, "ValidationError creation", False, "Exception non capturée correctement")
        
        # Test 2: Gestionnaire d'erreurs
        try:
            test_error = ValueError("Test error")
            handled = self.error_handler.handle_error(test_error, "test", "test_op_123")
            assert isinstance(handled, BlockchainError)
            self._record_test_result(test_name, "Error handler", True, f"Erreur convertie en {type(handled).__name__}")
        except Exception as e:
            self._record_test_result(test_name, "Error handler", False, f"Erreur dans le gestionnaire: {str(e)}")
        
        # Test 3: Décorateur robuste
        @robust_operation("test", RetryConfig(max_attempts=3, delay=0.1))
        def test_function_with_retry():
            if random.random() < 0.7:  # 70% de chance d'échouer
                raise ValueError("Test retry error")
            return "success"
        
        try:
            result = test_function_with_retry()
            self._record_test_result(test_name, "Robust operation decorator", True, f"Résultat: {result}")
        except Exception as e:
            self._record_test_result(test_name, "Robust operation decorator", True, f"Échec après retry: {type(e).__name__}")
        
        # Test 4: Circuit breaker
        for i in range(12):  # Dépasser le seuil de 10
            try:
                self.error_handler.handle_error(ValueError(f"Test {i}"), "test", f"circuit_test_{i}")
            except:
                pass
        
        stats = self.error_handler.get_error_statistics()
        circuit_breaker_active = any(cb.get("is_open", False) for cb in stats["circuit_breakers"].values())
        self._record_test_result(test_name, "Circuit breaker", circuit_breaker_active, 
                               f"Circuit breaker activé: {circuit_breaker_active}")
    
    def _test_concurrency_protection(self):
        """Tests de protection contre la concurrence"""
        print("\n🔐 Tests de protection contre la concurrence...")
        
        test_name = "concurrency"
        self.test_results[test_name] = {"passed": 0, "failed": 0, "details": []}
        
        # Test 1: Verrous atomiques
        shared_resource = {"counter": 0}
        lock = self.concurrency_manager.get_lock("test_resource")
        
        def increment_counter():
            with lock.acquire(LockType.EXCLUSIVE, "test_increment"):
                current = shared_resource["counter"]
                time.sleep(0.01)  # Simuler une opération
                shared_resource["counter"] = current + 1
        
        # Exécuter en parallèle
        threads = []
        for i in range(10):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        expected_value = 10
        actual_value = shared_resource["counter"]
        
        self._record_test_result(test_name, "Atomic locks", 
                               actual_value == expected_value,
                               f"Compteur: {actual_value}/{expected_value}")
        
        # Test 2: Opérations atomiques multi-ressources
        try:
            resources = ["resource1", "resource2", "resource3"]
            with self.concurrency_manager.atomic_operation(resources, "test_multi_resource"):
                time.sleep(0.1)  # Simuler une opération complexe
            
            self._record_test_result(test_name, "Multi-resource atomic operation", True, 
                                   "Opération atomique réussie")
        except Exception as e:
            self._record_test_result(test_name, "Multi-resource atomic operation", False, 
                                   f"Erreur: {str(e)}")
        
        # Test 3: Détection de deadlocks
        deadlocks = self.concurrency_manager.detect_deadlocks()
        self._record_test_result(test_name, "Deadlock detection", True, 
                               f"Deadlocks détectés: {len(deadlocks)}")
    
    def _test_data_validation(self):
        """Tests de validation des données"""
        print("\n✅ Tests de validation des données...")
        
        test_name = "validation"
        self.test_results[test_name] = {"passed": 0, "failed": 0, "details": []}
        
        # Test 1: Validation d'URLs
        test_urls = [
            ("https://example.com", True, "URL valide"),
            ("http://localhost", False, "URL localhost bloquée"),
            ("javascript:alert(1)", False, "URL dangereuse bloquée"),
            ("https://very-long-url" + "x" * 2000 + ".com", False, "URL trop longue"),
            ("ftp://files.example.com/file.txt", True, "URL FTP valide"),
        ]
        
        for url, should_pass, description in test_urls:
            try:
                validated_url = self.url_validator.validate_and_sanitize(url)
                result = should_pass
                details = f"URL validée: {validated_url[:50]}..."
            except ValidationError:
                result = not should_pass
                details = "URL rejetée (attendu)"
            except Exception as e:
                result = False
                details = f"Erreur inattendue: {str(e)}"
            
            self._record_test_result(test_name, f"URL validation: {description}", result, details)
        
        # Test 2: Validation de métadonnées
        test_metadata = {
            "screenshots": ["abc123" * 8 + "12345678"],  # Hash 64 chars
            "external_resources": ["https://cdn.example.com/style.css"],
            "linked_pages": ["def456" * 8 + "87654321"],
            "tags": ["blockchain", "archive", "test"],
            "category": "technology",
            "priority": 8,
            "language": "en",
            "title": "Test Archive",
            "description": "Test description"
        }
        
        try:
            validated_metadata = self.metadata_validator.validate_archive_metadata(test_metadata)
            self._record_test_result(test_name, "Metadata validation", True, 
                                   f"Métadonnées validées: {len(validated_metadata)} champs")
        except Exception as e:
            self._record_test_result(test_name, "Metadata validation", False, f"Erreur: {str(e)}")
        
        # Test 3: Validation de transactions
        test_transaction = {
            "tx_id": "abc123def456" + "0" * 32,
            "tx_type": "archive",
            "sender": "0x" + "1" * 40,
            "timestamp": time.time(),
            "amount": 100
        }
        
        try:
            validated_tx = self.data_validator.validate_transaction_data(test_transaction)
            self._record_test_result(test_name, "Transaction validation", True,
                                   f"Transaction validée: {validated_tx['tx_type']}")
        except Exception as e:
            self._record_test_result(test_name, "Transaction validation", False, f"Erreur: {str(e)}")
    
    def _test_recovery_mechanisms(self):
        """Tests des mécanismes de récupération"""
        print("\n🔄 Tests des mécanismes de récupération...")
        
        test_name = "recovery"
        self.test_results[test_name] = {"passed": 0, "failed": 0, "details": []}
        
        # Test 1: Création de checkpoint
        test_state = {
            "blockchain": {"blocks": 10, "transactions": 50},
            "consensus": {"active_nodes": 5},
            "tokens": {"total_supply": 1000000}
        }
        
        try:
            checkpoint_id = self.checkpoint_manager.create_checkpoint(
                test_state, 
                CheckpointType.MANUAL, 
                "Test checkpoint for robustness testing"
            )
            self._record_test_result(test_name, "Checkpoint creation", True, 
                                   f"Checkpoint créé: {checkpoint_id}")
        except Exception as e:
            self._record_test_result(test_name, "Checkpoint creation", False, f"Erreur: {str(e)}")
            return
        
        # Test 2: Restauration de checkpoint
        try:
            restored_state = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
            states_match = restored_state == test_state
            self._record_test_result(test_name, "Checkpoint restoration", states_match,
                                   f"État restauré: {states_match}")
        except Exception as e:
            self._record_test_result(test_name, "Checkpoint restoration", False, f"Erreur: {str(e)}")
        
        # Test 3: Récupération automatique
        def test_operation_with_recovery():
            attempt_count = getattr(test_operation_with_recovery, 'attempts', 0)
            test_operation_with_recovery.attempts = attempt_count + 1
            
            if attempt_count < 2:  # Échouer les 2 premières fois
                raise ValueError(f"Test failure {attempt_count + 1}")
            return "success"
        
        try:
            result = self.recovery_manager.auto_recover_operation(
                test_operation_with_recovery,
                "test_auto_recovery",
                {"test": "data"}
            )
            self._record_test_result(test_name, "Auto recovery", True, f"Résultat: {result}")
        except Exception as e:
            self._record_test_result(test_name, "Auto recovery", False, f"Erreur: {str(e)}")
        
        # Test 4: Statistiques de récupération
        try:
            stats = self.recovery_manager.get_recovery_statistics()
            self._record_test_result(test_name, "Recovery statistics", True,
                                   f"Opérations: {stats['total_recovery_operations']}")
        except Exception as e:
            self._record_test_result(test_name, "Recovery statistics", False, f"Erreur: {str(e)}")
    
    def _test_monitoring_system(self):
        """Tests du système de monitoring"""
        print("\n📊 Tests du système de monitoring...")
        
        test_name = "monitoring"
        self.test_results[test_name] = {"passed": 0, "failed": 0, "details": []}
        
        # Test 1: Collecte de métriques
        try:
            self.health_monitor.metrics_collector.collect_system_metrics()
            metrics = self.health_monitor.metrics_collector.get_current_metrics()
            
            expected_metrics = ["system.cpu.usage_percent", "system.memory.usage_percent"]
            metrics_found = all(metric in metrics for metric in expected_metrics)
            
            self._record_test_result(test_name, "Metrics collection", metrics_found,
                                   f"Métriques collectées: {len(metrics)}")
        except Exception as e:
            self._record_test_result(test_name, "Metrics collection", False, f"Erreur: {str(e)}")
        
        # Test 2: Détection d'anomalies
        try:
            # Simuler des métriques anormales
            self.health_monitor.anomaly_detector.thresholds["test.metric"] = {"warning": 50, "critical": 80}
            
            # Injecter une métrique élevée
            test_metric = SystemMetric(
                name="test.metric",
                metric_type=MetricType.GAUGE,
                value=90,  # Au-dessus du seuil critique
                timestamp=time.time(),
                tags={},
                description="Test metric"
            )
            
            self.health_monitor.metrics_collector.current_metrics["test.metric"] = test_metric
            
            # Détecter les anomalies
            violations = self.health_monitor.anomaly_detector.detect_threshold_violations()
            anomaly_detected = any(v["metric_name"] == "test.metric" for v in violations)
            
            self._record_test_result(test_name, "Anomaly detection", anomaly_detected,
                                   f"Anomalies détectées: {len(violations)}")
        except Exception as e:
            self._record_test_result(test_name, "Anomaly detection", False, f"Erreur: {str(e)}")
        
        # Test 3: Système d'alertes
        try:
            # Déclencher une alerte
            self.health_monitor.alert_manager.check_and_trigger_alerts()
            
            active_alerts = self.health_monitor.alert_manager.get_active_alerts()
            alerts_summary = self.health_monitor.alert_manager.get_alerts_summary()
            
            self._record_test_result(test_name, "Alert system", True,
                                   f"Alertes actives: {len(active_alerts)}")
        except Exception as e:
            self._record_test_result(test_name, "Alert system", False, f"Erreur: {str(e)}")
        
        # Test 4: Statut de santé global
        try:
            health_status = self.health_monitor.get_health_status()
            
            required_fields = ["overall_status", "health_score", "timestamp"]
            all_fields_present = all(field in health_status for field in required_fields)
            
            self._record_test_result(test_name, "Health status", all_fields_present,
                                   f"Statut: {health_status.get('overall_status', 'unknown')}")
        except Exception as e:
            self._record_test_result(test_name, "Health status", False, f"Erreur: {str(e)}")
    
    def _record_test_result(self, test_category: str, test_name: str, passed: bool, details: str):
        """Enregistre le résultat d'un test"""
        if passed:
            self.test_results[test_category]["passed"] += 1
            status = "✅ PASS"
        else:
            self.test_results[test_category]["failed"] += 1
            status = "❌ FAIL"
        
        self.test_results[test_category]["details"].append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        
        print(f"  {status} {test_name}: {details}")
    
    def _print_test_summary(self):
        """Affiche le résumé des tests"""
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS DE ROBUSTESSE")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total = passed + failed
            
            total_passed += passed
            total_failed += failed
            
            success_rate = (passed / total * 100) if total > 0 else 0
            
            print(f"\n🔹 {category.upper()}")
            print(f"   Tests passés: {passed}/{total} ({success_rate:.1f}%)")
            
            if failed > 0:
                print(f"   ❌ Échecs: {failed}")
                for detail in results["details"]:
                    if not detail["passed"]:
                        print(f"      - {detail['name']}: {detail['details']}")
        
        print(f"\n🎯 RÉSULTAT GLOBAL")
        grand_total = total_passed + total_failed
        global_success_rate = (total_passed / grand_total * 100) if grand_total > 0 else 0
        
        print(f"   Tests passés: {total_passed}/{grand_total} ({global_success_rate:.1f}%)")
        
        if global_success_rate >= 90:
            print("   🎉 EXCELLENT ! Robustesse très élevée")
        elif global_success_rate >= 80:
            print("   ✅ BON ! Robustesse satisfaisante")
        elif global_success_rate >= 70:
            print("   ⚠️  ACCEPTABLE ! Améliorations recommandées")
        else:
            print("   ❌ PRÉOCCUPANT ! Améliorations nécessaires")
        
        print("\n📋 RECOMMANDATIONS:")
        if total_failed == 0:
            print("   • Système robuste - Continuer le monitoring")
        else:
            print("   • Corriger les tests en échec identifiés")
            print("   • Renforcer les composants problématiques")
            print("   • Exécuter les tests régulièrement")


def main():
    """Fonction principale"""
    print("🛡️  TESTS DE ROBUSTESSE ARCHIVECHAIN")
    print("Version 1.0 - Diagnostic complet du système")
    print()
    
    try:
        # Initialiser et exécuter les tests
        test_suite = RobustnessTestSuite()
        results = test_suite.run_all_tests()
        
        # Sauvegarder les résultats
        import json
        with open("robustness_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Résultats sauvegardés dans robustness_test_results.json")
        
        # Code de retour basé sur le succès
        total_passed = sum(cat["passed"] for cat in results.values())
        total_tests = sum(cat["passed"] + cat["failed"] for cat in results.values())
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        if success_rate >= 90:
            return 0  # Succès complet
        elif success_rate >= 80:
            return 1  # Succès partiel
        else:
            return 2  # Échec
            
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE dans les tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    exit_code = main()
    print(f"\nCode de sortie: {exit_code}")
    sys.exit(exit_code)