#!/usr/bin/env python3
"""
BioResearch Assistant — Lokaler Installer
Synaptic Four

Installiert das vollständige System via Docker:
- PostgreSQL + pgvector
- Backend (FastAPI)
- Frontend (React/nginx)
- Ollama (lokales LLM, DSGVO-konform)
- BLAST (Sequenzsuche)
- Nextflow (Pipeline Engine)

Verwendung:
  python install.py              # Interaktiv
  python install.py --minimal    # Nur Core
  python install.py --unattended # Alle Defaults
  python install.py start        # Bestehende Installation starten
  python install.py stop         # Stoppen (Daten behalten)
  python install.py destroy      # Stoppen + Volumes entfernen
  python install.py --install-dir /opt/bioresearch
"""

import subprocess
import sys
import os
import secrets
import shutil
import json
import time
import urllib.request
from pathlib import Path


# ── Farben für Terminal Output ────────────────────────
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def ok(msg):
    print(f"{Colors.GREEN}  ✓ {msg}{Colors.RESET}")


def info(msg):
    print(f"{Colors.BLUE}  ℹ {msg}{Colors.RESET}")


def warn(msg):
    print(f"{Colors.YELLOW}  ⚠ {msg}{Colors.RESET}")


def err(msg):
    print(f"{Colors.RED}  ✗ {msg}{Colors.RESET}")


def step(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {msg}{Colors.RESET}")


def header():
    print(
        f"""
{Colors.BOLD}{Colors.BLUE}
╔═══════════════════════════════════════════════════╗
║   BioResearch Assistant — Installer v1.0.0        ║
║   Synaptic Four                                   ║
║   Proudly developed by individuals on the         ║
║   autism spectrum in Germany                      ║
╚═══════════════════════════════════════════════════╝
{Colors.RESET}"""
    )


# ── DB-Passwort-Check (bei bestehendem Volume) ─────────
def check_db_password_match(config: dict) -> bool:
    """Check if DB password matches existing volume.

    Runs psql inside the db container with PGPASSWORD from config.
    Returns True if connection succeeds, False otherwise.
    """
    install_dir = config.get("install_dir") or os.getcwd()
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.full.yml",
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "bioresearch",
                "-c",
                "SELECT 1",
            ],
            capture_output=True,
            timeout=15,
            cwd=install_dir,
            env={**os.environ, "PGPASSWORD": config.get("db_password", "")},
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def load_env_config(install_dir: Path) -> dict | None:
    """Load config from existing .env for start command."""
    env_path = install_dir / ".env"
    if not env_path.exists():
        return None
    config = {"install_dir": str(install_dir)}
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key == "POSTGRES_PASSWORD":
                config["db_password"] = val
                break
    return config if config.get("db_password") else None


def check_existing_installation(install_dir: Path) -> bool:
    """Check if installation already exists."""
    return (install_dir / "docker-compose.full.yml").exists()


def cleanup_existing(install_dir: Path) -> None:
    """Stop and remove existing Docker installation."""
    info("Stoppe bestehende Installation...")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(install_dir / "docker-compose.full.yml"),
            "down",
            "-v",
            "--remove-orphans",
        ],
        cwd=install_dir,
        capture_output=True,
    )
    ok("Bestehende Installation gestoppt")


def is_running(install_dir: Path) -> bool:
    """Check if Docker Compose is already running for this install."""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(install_dir / "docker-compose.full.yml"),
            "ps",
            "--quiet",
        ],
        cwd=install_dir,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout and result.stdout.strip())


def find_existing_ollama() -> str | None:
    """Return Ollama container name if running."""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    for name in (result.stdout or "").strip().split("\n"):
        if name and "ollama" in name.lower():
            return name
    return None


def find_ollama_volume() -> str | None:
    """Return Ollama volume name if exists."""
    result = subprocess.run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
    )
    for vol in (result.stdout or "").strip().split("\n"):
        if vol and "ollama" in vol.lower():
            return vol
    return None


def wait_for_backend(install_dir: Path, port: int = 8000, max_wait: int = 60) -> bool:
    """Wait until backend API responds."""
    url = f"http://localhost:{port}/api/v1/health"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


