from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "extension" / "src"
MD = "{http://v8.1c.ru/8.3/MDClasses}"
XR = "{http://v8.1c.ru/8.3/xcf/readable}"
PREFIX = "мкп"

CONTAINED_CLASS_IDS = [
    "9cd510cd-abfc-11d4-9434-004095e12fc7",
    "9fcd25a0-4822-11d4-9414-008048da11f9",
    "e3687481-0a87-462c-a166-9f34594f9bba",
    "9de14907-ec23-4a07-96f0-85521cb6b53b",
    "51f2d5d8-ea4d-4064-8892-82951750031e",
    "e68182ea-4237-4383-967f-90c1e3370bc7",
    "fb282519-d103-4dd3-bc12-cb271d631dfc",
]


def _xml_files() -> list[Path]:
    return sorted(SRC.rglob("*.xml"))


def test_all_xml_well_formed() -> None:
    assert _xml_files(), "нет XML в extension/src"
    for path in _xml_files():
        ET.parse(path)


def test_configuration_is_addon_with_prefix() -> None:
    tree = ET.parse(SRC / "Configuration.xml")
    props = tree.find(f"{MD}Configuration/{MD}Properties")
    assert props is not None
    assert props.findtext(f"{MD}Name") == "мкпКоннектор"
    assert props.findtext(f"{MD}NamePrefix") == PREFIX
    assert props.findtext(f"{MD}ConfigurationExtensionPurpose") == "AddOn"
    assert props.findtext(f"{MD}ConfigurationExtensionCompatibilityMode") == "Version8_3_20"
    assert props.findtext(f"{MD}Vendor") == "Стас Чашин"
    copyright = props.find(f"{MD}Copyright")
    assert copyright is not None
    copyright_text = ET.tostring(copyright, encoding="unicode")
    assert "Стас Чашин" in copyright_text
    assert "Stas@Chashin.pro" in copyright_text
    assert props.findtext(f"{MD}VendorInformationAddress") == "mailto:Stas@Chashin.pro"
    children = [
        (child.tag.removeprefix(MD), (child.text or "").strip())
        for child in tree.find(f"{MD}Configuration/{MD}ChildObjects")
    ]
    assert children == [
        ("Role", "мкпДоступКоннектора"),
        ("CommonModule", "мкпМаршрутизатор"),
        ("CommonModule", "мкпБезопасность"),
        ("CommonModule", "мкпСериализация"),
        ("CommonModule", "мкпИнтроспекция"),
        ("CommonModule", "мкпДанные"),
        ("CommonModule", "мкпЗапросы"),
        ("CommonModule", "мкпОтчёты"),
        ("CommonModule", "мкпЗадания"),
        ("CommonModule", "мкпДействия"),
        ("HTTPService", "мкпAPI"),
        ("DataProcessor", "мкпАдминистрированиеКоннектора"),
        ("Catalog", "мкпКлиентыИнтеграции"),
        ("Catalog", "мкпИменованныеЗапросы"),
        ("Catalog", "мкпДействияИнтеграции"),
        ("InformationRegister", "мкпПравилаДоступа"),
        ("InformationRegister", "мкпСемантическийСловарь"),
        ("InformationRegister", "мкпЖурналВызовов"),
        ("InformationRegister", "мкпСостоянияЗаданий"),
        ("InformationRegister", "мкпКлючиИдемпотентности"),
        ("InformationRegister", "мкпТокеныПодтверждения"),
        ("InformationRegister", "мкпОперацииСессии"),
    ]


def test_internal_info_has_seven_platform_class_ids() -> None:
    tree = ET.parse(SRC / "Configuration.xml")
    class_ids = [
        node.text
        for node in tree.findall(
            f"{MD}Configuration/{MD}InternalInfo/{XR}ContainedObject/{XR}ClassId"
        )
    ]
    assert class_ids == CONTAINED_CLASS_IDS


def test_native_object_names_use_prefix() -> None:
    names: list[str] = []
    for path in _xml_files():
        tree = ET.parse(path)
        for name_el in tree.findall(f".//{MD}Name"):
            if name_el.text:
                names.append(name_el.text)
    object_names = {
        "мкпКоннектор",
        "мкпДоступКоннектора",
        "мкпМаршрутизатор",
        "мкпБезопасность",
        "мкпСериализация",
        "мкпИнтроспекция",
        "мкпДанные",
        "мкпЗапросы",
        "мкпОтчёты",
        "мкпЗадания",
        "мкпДействия",
        "мкпAPI",
        "мкпАдминистрированиеКоннектора",
        "мкпКлиентыИнтеграции",
        "мкпИменованныеЗапросы",
        "мкпДействияИнтеграции",
        "мкпПравилаДоступа",
        "мкпСемантическийСловарь",
        "мкпЖурналВызовов",
        "мкпСостоянияЗаданий",
        "мкпКлючиИдемпотентности",
        "мкпТокеныПодтверждения",
        "мкпОперацииСессии",
    }
    assert object_names <= set(names)
    for name in object_names:
        assert name.startswith(PREFIX)


def test_no_borrowed_objects_except_configuration() -> None:
    adopted = []
    for path in _xml_files():
        tree = ET.parse(path)
        for node in tree.findall(f".//{MD}ObjectBelonging"):
            if (node.text or "") == "Adopted":
                adopted.append(path.relative_to(SRC))
    assert adopted == [Path("Configuration.xml")]


