"""
Development server runner for AlgoChanakya backend.
Run this file to start the FastAPI development server.

Usage:
    python run.py              # Default port 8001 (dev)
    python run.py --port 8001  # Explicit port

NOTE: Production uses port 8000. Use 8001 for development.
"""
import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AlgoChanakya backend server")
    parser.add_argument("--port", type=int, default=8001, help="Port to run on (default: 8001 for dev)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    print(f"Starting dev server on {args.host}:{args.port}")
    print("NOTE: Production runs on port 8000 - do not use that port for dev")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=True,
        log_level="info"
    )
