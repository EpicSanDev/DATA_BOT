#!/bin/bash
# ==============================================================================
# DATA_BOT v4 - Script de déploiement sécurisé
# ==============================================================================

set -euo pipefail

# Configuration par défaut
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"
ENVIRONMENT="${ENVIRONMENT:-development}"
TAG="${TAG:-latest}"
REGISTRY="${DOCKER_REGISTRY:-docker.io}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-databot}"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
    exit 1
}

# Fonction d'aide
show_help() {
    cat << EOF
DATA_BOT v4 - Script de déploiement

Usage: $0 [OPTIONS] [COMMAND]

COMMANDS:
    deploy          Déploie l'application (par défaut)
    build           Build les images Docker uniquement
    start           Démarre les services
    stop            Arrête les services
    restart         Redémarre les services
    logs            Affiche les logs
    status          Affiche le statut des services
    backup          Effectue une sauvegarde
    rollback        Revient à la version précédente
    cleanup         Nettoie les ressources inutilisées
    health          Vérifie l'état de santé

OPTIONS:
    -e, --environment ENV   Environnement (development/staging/production)
    -t, --tag TAG          Tag Docker à déployer
    -r, --registry REG     Registre Docker
    -f, --force            Force le redéploiement
    -v, --verbose          Mode verbeux
    -h, --help             Affiche cette aide

EXEMPLES:
    $0 deploy -e production -t v1.2.3
    $0 build --force
    $0 logs databot-api
    $0 rollback
    $0 health

EOF
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
    fi
    
    # Curl pour health checks
    if ! command -v curl &> /dev/null; then
        log_warning "curl n'est pas installé, les health checks peuvent échouer"
    fi
    
    log_success "Prérequis vérifiés"
}