def test_http_service_health_and_session_reuse() -> None:
    tree = ET.parse(SRC / "HTTPServices" / "мкпAPI.xml")
    props = tree.find(f"{MD}HTTPService/{MD}Properties")
    assert props.findtext(f"{MD}RootURL") == "mcp"
    assert props.findtext(f"{MD}ReuseSessions") == "AutoUse"
    assert props.findtext(f"{MD}SessionMaxAge") == "20"
    templates = {
        node.findtext(f"{MD}Properties/{MD}Template"): node.findtext(f"{MD}Properties/{MD}Name")
        for node in tree.findall(f"{MD}HTTPService/{MD}ChildObjects/{MD}URLTemplate")
    }
    assert "/v1/health" in templates
    assert "/v1/meta" in templates
    assert "/v1/meta/search" in templates
    assert "/v1/meta/{kind}/{name}" in templates
    assert "/v1/data/{kind}/{name}" in templates
    assert "/v1/data/{kind}/{name}/{id}" in templates
    assert "/v1/query" in templates
    assert "/v1/report" in templates
    assert "/v1/job" in templates
    assert "/v1/job/{id}" in templates
    assert "/v1/data/{kind}/{name}/dry-run" in templates
    assert "/v1/data/{kind}/{name}/{id}/post" in templates
    assert "/v1/action" in templates
    assert "/v1/session/rollback" in templates
    assert "/v1/session/{session_id}" in templates
    assert "/v1/diag" in templates
    assert "/v1/audit" in templates
    handlers = [
        node.findtext(f"{MD}Properties/{MD}Handler")
        for node in tree.findall(f".//{MD}Method")
    ]
    module = (SRC / "HTTPServices" / "мкпAPI" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    for handler in handlers:
        assert handler
        assert re.search(rf"Функция\s+{re.escape(handler)}\s*\(", module)


def test_router_implements_health_contract() -> None:
    module = (SRC / "CommonModules" / "мкпМаршрутизатор" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    for needle in (
        "Функция ОбработатьЗапрос",
        '"status"',
        '"1cmcp"',
        '"v1"',
        "application/problem+json",
        "/v1/health",
        "/v1/diag",
        "/v1/audit",
        "/v1/meta",
        "/v1/data",
        "/v1/query",
        "/v1/report",
        "/v1/job",
        "мкпБезопасность",
        "мкпИнтроспекция",
        "мкпДанные",
        "мкпЗапросы",
        "мкпОтчёты",
        "мкпЗадания",
        "мкпДействия",
        "/v1/action",
        "/v1/session/rollback",
        "dry-run",
    ):
        assert needle in module


def test_uuids_are_unique() -> None:
    uuids: list[str] = []
    uuid_re = re.compile(r'uuid="([0-9a-fA-F-]{36})"')
    object_id_re = re.compile(r"<xr:ObjectId>([0-9a-fA-F-]{36})</xr:ObjectId>")
    for path in _xml_files():
        text = path.read_text(encoding="utf-8")
        uuids.extend(uuid_re.findall(text))
        uuids.extend(object_id_re.findall(text))
    assert uuids
    assert len(uuids) == len(set(uuids))


def test_configuration_version_and_phase4_rights() -> None:
    tree = ET.parse(SRC / "Configuration.xml")
    props = tree.find(f"{MD}Configuration/{MD}Properties")
    assert props.findtext(f"{MD}Version") == "0.10.0"
    rights = (SRC / "Roles" / "мкпДоступКоннектора" / "Ext" / "Rights.xml").read_text(
        encoding="utf-8"
    )
    for needle in (
        "CommonModule.мкпБезопасность",
        "CommonModule.мкпЗапросы",
        "CommonModule.мкпОтчёты",
        "CommonModule.мкпЗадания",
        "CommonModule.мкпДействия",
        "Catalog.мкпКлиентыИнтеграции",
        "Catalog.мкпИменованныеЗапросы",
        "Catalog.мкпДействияИнтеграции",
        "InformationRegister.мкпЖурналВызовов",
        "InformationRegister.мкпСемантическийСловарь",
        "InformationRegister.мкпПравилаДоступа",
        "InformationRegister.мкпСостоянияЗаданий",
        "InformationRegister.мкпКлючиИдемпотентности",
        "InformationRegister.мкпТокеныПодтверждения",
        "InformationRegister.мкпОперацииСессии",
        "DataProcessor.мкпАдминистрированиеКоннектора",
    ):
        assert needle in rights


def test_phase1_modules_export_expected_entrypoints() -> None:
    security = (SRC / "CommonModules" / "мкпБезопасность" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "Функция КлиентПоЗапросу" in security
    assert "Функция ЭтоСлужебныйОбъект" in security
    assert "Функция ПроверитьЛимитыКлиента" in security
    data = (SRC / "CommonModules" / "мкпДанные" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "Функция Список" in data
    assert "Функция ПолучитьПоИд" in data
    assert "Функция Предпросмотр" in data
    assert "Функция Создать" in data
    assert "Функция Провести" in data
    assert "Функция ОткатитьСессию" in data
    meta = (SRC / "CommonModules" / "мкпИнтроспекция" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "Функция ПоискСемантики" in meta
    queries = (SRC / "CommonModules" / "мкпЗапросы" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "Функция ПроверитьТекстВыборки" in queries
    reports = (SRC / "CommonModules" / "мкпОтчёты" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "Функция ВыполнитьПоТелу" in reports
    jobs = (SRC / "CommonModules" / "мкпЗадания" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "Функция Поставить" in jobs
    assert "Функция Получить" in jobs
    actions = (SRC / "CommonModules" / "мкпДействия" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "Функция ВыполнитьПоТелу" in actions
    admin = (
        SRC / "DataProcessors" / "мкпАдминистрированиеКоннектора" / "Ext" / "ObjectModule.bsl"
    ).read_text(encoding="utf-8")
    assert "Функция СгенерироватьТокенКлиента" in admin
    assert "Функция ЧеклистПубликации" in admin
    assert "Функция Самодиагностика" in admin
    assert "not_required" in admin
    assert "ХешТокена" in admin
