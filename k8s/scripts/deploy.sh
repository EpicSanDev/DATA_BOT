#!/bin/bash

# ==============================================================================
# SCRIPT DE DÉPLOIEMENT DATA_BOT v4 KUBERNETES
# ==============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$K8S_DIR")"
NAMESPACE="databot-v4"
ENVIRONMENT="${ENVIRONMENT:-production}"
DRY_RUN="${DRY_RUN:-false}"
VERBOSE="${VERBOSE:-false}"

# Couleurs pour la sortie
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# Fonction d'aide
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [COMMAND]

COMMANDS:
    deploy      Déployer l'infrastructure complète
    update      Mettre à jour les services existants
    rollback    Revenir à la version précédente
    destroy     Supprimer toute l'infrastructure
    status      Afficher le statut du déploiement
    logs        Afficher les logs des services
    scale       Scaler les services
    backup      Créer une sauvegarde

OPTIONS:
    -e, --environment   Environnement (dev/staging/prod) [défaut: production]
    -n, --namespace     Namespace Kubernetes [défaut: databot-v4]
    -d, --dry-run       Mode dry-run (ne pas appliquer les changements)
    -v, --verbose       Mode verbose
    -h, --help          Afficher cette aide

EXEMPLES:
    $0 deploy                               # Déploiement complet
    $0 deploy -e staging -v                 # Déploiement staging en mode verbose
    $0 update -d                           # Mise à jour en dry-run
    $0 scale api 5                         # Scaler l'API à 5 replicas
    $0 logs api                            # Afficher les logs de l'API

EOF
}

# Vérifications préalables
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl n'est pas installé"
        exit 1
    fi
    
    # Vérifier kustomize
    if ! command -v kustomize &> /dev/null; then
        error "kustomize n'est pas installé"
        exit 1
    fi
    
    # Vérifier helm
    if ! command -v helm &> /dev/null; then
        warning "helm n'est pas installé, les charts Helm ne seront pas disponibles"
    fi
    
    # Vérifier la connexion au cluster
    if ! kubectl cluster-info &> /dev/null; then
        error "Impossible de se connecter au cluster Kubernetes"
        exit 1
    fi
    
    # Vérifier les permissions
    if ! kubectl auth can-i create namespace &> /dev/null; then
        error "Permissions insuffisantes pour créer des namespaces"
        exit 1
    fi
    
    success "Tous les prérequis sont satisfaits"
}

# Créer le namespace et les ressources de base
create_namespace() {
    log "Création du namespace et des ressources de base..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        kubectl apply --dry-run=client -f "$K8S_DIR/base/namespace.yaml"
    else
        kubectl apply -f "$K8S_DIR/base/namespace.yaml"
    fi
    
    success "Namespace $NAMESPACE créé"
}

# Déployer les secrets et ConfigMaps
deploy_config() {
    log "Déploiement de la configuration..."
    
    local config_files=(
        "$K8S_DIR/base/configmap.yaml"
        "$K8S_DIR/base/secrets.yaml"
    )
    
    for file in "${config_files[@]}"; do
        if [[ -f "$file" ]]; then
            verbose "Application de $file"
            if [[ "$DRY_RUN" == "true" ]]; then
                kubectl apply --dry-run=client -f "$file"
            else
                kubectl apply -f "$file"
            fi
        fi
    done
    
    success "Configuration déployée"
}

# Déployer le stockage
deploy_storage() {
    log "Déploiement du stockage persistant..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        kubectl apply --dry-run=client -f "$K8S_DIR/base/storage.yaml"
    else
        kubectl apply -f "$K8S_DIR/base/storage.yaml"
    fi
    
    success "Stockage déployé"
}

# Déployer la sécurité
deploy_security() {
    log "Déploiement des politiques de sécurité..."
    
    # RBAC
    if [[ -f "$K8S_DIR/security/rbac/rbac.yaml" ]]; then
        verbose "Application des politiques RBAC"
        if [[ "$DRY_RUN" == "true" ]]; then
            kubectl apply --dry-run=client -f "$K8S_DIR/security/rbac/rbac.yaml"
        else
            kubectl apply -f "$K8S_DIR/security/rbac/rbac.yaml"
        fi
    fi
    
    # Network Policies
    if [[ -f "$K8S_DIR/security/network-policies/network-policies.yaml" ]]; then
        verbose "Application des Network Policies"
        if [[ "$DRY_RUN" == "true" ]]; then
            kubectl apply --dry-run=client -f "$K8S_DIR/security/network-policies/network-policies.yaml"
        else
            kubectl apply -f "$K8S_DIR/security/network-policies/network-policies.yaml"
        fi
    fi
    
    success "Sécurité déployée"
}

