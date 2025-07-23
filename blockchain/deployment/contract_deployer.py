"""
Déployeur de Smart Contracts automatisé pour ArchiveChain
Gère le déploiement, la mise à jour et la vérification des contrats intelligents
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib

# Import des modules ArchiveChain
import sys
sys.path.append('../..')
from src.blockchain.smart_contracts import SmartContractManager, ArchiveBounty, PreservationPool, ContentVerification
from src.blockchain.blockchain import ArchiveChain
from src.blockchain.security import signature_manager

@dataclass
class DeploymentConfig:
    """Configuration de déploiement pour les smart contracts"""
    contract_type: str
    contract_name: str
    constructor_params: Dict[str, Any]
    gas_limit: int = 5000000
    gas_price: int = 20
    verify_on_deployment: bool = True
    auto_upgrade: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DeploymentResult:
    """Résultat d'un déploiement de contrat"""
    contract_id: str
    contract_type: str
    deployment_tx: str
    block_height: int
    gas_used: int
    timestamp: float
    success: bool
    error_message: Optional[str] = None
    verification_status: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ContractDeployer:
    """
    Déployeur automatisé de smart contracts avec vérification intégrée
    """
    
    def __init__(self, blockchain: ArchiveChain, config_path: Optional[str] = None):
        self.blockchain = blockchain
        self.contract_manager = blockchain.smart_contracts
        self.deployment_history: List[DeploymentResult] = []
        self.config_path = config_path or "blockchain/deployment/configs/"
        self.logger = self._setup_logger()
        
        # Templates de contrats pré-configurés
        self.contract_templates = self._load_contract_templates()
        
    def _setup_logger(self) -> logging.Logger:
        """Configure le logger pour le déploiement"""
        logger = logging.getLogger('ContractDeployer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('blockchain/deployment/deployment.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _load_contract_templates(self) -> Dict[str, DeploymentConfig]:
        """Charge les templates de contrats pré-configurés"""
        templates = {
            "archive_bounty_standard": DeploymentConfig(
                contract_type="ArchiveBounty",
                contract_name="StandardArchiveBounty",
                constructor_params={
                    "target_url": "",
                    "reward": "100.0",
                    "deadline": 0
                },
                gas_limit=3000000,
                verify_on_deployment=True
            ),
            "preservation_pool_community": DeploymentConfig(
                contract_type="PreservationPool",
                contract_name="CommunityPreservationPool",
                constructor_params={
                    "target_archives": [],
                    "initial_funding": "1000.0"
                },
                gas_limit=4000000,
                verify_on_deployment=True
            ),
            "content_verification_auto": DeploymentConfig(
                contract_type="ContentVerification",
                contract_name="AutoContentVerification",
                constructor_params={},
                gas_limit=2000000,
                verify_on_deployment=True
            )
        }
        return templates
    
    def deploy_contract_from_template(self, template_name: str, 
                                    custom_params: Optional[Dict[str, Any]] = None,
                                    deployer_address: str = "deployer") -> DeploymentResult:
        """
        Déploie un contrat à partir d'un template pré-configuré
        
        Args:
            template_name: Nom du template à utiliser
            custom_params: Paramètres personnalisés pour surcharger le template
            deployer_address: Adresse du déployeur
            
        Returns:
            Résultat du déploiement
        """
        if template_name not in self.contract_templates:
            raise ValueError(f"Template non trouvé: {template_name}")
        
        config = self.contract_templates[template_name]
        
        # Fusionner les paramètres personnalisés
        if custom_params:
            config.constructor_params.update(custom_params)
        
        return self.deploy_contract(config, deployer_address)
    
    def deploy_contract(self, config: DeploymentConfig, 
                       deployer_address: str) -> DeploymentResult:
        """
        Déploie un smart contract avec la configuration spécifiée
        
        Args:
            config: Configuration de déploiement
            deployer_address: Adresse du déployeur
            
        Returns:
            Résultat du déploiement
        """
        self.logger.info(f"Début du déploiement: {config.contract_type}")
        
        try:
            # Générer un ID unique pour le contrat
            contract_id = self._generate_contract_id(config)
            
            # Vérifier les paramètres requis
            self._validate_deployment_params(config)
            
            # Déployer le contrat
            start_time = time.time()
            deployment_tx = self._execute_deployment(config, contract_id, deployer_address)
            
            # Créer le résultat de déploiement
            result = DeploymentResult(
                contract_id=contract_id,
                contract_type=config.contract_type,
                deployment_tx=deployment_tx,
                block_height=len(self.blockchain.chain),
                gas_used=self._estimate_gas_used(config),
                timestamp=start_time,
                success=True
            )
            
            # Vérification automatique si demandée
            if config.verify_on_deployment:
                verification_status = self._verify_deployment(contract_id, config)
                result.verification_status = verification_status
            
            self.deployment_history.append(result)
            self.logger.info(f"Déploiement réussi: {contract_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"Erreur lors du déploiement: {str(e)}"
            self.logger.error(error_msg)
            
            result = DeploymentResult(
                contract_id="",
                contract_type=config.contract_type,
                deployment_tx="",
                block_height=0,
                gas_used=0,
                timestamp=time.time(),
                success=False,
                error_message=error_msg
            )
            
            self.deployment_history.append(result)
            return result
    
    def _generate_contract_id(self, config: DeploymentConfig) -> str:
        """Génère un ID unique pour le contrat"""
        timestamp = str(time.time())
        contract_data = f"{config.contract_type}_{config.contract_name}_{timestamp}"
        return hashlib.sha256(contract_data.encode()).hexdigest()[:16]
    
    def _validate_deployment_params(self, config: DeploymentConfig):
        """Valide les paramètres de déploiement"""
        if not config.contract_type:
            raise ValueError("Type de contrat requis")
        
        if config.contract_type not in ["ArchiveBounty", "PreservationPool", "ContentVerification"]:
            raise ValueError(f"Type de contrat non supporté: {config.contract_type}")
        
        # Validation spécifique par type de contrat
        if config.contract_type == "ArchiveBounty":
            required_params = ["target_url", "reward", "deadline"]
            for param in required_params:
                if param not in config.constructor_params:
                    raise ValueError(f"Paramètre requis manquant pour ArchiveBounty: {param}")
        
        elif config.contract_type == "PreservationPool":
            required_params = ["target_archives", "initial_funding"]
            for param in required_params:
                if param not in config.constructor_params:
                    raise ValueError(f"Paramètre requis manquant pour PreservationPool: {param}")
    
    def _execute_deployment(self, config: DeploymentConfig, 
                          contract_id: str, deployer_address: str) -> str:
        """Exécute le déploiement effectif du contrat"""
        try:
            # Déployer via le gestionnaire de contrats de la blockchain
            contract = self.contract_manager.deploy_contract(
                config.contract_type,
                contract_id,
                deployer_address,
                **config.constructor_params
            )
            
            # Simuler une transaction de déploiement
            tx_id = hashlib.sha256(f"deploy_{contract_id}_{time.time()}".encode()).hexdigest()[:16]
            
            self.logger.info(f"Contrat déployé avec succès: {contract_id}")
            return tx_id
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution du déploiement: {str(e)}")
            raise
    
    def _estimate_gas_used(self, config: DeploymentConfig) -> int:
        """Estime le gaz utilisé pour le déploiement"""
        # Estimation basée sur la complexité du contrat
        base_gas = 1000000
        
        if config.contract_type == "ArchiveBounty":
            return base_gas + 500000
        elif config.contract_type == "PreservationPool":
            return base_gas + 800000
        elif config.contract_type == "ContentVerification":
            return base_gas + 600000
        
        return base_gas
    
    def _verify_deployment(self, contract_id: str, config: DeploymentConfig) -> str:
        """Vérifie que le contrat a été correctement déployé"""
        try:
            # Vérifier l'existence du contrat
            contract = self.contract_manager.get_contract(contract_id)
            if not contract:
                return "FAILED - Contract not found"
            
            # Vérifier le type
            if type(contract).__name__ != config.contract_type:
                return "FAILED - Contract type mismatch"
            
            # Vérifications spécifiques par type
            if config.contract_type == "ArchiveBounty":
                if hasattr(contract, 'target_url') and hasattr(contract, 'reward'):
                    return "VERIFIED"
            elif config.contract_type == "PreservationPool":
                if hasattr(contract, 'target_archives') and hasattr(contract, 'total_funding'):
                    return "VERIFIED"
            elif config.contract_type == "ContentVerification":
                if hasattr(contract, 'verified_content'):
                    return "VERIFIED"
            
            return "PARTIAL - Some properties missing"
            
        except Exception as e:
            return f"ERROR - {str(e)}"
    
    def deploy_batch(self, configs: List[DeploymentConfig], 
                    deployer_address: str) -> List[DeploymentResult]:
        """Déploie plusieurs contrats en lot"""
        results = []
        
        for i, config in enumerate(configs):
            self.logger.info(f"Déploiement {i+1}/{len(configs)}: {config.contract_type}")
            result = self.deploy_contract(config, deployer_address)
            results.append(result)
            
            # Pause entre les déploiements pour éviter la congestion
            if i < len(configs) - 1:
                time.sleep(1)
        
        return results
    
    def get_deployment_status(self, contract_id: str) -> Optional[DeploymentResult]:
        """Récupère le statut de déploiement d'un contrat"""
        for result in self.deployment_history:
            if result.contract_id == contract_id:
                return result
        return None
    
    def list_deployed_contracts(self, contract_type: Optional[str] = None) -> List[DeploymentResult]:
        """Liste les contrats déployés, optionnellement filtrés par type"""
        if contract_type:
            return [r for r in self.deployment_history if r.contract_type == contract_type and r.success]
        return [r for r in self.deployment_history if r.success]
    
    def export_deployment_report(self, filepath: str):
        """Exporte un rapport de déploiement en JSON"""
        report = {
            "deployment_summary": {
                "total_deployments": len(self.deployment_history),
                "successful_deployments": len([r for r in self.deployment_history if r.success]),
                "failed_deployments": len([r for r in self.deployment_history if not r.success]),
                "timestamp": time.time()
            },
            "deployments": [result.to_dict() for result in self.deployment_history],
            "templates_used": list(self.contract_templates.keys())
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Rapport de déploiement exporté: {filepath}")
    
    def rollback_deployment(self, contract_id: str) -> bool:
        """
        Annule un déploiement (marque le contrat comme désactivé)
        Note: Dans une vraie blockchain, ceci nécessiterait une transaction de désactivation
        """
        try:
            contract = self.contract_manager.get_contract(contract_id)
            if contract:
                # Marquer le contrat comme désactivé
                contract.state = "cancelled"
                self.logger.info(f"Contrat {contract_id} annulé")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'annulation: {str(e)}")
            return False