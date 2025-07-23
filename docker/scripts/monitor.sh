#!/bin/bash
# ==============================================================================
# DATA_BOT v4 - Script de monitoring et alerting
# ==============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"
MONITORING_INTERVAL="${MONITORING_INTERVAL:-30}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
LOG_FILE="${LOG_FILE:-/var/log/databot-monitor.log}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${BLUE}${message}${NC}"
    echo "${message}" >> "${LOG_FILE}"
}

log_success() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1"
    echo -e "${GREEN}${message}${NC}"
    echo "${message}" >> "${LOG_FILE}"
}

log_warning() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ $1"
    echo -e "${YELLOW}${message}${NC}"
    echo "${message}" >> "${LOG_FILE}"
}

log_error() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1"
    echo -e "${RED}${message}${NC}"
    echo "${message}" >> "${LOG_FILE}"
}

# Envoi d'alerte
send_alert() {
    local severity="$1"
    local message="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    if [[ -n "${ALERT_WEBHOOK}" ]]; then
        curl -X POST "${ALERT_WEBHOOK}" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"🚨 DATA_BOT Alert\",
                \"attachments\": [{
                    \"color\": \"$([ "$severity" = "critical" ] && echo "danger" || echo "warning")\",
                    \"fields\": [{
                        \"title\": \"Severity\",
                        \"value\": \"$severity\",
                        \"short\": true
                    }, {
                        \"title\": \"Timestamp\",
                        \"value\": \"$timestamp\",
                        \"short\": true
                    }, {
                        \"title\": \"Message\",
                        \"value\": \"$message\",
                        \"short\": false
                    }]
                }]
            }" 2>/dev/null || log_error "Échec d'envoi d'alerte"
    fi
}

# Vérification de la santé des services
check_service_health() {
    local service_name="$1"
    local health_url="$2"
    local timeout="${3:-10}"
    
    if curl -f -s --max-time "${timeout}" "${health_url}" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Vérification des conteneurs
check_containers() {
    log "Vérification de l'état des conteneurs..."
    
    local services=(
        "databot-api"
        "databot-admin" 
        "databot-blockchain"
        "databot-postgres"
        "databot-redis"
        "databot-elasticsearch"
        "databot-prometheus"
        "databot-grafana"
        "databot-nginx"
    )
    
    local failed_services=()
    
    for service in "${services[@]}"; do
        local container_status
        container_status=$(docker inspect --format='{{.State.Status}}' "${service}" 2>/dev/null || echo "not_found")
        
        case "${container_status}" in
            "running")
                log_success "Service ${service} : Running"
                ;;
            "exited"|"dead")
                log_error "Service ${service} : Arrêté (${container_status})"
                failed_services+=("${service}")
                ;;
            "not_found")
                log_error "Service ${service} : Conteneur non trouvé"
                failed_services+=("${service}")
                ;;
            *)
                log_warning "Service ${service} : État inconnu (${container_status})"
                ;;
        esac
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        send_alert "critical" "Services en échec: ${failed_services[*]}"
        return 1
    fi
    
    return 0
}