# ── Voraussetzungen prüfen ────────────────────────────
def check_prerequisites() -> bool:
    step("Prüfe Voraussetzungen")
    all_ok = True

    # Docker
    if shutil.which("docker"):
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                ok("Docker läuft")
            else:
                err("Docker ist installiert aber läuft nicht")
                info("Bitte Docker Desktop starten")
                all_ok = False
        except Exception:
            err("Docker nicht erreichbar")
            all_ok = False
    else:
        err("Docker nicht installiert")
        info("Bitte von https://docker.com installieren")
        all_ok = False

    # Docker Compose
    compose_ok = False
    for cmd in [
        ["docker", "compose", "version"],
        ["docker-compose", "--version"],
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0:
                ok("Docker Compose verfügbar")
                compose_ok = True
                break
        except Exception:
            continue
    if not compose_ok:
        err("Docker Compose nicht gefunden")
        all_ok = False

    # Python Version
    if sys.version_info >= (3, 11):
        ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    else:
        err(
            f"Python 3.11+ benötigt "
            f"(aktuell: {sys.version_info.major}.{sys.version_info.minor})"
        )
        all_ok = False

    # Git
    if shutil.which("git"):
        ok("Git verfügbar")
    else:
        err("Git nicht gefunden")
        info("Bitte von https://git-scm.com installieren")
        all_ok = False

    # Freier Speicherplatz
    disk = shutil.disk_usage(".")
    free_gb = disk.free / (1024**3)
    if free_gb >= 20:
        ok(f"{free_gb:.1f} GB freier Speicher")
    elif free_gb >= 10:
        warn(f"Nur {free_gb:.1f} GB frei (20 GB empfohlen für Ollama-Modelle)")
    else:
        err(f"Zu wenig Speicher: {free_gb:.1f} GB (mind. 10 GB benötigt)")
        all_ok = False

    # RAM (optional via psutil)
    try:
        import psutil

        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb >= 16:
            ok(f"{ram_gb:.0f} GB RAM")
        elif ram_gb >= 8:
            warn(f"Nur {ram_gb:.0f} GB RAM (16 GB für Ollama empfohlen)")
        else:
            warn(
                f"Wenig RAM: {ram_gb:.0f} GB — Ollama wird möglicherweise langsam sein"
            )
    except ImportError:
        info("psutil nicht installiert — RAM-Check übersprungen")

    return all_ok


# ── Interaktive Konfiguration ─────────────────────────
def configure(
    unattended: bool = False,
    install_dir_arg: str | None = None,
) -> dict:
    step("Konfiguration")

    if unattended:
        info("Unattended Modus — nutze alle Defaults")

    def ask(prompt, default, secret=False):
        if unattended:
            return default
        display = "[auto-generiert]" if secret else default
        val = input(f"  {prompt} [{display}]: ").strip()
        return val if val else default

    def ask_bool(prompt, default=True):
        if unattended:
            return default
        d = "J/n" if default else "j/N"
        val = input(f"  {prompt} ({d}): ").strip().lower()
        if not val:
            return default
        return val in ("j", "ja", "y", "yes")

    config = {}

    # Basis
    print(f"\n  {Colors.BOLD}Basis:{Colors.RESET}")
    default_dir = install_dir_arg or str(Path.home() / "bioresearch")
    config["install_dir"] = ask("Installationsverzeichnis", default_dir)
    install_dir = Path(config["install_dir"])

    if not unattended and (install_dir / "docker-compose.full.yml").exists():
        print(f"\n⚠️  Bestehende Installation: {install_dir}")
        running = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(install_dir / "docker-compose.full.yml"),
                "ps",
                "--quiet",
            ],
            cwd=install_dir,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if running:
            print("   Docker Compose läuft gerade.")
            stop = input("   Stoppen und neu installieren? [j/N]: ").strip()
            if stop.lower() == "j":
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(install_dir / "docker-compose.full.yml"),
                        "down",
                        "--remove-orphans",
                    ],
                    cwd=install_dir,
                )
                ok("Gestoppt")
            else:
                print("Abgebrochen.")
                sys.exit(0)
        else:
            overwrite = input(
                "   Überschreiben? Volumes bleiben erhalten. [j/N]: "
            ).strip()
            if overwrite.lower() != "j":
                print("Abgebrochen.")
                sys.exit(0)

    # Prüfe ob bereits eine .env existiert — bestehende Secrets wiederverwenden
    existing_env = Path(config["install_dir"]) / ".env"
    existing_secrets = {}
    if existing_env.exists():
        info("Bestehende .env gefunden — lese vorhandene Secrets...")
        for line in existing_env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                existing_secrets[key.strip()] = val.strip()
        ok("Bestehende Secrets werden wiederverwendet")

    config["db_password"] = existing_secrets.get(
        "POSTGRES_PASSWORD",
        secrets.token_urlsafe(32),
    )
    config["jwt_secret"] = existing_secrets.get(
        "JWT_SECRET",
        secrets.token_urlsafe(64),
    )
    config["encryption_key"] = existing_secrets.get(
        "PSEUDONYMIZATION_ENCRYPTION_KEY",
        secrets.token_hex(32),
    )

    config["app_version"] = "1.0.0"
    config["institution"] = ask("Name der Institution", "Meine Institution")

    # Ports
    print(f"\n  {Colors.BOLD}Ports:{Colors.RESET}")
    config["frontend_port"] = ask("Frontend Port", "3000")
    config["backend_port"] = ask("Backend Port", "8000")
    config["db_port"] = ask("PostgreSQL Port", "5432")
    config["ollama_port"] = ask("Ollama Port", "11434")

    # LLM
    print(f"\n  {Colors.BOLD}LLM / KI:{Colors.RESET}")
    config["use_ollama"] = ask_bool(
        "Ollama installieren? (lokal, DSGVO-konform)",
        True,
    )
    if config["use_ollama"]:
        print(f"\n{Colors.CYAN}Hardware-Profil:{Colors.RESET}")
        print("  1) Laptop / klein (8-16 GB RAM, ohne starke GPU)")
        print("  2) Workstation (24-64 GB RAM, Consumer GPU)")
        print("  3) Institut-Server (>=100 GB RAM, z.B. NVIDIA A100)")
        print("  4) Benutzerdefiniert")
        if unattended:
            hw_choice = "2"
        else:
            hw_choice = input("  Profil [2=Workstation]: ").strip() or "2"

        hardware_profiles = {
            "1": {
                "name": "Laptop / klein",
                "recommended": ["llama3.2:3b", "gemma3:4b", "phi3", "mistral"],
                "default_model": "llama3.2:3b",
            },
            "2": {
                "name": "Workstation",
                "recommended": [
                    "mistral",
                    "qwen2.5:7b",
                    "deepseek-r1:8b",
                    "gpt-oss:20b",
                ],
                "default_model": "mistral",
            },
            "3": {
                "name": "Institut-Server (A100/100GB+)",
                "recommended": [
                    "gpt-oss:120b",
                    "deepseek-r1:70b",
                    "qwen2.5:32b",
                    "qwen2.5:72b",
                    "gpt-oss:20b",
                ],
                "default_model": "gpt-oss:120b",
            },
            "4": {
                "name": "Benutzerdefiniert",
                "recommended": [],
                "default_model": "mistral",
            },
        }
        selected_profile = hardware_profiles.get(hw_choice, hardware_profiles["2"])
        config["hardware_profile"] = selected_profile["name"]

        print(f"\n{Colors.CYAN}Ollama Modell:{Colors.RESET}")
        if selected_profile["recommended"]:
            print(
                f"  {Colors.YELLOW}Empfohlen für {selected_profile['name']}:{Colors.RESET}"
            )
            for model_name in selected_profile["recommended"]:
                print(f"   - {model_name}")
            print()
        print("  Verfügbare Modelle:")
        print("  1) mistral       (7B, robust, ~4.4 GB)")
        print("  2) llama3.2:3b   (3B, effizient, ~2.0 GB)")
        print("  3) gemma3:4b     (Google open model, ~3.3 GB)")
        print("  4) qwen2.5:7b    (Alibaba open model, ~4.7 GB)")
        print("  5) deepseek-r1:8b (Reasoning, ~5.2 GB)")
        print("  6) gpt-oss:20b   (OpenAI open-weight, ~14 GB)")
        print("  7) gpt-oss:120b  (OpenAI open-weight, ~65 GB)")
        print("  8) deepseek-r1:70b (Reasoning, ~43 GB)")
        print("  9) qwen2.5:32b   (Alibaba open model, ~20 GB)")
        print(" 10) qwen2.5:72b   (Alibaba open model, ~47 GB)")
        print(" 11) phi3          (3.8B, schnell, ~2.3 GB)")
        print(" 12) Eigenes Modell eingeben")
        print()
        print(f"  {Colors.YELLOW}Beispiel für MacBook Air M4:")
        print(f"  llama3.2:3b, gemma3:4b oder phi3 (weniger RAM){Colors.RESET}")
        if unattended:
            model_choice = "1"
        else:
            model_choice = input("  Modell [1=mistral]: ").strip() or "1"
        model_map = {
            "1": "mistral",
            "2": "llama3.2:3b",
            "3": "gemma3:4b",
            "4": "qwen2.5:7b",
            "5": "deepseek-r1:8b",
            "6": "gpt-oss:20b",
            "7": "gpt-oss:120b",
            "8": "deepseek-r1:70b",
            "9": "qwen2.5:32b",
            "10": "qwen2.5:72b",
            "11": "phi3",
        }
        if model_choice in model_map:
            config["ollama_model"] = model_map[model_choice]
        elif model_choice == "12":
            config["ollama_model"] = (
                input("  Modell Name (z.B. mistral, qwen2.5:14b): ").strip() or "mistral"
            )
        else:
            config["ollama_model"] = selected_profile["default_model"]
        ok(f"Ollama Modell: {config['ollama_model']}")
        existing_ollama = find_existing_ollama()
        ollama_volume = find_ollama_volume()
        if existing_ollama or ollama_volume:
            print(
                f"\n{Colors.GREEN}  ✓ Bestehende Ollama-Installation gefunden!{Colors.RESET}"
            )
            if existing_ollama:
                print(f"     Container: {existing_ollama}")
            if ollama_volume:
                print(f"     Volume: {ollama_volume}")
            if not unattended:
                reuse = input("  Ollama wiederverwenden? [J/n]: ").strip()
                config["reuse_ollama"] = reuse.lower() != "n"
            else:
                config["reuse_ollama"] = True
            if config.get("reuse_ollama"):
                config["ollama_volume"] = ollama_volume
        else:
            config["reuse_ollama"] = False
            config["ollama_volume"] = None
    else:
        config["anthropic_key"] = ask("Anthropic API Key (optional)", "")
        config["hardware_profile"] = "externe API"
        config["reuse_ollama"] = False
        config["ollama_volume"] = None

    # Optionale Komponenten
    print(f"\n  {Colors.BOLD}Optionale Komponenten:{Colors.RESET}")
    config["install_blast"] = ask_bool("BLAST installieren? (Sequenzsuche)", True)
    config["install_nextflow"] = ask_bool(
        "Nextflow installieren? (Pipeline Engine)", True
    )

    # Isolation Mode
    print(f"\n  {Colors.BOLD}Datenisolation:{Colors.RESET}")
    print(
        "  1) user  — Jeder Nutzer sieht nur seine eigenen Daten (empfohlen für Klinik)"
    )
    print("  2) team  — Team teilt Daten (empfohlen für Forschungsgruppen)")
    print("  3) open  — Alle sehen alles (nur für Demo/Entwicklung)")
    if not unattended:
        choice = input("  Wahl [1]: ").strip() or "1"
    else:
        choice = "1"
    config["isolation_mode"] = {"1": "user", "2": "team", "3": "open"}.get(
        choice, "user"
    )

    # Demo-Daten
    print(f"\n  {Colors.BOLD}Demo-Daten:{Colors.RESET}")
    if unattended:
        config["seed_demo_data"] = False
    else:
        demo = input(
            "\n  Demo-Daten laden? (Papers, Phenopacket,\n"
            "  Notebook, DRS-Dateien für Tests) [j/N]: "
        ).strip()
        config["seed_demo_data"] = demo.lower() == "j"

    # De-Pseudonymisierung Zugriff
    print(f"\n  {Colors.BOLD}De-Pseudonymisierung:{Colors.RESET}")
    print("  1) owner — Nur der pseudonymisierende User")
    print("  2) team  — Ganzes Team")
    print("  3) admin — Nur Admins")
    if not unattended:
        dchoice = input("  Wahl [1]: ").strip() or "1"
    else:
        dchoice = "1"
    config["depseudo_access"] = {
        "1": "owner",
        "2": "team",
        "3": "admin",
    }.get(dchoice, "owner")

    return config


