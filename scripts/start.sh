#!/bin/bash

# Script de démarrage du Bot d'Archivage Internet

echo "🤖 Bot d'Archivage Internet Automatique"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vérifier si Ollama est démarré
echo "🔍 Vérification d'Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama n'est pas accessible sur localhost:11434"
    echo "💡 Démarrez Ollama avec: ollama serve"
    echo "💡 Puis téléchargez un modèle: ollama pull llama2"
    exit 1
fi

echo "✅ Ollama est accessible"

# Vérifier les dépendances Python
echo "🔍 Vérification des dépendances..."
if ! python -c "import requests, beautifulsoup4, selenium, aiohttp" 2>/dev/null; then
    echo "❌ Dépendances manquantes"
    echo "💡 Installez avec: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Dépendances OK"

# Proposer les modes d'exécution
echo ""
echo "🎮 Modes disponibles:"
echo "1. Mode Continu (explore et traite automatiquement)"
echo "2. Mode Exploration (découvre nouvelles URLs)"
echo "3. Mode Traitement (traite URLs en attente)"
echo "4. Afficher les statistiques"
echo ""

read -p "Choisissez un mode (1-4): " choice

case $choice in
    1)
        echo "🚀 Démarrage en mode continu..."
        python main_robust.py --mode continuous
        ;;
    2)
        echo "🔍 Démarrage en mode exploration..."
        python main_robust.py --mode explore
        ;;
    3)
        echo "⚙️ Démarrage en mode traitement..."
        python main_robust.py --mode process
        ;;
    4)
        echo "📊 Affichage des statistiques..."
        python tools.py stats
        ;;
    *)
        echo "❌ Choix invalide"
        exit 1
        ;;
esac
