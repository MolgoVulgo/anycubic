import argparse
import json
from pathlib import Path

from .client import CloudClient
from .api import get_quota, list_files, get_download_url, delete_files
from .session_store import (
    DEFAULT_SESSION_PATH,
    load_cookies_from_json,
    load_tokens_from_json,
    load_session,
    load_session_from_har,
    save_session,
)
from .utils import format_bytes


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='accloud')
    sub = p.add_subparsers(dest='cmd', required=True)

    auth = sub.add_parser('auth')
    auth_sub = auth.add_subparsers(dest='auth_cmd', required=True)
    auth_import = auth_sub.add_parser('import')
    auth_import.add_argument('--cookies')
    auth_import.add_argument('--tokens')
    auth_import.add_argument('--out', default=DEFAULT_SESSION_PATH)
    auth_import.add_argument('--from-har')

    quota = sub.add_parser('quota')
    quota.add_argument('--json', action='store_true')
    quota.add_argument('--session', default=DEFAULT_SESSION_PATH)

    ls = sub.add_parser('ls')
    ls.add_argument('--page', type=int, default=1)
    ls.add_argument('--limit', type=int, default=10)
    ls.add_argument('--json', action='store_true')
    ls.add_argument('--session', default=DEFAULT_SESSION_PATH)

    pull = sub.add_parser('pull')
    pull.add_argument('file_id')
    pull.add_argument('--session', default=DEFAULT_SESSION_PATH)

    rm = sub.add_parser('rm')
    rm.add_argument('file_id')
    rm.add_argument('--session', default=DEFAULT_SESSION_PATH)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == 'auth' and args.auth_cmd == 'import':
        if args.from_har:
            session = load_session_from_har(args.from_har)
            save_session(args.out, session['cookies'], session.get('tokens', {}))
            print(f'OK: session saved to {args.out} (from HAR)')
            return 0

        if not args.cookies:
            raise SystemExit('Missing --cookies (or use --from-har <path>)')

        cookies = load_cookies_from_json(args.cookies)
        tokens = load_tokens_from_json(args.tokens) if args.tokens else {}
        save_session(args.out, cookies, tokens)
        print(f'OK: session saved to {args.out}')
        return 0

    cookies = None
    session_path = getattr(args, 'session', DEFAULT_SESSION_PATH)
    tokens = {}
    if session_path and Path(session_path).exists():
        session = load_session(session_path)
        cookies = session.get('cookies')
        tokens = session.get('tokens', {})

    client = CloudClient(cookies=cookies, tokens=tokens)

    if args.cmd == 'quota':
        q = get_quota(client)
        if args.json:
            print(json.dumps({'total_bytes': q.total_bytes, 'used_bytes': q.used_bytes, 'free_bytes': q.free_bytes, 'used_percent': q.used_percent}, indent=2))
        else:
            print(f"Used {format_bytes(q.used_bytes)} / {format_bytes(q.total_bytes)} ({q.used_percent:.1f}%)")
        return 0

    if args.cmd == 'ls':
        items = list_files(client, page=args.page, limit=args.limit)
        if args.json:
            print(json.dumps([item.__dict__ for item in items], indent=2))
        else:
            for item in items:
                print(f"{item.id}	{item.size_bytes}	{item.name}")
        return 0

    if args.cmd == 'pull':
        url = get_download_url(client, args.file_id)
        print(url)
        return 0

    if args.cmd == 'rm':
        delete_files(client, [args.file_id])
        print('OK')
        return 0

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