# ── .env Datei generieren ─────────────────────────────
def generate_env(config: dict, install_dir: Path):
    step("Generiere Konfigurationsdateien")

    env_content = f"""# BioResearch Assistant — Konfiguration
# Generiert von install.py am {time.strftime("%Y-%m-%d %H:%M")}
# ACHTUNG: Diese Datei enthält Secrets —
#          niemals in Git committen!

# ── App ──────────────────────────────────────────────
APP_VERSION={config["app_version"]}
ENVIRONMENT=production
INSTITUTION={config["institution"]}

# ── Datenbank ─────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://bioresearch:{config["db_password"]}@db:5432/bioresearch
POSTGRES_USER=bioresearch
POSTGRES_PASSWORD={config["db_password"]}
POSTGRES_DB=bioresearch

# ── Security ──────────────────────────────────────────
JWT_SECRET={config["jwt_secret"]}
JWT_ALGORITHM=HS256
PSEUDONYMIZATION_ENCRYPTION_KEY={config["encryption_key"]}

# ── LLM ───────────────────────────────────────────────
LLM_PROVIDER={"ollama" if config.get("use_ollama") else "anthropic"}
OLLAMA_URL=http://ollama:{config["ollama_port"]}
OLLAMA_MODEL={config.get("ollama_model", "mistral")}
ANTHROPIC_API_KEY={config.get("anthropic_key", "")}

# ── Isolation & Zugriff ───────────────────────────────
ISOLATION_MODE={config["isolation_mode"]}
DEPSEUDO_ACCESS={config["depseudo_access"]}

# ── Deployment ────────────────────────────────────────
DEPLOYMENT=local
DRS_DATA_DIR=/data/drs

# ── Ports ─────────────────────────────────────────────
FRONTEND_PORT={config["frontend_port"]}
BACKEND_PORT={config["backend_port"]}
DB_PORT={config["db_port"]}
OLLAMA_PORT={config["ollama_port"]}
"""

    (install_dir / ".env").write_text(env_content)
    ok(".env erstellt")

    frontend_env = f"""VITE_API_URL=http://localhost:{config["backend_port"]}
VITE_APP_VERSION={config["app_version"]}
VITE_DEPLOYMENT=local
VITE_INSTITUTION={config["institution"]}
"""
    (install_dir / ".env.frontend").write_text(frontend_env)
    ok(".env.frontend erstellt")


