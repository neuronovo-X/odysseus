#!/usr/bin/env python3
"""Odysseus — first-time setup script.

Creates data directories, initializes the database, and sets up an
initial admin user. Safe to re-run (skips what already exists).
"""

import os
import shutil
import sys

# Ensure UTF-8 output on Windows so Cyrillic prints correctly
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.system("chcp 65001 >nul 2>&1")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

DIRS = [
    DATA_DIR,
    os.path.join(DATA_DIR, "uploads"),
    os.path.join(DATA_DIR, "personal_docs"),
    os.path.join(DATA_DIR, "personal_uploads"),
    os.path.join(DATA_DIR, "tts_cache"),
    os.path.join(DATA_DIR, "generated_images"),
    os.path.join(DATA_DIR, "deep_research"),
    os.path.join(DATA_DIR, "chroma"),
    os.path.join(DATA_DIR, "rag"),
    os.path.join(DATA_DIR, "memory_vectors"),
    os.path.join(BASE_DIR, "logs"),
]


def create_dirs():
    for d in DIRS:
        os.makedirs(d, exist_ok=True)
        print(f"  [ok] {os.path.relpath(d, BASE_DIR)}/")


def init_database():
    """Create all SQLAlchemy tables."""
    sys.path.insert(0, BASE_DIR)
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'app.db')}")

    from core.database import Base, engine
    Base.metadata.create_all(bind=engine)
    print("  [ok] База данных инициализирована")


def _prompt_admin_credentials():
    """Interactively ask for admin username and password when running in a terminal."""
    import getpass

    print()
    print("  Настройка учётной записи администратора:")
    print("  (Enter — оставить значение по умолчанию)")
    print()

    username = input("  Имя пользователя [admin]: ").strip().lower()
    if not username:
        username = "admin"

    while True:
        password = getpass.getpass("  Пароль: ")
        if not password:
            print("  Пароль не может быть пустым.")
            continue
        confirm = getpass.getpass("  Подтвердите пароль: ")
        if password != confirm:
            print("  Пароли не совпадают. Попробуйте ещё раз.")
            continue
        break

    return username, password


def create_default_admin():
    """Create an initial admin user if none exists."""
    auth_path = os.path.join(DATA_DIR, "auth.json")
    if os.path.exists(auth_path):
        print("  [skip] auth.json уже существует")
        return "exists"

    try:
        import bcrypt
        import json

        # Priority: env vars > interactive prompt > random password
        username = os.getenv("ODYSSEUS_ADMIN_USER", "").strip().lower()
        password = os.getenv("ODYSSEUS_ADMIN_PASSWORD", "").strip()

        if username and password:
            # Both provided via env — use them directly
            pass
        elif sys.stdin.isatty() and not os.getenv("ODYSSEUS_SKIP_ADMIN_PROMPT"):
            # Interactive terminal — ask the user
            username, password = _prompt_admin_credentials()
        else:
            # Non-interactive (Docker, CI) — fall back to generated password
            username = username or "admin"
            password = password or __import__("secrets").token_urlsafe(18)

        username = username or "admin"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        auth_data = {
            "users": {
                username: {
                    "password_hash": hashed,
                    "is_admin": True,
                }
            }
        }
        with open(auth_path, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=2)

        if sys.stdin.isatty() and not os.getenv("ODYSSEUS_ADMIN_PASSWORD"):
            print(f"  [ok] Учётная запись администратора создана ({username})")
        else:
            print(f"  [ok] Администратор создан ({username})")
            if not os.getenv("ODYSSEUS_ADMIN_PASSWORD"):
                print(f"        Временный пароль: {password}")
                print(f"        ** Смените пароль после первого входа. Укажите ODYSSEUS_ADMIN_PASSWORD для выбора своего. **")
        return "created"
    except ImportError:
        print("  [warn] bcrypt не установлен — создание администратора пропущено")
        print("         Выполните: pip install bcrypt")
        return "skipped"


def create_env():
    """Copy .env.example to .env if it doesn't exist."""
    env_path = os.path.join(BASE_DIR, ".env")
    example_path = os.path.join(BASE_DIR, ".env.example")
    if os.path.exists(env_path):
        print("  [skip] .env уже существует")
        return
    if os.path.exists(example_path):
        import shutil
        shutil.copy2(example_path, env_path)
        print("  [ok] .env создан из .env.example")
        print("        ** Укажите в .env адрес LLM-сервера и API-ключи **")
    else:
        print("  [warn] .env.example не найден — создайте .env вручную")


def check_deps():
    """Check for common missing dependencies."""
    missing = []
    for mod in ["fastapi", "uvicorn", "sqlalchemy", "bcrypt", "httpx", "dotenv"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"\n  [warn] Отсутствуют пакеты: {', '.join(missing)}")
        print(f"         Выполните: pip install -r requirements.txt")
    else:
        print("  [ok] Все основные зависимости установлены")

    if os.name != "nt" and shutil.which("tmux") is None:
        print("\n  [warn] tmux не найден")
        print("         Каталог моделей использует tmux для фоновых загрузок и запуска.")
        print("         Установите через менеджер пакетов вашей ОС, например:")
        if sys.platform == "darwin":
            print("           brew install tmux")
        else:
            print("           sudo apt install tmux")
            print("           sudo pacman -S tmux")
            print("           sudo dnf install tmux")
    elif os.name != "nt":
        print("  [ok] tmux установлен")


def main():
    print("\n=== Настройка Одиссеи ===\n")

    print("1. Создание директорий...")
    create_dirs()

    print("\n2. Файл окружения...")
    create_env()

    print("\n3. Проверка зависимостей...")
    check_deps()

    print("\n4. Инициализация базы данных...")
    try:
        init_database()
    except Exception as e:
        print(f"  [warn] Ошибка инициализации БД: {e}")
        print("         Это нормально, если зависимости ещё не установлены.")

    print("\n5. Создание администратора...")

    admin_status = "failed"

    try:
        admin_status = create_default_admin()
    except Exception as e:
        print(f"  [warn] Ошибка создания администратора: {e}")
        admin_status = "failed"

    print("\n=== Настройка завершена ===")
    if not os.getenv("ODYSSEUS_SKIP_RUN_HINT"):
        print(f"\nЗапустите сервер командой:")
        print(f"  python -m uvicorn app:app --host 127.0.0.1 --port 7000")
        print(f"\nЗатем откройте http://localhost:7000")

    if admin_status == "created":
        print("Войдите с учётными данными администратора.\n")
    elif admin_status == "exists":
        print("Войдите с существующими учётными данными администратора.\n")
    elif admin_status == "skipped":
        print("Администратор не создан: отсутствуют зависимости.\nВыполните 'pip install bcrypt' и запустите setup заново.\n")
    elif admin_status == "failed":
        print("Администратор не создан: системная ошибка.\nПроверьте права на запись в директорию 'data' и запустите setup заново.\n")
    else:
        print("Администратор не создан: системная ошибка.\nПроверьте права на запись в директорию 'data' и запустите setup заново.\n")


if __name__ == "__main__":
    main()
