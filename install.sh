#!/bin/bash

echo "🔧 Installation des dépendances pour le Bot d'Archivage"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trouvé. Installez Python 3.8+"
    exit 1
fi

echo "✅ Python trouvé: $(python3 --version)"

# Installer les dépendances Python
echo "📦 Installation des dépendances Python..."
pip install requests beautifulsoup4 aiohttp aiofiles python-dotenv
pip install fake-useragent validators tqdm

# Selenium (optionnel pour screenshots)
echo "📸 Installation de Selenium (optionnel)..."
pip install selenium webdriver-manager pillow || echo "⚠️ Selenium non installé (screenshots désactivés)"

# Vérifier/installer Chrome
echo "🌐 Vérification de Chrome..."
if [[ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    echo "✅ Google Chrome trouvé"
elif [[ -f "/Applications/Chromium.app/Contents/MacOS/Chromium" ]]; then
    echo "✅ Chromium trouvé"
else
    echo "⚠️ Chrome/Chromium non trouvé"
    echo "💡 Pour activer les screenshots, installez:"
    echo "   - Google Chrome: https://www.google.com/chrome/"
    echo "   - Ou Chromium: brew install chromium"
fi

# Vérifier/installer Ollama
echo "🤖 Vérification d'Ollama..."
if command -v ollama &> /dev/null; then
    echo "✅ Ollama trouvé: $(ollama --version)"
    
    # Vérifier si le service est démarré
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Service Ollama actif"
    else
        echo "⚠️ Service Ollama non actif"
        echo "💡 Démarrez avec: ollama serve"
    fi
    
    # Vérifier les modèles
    echo "📋 Modèles Ollama disponibles:"
    ollama list || echo "Aucun modèle installé"
    
    echo "💡 Pour télécharger un modèle: ollama pull llama2"
    
else
    echo "❌ Ollama non trouvé"
    echo "💡 Installez Ollama:"
    echo "   curl -fsSL https://ollama.com/install.sh | sh"
    echo "   Ou: brew install ollama"
fi

echo ""
echo "🎯 Installation terminée!"
echo "📚 Lisez le README.md pour les instructions d'utilisation"
echo "🚀 Démarrez avec: ./start.sh"