# ── docker-compose.full.yml generieren ───────────────
def generate_docker_compose(config: dict, install_dir: Path):
    step("Generiere Docker Compose Konfiguration")

    # depends_on für backend: db (required) + optional ollama
    depends_on_lines = ["      db:", "        condition: service_healthy"]
    if config.get("use_ollama"):
        depends_on_lines.append("      ollama:")
        depends_on_lines.append("        condition: service_started")
    depends_on_str = "\n".join(depends_on_lines)

    optional_services = ""
    if config.get("use_ollama"):
        ollama_model = config.get("ollama_model", "mistral")
        if config.get("reuse_ollama"):
            optional_services += f"""
  ollama:
    image: ollama/ollama:latest
    ports:
      - "{config["ollama_port"]}:11434"
    volumes:
      - ollama_data:/root/.ollama
    entrypoint: ["ollama", "serve"]
    restart: unless-stopped
"""
        else:
            optional_services += f"""
  ollama:
    image: ollama/ollama:latest
    ports:
      - "{config["ollama_port"]}:11434"
    volumes:
      - ollama_data:/root/.ollama
    entrypoint: >
      sh -c "ollama serve &
             sleep 5 &&
             ollama pull {ollama_model} &&
             wait"
    restart: unless-stopped
"""
    if config.get("install_blast"):
        optional_services += """
  blast:
    image: ncbi/blast:2.15.0
    platform: linux/amd64
    volumes:
      - blast_data:/blast/db
    command: tail -f /dev/null
    restart: unless-stopped
"""
    if config.get("install_nextflow"):
        # Nextflow existiert nicht als öffentliches Docker Image —
        # wird als Binary im Backend-Container installiert via requirements.
        # Kein separater Service nötig.
        pass

    ollama_vol = config.get("ollama_volume") if config.get("reuse_ollama") else None
    ollama_volume_spec = (
        f"\n    external: true\n    name: {ollama_vol}" if ollama_vol else ""
    )

    compose = f"""# BioResearch Assistant — Docker Compose (Vollinstallation)
# Generiert von install.py v1.0.0

services:

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: bioresearch
      POSTGRES_PASSWORD: {config["db_password"]}
      POSTGRES_DB: bioresearch
    ports:
      - "{config["db_port"]}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bioresearch"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "{config["backend_port"]}:8000"
    env_file:
      - .env
    volumes:
      - drs_data:/data/drs
    depends_on:
{depends_on_str}
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_URL: http://localhost:{config["backend_port"]}
        VITE_APP_VERSION: {config["app_version"]}
        VITE_DEPLOYMENT: local
        VITE_INSTITUTION: {config["institution"]}
    ports:
      - "{config["frontend_port"]}:80"
    depends_on:
      - backend
    restart: unless-stopped
{optional_services}

volumes:
  postgres_data:
  drs_data:
  blast_data:
  ollama_data:{ollama_volume_spec}
"""

    (install_dir / "docker-compose.full.yml").write_text(compose)
    ok("docker-compose.full.yml erstellt")

    # Wenn bei install() bestehende DB-Volumes ein anderes Passwort haben als
    # die aktuelle .env (z. B. nach Passwortänderung), erkennt install() das
    # nach dem Start der DB per check_db_password_match() und entfernt die
    # Volumes (down -v), startet die DB neu und fährt mit Migrationen fort.


