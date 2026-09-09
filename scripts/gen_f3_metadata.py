#!/usr/bin/env python3
"""Генерация XML собственных объектов расширения для Ф3. Запускается вручную."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gen_f1_metadata", HERE / "gen_f1_metadata.py")
gen = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gen)

ROOT = gen.ROOT
NS = gen.NS

# Зафиксированные UUID, сгенерированные в этом репозитории.
IDS = [
    "de2f9b24-41e4-4f0b-9cf1-46f916813768",
    "56b722fb-c99c-43e1-8c9c-6716b51be851",
    "a62ea891-ea34-4eab-8156-ed5b3486b45c",
    "e340f802-6d1e-4b28-8030-576cd51b0290",
    "f6aa22e0-61dd-4110-9005-cdca3e87e4a1",
    "d072923d-808a-4237-96f3-4001a94f2daf",
    "e223588e-8ad7-42a4-b6a1-4662a0227c59",
    "5f335a85-c8cd-4850-889e-c37c74ae486d",
    "74d1987c-3921-41d2-aec3-a30c8f5620e4",
    "d5957ec5-6dda-480c-b1b2-cd9f2f721630",
    "00b55044-e04b-4681-aaf3-04013b6eabf5",
    "4ef74531-009b-4492-8a4b-050eb64940fc",
    "ad47ba3c-ab62-4b97-a566-023ff3a7fc41",
    "c23b2eef-3f68-4b5b-aba1-c006df740545",
    "802a0dd6-c826-4165-baa4-e01c856feee7",
    "ba5bf9f0-97f6-4b1e-be47-90ccad2b2879",
    "8cc574ed-ccff-487c-85ac-1f2360bfef09",
    "e26c2404-1670-4fb5-9bc2-40885ba51ca1",
    "2bed8d1e-e5aa-4844-8a9c-3de7ae78da03",
    "aa410961-9f6c-4e63-88fb-ad5788f43add",
    "7708bec5-4c72-4b5c-a8ae-3872b8da25c0",
    "b0c38f2c-a499-4349-9c48-e68452cdb859",
    "173dd53b-56b2-4104-ab19-a1a579142912",
    "4a6771ed-7000-4a18-973e-4f8fbe5b17c3",
    "ebbd99b5-9669-40b1-8842-aec66c8fe985",
    "9a05398a-1aa6-4fc5-9df5-552d438c5dbb",
    "81e4baca-9aeb-40a8-8a11-31c5cabe9341",
    "2011e06e-acb1-4814-afb6-efd3fa0a215f",
    "7b678e1e-23a6-48a0-b35e-b4ba266d4595",
    "874c4ce1-0597-4ee0-a3a6-c4fd73ebfe54",
    "aa94a685-18c2-410a-aeb4-b7c270919ff7",
    "40b99231-46e3-426a-ab0b-da13525b9639",
    "bb6961c0-ffd1-4161-a5ae-6ff62bb4ef04",
    "cae9604b-1a28-45e4-ba0d-45be1314dd6d",
    "0517d5a1-3790-4540-93e3-8f673ff415fc",
    "9b00466d-18e2-4007-ae0e-149a823e2c60",
    "5ee9a3ba-96a4-4475-82aa-fc34815dc197",
    "b504de21-ee30-4373-8746-f76bcea29d97",
    "62a73516-6269-4f05-a1b3-f3fbd752b731",
    "9c1ed875-3d2d-4561-961e-20c236233ec4",
    "9411e4ab-3b2a-454d-accf-169a6c82c86b",
    "17131aa8-1e7c-407c-9153-aad93f4fae25",
    "a8f0c303-07b5-4c3d-a8c4-c4ceaec14eab",
    "7a9a6d83-e62a-4ce8-b5bd-aeb541e1b8d0",
    "7252d0ac-6f4b-4a8d-b8c5-f936546f983a",
    "951b80cc-c089-42bb-8770-fccf184b13d5",
    "e6a90912-ba79-46d6-bb86-d7166a130d2f",
    "8a8fad50-9d3f-4938-b4da-432794ac3598",
    "efe8df90-5fb8-46a3-afcd-3cbfb3c25249",
    "0ba75f3c-94ff-49ec-98b0-bed1920a3ef9",
    "f1f97f36-83a2-4958-a0db-8ae242335438",
    "01ed7e2d-a71b-4e74-81ac-e72f54fab460",
    "596dd4c6-1f90-48f7-876b-807edd2f49a1",
    "28ca4f45-7932-41d7-b839-8a6a5953804a",
    "3607de5b-1d6d-4fd6-8f6d-0ff9e914648f",
    "b9d7f26b-d22b-4090-9a5e-a3d137e9d522",
    "b1e1e3a4-4a78-4f48-9de5-be2ea5f5ebea",
    "4e22fc96-0a82-471e-b649-e1cc7ab31b67",
    "2dea98f5-982d-4356-bf26-cb7e944bc339",
    "55d9cbc9-fea9-4732-9096-ea6fac710fa2",
    "07e333ff-8c6b-4a62-ac28-b99debd8fc03",
    "88e03190-f89f-4dd6-b620-acc5002d1f27",
    "e3f789d4-6ca4-4e39-bdea-71c5bbf55d1f",
    "bf884bd7-4e1f-4d9c-b5da-09c15d104cc8",
    "a5e9c084-485f-42f9-9b46-0b55f8c1f126",
    "45d0e279-208b-4f10-843e-2080ed627262",
    "75309773-fb04-48bc-bce9-f5bcf5ed0c70",
    "cf81269f-c0ea-4730-894e-d0eec2d65019",
    "0da38630-5492-4f64-aef7-4a922aacff56",
    "f5b2be50-9865-4167-b8ae-5f3293569fcb",
    "720a34ea-2ecf-4b56-8bbb-4a5402e3883a",
    "40661fed-3636-4712-a578-46eeaa5e77eb",
    "bc033e4d-7cae-4966-a8b8-94bfdac457b1",
    "7794c407-97be-474b-9ffe-c712b0083325",
    "2b546241-646a-4788-9198-291f22bfbb1f",
    "5eccd7ae-cf65-4bd4-881b-f3e528c3708d",
    "a6310b49-1e38-4d8e-854b-f5fc916e3306",
    "3e967dbc-70a8-43b5-a5c7-613d4878eda2",
    "4715617b-ce25-4197-b505-8aab28b464b5",
    "852a464c-7d9b-4431-8174-18e6cd042c2f",
    "b1451a59-5ccd-4f02-96a3-673303b2f6c6",
    "6da5bc3f-e981-41b8-90b4-49f7db394341",
    "082effeb-239d-4870-bee5-7b678989e908",
    "d54e4605-ffc5-46be-87b3-c7291eb00d01",
    "5fe489ce-0cf4-495e-8489-6799147c8f86",
    "69547a20-48ea-478c-8764-9d6730fd7c4f",
    "171815e3-b168-4527-87a7-256bc7d2cf32",
    "0995dedc-7a9d-4e8a-a41f-47fde058c4d2",
    "5c89c8c1-0181-4f11-9631-ab945d5eb8a2",
    "8b5a22ed-7b1e-4e4e-b537-63f66d71f0f9",
    "28b1c789-b4e2-4c2c-8a80-9173cd404911",
    "1179cc44-0ab3-483e-83e9-7a18a9c36c22",
    "a677de84-381c-49af-8b6d-53b55f7eef5b",
    "d14af1e7-5b85-4276-9ab3-c41778316293",
    "df0fa0d8-51dd-45ca-a667-64022f8f0fff",
]


def take(n: int) -> list[str]:
    chunk = IDS[:n]
    del IDS[:n]
    return chunk


def ir_types(name: str, ids: list[str]) -> list[tuple[str, str, str, str]]:
    cats = [
        ("InformationRegisterRecord." + name, "Record"),
        ("InformationRegisterManager." + name, "Manager"),
        ("InformationRegisterSelection." + name, "Selection"),
        ("InformationRegisterList." + name, "List"),
        ("InformationRegisterRecordSet." + name, "RecordSet"),
        ("InformationRegisterRecordKey." + name, "RecordKey"),
        ("InformationRegisterRecordManager." + name, "RecordManager"),
    ]
    out = []
    it = iter(ids)
    for full, cat in cats:
        out.append((full, cat, next(it), next(it)))
    return out


def write_actions_catalog() -> None:
    name = "мкпДействияИнтеграции"
    uuid = take(1)[0]
    type_ids = take(10)
    types = [
        ("CatalogObject." + name, "Object", type_ids[0], type_ids[1]),
        ("CatalogRef." + name, "Ref", type_ids[2], type_ids[3]),
        ("CatalogSelection." + name, "Selection", type_ids[4], type_ids[5]),
        ("CatalogList." + name, "List", type_ids[6], type_ids[7]),
        ("CatalogManager." + name, "Manager", type_ids[8], type_ids[9]),
    ]
    attr_ids = take(4)
    attrs = [
        gen.attribute(attr_ids[0], "ИмяДействия", "Имя действия", gen.string_type(100)),
        gen.attribute(attr_ids[1], "Разрешено", "Разрешено", gen.bool_type()),
        gen.attribute(attr_ids[2], "ВидОбъекта", "Вид объекта", gen.string_type(50)),
        gen.attribute(attr_ids[3], "ИмяОбъекта", "Имя объекта", gen.string_type(255)),
    ]
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS}>
	<Catalog uuid="{uuid}">
		<InternalInfo>
{chr(10).join(gen.generated(*t) for t in types)}
		</InternalInfo>
		<Properties>
			<Name>{name}</Name>
{gen.synonym("1cmcp. Действия интеграции")}
			<Comment>Whitelist экспортных процедур, доступных агенту.</Comment>
			<Hierarchical>false</Hierarchical>
			<HierarchyType>HierarchyFoldersAndItems</HierarchyType>
			<LimitLevelCount>false</LimitLevelCount>
			<LevelCount>2</LevelCount>
			<FoldersOnTop>true</FoldersOnTop>
			<UseStandardCommands>true</UseStandardCommands>
			<Owners/>
			<SubordinationUse>ToItems</SubordinationUse>
			<CodeLength>9</CodeLength>
			<DescriptionLength>150</DescriptionLength>
			<CodeType>String</CodeType>
			<CodeAllowedLength>Variable</CodeAllowedLength>
			<CodeSeries>WholeCatalog</CodeSeries>
			<CheckUnique>true</CheckUnique>
			<Autonumbering>true</Autonumbering>
			<DefaultPresentation>AsDescription</DefaultPresentation>
			<Characteristics/>
			<PredefinedDataUpdate>Auto</PredefinedDataUpdate>
			<EditType>InDialog</EditType>
			<QuickChoice>false</QuickChoice>
			<ChoiceMode>BothWays</ChoiceMode>
			<InputByString/>
			<CreateOnInput>Auto</CreateOnInput>
			<SearchStringModeOnInputByString>Begin</SearchStringModeOnInputByString>
			<FullTextSearchOnInputByString>DontUse</FullTextSearchOnInputByString>
			<ChoiceDataGetModeOnInputByString>Directly</ChoiceDataGetModeOnInputByString>
			<DefaultObjectForm/>
			<DefaultFolderForm/>
			<DefaultListForm/>
			<DefaultChoiceForm/>
			<DefaultFolderChoiceForm/>
			<AuxiliaryObjectForm/>
			<AuxiliaryFolderForm/>
			<AuxiliaryListForm/>
			<AuxiliaryChoiceForm/>
			<AuxiliaryFolderChoiceForm/>
			<IncludeHelpInContents>false</IncludeHelpInContents>
			<BasedOn/>
			<DataLockControlMode>Managed</DataLockControlMode>
			<FullTextSearch>Use</FullTextSearch>
			<ObjectPresentation/>
			<ExtendedObjectPresentation/>
			<ListPresentation/>
			<ExtendedListPresentation/>
			<Explanation/>
			<DataHistory>DontUse</DataHistory>
			<UpdateDataHistoryImmediatelyAfterWrite>false</UpdateDataHistoryImmediatelyAfterWrite>
			<ExecuteAfterWriteDataHistoryVersionProcessing>false</ExecuteAfterWriteDataHistoryVersionProcessing>
		</Properties>
		<ChildObjects>
{chr(10).join(attrs)}
		</ChildObjects>
	</Catalog>
</MetaDataObject>
"""
    path = ROOT / "Catalogs" / f"{name}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def main() -> None:
    gen.common_module(
        ROOT / "CommonModules" / "мкпДействия.xml",
        take(1)[0],
        "мкпДействия",
        "1cmcp. Действия",
        "Whitelist экспортных процедур конфигурации.",
    )
    write_actions_catalog()
    gen.write_register(
        "мкпКлючиИдемпотентности",
        take(1)[0],
        "1cmcp. Ключи идемпотентности",
        "Повтор с тем же Idempotency-Key не создаёт дубль.",
        ir_types("мкпКлючиИдемпотентности", take(14)),
        [
            gen.dimension(take(1)[0], "Клиент", "Клиент", gen.catalog_ref("мкпКлиентыИнтеграции")),
            gen.dimension(take(1)[0], "Ключ", "Ключ", gen.string_type(128)),
        ],
        [
            gen.resource(take(1)[0], "Отпечаток", "Отпечаток", gen.string_type(0)),
            gen.resource(take(1)[0], "РезультатJSON", "Результат JSON", gen.string_type(0)),
            gen.resource(take(1)[0], "Момент", "Момент", gen.datetime_type()),
        ],
    )
    gen.write_register(
        "мкпТокеныПодтверждения",
        take(1)[0],
        "1cmcp. Токены подтверждения",
        "confirm_token dry-run: отпечаток тела и срок.",
        ir_types("мкпТокеныПодтверждения", take(14)),
        [
            gen.dimension(take(1)[0], "Токен", "Токен", gen.string_type(64)),
        ],
        [
            gen.resource(take(1)[0], "ВидОбъекта", "Вид объекта", gen.string_type(50)),
            gen.resource(take(1)[0], "ИмяОбъекта", "Имя объекта", gen.string_type(255)),
            gen.resource(take(1)[0], "ИдОбъекта", "Идентификатор", gen.string_type(36)),
            gen.resource(take(1)[0], "Отпечаток", "Отпечаток", gen.string_type(0)),
            gen.resource(take(1)[0], "Проводить", "Проводить", gen.bool_type()),
            gen.resource(take(1)[0], "Истекает", "Истекает", gen.datetime_type()),
            gen.resource(take(1)[0], "ТелоJSON", "Тело JSON", gen.string_type(0)),
        ],
    )
    gen.write_register(
        "мкпОперацииСессии",
        take(1)[0],
        "1cmcp. Операции сессии",
        "Журнал записи сессии агента для группового отката.",
        ir_types("мкпОперацииСессии", take(14)),
        [
            gen.dimension(take(1)[0], "ИдентификаторСессии", "Сессия", gen.string_type(64)),
            gen.dimension(take(1)[0], "Номер", "Номер", gen.number_type()),
        ],
        [
            gen.resource(take(1)[0], "Операция", "Операция", gen.string_type(20)),
            gen.resource(take(1)[0], "ВидОбъекта", "Вид объекта", gen.string_type(50)),
            gen.resource(take(1)[0], "ИмяОбъекта", "Имя объекта", gen.string_type(255)),
            gen.resource(take(1)[0], "ИдОбъекта", "Идентификатор", gen.string_type(36)),
            gen.resource(take(1)[0], "СнимокJSON", "Снимок JSON", gen.string_type(0)),
        ],
    )
    leftover = IDS
    print("unused", leftover)


if __name__ == "__main__":
    main()
