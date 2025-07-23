import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.config import Config
from src.database.database import DatabaseManager

async def show_stats():
    """Affiche les statistiques de l'archive"""
    async with DatabaseManager() as db:
        stats = await db.get_archive_stats()
        
        print("📊 STATISTIQUES D'ARCHIVE")
        print("━" * 40)
        print(f"🔍 Total découvert: {stats.total_discovered}")
        print(f"💾 Total téléchargé: {stats.total_downloaded}")
        print(f"📸 Total screenshots: {stats.total_screenshots}")
        print(f"❌ Total échecs: {stats.total_failed}")
        print(f"💽 Taille totale: {stats.total_size_mb:.2f} MB")
        print(f"🌐 Domaines explorés: {stats.domains_discovered}")
        
        if stats.total_discovered > 0:
            success_rate = ((stats.total_downloaded + stats.total_screenshots) / stats.total_discovered) * 100
            print(f"✅ Taux de réussite: {success_rate:.1f}%")

async def search_archive(query: str):
    """Recherche dans l'archive"""
    async with DatabaseManager() as db:
        results = await db.search_resources(query)
        
        print(f"🔍 Résultats pour '{query}': {len(results)} trouvés")
        print("━" * 50)
        
        for i, resource in enumerate(results[:10], 1):
            print(f"{i}. {resource.title or 'Sans titre'}")
            print(f"   URL: {resource.url}")
            print(f"   Status: {resource.status.value}")
            if resource.file_path:
                print(f"   Fichier: {resource.file_path}")
            if resource.screenshot_path:
                print(f"   Screenshot: {resource.screenshot_path}")
            print()

async def list_recent():
    """Liste les ressources récentes"""
    async with DatabaseManager() as db:
        from src.core.models import ArchiveStatus
        
        downloaded = await db.get_resources_by_status(ArchiveStatus.DOWNLOADED, 10)
        screenshots = await db.get_resources_by_status(ArchiveStatus.SCREENSHOT, 10)
        
        print("📥 DERNIERS TÉLÉCHARGEMENTS")
        print("━" * 40)
        for resource in downloaded:
            print(f"• {resource.title or resource.url[:50]}...")
            print(f"  {resource.archived_at}")
        
        print("\n📸 DERNIERS SCREENSHOTS")
        print("━" * 40)
        for resource in screenshots:
            print(f"• {resource.title or resource.url[:50]}...")
            print(f"  {resource.archived_at}")

async def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tools.py stats              # Afficher les statistiques")
        print("  python tools.py search <query>     # Rechercher dans l'archive")
        print("  python tools.py recent             # Lister les ressources récentes")
        return
    
    Config.setup_directories()
    
    command = sys.argv[1]
    
    if command == "stats":
        await show_stats()
    elif command == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        await search_archive(query)
    elif command == "recent":
        await list_recent()
    else:
        print("Commande inconnue")

if __name__ == "__main__":
    asyncio.run(main())