# ── System installieren ───────────────────────────────
def install(config: dict, install_dir: Path) -> bool:
    step("Installiere BioResearch Assistant")
    install_dir = Path(config["install_dir"])
    install_dir.mkdir(parents=True, exist_ok=True)
    ok(f"Installationsverzeichnis: {install_dir}")
    os.chdir(install_dir)

    # Prüfe ob DB bereits läuft
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.full.yml",
            "ps",
            "db",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        cwd=install_dir,
    )
    if result.returncode == 0 and "running" in (result.stdout or "").lower():
        warn("Datenbank läuft bereits!")
        warn("Bestehende Daten bleiben erhalten.")
        info("Für kompletten Neustart:")
        info("  docker compose -f docker-compose.full.yml down -v")

    # Docker Images bauen
    info("Baue Docker Images (kann einige Minuten dauern)...")
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.full.yml",
            "build",
            "--no-cache",
        ],
        cwd=install_dir,
    )
    if result.returncode != 0:
        err("Docker Build fehlgeschlagen")
        return False
    ok("Docker Images gebaut")

    # Datenbank zuerst starten
    info("Starte Datenbank...")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.full.yml",
            "up",
            "-d",
            "db",
        ],
        cwd=install_dir,
    )

    # Warte auf DB Health
    info("Warte auf Datenbank...")
    for i in range(30):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.full.yml",
                "exec",
                "db",
                "pg_isready",
                "-U",
                "bioresearch",
            ],
            capture_output=True,
            cwd=install_dir,
        )
        if result.returncode == 0:
            ok("Datenbank bereit")
            break
        time.sleep(2)
        print(f"  Warte... ({i + 1}/30)", end="\r")
    else:
        err("Datenbank Timeout — bitte Docker Logs prüfen")
        return False

    # Prüfe ob Volumes existieren mit anderem Passwort
    if not check_db_password_match(config):
        warn("Bestehende DB-Volumes gefunden mit anderem Passwort — lösche Volumes...")
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.full.yml",
                "down",
                "-v",
            ],
            cwd=install_dir,
            capture_output=True,
        )
        ok("DB-Volumes gelöscht — werden neu erstellt")
        info("Starte Datenbank neu...")
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.full.yml",
                "up",
                "-d",
                "db",
            ],
            cwd=install_dir,
            capture_output=True,
        )
        for i in range(30):
            r = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.full.yml",
                    "exec",
                    "-T",
                    "db",
                    "pg_isready",
                    "-U",
                    "bioresearch",
                ],
                capture_output=True,
                cwd=install_dir,
            )
            if r.returncode == 0:
                ok("Datenbank bereit")
                break
            time.sleep(2)
            print(f"  Warte... ({i + 1}/30)", end="\r")
        else:
            err("Datenbank startet nicht nach Volume-Reset")
            return False

    # pgvector Extension aktivieren
    info("Aktiviere pgvector Extension...")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.full.yml",
            "exec",
            "db",
            "psql",
            "-U",
            "bioresearch",
            "-c",
            "CREATE EXTENSION IF NOT EXISTS vector;",
        ],
        cwd=install_dir,
    )
    ok("pgvector aktiviert")

    # Alembic Migrationen
    info("Führe Datenbank-Migrationen durch...")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.full.yml",
            "run",
            "--rm",
            "backend",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=install_dir,
    )
    ok("Migrationen abgeschlossen")

    # Erst alle Services versuchen
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.full.yml",
            "up",
            "-d",
        ],
        cwd=install_dir,
        capture_output=True,
    )

    # Backend und Frontend explizit sicherstellen
    # (falls optionale Services wie Nextflow fehlen)
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.full.yml",
            "up",
            "-d",
            "backend",
            "frontend",
        ],
        cwd=install_dir,
    )
    ok("Alle Services gestartet")

    # Optional: Demo-Daten laden (erst wenn Backend healthy)
    if config.get("seed_demo_data"):
        port = int(config.get("backend_port", "8000"))
        info("Warte auf Backend...")
        if wait_for_backend(install_dir, port=port):
            info("Lade Demo-Daten...")
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.full.yml",
                    "exec",
                    "-T",
                    "backend",
                    "python",
                    "scripts/seed_demo_data.py",
                ],
                cwd=install_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                ok("Demo-Daten geladen")
            else:
                warn(f"Demo-Daten fehlgeschlagen: {result.stderr or result.stdout}")
        else:
            warn("Backend nicht erreichbar — Demo-Daten übersprungen")

    # Ollama Modell herunterladen (nur wenn nicht wiederverwendet)
    if config.get("use_ollama") and not config.get("reuse_ollama"):
        model = config.get("ollama_model", "mistral")
        info(f"Lade Ollama Modell '{model}' herunter...")
        info("(Das kann 5-15 Minuten dauern je nach Internetgeschwindigkeit)")
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.full.yml",
                "exec",
                "ollama",
                "ollama",
                "pull",
                model,
            ],
            cwd=install_dir,
        )
        ok(f"Modell '{model}' heruntergeladen")
    elif config.get("use_ollama") and config.get("reuse_ollama"):
        ok("Ollama Modell bereits vorhanden — übersprungen")

    return True


