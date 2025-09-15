# start_api.py - Démarrage API RAG simplifié
# =============================================================================

import uvicorn
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    
    print(f"🚀 API RAG SIRH: http://localhost:{args.port}")
    print(f"📚 Documentation: http://localhost:{args.port}/docs")
    
    uvicorn.run(
        "rag.api:app",
        host="127.0.0.1", 
        port=args.port,
        reload=args.dev
    )

if __name__ == "__main__":
    main()