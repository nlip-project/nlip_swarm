import sys
from pathlib import Path
import importlib
import runpy
import uvicorn

# ensure the backend package dir is on sys.path so "import app" works
sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    # import the main module and select the ASGI app object if present
    try:
        module = importlib.import_module("app.system.main")
    except Exception:
        # fallback: execute the module as a script (runs its __main__ block)
        runpy.run_module("app.system.main", run_name="__main__")
        sys.exit(0)

    if hasattr(module, "app"):
        asgi_app = module.app
        uvicorn.run(asgi_app, host="127.0.0.1", port=8024, reload=True)
    elif hasattr(module, "ms"):
        asgi_app = module.ms
        uvicorn.run(asgi_app, host="127.0.0.1", port=8024, reload=True)
    else:
        # if neither object exists, execute the module's __main__ so main.py behaves as before
        runpy.run_module("app.system.main", run_name="__main__")