# ── Health Check ──────────────────────────────────────
def health_check(config: dict) -> bool:
    step("Prüfe Installation")
    port = config["backend_port"]
    url = f"http://localhost:{port}/api/v1/health"

    info("Warte auf Backend...")
    for i in range(15):
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "healthy":
                    ok("Backend gesund")
                    features = data.get("features", {})
                    for feat, active in features.items():
                        if active:
                            ok(f"Feature aktiv: {feat}")
                        else:
                            info(f"Feature inaktiv: {feat} (optional)")
                    return True
        except Exception:
            time.sleep(3)
            print(f"  Warte... ({i + 1}/15)", end="\r")

    warn("Backend antwortet noch nicht — warte 1-2 Minuten und prüfe ./logs.sh")
    return False


# ── Management Scripts erstellen ──────────────────────
def create_management_scripts(config: dict, install_dir: Path):
    step("Erstelle Management Scripts")

    fp = config["frontend_port"]
    bp = config["backend_port"]
    install_dir_str = str(install_dir)

    scripts = {
        "start.sh": f"""#!/bin/bash
cd "{install_dir_str}"
echo "🚀 Starte BioResearch Assistant v1.0.0..."
python3 install.py start
echo ""
echo "   Frontend:  http://localhost:{fp}"
echo "   Backend:   http://localhost:{bp}"
echo "   API Docs:  http://localhost:{bp}/docs"
echo "   Health:    http://localhost:{bp}/api/v1/health"
""",
        "stop.sh": f"""#!/bin/bash
cd "{install_dir_str}"
echo "⏹ Stoppe BioResearch Assistant..."
docker compose -f docker-compose.full.yml down --remove-orphans
echo "✅ Gestoppt (Daten behalten)."
""",
        "destroy.sh": f"""#!/bin/bash
cd "{install_dir_str}"
echo "🗑 Entferne Stack (Container + Volumes)..."
docker compose -f docker-compose.full.yml down -v --remove-orphans
echo "✅ Stack zerstört. Neu starten: ./start.sh oder python install.py start"
""",
        "restart.sh": f"""#!/bin/bash
cd "{install_dir_str}"
echo "🔄 Neustart..."
docker compose -f docker-compose.full.yml restart
echo "✅ Neugestartet."
""",
        "update.sh": f"""#!/bin/bash
cd "{install_dir_str}"
echo "🔄 Update BioResearch Assistant..."
git pull origin main
docker compose -f docker-compose.full.yml build --no-cache
docker compose -f docker-compose.full.yml up -d
echo "✅ Update abgeschlossen!"
""",
        "logs.sh": f"""#!/bin/bash
cd "{install_dir_str}"
docker compose -f docker-compose.full.yml logs --follow --tail=100 "$@"
""",
        "backup.sh": f"""#!/bin/bash
cd "{install_dir_str}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/$DATE"
mkdir -p "$BACKUP_DIR"
echo "📦 Erstelle Backup..."
docker compose -f docker-compose.full.yml exec -T db pg_dump -U bioresearch bioresearch > "$BACKUP_DIR/database.sql"
echo "✅ Backup: $BACKUP_DIR/database.sql"
""",
        "status.sh": f"""#!/bin/bash
cd "{install_dir_str}"
echo "📊 BioResearch Assistant Status"
echo ""
docker compose -f docker-compose.full.yml ps
echo ""
curl -s http://localhost:{bp}/api/v1/health | python3 -m json.tool 2>/dev/null || echo "Backend nicht erreichbar"
""",
    }

    for name, content in scripts.items():
        script_path = install_dir / name
        script_path.write_text(content)
        script_path.chmod(0o755)
        ok(f"{name} erstellt")

    (install_dir / "start.bat").write_text(
        f'@echo off\ncd /d "{install_dir_str}"\n'
        f"echo Starte BioResearch Assistant v1.0.0...\n"
        f"docker compose -f docker-compose.full.yml up -d\n"
        f"echo.\necho Frontend: http://localhost:{fp}\n"
        f"echo Backend:  http://localhost:{bp}\npause\n"
    )
    (install_dir / "stop.bat").write_text(
        f'@echo off\ncd /d "{install_dir_str}"\n'
        f"docker compose -f docker-compose.full.yml down\npause\n"
    )
    ok("start.bat / stop.bat erstellt")

    # reset_db.sh — Kopie aus Repo ins Installationsverzeichnis
    _repo_root = Path(__file__).resolve().parent
    _reset_src = _repo_root / "scripts" / "reset_db.sh"
    if _reset_src.exists():
        (install_dir / "reset_db.sh").write_text(_reset_src.read_text())
        (install_dir / "reset_db.sh").chmod(0o755)
        ok("reset_db.sh erstellt")
    else:
        warn("scripts/reset_db.sh nicht gefunden — DB-Reset-Skript nicht kopiert")


