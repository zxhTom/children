import os
import sys
from pathlib import Path
import uvicorn

def main():
    repo_root = Path(__file__).resolve().parent.parent
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))
    os.chdir(str(backend_dir))

    host = os.environ.get("CHILDREN_HOST", "0.0.0.0")
    port = int(os.environ.get("CHILDREN_PORT", 8088))
    proxy_headers = os.environ.get("CHILDREN_PROXY_HEADERS", "true").lower() == "true"
    forwarded_ips = os.environ.get("CHILDREN_FORWARDED_IPS", "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        proxy_headers=proxy_headers,
        forwarded_allow_ips=forwarded_ips,
        log_level="info",
    )

if __name__ == "__main__":
    main()
