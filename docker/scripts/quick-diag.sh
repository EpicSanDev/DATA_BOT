#!/bin/bash
# ==============================================================================
# Script de diagnostic rapide DATA_BOT v4
# ==============================================================================

set -euo pipefail

echo "🔍 Diagnostic DATA_BOT v4 - $(date)"
echo "=================================="

echo
echo "📦 État des conteneurs:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=databot" || echo "❌ Aucun conteneur trouvé"

echo
echo "🔍 Images disponibles:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" --filter "reference=databot/*" || echo "❌ Aucune image trouvée"

echo
echo "🌐 Test rapide des endpoints:"
endpoints=(
    "http://localhost:8080/health"
    "http://localhost:8082/health"
    "http://localhost:80/health"
)

for endpoint in "${endpoints[@]}"; do
    if curl -s -m 3 "$endpoint" > /dev/null 2>&1; then
        echo "✅ $endpoint : Accessible"
    else
        echo "❌ $endpoint : Non accessible"
    fi
done

echo
echo "📋 Logs récents (erreurs uniquement):"
for container in $(docker ps -a --format "{{.Names}}" --filter "name=databot" | head -3); do
    if [[ -n "$container" ]]; then
        echo "--- $container ---"
        docker logs --tail=5 "$container" 2>&1 | grep -iE "(error|exception|failed)" | head -3 || echo "Pas d'erreurs récentes"
    fi
done

echo
echo "🔧 Actions recommandées:"
echo "1. Vérifier les logs détaillés: docker logs <container_name>"
echo "2. Redémarrer un service: docker restart <container_name>"
echo "3. Monitoring continu: ./docker/scripts/monitor.sh monitor"
