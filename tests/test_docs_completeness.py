from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from onecmcp.config import Settings

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"
MD = "{http://v8.1c.ru/8.3/MDClasses}"
CONSULTANT_METADATA = [
    ROOT / "extension" / "src" / "Catalogs" / "мкпКлиентыИнтеграции.xml",
    ROOT / "extension" / "src" / "Catalogs" / "мкпИменованныеЗапросы.xml",
    ROOT / "extension" / "src" / "Catalogs" / "мкпДействияИнтеграции.xml",
    ROOT / "extension" / "src" / "InformationRegisters" / "мкпПравилаДоступа.xml",
    ROOT / "extension" / "src" / "InformationRegisters" / "мкпСемантическийСловарь.xml",
]


def _docs_text() -> str:
    parts: list[str] = []
    for path in sorted(DOCS.rglob("*")):
        if path.suffix.lower() in {".md", ".yml", ".yaml", ".json"}:
            parts.append(path.read_text(encoding="utf-8"))
    if MKDOCS.is_file():
        parts.append(MKDOCS.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _settings_page() -> str:
    return (DOCS / "reference" / "settings.md").read_text(encoding="utf-8")


def _walk_yaml_paths(prefix: str, node: object) -> list[str]:
    if isinstance(node, dict):
        found: list[str] = []
        for key, child in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.append(path)
            found.extend(_walk_yaml_paths(path, child))
        return found
    return []


def test_mkdocs_site_has_russian_tabs() -> None:
    assert MKDOCS.is_file(), "нужен mkdocs.yml — сайт документации"
    raw = MKDOCS.read_text(encoding="utf-8")
    raw = re.sub(r"!!python/name:[^\s]+", "fence_code_format", raw)
    config = yaml.safe_load(raw)
    assert config["site_name"]
    theme = config["theme"]
    assert theme["name"] == "material"
    assert "navigation.tabs" in theme.get("features", [])
    nav_labels = [next(iter(item)) if isinstance(item, dict) else item for item in config["nav"]]
    for label in ("Начало", "Установка", "Пользование", "Администрирование", "Справочник"):
        assert label in nav_labels
    assert (DOCS / "reference" / "settings.md").is_file()
    assert (DOCS / "admin" / "clients.md").is_file()
    assert (DOCS / "index.md").is_file()


def test_every_gateway_setting_is_documented() -> None:
    text = _docs_text()
    settings_page = _settings_page()
    for name in Settings.model_fields:
        env = name.upper()
        assert env in settings_page, f"переменная {env} должна быть в reference/settings.md"
        assert env in text


def test_env_example_keys_are_documented() -> None:
    settings_page = _settings_page()
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    keys = re.findall(r"^([A-Z][A-Z0-9_]+)=", example, flags=re.M)
    assert keys
    for key in keys:
        assert key in settings_page, f"{key} из .env.example нет в справочнике настроек"


def test_helm_values_are_documented() -> None:
    settings_page = _settings_page()
    values = yaml.safe_load((ROOT / "deploy" / "helm" / "onecmcp" / "values.yaml").read_text(encoding="utf-8"))
    paths = _walk_yaml_paths("", values)
    assert paths
    for path in paths:
        assert path in settings_page, f"Helm {path} должен быть в reference/settings.md"


def test_cli_flags_from_main_are_documented() -> None:
    main = (ROOT / "gateway" / "src" / "onecmcp" / "__main__.py").read_text(encoding="utf-8")
    flags = re.findall(r'add_argument\(\s*"(--[a-z]+)"', main)
    assert "--host" in flags and "--transport" in flags and "--path" in flags
    cli_page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    settings_page = _settings_page()
    for flag in sorted(set(flags)):
        assert flag in cli_page, f"флаг {flag} должен быть в reference/cli.md"
        assert flag in settings_page, f"флаг {flag} должен быть в reference/settings.md"


def test_consultant_metadata_fields_are_documented() -> None:
    settings_page = _settings_page()
    found = 0
    for path in CONSULTANT_METADATA:
        tree = ET.parse(path)
        for tag in ("Attribute", "Dimension", "Resource"):
            for node in tree.iter(f"{MD}{tag}"):
                name = node.findtext(f"{MD}Properties/{MD}Name")
                assert name, f"безымянное поле в {path}"
                assert name in settings_page, f"{path.name}: реквизит {name} нет в справочнике настроек"
                found += 1
    assert found >= 20


def test_cli_flags_and_extension_fields_are_documented() -> None:
    text = _docs_text()
    for needle in (
        "onecmcp serve",
        "onecmcp mock1c",
        "onecmcp mcp",
        "--transport",
        "streamable-http",
        "stdio",
        "ЛимитСуммы",
        "ЛимитКоличества",
        "limit_exceeded",
        "ХешТокена",
        "Скоупы",
        "ПользовательИБ",
        "мкпПравилаДоступа",
        "мкпИменованныеЗапросы",
        "мкпДействияИнтеграции",
        "мкпСемантическийСловарь",
        "ReuseSessions",
        "SessionMaxAge",
        "RootURL",
        "ONEC_PRESET",
        "RATE_LIMIT_PER_MINUTE",
        "ONEC_TENANTS",
        "MCP_HTTP_PATH",
        "confirm_token",
        "600",
        "10000",
        "Idempotency-Key",
        "imagePullSecrets",
        "PYTHONUNBUFFERED",
        "gateway[otel]",
        "/v1/audit",
        "audit_list",
        "СсылкиJSON",
        "session_get",
        "/v1/session/",
    ):
        assert needle in text, f"в документации нет {needle!r}"
    clients = (DOCS / "admin" / "clients.md").read_text(encoding="utf-8")
    assert "ЛимитСуммы" in clients
    assert "как изменить" in clients.lower() or "Как задать" in clients
    assert "```mermaid" in (DOCS / "index.md").read_text(encoding="utf-8")
    assert "```mermaid" in clients
    assert "Stas@Chashin.pro" in (DOCS / "index.md").read_text(encoding="utf-8")


def test_pervy_bit_removed_and_developer_is_chashin() -> None:
    forbidden = ("Первый" + " Бит", "Первый" + " БИТ", "Первый" + "Бит")
    skip_parts = {
        ".git",
        "site",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
    }
    suffixes = {".md", ".yml", ".yaml", ".toml", ".xml", ".py", ".bsl", ".html", ".txt", ".json", ".sh"}
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_parts or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix.lower() not in suffixes and path.name not in {"Dockerfile", "mkdocs.yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for needle in forbidden:
            if needle in text:
                hits.append(f"{path.relative_to(ROOT)}: {needle}")
    assert hits == [], "остались упоминания бывшего поставщика: " + "; ".join(hits)
    identity = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "gateway" / "pyproject.toml").read_text(encoding="utf-8"),
            (ROOT / "extension" / "src" / "Configuration.xml").read_text(encoding="utf-8"),
            MKDOCS.read_text(encoding="utf-8"),
        ]
    )
    assert "Стас Чашин" in identity
    assert "Stas@Chashin.pro" in identity
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License")
    assert "Стас Чашин" in license_text
    assert "Stas@Chashin.pro" in license_text
    assert "MIT" in (ROOT / "gateway" / "pyproject.toml").read_text(encoding="utf-8")
    assert "name: MIT" in (ROOT / "specs" / "openapi.yaml").read_text(encoding="utf-8")