# ── Zusammenfassung ───────────────────────────────────
def print_summary(config: dict, install_dir: Path):
    fp = config["frontend_port"]
    bp = config["backend_port"]
    hw_profile = config.get("hardware_profile", "nicht gesetzt")
    llm = (
        "Ollama — " + config.get("ollama_model", "mistral") + " (lokal, DSGVO-konform)"
        if config.get("use_ollama")
        else "Anthropic API"
    )

    print(
        f"""
{Colors.BOLD}{Colors.GREEN}
╔═══════════════════════════════════════════════════╗
║        Installation erfolgreich! 🎉               ║
║        BioResearch Assistant v1.0.0               ║
╚═══════════════════════════════════════════════════╝
{Colors.RESET}
{Colors.BOLD}URLs:{Colors.RESET}
  Frontend:  http://localhost:{fp}
  Backend:   http://localhost:{bp}
  API Docs:  http://localhost:{bp}/docs
  Health:    http://localhost:{bp}/api/v1/health

{Colors.BOLD}Management:{Colors.RESET}
  ./start.sh    System starten
  ./stop.sh     System stoppen
  ./restart.sh  System neustarten
  ./update.sh   Auf neue Version aktualisieren
  ./logs.sh     Logs anzeigen (./logs.sh backend)
  ./backup.sh   Datenbank-Backup erstellen
  ./status.sh   System-Status anzeigen
  ./reset_db.sh DB-Reset (Volume löschen, Migrationen neu)
  ./reset_db.sh --seed   DB-Reset inkl. Demo-Daten

{Colors.BOLD}Konfiguration:{Colors.RESET}
  {install_dir}/.env

{Colors.BOLD}Einstellungen:{Colors.RESET}
  Isolation:  {config["isolation_mode"]}
  De-Pseudo:  {config["depseudo_access"]}
  Hardware:   {hw_profile}
  LLM:        {llm}

{Colors.YELLOW}Auth-Modus: Dev (kein Login erforderlich)
Für Produktion: OIDC_ISSUER in .env setzen{Colors.RESET}

{Colors.YELLOW}Secrets gespeichert in:
  {install_dir}/.env

Bei Neuinstallation werden bestehende Secrets
automatisch wiederverwendet.
Für komplett neue Secrets: .env vorher löschen.{Colors.RESET}

{Colors.YELLOW}⚠ WICHTIG: .env enthält Secrets —
  niemals in Git committen!{Colors.RESET}
"""
    )


