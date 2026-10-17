"""
Climate Trend Analyzer - Local Development Server Runner
"""
import sys

def main():
    try:
        import uvicorn
    except ImportError:
        print("[ERROR] uvicorn is not installed in the active environment.", file=sys.stderr)
        print("Please activate your virtual environment (.venv) and run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print(f" Climate Trend Analyzer - Development Server")
    print(f" Python: {sys.version.split()[0]}")
    print(f" Host: http://127.0.0.1:8000")
    print(f" Health Check: http://127.0.0.1:8000/health")
    print("=" * 60)

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
