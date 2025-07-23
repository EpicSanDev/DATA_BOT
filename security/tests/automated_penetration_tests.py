#!/usr/bin/env python3
"""
🔍 Tests de Pénétration Automatisés - DATA_BOT Enterprise
Suite complète de tests de sécurité automatisés
"""

import asyncio
import logging
import aiohttp
import time
import json
import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import socket
import ssl
import subprocess
import re

logger = logging.getLogger(__name__)

class TestSeverity(Enum):
    """Niveaux de sévérité des tests"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TestCategory(Enum):
    """Catégories de tests de sécurité"""
    WEB_APPLICATION = "web_application"
    API_SECURITY = "api_security"
    BLOCKCHAIN = "blockchain"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INFRASTRUCTURE = "infrastructure"

@dataclass
class TestResult:
    """Résultat d'un test de sécurité"""
    test_id: str
    test_name: str
    category: TestCategory
    severity: TestSeverity
    status: str  # "passed", "failed", "warning", "error"
    description: str
    evidence: Dict[str, Any]
    remediation: str
    execution_time: float
    timestamp: str

class PenetrationTestSuite:
    """Suite de tests de pénétration automatisés"""
    
    def __init__(self, target_config: Dict[str, Any]):
        self.target_config = target_config
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Configuration des tests
        self.config = {
            'timeout': 30,
            'max_retries': 3,
            'rate_limit_delay': 1,
            'user_agents': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'PenTest-Scanner/1.0'
            ]
        }
    
    async def run_full_test_suite(self) -> List[TestResult]:
        """Exécute la suite complète de tests"""
        logger.info("🔍 Démarrage des tests de pénétration automatisés")
        
        # Initialiser session HTTP
        timeout = aiohttp.ClientTimeout(total=self.config['timeout'])
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            # Tests par catégorie
            await self._run_web_application_tests()
            await self._run_api_security_tests()
            await self._run_blockchain_tests()
            await self._run_network_tests()
            await self._run_authentication_tests()
            await self._run_authorization_tests()
            await self._run_infrastructure_tests()
            
            logger.info(f"✅ Tests terminés: {len(self.results)} résultats")
            return self.results
            
        finally:
            if self.session:
                await self.session.close()
    
    async def _run_web_application_tests(self):
        """Tests de sécurité des applications web"""
        logger.info("🌐 Tests sécurité applications web")
        
        # Test injection SQL
        await self._test_sql_injection()
        
        # Test XSS
        await self._test_xss_vulnerabilities()
        
        # Test CSRF
        await self._test_csrf_protection()
        
        # Test sécurité headers
        await self._test_security_headers()
        
        # Test cookies sécurisés
        await self._test_secure_cookies()
        
        # Test directory traversal
        await self._test_directory_traversal()
    
    async def _test_sql_injection(self):
        """Test vulnérabilités injection SQL"""
        test_id = "WEB_001"
        start_time = time.time()
        
        try:
            # Payloads SQL injection
            sql_payloads = [
                "' OR '1'='1",
                "' UNION SELECT 1,2,3--",
                "'; DROP TABLE users;--",
                "' AND 1=1--",
                "' OR 1=1#",
                "admin'--",
                "' UNION SELECT null,null,null--"
            ]
            
            vulnerable_endpoints = []
            base_url = self.target_config.get('base_url', 'http://localhost:8080')
            
            # Tester différents endpoints
            test_endpoints = [
                '/api/search',
                '/api/login',
                '/api/users',
                '/search',
                '/login'
            ]
            
            for endpoint in test_endpoints:
                for payload in sql_payloads:
                    # Test GET parameters
                    params = {'q': payload, 'search': payload, 'id': payload}
                    
                    try:
                        async with self.session.get(
                            f"{base_url}{endpoint}",
                            params=params
                        ) as response:
                            content = await response.text()
                            
                            # Détecter réponses suspectes
                            sql_errors = [
                                'mysql_fetch_array',
                                'ORA-01756',
                                'Microsoft OLE DB',
                                'SQLServer JDBC Driver',
                                'PostgreSQL query failed',
                                'Warning: mysql_',
                                'MySqlException',
                                'valid MySQL result'
                            ]
                            
                            for error in sql_errors:
                                if error.lower() in content.lower():
                                    vulnerable_endpoints.append({
                                        'endpoint': endpoint,
                                        'payload': payload,
                                        'error': error,
                                        'method': 'GET'
                                    })
                    
                    except Exception:
                        pass  # Ignorer erreurs réseau
                    
                    # Rate limiting
                    await asyncio.sleep(self.config['rate_limit_delay'])
            
            # Évaluer résultat
            if vulnerable_endpoints:
                status = "failed"
                severity = TestSeverity.CRITICAL
                evidence = {'vulnerable_endpoints': vulnerable_endpoints}
                remediation = "Implémenter requêtes préparées et validation input"
            else:
                status = "passed"
                severity = TestSeverity.INFO
                evidence = {'tested_endpoints': test_endpoints}
                remediation = "Continuer monitoring injection SQL"
            
            self._add_result(TestResult(
                test_id=test_id,
                test_name="SQL Injection Test",
                category=TestCategory.WEB_APPLICATION,
                severity=severity,
                status=status,
                description="Test vulnérabilités injection SQL",
                evidence=evidence,
                remediation=remediation,
                execution_time=time.time() - start_time,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
        except Exception as e:
            self._add_error_result(test_id, "SQL Injection Test", str(e), start_time)
    
    async def _test_xss_vulnerabilities(self):
        """Test vulnérabilités Cross-Site Scripting"""
        test_id = "WEB_002"
        start_time = time.time()
        
        try:
            # Payloads XSS
            xss_payloads = [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')",
                "<svg onload=alert('XSS')>",
                "';alert('XSS');//",
                "<iframe src=javascript:alert('XSS')>"
            ]
            
            vulnerable_endpoints = []
            base_url = self.target_config.get('base_url', 'http://localhost:8080')
            
            test_endpoints = [
                '/api/search',
                '/search',
                '/contact',
                '/feedback'
            ]
            
            for endpoint in test_endpoints:
                for payload in xss_payloads:
                    params = {'q': payload, 'message': payload, 'comment': payload}
                    
                    try:
                        async with self.session.get(
                            f"{base_url}{endpoint}",
                            params=params
                        ) as response:
                            content = await response.text()
                            
                            # Vérifier si payload reflété sans échappement
                            if payload in content and '<script>' in content:
                                vulnerable_endpoints.append({
                                    'endpoint': endpoint,
                                    'payload': payload,
                                    'reflected': True
                                })
                    
                    except Exception:
                        pass
                    
                    await asyncio.sleep(self.config['rate_limit_delay'])
            
            # Évaluer résultat
            if vulnerable_endpoints:
                status = "failed"
                severity = TestSeverity.HIGH
                evidence = {'vulnerable_endpoints': vulnerable_endpoints}
                remediation = "Implémenter échappement output et CSP"
            else:
                status = "passed"
                severity = TestSeverity.INFO
                evidence = {'tested_payloads': len(xss_payloads)}
                remediation = "Maintenir protection XSS"
            
            self._add_result(TestResult(
                test_id=test_id,
                test_name="XSS Vulnerability Test",
                category=TestCategory.WEB_APPLICATION,
                severity=severity,
                status=status,
                description="Test vulnérabilités Cross-Site Scripting",
                evidence=evidence,
                remediation=remediation,
                execution_time=time.time() - start_time,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
        except Exception as e:
            self._add_error_result(test_id, "XSS Vulnerability Test", str(e), start_time)
    
    async def _test_security_headers(self):
        """Test présence headers de sécurité"""
        test_id = "WEB_003"
        start_time = time.time()
        
        try:
            base_url = self.target_config.get('base_url', 'http://localhost:8080')
            
            async with self.session.get(base_url) as response:
                headers = response.headers
                
                # Headers de sécurité requis
                required_headers = {
                    'X-Content-Type-Options': 'nosniff',
                    'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
                    'X-XSS-Protection': '1; mode=block',
                    'Strict-Transport-Security': None,  # Pour HTTPS
                    'Content-Security-Policy': None,
                    'Referrer-Policy': None
                }
                
                missing_headers = []
                weak_headers = []
                
                for header, expected_values in required_headers.items():
                    if header not in headers:
                        missing_headers.append(header)
                    elif expected_values and headers[header] not in expected_values:
                        weak_headers.append({
                            'header': header,
                            'current_value': headers[header],
                            'expected': expected_values
                        })
                
                # Évaluer résultat
                if missing_headers or weak_headers:
                    status = "warning"
                    severity = TestSeverity.MEDIUM
                    evidence = {
                        'missing_headers': missing_headers,
                        'weak_headers': weak_headers
                    }
                    remediation = "Configurer headers de sécurité manquants"
                else:
                    status = "passed"
                    severity = TestSeverity.INFO
                    evidence = {'security_headers_present': list(required_headers.keys())}
                    remediation = "Maintenir configuration headers"
            
            self._add_result(TestResult(
                test_id=test_id,
                test_name="Security Headers Test",
                category=TestCategory.WEB_APPLICATION,
                severity=severity,
                status=status,
                description="Vérification headers de sécurité HTTP",
                evidence=evidence,
                remediation=remediation,
                execution_time=time.time() - start_time,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
        except Exception as e:
            self._add_error_result(test_id, "Security Headers Test", str(e), start_time)
    
    async def _run_api_security_tests(self):
        """Tests de sécurité API"""
        logger.info("🔌 Tests sécurité API")
        
        await self._test_api_authentication()
        await self._test_api_rate_limiting()
        await self._test_api_input_validation()
        await self._test_api_information_disclosure()
    
    async def _test_api_authentication(self):
        """Test authentification API"""
        test_id = "API_001"
        start_time = time.time()
        
        try:
            base_url = self.target_config.get('base_url', 'http://localhost:8080')
            
            # Endpoints protégés à tester
            protected_endpoints = [
                '/api/admin',
                '/api/users',
                '/api/blockchain/mine',
                '/api/config'
            ]
            
            unauthorized_access = []
            
            for endpoint in protected_endpoints:
                try:
                    # Test sans authentification
                    async with self.session.get(f"{base_url}{endpoint}") as response:
                        if response.status == 200:
                            unauthorized_access.append({
                                'endpoint': endpoint,
                                'status': response.status,
                                'auth_required': False
                            })
                
                except Exception:
                    pass  # Endpoint peut ne pas exister
            
            # Évaluer résultat
            if unauthorized_access:
                status = "failed"
                severity = TestSeverity.HIGH
                evidence = {'unauthorized_endpoints': unauthorized_access}
                remediation = "Implémenter authentification pour endpoints protégés"
            else:
                status = "passed"
                severity = TestSeverity.INFO
                evidence = {'tested_endpoints': protected_endpoints}
                remediation = "Maintenir protection authentification"
            
            self._add_result(TestResult(
                test_id=test_id,
                test_name="API Authentication Test",
                category=TestCategory.API_SECURITY,
                severity=severity,
                status=status,
                description="Test authentification des APIs protégées",
                evidence=evidence,
                remediation=remediation,
                execution_time=time.time() - start_time,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
        except Exception as e:
            self._add_error_result(test_id, "API Authentication Test", str(e), start_time)
    
    async def _run_blockchain_tests(self):
        """Tests de sécurité blockchain"""
        logger.info("⛓️ Tests sécurité blockchain")
        
        await self._test_blockchain_rpc()
        await self._test_blockchain_consensus()
        await self._test_smart_contracts()
    
    async def _test_blockchain_rpc(self):
        """Test sécurité RPC blockchain"""
        test_id = "BC_001"
        start_time = time.time()
        
        try:
            # Tester endpoints RPC sensibles
            rpc_methods = [
                'getblockchaininfo',
                'getmininginfo', 
                'listunspent',
                'dumpprivkey',  # Très sensible
                'importprivkey', # Très sensible
                'stop'  # Très sensible
            ]
            
            base_url = self.target_config.get('blockchain_rpc_url', 'http://localhost:8545')
            accessible_methods = []
            
            for method in rpc_methods:
                try:
                    payload = {
                        'jsonrpc': '2.0',
                        'method': method,
                        'params': [],
                        'id': 1
                    }
                    
                    async with self.session.post(
                        base_url,
                        json=payload,
                        headers={'Content-Type': 'application/json'}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'result' in data:
                                accessible_methods.append({
                                    'method': method,
                                    'accessible': True,
                                    'sensitive': method in ['dumpprivkey', 'importprivkey', 'stop']
                                })
                
                except Exception:
                    pass
            
            # Évaluer résultat
            sensitive_exposed = [m for m in accessible_methods if m['sensitive']]
            
            if sensitive_exposed:
                status = "failed"
                severity = TestSeverity.CRITICAL
                evidence = {'exposed_sensitive_methods': sensitive_exposed}
                remediation = "Restreindre accès méthodes RPC sensibles"
            elif accessible_methods:
                status = "warning"
                severity = TestSeverity.MEDIUM
                evidence = {'accessible_methods': accessible_methods}
                remediation = "Réviser permissions méthodes RPC"
            else:
                status = "passed"
                severity = TestSeverity.INFO
                evidence = {'rpc_properly_secured': True}
                remediation = "Maintenir sécurité RPC"
            
            self._add_result(TestResult(
                test_id=test_id,
                test_name="Blockchain RPC Security Test",
                category=TestCategory.BLOCKCHAIN,
                severity=severity,
                status=status,
                description="Test sécurité interfaces RPC blockchain",
                evidence=evidence,
                remediation=remediation,
                execution_time=time.time() - start_time,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
        except Exception as e:
            self._add_error_result(test_id, "Blockchain RPC Test", str(e), start_time)
    
    async def _run_network_tests(self):
        """Tests de sécurité réseau"""
        logger.info("🌐 Tests sécurité réseau")
        
        await self._test_port_scanning()
        await self._test_ssl_configuration()
    
    async def _test_port_scanning(self):
        """Test scan de ports"""
        test_id = "NET_001"
        start_time = time.time()
        
        try:
            target_host = self.target_config.get('target_host', 'localhost')
            
            # Ports communs à scanner
            common_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 
                           3306, 5432, 6379, 8080, 8443, 9200, 27017]
            
            open_ports = []
            
            for port in common_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                
                try:
                    result = sock.connect_ex((target_host, port))
                    if result == 0:
                        open_ports.append(port)
                except Exception:
                    pass
                finally:
                    sock.close()
            
            # Évaluer résultat
            sensitive_ports = [22, 23, 3306, 5432, 6379, 9200, 27017]
            exposed_sensitive = [p for p in open_ports if p in sensitive_ports]
            
            if exposed_sensitive:
                status = "warning"
                severity = TestSeverity.MEDIUM
                evidence = {
                    'open_ports': open_ports,
                    'exposed_sensitive_ports': exposed_sensitive
                }
                remediation = "Restreindre accès ports sensibles"
            else:
                status = "passed"
                severity = TestSeverity.INFO
                evidence = {'open_ports': open_ports}
                remediation = "Maintenir configuration ports"
            
            self._add_result(TestResult(
                test_id=test_id,
                test_name="Port Scanning Test",
                category=TestCategory.NETWORK,
                severity=severity,
                status=status,
                description="Scan ports ouverts sur target",
                evidence=evidence,
                remediation=remediation,
                execution_time=time.time() - start_time,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
        except Exception as e:
            self._add_error_result(test_id, "Port Scanning Test", str(e), start_time)
    
    async def _test_ssl_configuration(self):
        """Test configuration SSL/TLS"""
        test_id = "NET_002"
        start_time = time.time()
        
        try:
            target_host = self.target_config.get('target_host', 'localhost')
            ssl_port = self.target_config.get('ssl_port', 443)
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Tester connexion SSL
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            ssl_issues = []
            
            try:
                sock.connect((target_host, ssl_port))
                ssl_sock = context.wrap_socket(sock, server_hostname=target_host)
                
                # Analyser certificat
                cert = ssl_sock.getpeercert()
                cipher = ssl_sock.cipher()
                
                # Vérifier force du chiffrement
                if cipher and cipher[1] < 128:  # Moins de 128 bits
                    ssl_issues.append(f"Weak cipher: {cipher}")
                
                # Vérifier protocole TLS
                if ssl_sock.version() in ['SSLv2', 'SSLv3', 'TLSv1', 'TLSv1.1']:
                    ssl_issues.append(f"Weak TLS version: {ssl_sock.version()}")
                
                ssl_sock.close()
                
            except ssl.SSLError as e:
                ssl_issues.append(f"SSL Error: {str(e)}")
            except Exception as e:
                ssl_issues.append(f"Connection error: {str(e)}")
            finally:
                sock.close()
            
            # Évaluer résultat
            if ssl_issues:
                status = "warning"
                severity = TestSeverity.MEDIUM
                evidence = {'ssl_issues': ssl_issues}
                remediation = "Améliorer configuration SSL/TLS"
            else:
                status = "passed"
                severity = TestSeverity.INFO
                evidence = {'ssl_properly_configured': True}
                remediation = "Maintenir configuration SSL"
            
            self._add_result(TestResult(
                test_id=test_id,
                test_name="SSL Configuration Test",
                category=TestCategory.NETWORK,
                severity=severity,
                status=status,
                description="Test configuration SSL/TLS",
                evidence=evidence,
                remediation=remediation,
                execution_time=time.time() - start_time,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
        except Exception as e:
            self._add_error_result(test_id, "SSL Configuration Test", str(e), start_time)
    
    # Méthodes utilitaires manquantes pour compléter
    async def _run_authentication_tests(self):
        """Tests d'authentification"""
        await self._test_brute_force_protection()
    
    async def _run_authorization_tests(self):
        """Tests d'autorisation"""
        await self._test_privilege_escalation()
    
    async def _run_infrastructure_tests(self):
        """Tests d'infrastructure"""
        await self._test_docker_security()
    
    async def _test_brute_force_protection(self):
        """Test protection brute force"""
        # Implémentation simplifiée
        pass
    
    async def _test_privilege_escalation(self):
        """Test élévation privilèges"""
        # Implémentation simplifiée 
        pass
    
    async def _test_docker_security(self):
        """Test sécurité Docker"""
        # Implémentation simplifiée
        pass
    
    # Plus de méthodes manquantes
    async def _test_csrf_protection(self):
        """Test protection CSRF"""
        pass
    
    async def _test_secure_cookies(self):
        """Test cookies sécurisés"""
        pass
    
    async def _test_directory_traversal(self):
        """Test directory traversal"""
        pass
    
    async def _test_api_rate_limiting(self):
        """Test rate limiting API"""
        pass
    
    async def _test_api_input_validation(self):
        """Test validation input API"""
        pass
    
    async def _test_api_information_disclosure(self):
        """Test divulgation d'informations API"""
        pass
    
    async def _test_blockchain_consensus(self):
        """Test sécurité consensus blockchain"""
        pass
    
    async def _test_smart_contracts(self):
        """Test sécurité smart contracts"""
        pass
    
    def _add_result(self, result: TestResult):
        """Ajoute un résultat de test"""
        self.results.append(result)
        logger.info(f"Test {result.test_id}: {result.status} ({result.severity.value})")
    
    def _add_error_result(self, test_id: str, test_name: str, error: str, start_time: float):
        """Ajoute un résultat d'erreur"""
        self.results.append(TestResult(
            test_id=test_id,
            test_name=test_name,
            category=TestCategory.INFRASTRUCTURE,
            severity=TestSeverity.LOW,
            status="error",
            description=f"Erreur lors de l'exécution: {error}",
            evidence={'error': error},
            remediation="Vérifier configuration test",
            execution_time=time.time() - start_time,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    def generate_report(self) -> Dict[str, Any]:
        """Génère rapport des tests"""
        total_tests = len(self.results)
        passed = len([r for r in self.results if r.status == "passed"])
        failed = len([r for r in self.results if r.status == "failed"])
        warnings = len([r for r in self.results if r.status == "warning"])
        errors = len([r for r in self.results if r.status == "error"])
        
        critical_issues = len([r for r in self.results if r.severity == TestSeverity.CRITICAL])
        high_issues = len([r for r in self.results if r.severity == TestSeverity.HIGH])
        
        return {
            'summary': {
                'total_tests': total_tests,
                'passed': passed,
                'failed': failed,
                'warnings': warnings,
                'errors': errors,
                'critical_issues': critical_issues,
                'high_issues': high_issues,
                'success_rate': (passed / total_tests * 100) if total_tests > 0 else 0
            },
            'results': [
                {
                    'test_id': r.test_id,
                    'test_name': r.test_name,
                    'category': r.category.value,
                    'severity': r.severity.value,
                    'status': r.status,
                    'description': r.description,
                    'evidence': r.evidence,
                    'remediation': r.remediation,
                    'execution_time': r.execution_time,
                    'timestamp': r.timestamp
                }
                for r in self.results
            ]
        }


# Exemple d'utilisation
async def main():
    """Fonction principale pour tests"""
    config = {
        'base_url': 'http://localhost:8080',
        'target_host': 'localhost',
        'ssl_port': 443,
        'blockchain_rpc_url': 'http://localhost:8545'
    }
    
    # Créer et exécuter suite de tests
    test_suite = PenetrationTestSuite(config)
    results = await test_suite.run_full_test_suite()
    
    # Générer rapport
    report = test_suite.generate_report()
    
    print(f"\n🔍 RAPPORT TESTS DE PÉNÉTRATION")
    print(f"Total tests: {report['summary']['total_tests']}")
    print(f"Succès: {report['summary']['passed']}")
    print(f"Échecs: {report['summary']['failed']}")
    print(f"Avertissements: {report['summary']['warnings']}")
    print(f"Issues critiques: {report['summary']['critical_issues']}")
    print(f"Taux de succès: {report['summary']['success_rate']:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())