# ── Start (mit DB-Passwort-Check) ──────────────────────
def run_start(install_dir: Path) -> bool:
    """Run start with DB password mismatch check. Returns True on success."""
    step("Starte BioResearch Assistant")
    config = load_env_config(install_dir)
    if not config:
        warn(".env nicht gefunden oder POSTGRES_PASSWORD fehlt — starte ohne Check.")
        subprocess.run(
            ["docker", "compose", "-f", "docker-compose.full.yml", "up", "-d"],
            cwd=install_dir,
        )
        ok("Services gestartet")
        return True

    # DB zuerst starten
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.full.yml", "up", "-d", "db"],
        cwd=install_dir,
        capture_output=True,
    )
    info("Warte auf Datenbank...")
    for i in range(25):
        r = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.full.yml",
                "exec",
                "-T",
                "db",
                "pg_isready",
                "-U",
                "bioresearch",
            ],
            capture_output=True,
            cwd=install_dir,
        )
        if r.returncode == 0:
            break
        time.sleep(2)
        if i < 24:
            print(f"  Warte... ({i + 1}/25)", end="\r")
    else:
        err("Datenbank startet nicht — bitte Logs prüfen (docker compose logs db)")
        return False

    if not check_db_password_match(config):
        print("")
        warn("DB-Passwort Mismatch erkannt!")
        print("   Das gespeicherte DB-Volume verwendet")
        print("   ein anderes Passwort als .env")
        print("")
        print("   Optionen:")
        print("   1. Volumes löschen (Daten gehen verloren):")
        print("      docker compose -f docker-compose.full.yml down -v")
        print("   2. Altes Passwort in .env wiederherstellen")
        print("")
        try:
            answer = input("Volumes jetzt löschen? (j/N): ").strip()
        except EOFError:
            answer = "n"
        if answer.lower() == "j":
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.full.yml",
                    "down",
                    "-v",
                ],
                cwd=install_dir,
            )
            ok("Volumes gelöscht — starte neu...")
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.full.yml",
                    "up",
                    "-d",
                    "db",
                ],
                cwd=install_dir,
                capture_output=True,
            )
            info("Warte auf Datenbank...")
            for _ in range(25):
                r = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        "docker-compose.full.yml",
                        "exec",
                        "-T",
                        "db",
                        "pg_isready",
                        "-U",
                        "bioresearch",
                    ],
                    capture_output=True,
                    cwd=install_dir,
                )
                if r.returncode == 0:
                    break
                time.sleep(2)
            else:
                err("Datenbank startet nicht")
                return False
            info("Führe Migrationen aus...")
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.full.yml",
                    "run",
                    "--rm",
                    "backend",
                    "alembic",
                    "upgrade",
                    "head",
                ],
                cwd=install_dir,
            )
            subprocess.run(
                ["docker", "compose", "-f", "docker-compose.full.yml", "up", "-d"],
                cwd=install_dir,
            )
        else:
            err("Start abgebrochen. Bitte .env anpassen oder Volumes löschen.")
            return False
    else:
        subprocess.run(
            ["docker", "compose", "-f", "docker-compose.full.yml", "up", "-d"],
            cwd=install_dir,
        )
    ok("System gestartet")
    return True


def run_stop(install_dir: Path) -> bool:
    """Stop containers; keep volumes."""
    compose = install_dir / "docker-compose.full.yml"
    if not compose.exists():
        err(
            "docker-compose.full.yml nicht gefunden. Bitte aus Installationsverzeichnis ausführen."
        )
        return False
    step("Stoppe BioResearch Assistant…")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(compose),
            "down",
            "--remove-orphans",
        ],
        cwd=install_dir,
    )
    ok("Gestoppt (Daten behalten).")
    return True


def run_destroy(install_dir: Path) -> bool:
    """Stop containers and remove volumes."""
    compose = install_dir / "docker-compose.full.yml"
    if not compose.exists():
        warn("Keine docker-compose.full.yml — nichts zu entfernen.")
        return True
    step("Entferne Stack (Container + Volumes)…")
    cleanup_existing(install_dir)
    ok(
        "Stack zerstört. Konfiguration und Skripte in "
        f"{install_dir} bleiben erhalten — erneut starten mit: python install.py start"
    )
    return True


# ── Main ──────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="BioResearch Assistant Installer v1.0.0"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="install",
        choices=["install", "start", "stop", "destroy"],
        help="install (default), start, stop, oder destroy",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Nur Core Komponenten",
    )
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="Keine interaktiven Fragen",
    )
    parser.add_argument(
        "--install-dir",
        default=None,
        help="Installationsverzeichnis",
    )
    args = parser.parse_args()

    if args.command == "start":
        install_dir = Path(args.install_dir or os.getcwd())
        if not (install_dir / "docker-compose.full.yml").exists():
            err(
                "docker-compose.full.yml nicht gefunden. Bitte aus Installationsverzeichnis ausführen."
            )
            sys.exit(1)
        if not run_start(install_dir):
            sys.exit(1)
        return

    if args.command == "stop":
        install_dir = Path(args.install_dir or os.getcwd())
        if not run_stop(install_dir):
            sys.exit(1)
        return

    if args.command == "destroy":
        install_dir = Path(args.install_dir or os.getcwd())
        if not run_destroy(install_dir):
            sys.exit(1)
        return

    header()

    if not check_prerequisites():
        err("Voraussetzungen nicht erfüllt.")
        sys.exit(1)

    config = configure(
        unattended=args.unattended,
        install_dir_arg=args.install_dir,
    )
    install_dir = Path(config["install_dir"])

    # Repo klonen falls nicht vorhanden
    if not (install_dir / "backend").exists():
        step("Lade BioResearch Assistant herunter")
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "git",
                "clone",
                "https://github.com/SynapticFour/bioresearch-assistant.git",
                str(install_dir),
            ]
        )
        if result.returncode != 0:
            err("Git clone fehlgeschlagen")
            sys.exit(1)
        ok(f"Repository geklont: {install_dir}")
    else:
        ok(f"Repository gefunden: {install_dir}")

    generate_env(config, install_dir)
    generate_docker_compose(config, install_dir)
    create_management_scripts(config, install_dir)

    if not install(config, install_dir):
        err("Installation fehlgeschlagen — bitte Logs prüfen")
        sys.exit(1)

    health_check(config)
    print_summary(config, install_dir)


if __name__ == "__main__":
    main()
