# =============================================================================
# start_rag_api.py - Script de démarrage
# =============================================================================

#!/usr/bin/env python3
"""
Script de démarrage pour l'API RAG SIRH

Usage:
    python start_rag_api.py                # Démarrage normal
    python start_rag_api.py --dev          # Mode développement
    python start_rag_api.py --port 8001    # Port personnalisé
"""

import argparse
import uvicorn
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="API RAG SIRH - Flow Solutions")
    parser.add_argument("--host", default="127.0.0.1", help="Host à utiliser")
    parser.add_argument("--port", type=int, default=8000, help="Port à utiliser")
    parser.add_argument("--dev", action="store_true", help="Mode développement")
    parser.add_argument("--reload", action="store_true", help="Auto-reload")
    
    args = parser.parse_args()
    
    print("🚀 Démarrage de l'API RAG SIRH...")
    print(f"📍 URL: http://{args.host}:{args.port}")
    print(f"📚 Documentation: http://{args.host}:{args.port}/docs")
    print(f"🔄 Mode: {'Développement' if args.dev else 'Production'}")
    
    # Configuration uvicorn
    config = {
        "app": "rag.api:app",
        "host": args.host,
        "port": args.port,
        "reload": args.dev or args.reload,
        "log_level": "debug" if args.dev else "info",
    }
    
    if args.dev:
        config.update({
            "reload_dirs": [str(Path.cwd())],
            "reload_excludes": ["*.pyc", "__pycache__", ".git"]
        })
    
    uvicorn.run(**config)

if __name__ == "__main__":
    main()