# Génération des secrets
generate_secrets() {
    log "Génération des secrets..."
    
    SECRETS_DIR="${DOCKER_DIR}/secrets"
    mkdir -p "${SECRETS_DIR}"
    
    # Mot de passe PostgreSQL
    if [[ ! -f "${SECRETS_DIR}/postgres_password.txt" ]]; then
        openssl rand -base64 32 > "${SECRETS_DIR}/postgres_password.txt"
        log_success "Mot de passe PostgreSQL généré"
    fi
    
    # Mot de passe Redis
    if [[ ! -f "${SECRETS_DIR}/redis_password.txt" ]]; then
        openssl rand -base64 32 > "${SECRETS_DIR}/redis_password.txt"
        log_success "Mot de passe Redis généré"
    fi
    
    # Mot de passe Grafana
    if [[ ! -f "${SECRETS_DIR}/grafana_password.txt" ]]; then
        openssl rand -base64 16 > "${SECRETS_DIR}/grafana_password.txt"
        log_success "Mot de passe Grafana généré"
    fi
    
    # Certificats SSL auto-signés pour développement
    if [[ "${ENVIRONMENT}" != "production" && ! -f "${SECRETS_DIR}/ssl_cert.pem" ]]; then
        openssl req -x509 -newkey rsa:4096 -keyout "${SECRETS_DIR}/ssl_key.pem" \
            -out "${SECRETS_DIR}/ssl_cert.pem" -days 365 -nodes \
            -subj "/C=FR/ST=IDF/L=Paris/O=DataBot/CN=databot.local"
        log_success "Certificats SSL générés"
    fi
    
    # Sécurisation des fichiers
    chmod 600 "${SECRETS_DIR}"/*
    log_success "Secrets sécurisés"
}

# Build des images Docker
build_images() {
    log "Build des images Docker..."
    
    cd "${PROJECT_ROOT}"
    
    # Build avec cache et optimisations
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    local build_args=(
        "--build-arg" "BUILDKIT_INLINE_CACHE=1"
        "--build-arg" "TAG=${TAG}"
    )
    
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        build_args+=("--progress=plain")
    fi
    
    # Build en parallèle
    docker-compose -f "${DOCKER_DIR}/docker-compose.yml" build "${build_args[@]}" --parallel
    
    log_success "Images construites avec succès"
}

# Déploiement
deploy() {
    log "Déploiement de DATA_BOT v4 (${ENVIRONMENT})..."
    
    cd "${PROJECT_ROOT}"
    
    # Fichiers de composition
    local compose_files=("-f" "${DOCKER_DIR}/docker-compose.yml")
    
    if [[ "${ENVIRONMENT}" == "production" ]]; then
        compose_files+=("-f" "${DOCKER_DIR}/docker-compose.prod.yml")
    fi
    
    # Variables d'environnement
    export ENVIRONMENT
    export TAG
    export DOCKER_REGISTRY="${REGISTRY}"
    export COMPOSE_PROJECT_NAME
    
    # Sauvegarde avant déploiement
    if [[ "${ENVIRONMENT}" == "production" ]]; then
        backup_data
    fi
    
    # Déploiement avec rolling update
    docker-compose "${compose_files[@]}" pull
    docker-compose "${compose_files[@]}" up -d --remove-orphans
    
    log_success "Déploiement terminé"
    
    # Vérification de santé
    health_check
}

# Vérification de santé
health_check() {
    log "Vérification de l'état de santé..."
    
    local services=("databot-api:8080" "databot-admin:8082" "nginx:80")
    local max_attempts=30
    local attempt=1
    
    for service in "${services[@]}"; do
        local service_name="${service%:*}"
        local port="${service#*:}"
        
        log "Vérification de ${service_name}..."
        
        while [[ ${attempt} -le ${max_attempts} ]]; do
            if curl -f -s "http://localhost:${port}/health" > /dev/null 2>&1; then
                log_success "${service_name} est opérationnel"
                break
            fi
            
            if [[ ${attempt} -eq ${max_attempts} ]]; then
                log_error "${service_name} ne répond pas après ${max_attempts} tentatives"
            fi
            
            log "Tentative ${attempt}/${max_attempts} pour ${service_name}..."
            sleep 10
            ((attempt++))
        done
        
        attempt=1
    done
    
    log_success "Tous les services sont opérationnels"
}

# Sauvegarde
backup_data() {
    log "Sauvegarde des données..."
    
    local backup_dir="${PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "${backup_dir}"
    
    # Sauvegarde PostgreSQL
    docker-compose -f "${DOCKER_DIR}/docker-compose.yml" exec -T postgres \
        pg_dump -U databot databot_v4 | gzip > "${backup_dir}/postgres_backup.sql.gz"
    
    # Sauvegarde volumes Docker
    docker run --rm -v databot_databot-data:/data -v "${backup_dir}:/backup" \
        alpine tar czf /backup/databot_data.tar.gz -C /data .
    
    log_success "Sauvegarde créée dans ${backup_dir}"
}

# Rollback
rollback() {
    log "Rollback vers la version précédente..."
    
    # Récupération de la version précédente
    local previous_tag
    previous_tag=$(docker images --format "table {{.Tag}}" "${REGISTRY}/databot/api" | grep -v TAG | grep -v latest | head -n 2 | tail -n 1)
    
    if [[ -z "${previous_tag}" ]]; then
        log_error "Aucune version précédente trouvée"
    fi
    
    log "Rollback vers la version ${previous_tag}"
    
    export TAG="${previous_tag}"
    deploy
    
    log_success "Rollback terminé vers ${previous_tag}"
}

# Nettoyage
cleanup() {
    log "Nettoyage des ressources inutilisées..."
    
    # Images inutilisées
    docker image prune -f
    
    # Volumes non utilisés
    docker volume prune -f
    
    # Networks non utilisés
    docker network prune -f
    
    # Conteneurs arrêtés
    docker container prune -f
    
    log_success "Nettoyage terminé"
}

# Logs
show_logs() {
    local service="${1:-}"
    
    if [[ -n "${service}" ]]; then
        docker-compose -f "${DOCKER_DIR}/docker-compose.yml" logs -f "${service}"
    else
        docker-compose -f "${DOCKER_DIR}/docker-compose.yml" logs -f
    fi
}

# Status
show_status() {
    log "Statut des services DATA_BOT..."
    docker-compose -f "${DOCKER_DIR}/docker-compose.yml" ps
}

# Parsing des arguments
FORCE=false
VERBOSE=false
COMMAND="deploy"

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        deploy|build|start|stop|restart|logs|status|backup|rollback|cleanup|health)
            COMMAND="$1"
            shift
            ;;
        *)
            log_error "Option inconnue: $1"
            ;;
    esac
done

# Validation de l'environnement
if [[ ! "${ENVIRONMENT}" =~ ^(development|staging|production)$ ]]; then
    log_error "Environnement invalide: ${ENVIRONMENT}"
fi

# Exécution de la commande
main() {
    log "Démarrage du déploiement DATA_BOT v4"
    log "Environnement: ${ENVIRONMENT}"
    log "Tag: ${TAG}"
    log "Registry: ${REGISTRY}"
    
    check_prerequisites
    
    case "${COMMAND}" in
        deploy)
            generate_secrets
            build_images
            deploy
            ;;
        build)
            build_images
            ;;
        start)
            docker-compose -f "${DOCKER_DIR}/docker-compose.yml" up -d
            ;;
        stop)
            docker-compose -f "${DOCKER_DIR}/docker-compose.yml" down
            ;;
        restart)
            docker-compose -f "${DOCKER_DIR}/docker-compose.yml" restart
            ;;
        logs)
            show_logs "$@"
            ;;
        status)
            show_status
            ;;
        backup)
            backup_data
            ;;
        rollback)
            rollback
            ;;
        cleanup)
            cleanup
            ;;
        health)
            health_check
            ;;
    esac
    
    log_success "Opération '${COMMAND}' terminée avec succès"
}

# Exécution
main "$@"