# Déployer les bases de données
deploy_databases() {
    log "Déploiement des bases de données..."
    
    # Attendre que les PVC soient disponibles
    log "Attente de la disponibilité des volumes..."
    kubectl wait --for=condition=Bound pvc/postgres-pvc -n "$NAMESPACE" --timeout=300s || true
    kubectl wait --for=condition=Bound pvc/redis-pvc -n "$NAMESPACE" --timeout=300s || true
    
    # Déployer PostgreSQL et Redis
    if [[ -f "$K8S_DIR/base/postgres.yaml" ]]; then
        verbose "Déploiement de PostgreSQL"
        if [[ "$DRY_RUN" == "true" ]]; then
            kubectl apply --dry-run=client -f "$K8S_DIR/base/postgres.yaml"
        else
            kubectl apply -f "$K8S_DIR/base/postgres.yaml"
        fi
    fi
    
    if [[ -f "$K8S_DIR/base/redis.yaml" ]]; then
        verbose "Déploiement de Redis"
        if [[ "$DRY_RUN" == "true" ]]; then
            kubectl apply --dry-run=client -f "$K8S_DIR/base/redis.yaml"
        else
            kubectl apply -f "$K8S_DIR/base/redis.yaml"
        fi
    fi
    
    # Attendre que les bases de données soient prêtes
    if [[ "$DRY_RUN" == "false" ]]; then
        log "Attente de la disponibilité de PostgreSQL..."
        kubectl wait --for=condition=Ready pod -l app=postgres -n "$NAMESPACE" --timeout=600s
        
        log "Attente de la disponibilité de Redis..."
        kubectl wait --for=condition=Ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
    fi
    
    success "Bases de données déployées"
}

# Déployer les moteurs de recherche
deploy_search_engines() {
    log "Déploiement des moteurs de recherche..."
    
    # Déployer Elasticsearch, OpenSearch, Qdrant
    local search_files=(
        "$K8S_DIR/base/elasticsearch.yaml"
        "$K8S_DIR/base/opensearch.yaml"
        "$K8S_DIR/base/qdrant.yaml"
    )
    
    for file in "${search_files[@]}"; do
        if [[ -f "$file" ]]; then
            basename_file=$(basename "$file")
            verbose "Déploiement de $basename_file"
            if [[ "$DRY_RUN" == "true" ]]; then
                kubectl apply --dry-run=client -f "$file"
            else
                kubectl apply -f "$file"
            fi
        fi
    done
    
    # Attendre que les services soient prêts
    if [[ "$DRY_RUN" == "false" ]]; then
        log "Attente de la disponibilité des moteurs de recherche..."
        kubectl wait --for=condition=Ready pod -l app=elasticsearch -n "$NAMESPACE" --timeout=600s || true
        kubectl wait --for=condition=Ready pod -l app=opensearch -n "$NAMESPACE" --timeout=600s || true
        kubectl wait --for=condition=Ready pod -l app=qdrant -n "$NAMESPACE" --timeout=300s || true
    fi
    
    success "Moteurs de recherche déployés"
}

# Déployer les services IA
deploy_ai_services() {
    log "Déploiement des services IA..."
    
    if [[ -f "$K8S_DIR/base/ollama.yaml" ]]; then
        verbose "Déploiement d'Ollama"
        if [[ "$DRY_RUN" == "true" ]]; then
            kubectl apply --dry-run=client -f "$K8S_DIR/base/ollama.yaml"
        else
            kubectl apply -f "$K8S_DIR/base/ollama.yaml"
        fi
        
        # Attendre qu'Ollama soit prêt
        if [[ "$DRY_RUN" == "false" ]]; then
            log "Attente de la disponibilité d'Ollama..."
            kubectl wait --for=condition=Ready pod -l app=ollama -n "$NAMESPACE" --timeout=600s || true
        fi
    fi
    
    success "Services IA déployés"
}

# Déployer les services principaux DATA_BOT
deploy_databot_services() {
    log "Déploiement des services principaux DATA_BOT..."
    
    # Déployer les services dans l'ordre
    local service_files=(
        "$K8S_DIR/base/databot-blockchain.yaml"
        "$K8S_DIR/base/databot-api.yaml"
        "$K8S_DIR/base/databot-admin.yaml"
    )
    
    for file in "${service_files[@]}"; do
        if [[ -f "$file" ]]; then
            basename_file=$(basename "$file")
            verbose "Déploiement de $basename_file"
            if [[ "$DRY_RUN" == "true" ]]; then
                kubectl apply --dry-run=client -f "$file"
            else
                kubectl apply -f "$file"
            fi
        fi
    done
    
    # Attendre que les services soient prêts
    if [[ "$DRY_RUN" == "false" ]]; then
        log "Attente de la disponibilité des services DATA_BOT..."
        kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=blockchain -n "$NAMESPACE" --timeout=900s || true
        kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=api -n "$NAMESPACE" --timeout=600s || true
        kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=admin -n "$NAMESPACE" --timeout=300s || true
    fi
    
    success "Services DATA_BOT déployés"
}

