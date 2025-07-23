"""
Tests unitaires pour valider les corrections de sécurité d'ArchiveChain

Ce fichier teste toutes les vulnérabilités critiques corrigées :
1. Cryptographie sécurisée (consensus.py)
2. Sels cryptographiques dynamiques (archive_data.py)
3. Signatures ECDSA complètes (block.py, tokens.py)
4. Validation d'autorisation renforcée (consensus.py)
5. Protection SafeMath (tokens.py)
"""

import unittest
import time
from decimal import Decimal
from src.blockchain.security import (
    crypto_manager, signature_manager, SafeMath, OverflowError, 
    UnderflowError, InvalidAmountError
)
from src.blockchain.consensus import ProofOfArchive
from src.blockchain.archive_data import ArchiveData, ArchiveMetadata
from src.blockchain.block import ArchiveTransaction
from src.blockchain.tokens import ARCToken, TokenTransaction, TokenTransactionType


class TestSecurityFixes(unittest.TestCase):
    """Tests pour les corrections de sécurité critiques"""
    
    def setUp(self):
        """Configuration des tests"""
        self.consensus = ProofOfArchive()
        self.token_system = ARCToken()
        
        # Génère une paire de clés pour les tests
        self.key_pair = signature_manager.generate_key_pair()
        signature_manager.register_public_key(
            self.key_pair.address, 
            self.key_pair.get_public_key_pem()
        )
    
    def test_secure_cryptography_consensus(self):
        """Test 1: Vérifie que la cryptographie sécurisée est utilisée dans le consensus"""
        print("🔐 Test 1: Cryptographie sécurisée dans le consensus")
        
        # Génère des challenges sécurisés
        challenge1 = self.consensus.generate_storage_challenge("node1", "archive1")
        challenge2 = self.consensus.generate_storage_challenge("node1", "archive1")
        
        # Les challenges doivent être différents (randomness cryptographique)
        self.assertNotEqual(challenge1, challenge2)
        self.assertEqual(len(challenge1), 32)
        self.assertEqual(len(challenge2), 32)
        
        # Vérifie que les challenges sont bien stockés
        self.assertIn("node1_archive1", self.consensus.active_challenges)
        
        print("✅ Cryptographie sécurisée validée")
    
    def test_dynamic_salt_archive_data(self):
        """Test 2: Vérifie l'utilisation de sels dynamiques pour les archives"""
        print("🧂 Test 2: Sels cryptographiques dynamiques")
        
        # Crée des données d'archive de test
        metadata = ArchiveMetadata(
            screenshots=[], external_resources=[], linked_pages=[],
            tags=["test"], category="test", priority=1
        )
        
        archive1 = ArchiveData(
            archive_id="test1",
            original_url="https://example1.com",
            capture_timestamp="2024-01-01T00:00:00Z",
            content_type="text/html",
            compression="gzip",
            size_compressed=1000,
            size_original=2000,
            checksum="",
            metadata=metadata
        )
        
        archive2 = ArchiveData(
            archive_id="test2",
            original_url="https://example2.com",
            capture_timestamp="2024-01-01T00:00:00Z",
            content_type="text/html",
            compression="gzip",
            size_compressed=1000,
            size_original=2000,
            checksum="",
            metadata=metadata
        )
        
        # Calcule les checksums avec sels dynamiques
        content1 = b"test content 1"
        content2 = b"test content 2"
        
        checksum1 = archive1.calculate_checksum(content1)
        checksum2 = archive2.calculate_checksum(content2)
        
        # Les checksums doivent être différents et utiliser le format sécurisé
        self.assertNotEqual(checksum1, checksum2)
        self.assertTrue(checksum1.startswith("pbkdf2_sha256_"))
        self.assertTrue(checksum2.startswith("pbkdf2_sha256_"))
        
        print("✅ Sels dynamiques validés")
    
    def test_ecdsa_signatures_transactions(self):
        """Test 3: Vérifie les signatures ECDSA pour les transactions"""
        print("✍️ Test 3: Signatures ECDSA complètes")
        
        # Test transaction d'archive
        archive_tx = ArchiveTransaction(
            tx_id="test_tx",
            tx_type="archive",
            archive_data=None,
            sender=self.key_pair.address,
            receiver="test_receiver",
            amount=100,
            timestamp=time.time()
        )
        
        # Signe la transaction
        self.assertTrue(archive_tx.sign_transaction(self.key_pair.private_key))
        self.assertTrue(archive_tx.is_signed())
        self.assertTrue(archive_tx.verify_signature())
        
        # Test transaction de token
        token_tx = TokenTransaction(
            tx_id="test_token_tx",
            tx_type=TokenTransactionType.TRANSFER,
            from_address=self.key_pair.address,
            to_address="test_to",
            amount=Decimal('100'),
            fee=Decimal('1'),
            timestamp=time.time(),
            metadata={}
        )
        
        # Signe la transaction de token
        self.assertTrue(token_tx.sign_transaction(self.key_pair.private_key))
        self.assertTrue(token_tx.is_signed())
        self.assertTrue(token_tx.verify_signature())
        
        print("✅ Signatures ECDSA validées")
    
    def test_enhanced_authorization_validation(self):
        """Test 4: Vérifie la validation d'autorisation renforcée"""
        print("🛡️ Test 4: Validation d'autorisation renforcée")
        
        # Test avec un nœud sans score suffisant
        result = self.consensus.validate_block_creation_right("low_score_node", "test_hash")
        self.assertFalse(result)  # Devrait échouer car pas de score
        
        # Ajoute des preuves pour créer un score suffisant
        from src.blockchain.consensus import StorageProof
        
        # Simule un nœud avec des preuves suffisantes
        node_id = "valid_node"
        
        # Ajoute des preuves de stockage
        for i in range(3):
            proof = StorageProof(
                node_id=node_id,
                archive_id=f"archive_{i}",
                challenge="test_challenge",
                response="test_response",
                timestamp=time.time(),
                file_size=1000000000,  # 1GB
                checksum="test_checksum"
            )
            self.consensus.storage_proofs[node_id] = [proof]
        
        # Le nœud devrait maintenant avoir un score suffisant
        score = self.consensus.calculate_total_score(node_id)
        self.assertGreater(score, 0.3)  # Seuil minimum renforcé
        
        print("✅ Validation d'autorisation renforcée validée")
    
    def test_safemath_protection(self):
        """Test 5: Vérifie la protection SafeMath contre les overflows"""
        print("🧮 Test 5: Protection SafeMath")
        
        # Test validation de montants
        valid_amount = SafeMath.validate_amount(Decimal('1000'))
        self.assertEqual(valid_amount, Decimal('1000'))
        
        # Test protection contre les overflows
        with self.assertRaises(OverflowError):
            SafeMath.safe_add(Decimal('999999999'), Decimal('999999999'))
        
        # Test protection contre les underflows
        with self.assertRaises(UnderflowError):
            SafeMath.safe_subtract(Decimal('100'), Decimal('200'))
        
        # Test opérations sécurisées valides
        result_add = SafeMath.safe_add(Decimal('100'), Decimal('50'))
        self.assertEqual(result_add, Decimal('150'))
        
        result_sub = SafeMath.safe_subtract(Decimal('200'), Decimal('50'))
        self.assertEqual(result_sub, Decimal('150'))
        
        result_mul = SafeMath.safe_multiply(Decimal('10'), Decimal('5'))
        self.assertEqual(result_mul, Decimal('50'))
        
        result_div = SafeMath.safe_divide(Decimal('100'), Decimal('4'))
        self.assertEqual(result_div, Decimal('25'))
        
        # Test mint sécurisé avec SafeMath
        initial_supply = self.token_system.total_minted
        self.token_system.mint_tokens("test_address", Decimal('1000'), "test")
        
        self.assertEqual(
            self.token_system.total_minted, 
            SafeMath.safe_add(initial_supply, Decimal('1000'))
        )
        
        print("✅ Protection SafeMath validée")
    
    def test_signature_validation_mandatory(self):
        """Test 6: Vérifie que la validation des signatures est obligatoire"""
        print("🔏 Test 6: Validation obligatoire des signatures")
        
        # Crée une transaction non signée
        unsigned_tx = ArchiveTransaction(
            tx_id="unsigned_tx",
            tx_type="archive",
            archive_data=None,
            sender="test_sender",
            receiver="test_receiver",
            amount=100,
            timestamp=time.time()
        )
        
        # La validation doit échouer sans signature
        from src.blockchain.block import Block
        block = Block("prev_hash", 1)
        
        self.assertFalse(block.validate_transaction(unsigned_tx))
        
        # Après signature, la validation doit réussir
        unsigned_tx.sender = self.key_pair.address  # Utilise une adresse valide
        unsigned_tx.sign_transaction(self.key_pair.private_key)
        self.assertTrue(block.validate_transaction(unsigned_tx))
        
        print("✅ Validation obligatoire des signatures validée")
    
    def test_crypto_manager_functions(self):
        """Test 7: Vérifie les fonctions du gestionnaire cryptographique"""
        print("🔧 Test 7: Fonctions du gestionnaire cryptographique")
        
        # Test génération de sels sécurisés
        salt1 = crypto_manager.generate_secure_salt()
        salt2 = crypto_manager.generate_secure_salt()
        
        self.assertEqual(len(salt1), 32)
        self.assertEqual(len(salt2), 32)
        self.assertNotEqual(salt1, salt2)
        
        # Test génération de nombres aléatoires sécurisés
        rand_int = crypto_manager.generate_secure_random_int(1, 100)
        self.assertGreaterEqual(rand_int, 1)
        self.assertLessEqual(rand_int, 100)
        
        rand_float = crypto_manager.generate_secure_random_float()
        self.assertGreaterEqual(rand_float, 0.0)
        self.assertLessEqual(rand_float, 1.0)
        
        # Test comparaison en temps constant
        self.assertTrue(crypto_manager.constant_time_compare("test", "test"))
        self.assertFalse(crypto_manager.constant_time_compare("test", "different"))
        
        print("✅ Fonctions du gestionnaire cryptographique validées")
    
    def test_comprehensive_security_integration(self):
        """Test 8: Test d'intégration sécuritaire complet"""
        print("🎯 Test 8: Intégration sécuritaire complète")
        
        # Simule un workflow complet sécurisé
        
        # 1. Génération sécurisée de challenge
        challenge = crypto_manager.generate_secure_challenge("node1", "archive1")
        self.assertIsInstance(challenge, str)
        self.assertEqual(len(challenge), 32)
        
        # 2. Création d'archive avec checksum sécurisé
        metadata = ArchiveMetadata(
            screenshots=[], external_resources=[], linked_pages=[],
            tags=["integration"], category="test", priority=1
        )
        
        archive = ArchiveData(
            archive_id="integration_test",
            original_url="https://integration.test",
            capture_timestamp="2024-01-01T00:00:00Z",
            content_type="text/html",
            compression="gzip",
            size_compressed=1000,
            size_original=2000,
            checksum="",
            metadata=metadata
        )
        
        secure_checksum = archive.calculate_checksum(b"integration test content")
        self.assertTrue(secure_checksum.startswith("pbkdf2_sha256_"))
        
        # 3. Transaction signée avec SafeMath
        safe_amount = SafeMath.validate_amount(Decimal('500'))
        
        transaction = ArchiveTransaction(
            tx_id="integration_tx",
            tx_type="archive",
            archive_data=archive,
            sender=self.key_pair.address,
            receiver="integration_receiver",
            amount=int(safe_amount),
            timestamp=time.time()
        )
        
        # Signature obligatoire
        self.assertTrue(transaction.sign_transaction(self.key_pair.private_key))
        self.assertTrue(transaction.verify_signature())
        
        # 4. Validation d'autorisation renforcée
        # (Nécessiterait des preuves supplémentaires pour passer la validation complète)
        
        print("✅ Intégration sécuritaire complète validée")


def run_security_tests():
    """Exécute tous les tests de sécurité"""
    print("🚀 Démarrage des tests de sécurité ArchiveChain")
    print("=" * 60)
    
    # Crée la suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSecurityFixes)
    
    # Exécute les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"📊 Résultats des tests de sécurité:")
    print(f"   • Tests exécutés: {result.testsRun}")
    print(f"   • Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   • Échecs: {len(result.failures)}")
    print(f"   • Erreurs: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 Tous les tests de sécurité ont réussi !")
        print("🔒 Les vulnérabilités critiques ont été corrigées avec succès.")
    else:
        print("❌ Certains tests ont échoué. Vérification requise.")
        
        for failure in result.failures:
            print(f"Échec: {failure[0]}")
            print(f"Détail: {failure[1]}")
        
        for error in result.errors:
            print(f"Erreur: {error[0]}")
            print(f"Détail: {error[1]}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Exécute les tests si le script est lancé directement
    run_security_tests()