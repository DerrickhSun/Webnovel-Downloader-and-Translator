"""
Terminal-only entry point (original text menu). Use if you prefer not to use the browser menu.

Run from the project root:
    python terminal_main.py
"""

from main import TerminalPrompts, download_novel, package_novel, update_library


def _print_main_menu():
    print()
    print("Webnovel Downloader and Translator")
    print("----------------------------------")
    print("  1) Download novel")
    print("  2) Update library (add/remove titles in data/)")
    print("  3) Package novel (finished translations → volume)")
    print("  4) Exit")
    print()
    print('You can enter the number or a phrase (e.g. "download novel", "update library").')


def main():
    prompts = TerminalPrompts()
    while True:
        _print_main_menu()
        choice = input("What would you like to do? ").strip().lower()

        if choice in ("4", "exit", "quit", "q"):
            print("Goodbye.")
            break

        if choice in ("1", "download", "download novel"):
            download_novel(prompts=prompts)
        elif choice in ("2", "update", "update library"):
            update_library(prompts=prompts)
        elif choice in ("3", "package", "package novel"):
            package_novel(prompts=prompts)
        else:
            print("Unrecognized choice. Enter 1–4 or a matching phrase.")


if __name__ == "__main__":
    main()
