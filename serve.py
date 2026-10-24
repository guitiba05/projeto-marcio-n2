"""Sobe o servidor local do módulo Trusses e abre a interface no navegador.

Uso:
    python serve.py                 # http://127.0.0.1:8000
    python serve.py --port 8123
    python serve.py --no-browser    # só sobe o servidor
"""

from __future__ import annotations

import argparse
import threading
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor local do módulo Trusses")
    parser.add_argument("--host", default="127.0.0.1", help="endereço (padrão: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="porta (padrão: 8000)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="não abrir o navegador automaticamente",
    )
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"
    print("=" * 68)
    print("  Treliças — módulo Trusses (versão própria do MdSolids)")
    print(f"  interface: {url}")
    print(f"  API docs:  {url}docs")
    print("  Ctrl+C para encerrar")
    print("=" * 68)

    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    import uvicorn

    uvicorn.run(
        "app.api.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