# Déployer le reverse proxy
deploy_proxy() {
    log "Déploiement du reverse proxy..."
    
    if [[ -f "$K8S_DIR/base/nginx.yaml" ]]; then
        verbose "Déploiement de Nginx"
        if [[ "$DRY_RUN" == "true" ]]; then
            kubectl apply --dry-run=client -f "$K8S_DIR/base/nginx.yaml"
        else
            kubectl apply -f "$K8S_DIR/base/nginx.yaml"
        fi
        
        # Attendre que Nginx soit prêt
        if [[ "$DRY_RUN" == "false" ]]; then
            log "Attente de la disponibilité de Nginx..."
            kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=proxy -n "$NAMESPACE" --timeout=300s || true
        fi
    fi
    
    success "Reverse proxy déployé"
}

# Déployer l'auto-scaling
deploy_autoscaling() {
    log "Déploiement de l'auto-scaling..."
    
    if [[ -f "$K8S_DIR/base/autoscaling.yaml" ]]; then
        verbose "Déploiement des HPA/VPA"
        if [[ "$DRY_RUN" == "true" ]]; then
            kubectl apply --dry-run=client -f "$K8S_DIR/base/autoscaling.yaml"
        else
            kubectl apply -f "$K8S_DIR/base/autoscaling.yaml"
        fi
    fi
    
    success "Auto-scaling déployé"
}

# Déployer le monitoring
deploy_monitoring() {
    log "Déploiement du monitoring..."
    
    local monitoring_files=(
        "$K8S_DIR/base/monitoring.yaml"
        "$K8S_DIR/monitoring/prometheus/prometheus.yaml"
        "$K8S_DIR/monitoring/grafana/grafana.yaml"
    )
    
    for file in "${monitoring_files[@]}"; do
        if [[ -f "$file" ]]; then
            basename_file=$(basename "$file")
            verbose "Déploiement de $basename_file"
            if [[ "$DRY_RUN" == "true" ]]; then
                kubectl apply --dry-run=client -f "$file"
            else
                kubectl apply -f "$file"
            fi
        fi
    done
    
    success "Monitoring déployé"
}

# Déploiement complet
deploy_all() {
    log "Démarrage du déploiement complet de DATA_BOT v4..."
    
    check_prerequisites
    create_namespace
    deploy_config
    deploy_storage
    deploy_security
    deploy_databases
    deploy_search_engines
    deploy_ai_services
    deploy_databot_services
    deploy_proxy
    deploy_autoscaling
    deploy_monitoring
    
    success "Déploiement complet terminé !"
    
    # Afficher les informations de connexion
    show_connection_info
}

# Afficher les informations de connexion
show_connection_info() {
    log "Informations de connexion :"
    
    # Obtenir l'IP du load balancer ou NodePort
    local nginx_service_type
    nginx_service_type=$(kubectl get service nginx-service -n "$NAMESPACE" -o jsonpath='{.spec.type}' 2>/dev/null || echo "ClusterIP")
    
    if [[ "$nginx_service_type" == "LoadBalancer" ]]; then
        local external_ip
        external_ip=$(kubectl get service nginx-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "En attente...")
        echo "  API DATA_BOT: https://$external_ip"
        echo "  Admin Interface: https://$external_ip/admin"
        echo "  GraphQL: https://$external_ip/graphql"
    else
        echo "  Utilisez port-forward pour accéder aux services :"
        echo "  kubectl port-forward -n $NAMESPACE service/nginx-service 8080:80"
        echo "  Puis accédez à http://localhost:8080"
    fi
    
    # Monitoring
    echo "  Grafana: kubectl port-forward -n $NAMESPACE service/grafana-service 3000:3000"
    echo "  Prometheus: kubectl port-forward -n $NAMESPACE service/prometheus-service 9090:9090"
}

# Afficher le statut
show_status() {
    log "Statut du déploiement DATA_BOT v4:"
    
    echo ""
    echo "=== PODS ==="
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo ""
    echo "=== SERVICES ==="
    kubectl get services -n "$NAMESPACE"
    
    echo ""
    echo "=== PVC ==="
    kubectl get pvc -n "$NAMESPACE"
    
    echo ""
    echo "=== HPA ==="
    kubectl get hpa -n "$NAMESPACE" 2>/dev/null || echo "Aucun HPA trouvé"
    
    echo ""
    echo "=== INGRESS ==="
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo "Aucun Ingress trouvé"
}

# Fonction principale
main() {
    local command="${1:-deploy}"
    
    case "$command" in
        deploy)
            deploy_all
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Commande inconnue: $command"
            show_help
            exit 1
            ;;
    esac
}

# Parse des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            main "$@"
            exit 0
            ;;
    esac
done

# Si aucun argument, exécuter le déploiement
main "deploy"