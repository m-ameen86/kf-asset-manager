"""Launch the KF Asset Manager local app:  python -m kf_asset_manager [--root PATH]"""

import argparse
import threading
import webbrowser

from . import config
from .app import app, open_root, set_db_path, DB_PATH


def main():
    ap = argparse.ArgumentParser(description=config.APP_NAME)
    ap.add_argument("--root", help="asset folder to open immediately")
    ap.add_argument("--db", help="database file location (default: ./kf_assets.db)")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if args.db:
        set_db_path(args.db)
    if args.root:
        open_root(args.root)

    url = f"http://127.0.0.1:{args.port}/"
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"{config.APP_NAME} running at {url}  (Ctrl+C to stop)")
    app.run(port=args.port, debug=False)


if __name__ == "__main__":
    main()
