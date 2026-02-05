import sys


def main() -> int:
    args = [a for a in sys.argv[1:] if a]
    if "--tk" in args or "tk" in args:
        from .gui import main as tk_main

        tk_main()
        return 0

    from .ui.qt_main import main as qt_main

    return qt_main()


if __name__ == "__main__":
    raise SystemExit(main())