# Vérification des endpoints
check_endpoints() {
    log "Vérification des endpoints..."
    
    local endpoints=(
        "API:http://localhost:8080/health"
        "Admin:http://localhost:8082/_stcore/health"
        "Nginx:http://localhost:80/nginx-health"
        "Prometheus:http://localhost:9090/-/healthy"
        "Grafana:http://localhost:3000/api/health"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${endpoints[@]}"; do
        local name="${endpoint%%:*}"
        local url="${endpoint#*:}"
        
        if check_service_health "${name}" "${url}"; then
            log_success "Endpoint ${name} : OK"
        else
            log_error "Endpoint ${name} : Indisponible"
            failed_endpoints+=("${name}")
        fi
    done
    
    if [[ ${#failed_endpoints[@]} -gt 0 ]]; then
        send_alert "warning" "Endpoints indisponibles: ${failed_endpoints[*]}"
        return 1
    fi
    
    return 0
}

# Vérification des ressources système
check_system_resources() {
    log "Vérification des ressources système..."
    
    # CPU
    local cpu_usage
    cpu_usage=$(docker stats --no-stream --format "table {{.CPUPerc}}" | tail -n +2 | sed 's/%//' | awk '{sum+=$1} END {print sum}')
    
    if (( $(echo "${cpu_usage} > 80" | bc -l) )); then
        log_warning "Utilisation CPU élevée: ${cpu_usage}%"
        send_alert "warning" "Utilisation CPU élevée: ${cpu_usage}%"
    else
        log_success "Utilisation CPU: ${cpu_usage}%"
    fi
    
    # Mémoire
    local memory_usage
    memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    
    if (( $(echo "${memory_usage} > 85" | bc -l) )); then
        log_warning "Utilisation mémoire élevée: ${memory_usage}%"
        send_alert "warning" "Utilisation mémoire élevée: ${memory_usage}%"
    else
        log_success "Utilisation mémoire: ${memory_usage}%"
    fi
    
    # Espace disque
    local disk_usage
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [[ ${disk_usage} -gt 85 ]]; then
        log_warning "Utilisation disque élevée: ${disk_usage}%"
        send_alert "warning" "Utilisation disque élevée: ${disk_usage}%"
    else
        log_success "Utilisation disque: ${disk_usage}%"
    fi
}

# Vérification des volumes Docker
check_docker_volumes() {
    log "Vérification des volumes Docker..."
    
    local volumes=(
        "databot_postgres-data"
        "databot_redis-data"
        "databot_elasticsearch-data"
        "databot_databot-data"
    )
    
    for volume in "${volumes[@]}"; do
        if docker volume inspect "${volume}" > /dev/null 2>&1; then
            log_success "Volume ${volume} : OK"
        else
            log_error "Volume ${volume} : Manquant"
            send_alert "critical" "Volume Docker manquant: ${volume}"
        fi
    done
}

# Vérification des logs d'erreur
check_error_logs() {
    log "Recherche d'erreurs dans les logs..."
    
    local services=("databot-api" "databot-admin" "databot-blockchain")
    local error_patterns=("ERROR" "FATAL" "CRITICAL" "Exception" "Traceback")
    
    for service in "${services[@]}"; do
        for pattern in "${error_patterns[@]}"; do
            local error_count
            error_count=$(docker logs "${service}" --since=10m 2>&1 | grep -c "${pattern}" || echo 0)
            
            if [[ ${error_count} -gt 5 ]]; then
                log_warning "Service ${service}: ${error_count} erreurs '${pattern}' détectées"
                send_alert "warning" "Erreurs détectées dans ${service}: ${error_count} '${pattern}'"
            fi
        done
    done
}

# Vérification de la base de données
check_database() {
    log "Vérification de la base de données..."
    
    # PostgreSQL
    if docker exec databot-postgres pg_isready -U databot > /dev/null 2>&1; then
        log_success "PostgreSQL : Connecté"
        
        # Vérification des connexions actives
        local connections
        connections=$(docker exec databot-postgres psql -U databot -d databot_v4 -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
        
        if [[ ${connections} -gt 150 ]]; then
            log_warning "PostgreSQL: Nombre élevé de connexions (${connections})"
        else
            log_success "PostgreSQL: ${connections} connexions actives"
        fi
    else
        log_error "PostgreSQL : Indisponible"
        send_alert "critical" "Base de données PostgreSQL indisponible"
    fi
    
    # Redis
    if docker exec databot-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis : Connecté"
    else
        log_error "Redis : Indisponible"
        send_alert "critical" "Cache Redis indisponible"
    fi
}

# Génération de rapport
generate_report() {
    local report_file="/tmp/databot-health-$(date +%Y%m%d_%H%M%S).json"
    
    cat > "${report_file}" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "status": "$(check_containers && check_endpoints && echo "healthy" || echo "unhealthy")",
    "services": {
        "containers": $(docker ps --format "{{.Names}}: {{.Status}}" | jq -R -s -c 'split("\n")[:-1] | map(split(": ")) | map({(.[0]): .[1]}) | add'),
        "endpoints": {
            "api": "$(check_service_health "API" "http://localhost:8080/health" && echo "up" || echo "down")",
            "admin": "$(check_service_health "Admin" "http://localhost:8082/_stcore/health" && echo "up" || echo "down")",
            "nginx": "$(check_service_health "Nginx" "http://localhost:80/nginx-health" && echo "up" || echo "down")"
        }
    },
    "resources": {
        "cpu_usage": "$(docker stats --no-stream --format "{{.CPUPerc}}" | tail -n +2 | sed 's/%//' | awk '{sum+=$1} END {print sum}')%",
        "memory_usage": "$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')%",
        "disk_usage": "$(df / | tail -1 | awk '{print $5}')"
    }
}
EOF
    
    echo "${report_file}"
}

# Mode monitoring continu
continuous_monitoring() {
    log "Démarrage du monitoring continu (intervalle: ${MONITORING_INTERVAL}s)"
    
    while true; do
        log "=== Cycle de monitoring $(date) ==="
        
        check_containers
        check_endpoints
        check_system_resources
        check_docker_volumes
        check_database
        check_error_logs
        
        log "=== Fin du cycle ==="
        sleep "${MONITORING_INTERVAL}"
    done
}

# Fonction d'aide
show_help() {
    cat << EOF
DATA_BOT v4 - Script de monitoring

Usage: $0 [COMMAND] [OPTIONS]

COMMANDS:
    status          Vérification unique de l'état
    monitor         Monitoring continu
    report          Génère un rapport JSON
    containers      Vérifie uniquement les conteneurs
    endpoints       Vérifie uniquement les endpoints
    resources       Vérifie uniquement les ressources
    database        Vérifie uniquement la base de données

OPTIONS:
    -i, --interval SEC    Intervalle de monitoring (défaut: 30s)
    -w, --webhook URL     URL webhook pour les alertes
    -l, --log FILE        Fichier de log (défaut: /var/log/databot-monitor.log)
    -h, --help            Affiche cette aide

EXEMPLES:
    $0 status
    $0 monitor -i 60 -w https://hooks.slack.com/...
    $0 report > health_report.json

EOF
}

# Parsing des arguments
COMMAND="status"

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interval)
            MONITORING_INTERVAL="$2"
            shift 2
            ;;
        -w|--webhook)
            ALERT_WEBHOOK="$2"
            shift 2
            ;;
        -l|--log)
            LOG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        status|monitor|report|containers|endpoints|resources|database)
            COMMAND="$1"
            shift
            ;;
        *)
            echo "Option inconnue: $1"
            exit 1
            ;;
    esac
done

# Création du répertoire de logs
mkdir -p "$(dirname "${LOG_FILE}")"

# Exécution
case "${COMMAND}" in
    status)
        log "Vérification de l'état de DATA_BOT v4"
        check_containers && check_endpoints && check_system_resources && check_database
        log_success "Vérification terminée"
        ;;
    monitor)
        continuous_monitoring
        ;;
    report)
        generate_report
        ;;
    containers)
        check_containers
        ;;
    endpoints)
        check_endpoints
        ;;
    resources)
        check_system_resources
        ;;
    database)
        check_database
        ;;
esac