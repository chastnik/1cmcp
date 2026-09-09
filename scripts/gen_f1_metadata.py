#!/usr/bin/env python3
"""Генерация XML собственных объектов расширения для Ф1. Запускается вручную."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "extension" / "src"
NS = """xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:app="http://v8.1c.ru/8.2/managed-application/core" xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config" xmlns:cmi="http://v8.1c.ru/8.2/managed-application/cmi" xmlns:ent="http://v8.1c.ru/8.1/data/enterprise" xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform" xmlns:style="http://v8.1c.ru/8.1/data/ui/style" xmlns:sys="http://v8.1c.ru/8.1/data/ui/fonts/system" xmlns:v8="http://v8.1c.ru/8.1/data/core" xmlns:v8ui="http://v8.1c.ru/8.1/data/ui" xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web" xmlns:win="http://v8.1c.ru/8.1/data/ui/colors/windows" xmlns:xen="http://v8.1c.ru/8.3/xcf/enums" xmlns:xpr="http://v8.1c.ru/8.3/xcf/predef" xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.17\""""


def synonym(text: str) -> str:
    return f"""			<Synonym>
				<v8:item>
					<v8:lang>ru</v8:lang>
					<v8:content>{text}</v8:content>
				</v8:item>
			</Synonym>"""


def generated(name: str, category: str, type_id: str, value_id: str) -> str:
    return f"""			<xr:GeneratedType name="{name}" category="{category}">
				<xr:TypeId>{type_id}</xr:TypeId>
				<xr:ValueId>{value_id}</xr:ValueId>
			</xr:GeneratedType>"""


def string_type(length: int) -> str:
    return f"""				<Type>
					<v8:Type>xs:string</v8:Type>
					<v8:StringQualifiers>
						<v8:Length>{length}</v8:Length>
						<v8:AllowedLength>Variable</v8:AllowedLength>
					</v8:StringQualifiers>
				</Type>"""


def bool_type() -> str:
    return """				<Type>
					<v8:Type>xs:boolean</v8:Type>
				</Type>"""


def number_type() -> str:
    return """				<Type>
					<v8:Type>xs:decimal</v8:Type>
					<v8:NumberQualifiers>
						<v8:Digits>10</v8:Digits>
						<v8:FractionDigits>0</v8:FractionDigits>
						<v8:AllowedSign>Nonnegative</v8:AllowedSign>
					</v8:NumberQualifiers>
				</Type>"""


def datetime_type() -> str:
    return """				<Type>
					<v8:Type>xs:dateTime</v8:Type>
					<v8:DateQualifiers>
						<v8:DateFractions>DateTime</v8:DateFractions>
					</v8:DateQualifiers>
				</Type>"""


def catalog_ref(name: str) -> str:
    return f"""				<Type>
					<v8:Type>cfg:CatalogRef.{name}</v8:Type>
				</Type>"""


ATTR_TAIL = """				<PasswordMode>false</PasswordMode>
				<Format/>
				<EditFormat/>
				<ToolTip/>
				<MarkNegatives>false</MarkNegatives>
				<Mask/>
				<MultiLine>false</MultiLine>
				<ExtendedEdit>false</ExtendedEdit>
				<MinValue xsi:nil="true"/>
				<MaxValue xsi:nil="true"/>
				<FillFromFillingValue>false</FillFromFillingValue>
				<FillValue xsi:nil="true"/>
				<FillChecking>DontCheck</FillChecking>
				<ChoiceFoldersAndItems>Items</ChoiceFoldersAndItems>
				<ChoiceParameterLinks/>
				<ChoiceParameters/>
				<QuickChoice>Auto</QuickChoice>
				<CreateOnInput>Auto</CreateOnInput>
				<ChoiceForm/>
				<LinkByType/>
				<ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput>
				<Indexing>DontIndex</Indexing>
				<FullTextSearch>Use</FullTextSearch>
				<DataHistory>Use</DataHistory>"""


def attribute(uuid: str, name: str, syn: str, type_xml: str, extra: str = "") -> str:
    return f"""			<Attribute uuid="{uuid}">
				<Properties>
					<Name>{name}</Name>
{synonym(syn)}
					<Comment/>
{type_xml}
{ATTR_TAIL}
{extra}				</Properties>
			</Attribute>"""


def dimension(uuid: str, name: str, syn: str, type_xml: str) -> str:
    return f"""			<Dimension uuid="{uuid}">
				<Properties>
					<Name>{name}</Name>
{synonym(syn)}
					<Comment/>
{type_xml}
{ATTR_TAIL}
					<Master>false</Master>
					<MainFilter>true</MainFilter>
					<DenyIncompleteValues>false</DenyIncompleteValues>
					<UseInTotals>true</UseInTotals>
				</Properties>
			</Dimension>"""


def resource(uuid: str, name: str, syn: str, type_xml: str) -> str:
    return f"""			<Resource uuid="{uuid}">
				<Properties>
					<Name>{name}</Name>
{synonym(syn)}
					<Comment/>
{type_xml}
{ATTR_TAIL}
				</Properties>
			</Resource>"""


def common_module(path: Path, uuid: str, name: str, syn: str, comment: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS}>
	<CommonModule uuid="{uuid}">
		<Properties>
			<Name>{name}</Name>
{synonym(syn)}
			<Comment>{comment}</Comment>
			<Global>false</Global>
			<ClientManagedApplication>false</ClientManagedApplication>
			<Server>true</Server>
			<ExternalConnection>true</ExternalConnection>
			<ClientOrdinaryApplication>false</ClientOrdinaryApplication>
			<ServerCall>true</ServerCall>
			<Privileged>false</Privileged>
			<ReturnValuesReuse>DontUse</ReturnValuesReuse>
		</Properties>
	</CommonModule>
</MetaDataObject>
""",
        encoding="utf-8",
    )


def write_catalog() -> None:
    name = "мкпКлиентыИнтеграции"
    uuid = "f4e1cc17-36e7-4e5a-83cc-3f485949e6e3"
    types = [
        ("CatalogObject." + name, "Object", "b8d69a56-7cd5-4230-8ddf-3ac60e442618", "5939add1-475d-4b83-a34a-8dc48e79d9d5"),
        ("CatalogRef." + name, "Ref", "b3f7b94b-5fbb-4fe8-b2ea-1427708937d5", "eca5acc3-320d-4fc9-b0e0-572fa6025026"),
        ("CatalogSelection." + name, "Selection", "affc911b-d6d3-41ff-875b-6c2bd1326eac", "92559e9a-5428-4e2e-86e1-fe037766c52a"),
        ("CatalogList." + name, "List", "b2830b4b-9b0a-4383-a9fa-35b5441ccf4a", "5d7e6bb5-bbc0-4917-87f1-93beaa7183bd"),
        ("CatalogManager." + name, "Manager", "a2b4bf6f-791d-47a4-83f5-6be6e8e16f51", "50167d57-11b6-42f7-bbdd-a36621cd0e1e"),
    ]
    attrs = [
        attribute("caab3d2c-5b3f-49be-852b-b079e76bfbb0", "ХешТокена", "Хеш токена", string_type(64)),
        attribute("4ab7e051-9502-412d-ba84-fdc7a8e657a6", "Скоупы", "Скоупы", string_type(500)),
        attribute("aa80a611-eeb7-4f66-9c46-85e91bbd205e", "ПользовательИБ", "Пользователь ИБ", string_type(100)),
        attribute("48ecff4f-79f0-4f01-9401-60e1195548d5", "Активен", "Активен", bool_type()),
    ]
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS}>
	<Catalog uuid="{uuid}">
		<InternalInfo>
{chr(10).join(generated(*t) for t in types)}
		</InternalInfo>
		<Properties>
			<Name>{name}</Name>
{synonym("1cmcp. Клиенты интеграции")}
			<Comment>Приложения и агенты: хеш токена, скоупы, сопоставленный пользователь 1С.</Comment>
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


def write_register(
    name: str,
    uuid: str,
    syn: str,
    comment: str,
    type_ids: list[tuple[str, str, str, str]],
    dimensions: list[str],
    resources: list[str],
) -> None:
    types_xml = chr(10).join(generated(*t) for t in type_ids)
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS}>
	<InformationRegister uuid="{uuid}">
		<InternalInfo>
{types_xml}
		</InternalInfo>
		<Properties>
			<Name>{name}</Name>
{synonym(syn)}
			<Comment>{comment}</Comment>
			<UseStandardCommands>true</UseStandardCommands>
			<EditType>InDialog</EditType>
			<DefaultRecordForm/>
			<DefaultListForm/>
			<AuxiliaryRecordForm/>
			<AuxiliaryListForm/>
			<StandardAttributes/>
			<InformationRegisterPeriodicity>Nonperiodical</InformationRegisterPeriodicity>
			<WriteMode>Independent</WriteMode>
			<MainFilterOnPeriod>false</MainFilterOnPeriod>
			<IncludeHelpInContents>false</IncludeHelpInContents>
			<DataLockControlMode>Managed</DataLockControlMode>
			<FullTextSearch>Use</FullTextSearch>
			<EnableTotalsSliceFirst>false</EnableTotalsSliceFirst>
			<EnableTotalsSliceLast>false</EnableTotalsSliceLast>
			<RecordPresentation/>
			<ExtendedRecordPresentation/>
			<ListPresentation/>
			<ExtendedListPresentation/>
			<Explanation/>
			<DataHistory>DontUse</DataHistory>
			<UpdateDataHistoryImmediatelyAfterWrite>false</UpdateDataHistoryImmediatelyAfterWrite>
			<ExecuteAfterWriteDataHistoryVersionProcessing>false</ExecuteAfterWriteDataHistoryVersionProcessing>
		</Properties>
		<ChildObjects>
{chr(10).join(dimensions)}
{chr(10).join(resources)}
		</ChildObjects>
	</InformationRegister>
</MetaDataObject>
"""
    path = ROOT / "InformationRegisters" / f"{name}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def main() -> None:
    write_catalog()

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

    write_register(
        "мкпПравилаДоступа",
        "f0b3dc98-3fb9-4aef-8b6c-a0cbcb5670c3",
        "1cmcp. Правила доступа",
        "Матрица объект × операция × поля для клиента интеграции.",
        ir_types(
            "мкпПравилаДоступа",
            [
                "3d9b3674-3523-4428-90c8-1ceb0eda1e61",
                "0f5ff89e-2878-480e-8992-cf6a6a92cba8",
                "05c39158-afff-4c02-b8c6-e8c60831f24b",
                "6cc1f8df-87b2-4784-a796-6e5e278f35c9",
                "e83769ff-c918-495a-acd4-5e768e0e92c1",
                "61dd5d4f-2df7-4170-b8a1-2520f3845c43",
                "502a27dd-fa82-458f-8a94-823e609cd32b",
                "aaf0a681-e180-4a07-affc-8a65dfd6e2d9",
                "79828e76-0b54-4b4b-a51c-c255d2da1578",
                "ab69cf8d-1848-494b-b2f3-42926adb985a",
                "74102897-290f-453f-9553-4fc22dbf150f",
                "8b8c1146-73a8-4af4-a1ad-088d9121817f",
                "21a5e422-9eef-4637-a155-7858bd8852ef",
                "2f172bc8-71ff-49d3-97b8-dac046aafda1",
            ],
        ),
        [
            dimension("de839395-e660-46bf-b561-214317b43a80", "Клиент", "Клиент", catalog_ref("мкпКлиентыИнтеграции")),
            dimension("99f3d9e7-463c-4872-9d0d-42535f28e3d9", "ВидОбъекта", "Вид объекта", string_type(50)),
            dimension("4ecc98a6-26ab-488f-a639-32a7403ced8f", "ИмяОбъекта", "Имя объекта", string_type(255)),
            dimension("4c6d712d-4aac-4b9e-a64d-11839184e00e", "Операция", "Операция", string_type(50)),
        ],
        [
            resource("8e0ddc68-7587-4874-bc22-39d2fea48a8a", "Разрешено", "Разрешено", bool_type()),
            resource("e347a2d4-1e94-4079-9c9a-981410e37af8", "Поля", "Поля", string_type(1000)),
        ],
    )

    write_register(
        "мкпСемантическийСловарь",
        "5ee34881-c6f5-49b6-8c6b-9cbceb0c3926",
        "1cmcp. Семантический словарь",
        "Человеческие названия, синонимы и примеры для объектов и реквизитов.",
        ir_types(
            "мкпСемантическийСловарь",
            [
                "0b97066e-0470-4616-b730-d80450dca11f",
                "56a96844-9cae-4057-ab1e-79ac9ee654c4",
                "1dcd0bd2-3018-4299-b6b6-ef6b9537fa6d",
                "7a57c3c4-a01c-4281-802e-859ec83ff2c3",
                "f66bbb28-9279-4121-84ac-9a5de7280aa1",
                "3dbf8ea8-1fd4-4974-b058-f79e625332ee",
                "7b351263-64b3-4204-9c07-4583d79ca471",
                "d0d27b7f-04c5-4f70-a4a8-0d878b0ab378",
                "edfdcdb4-8d46-4d46-82a6-8fcd20ed215e",
                "4d45032f-1b9c-4dea-b8fe-be6b6ecb29fd",
                "b9d0c219-5d43-48b4-9f56-a7b0c6b7d267",
                "4c385339-0fdc-4481-8f88-bf4b1de599b4",
                "f638bfc2-623f-4b49-b36f-748e277cb8c0",
                "154903e4-f80d-4b83-9403-7629b77bc969",
            ],
        ),
        [
            dimension("527604ae-7fb2-4b60-b24e-9c243e9fc33e", "ВидОбъекта", "Вид объекта", string_type(50)),
            dimension("305e3bf7-8b9f-43ad-9782-ca0201d931b3", "ИмяОбъекта", "Имя объекта", string_type(255)),
            dimension("af7f1bb2-d0c1-4937-95d6-b2b85dc15180", "ИмяПоля", "Имя поля", string_type(255)),
        ],
        [
            resource("89f8f050-863b-432d-bcda-174106af9898", "Синонимы", "Синонимы", string_type(500)),
            resource("43cfd8d1-80fd-4bd5-af33-af20a6ea9cac", "Описание", "Описание", string_type(1000)),
            resource("3f067ab6-eeec-4e00-98c5-7751599b9624", "Примеры", "Примеры", string_type(500)),
        ],
    )

    write_register(
        "мкпЖурналВызовов",
        "d20433f8-6391-42bd-a67c-a9c96c91f60d",
        "1cmcp. Журнал вызовов",
        "Кто, что, когда, сколько длилось.",
        ir_types(
            "мкпЖурналВызовов",
            [
                "e8b50c8c-3d78-4e73-bf52-26223c4963ef",
                "b9a98b9b-8636-4666-b9ee-16b8f524d32e",
                "a0c4c765-db9e-49eb-b152-8f542e555967",
                "d1285f90-6ad2-4a2a-a894-f0f4251e27e2",
                "6c9ad555-006a-45a4-9271-f0c18b69772c",
                "1b1307c8-ce49-4712-8bd6-ebba558aee54",
                "ae959b15-d267-47b8-ae2e-275ada303c5f",
                "5a827523-df06-42fd-849c-58b70c541864",
                "77fb33f0-b94b-460e-9003-7d86abc47165",
                "7e80ba6e-b176-4817-82ac-b523756e57be",
                "d65d6478-33cf-47a4-9a14-c92763eefb4c",
                "4e5ec630-2593-4e62-a02f-27ebc1e80d97",
                "dc766a78-8e27-4091-a453-6a797895f3a0",
                "9028dd9a-82ee-473c-b45b-ec795fa9596a",
            ],
        ),
        [
            dimension("dce313b7-3ca8-4eca-a0e9-61b891cc01a6", "Идентификатор", "Идентификатор", string_type(36)),
        ],
        [
            resource("04488a44-46bf-456d-8a8a-99f79d94a97a", "Клиент", "Клиент", catalog_ref("мкпКлиентыИнтеграции")),
            resource("9af25f0a-08b8-4019-8cdb-40c2cfa9e1ba", "Метод", "Метод", string_type(10)),
            resource("4fbf68dc-469f-49fa-8c45-646ec347d152", "Путь", "Путь", string_type(500)),
            resource("384211cb-a989-4e14-a348-66b37eea7f92", "КодОтвета", "Код ответа", number_type()),
            resource("b422845f-25bc-4170-9088-44b11f9fa251", "ДлительностьМс", "Длительность, мс", number_type()),
            resource("8fbe83d5-4b90-49b0-9549-ce9793c473c3", "Момент", "Момент", datetime_type()),
        ],
    )

    modules = [
        ("7e6f6875-4e3c-4b30-b633-9689d4695281", "мкпМаршрутизатор", "1cmcp. Маршрутизатор", "Разбор запроса и версия API."),
        ("6232905d-f648-4071-a936-6b34dfd57764", "мкпБезопасность", "1cmcp. Безопасность", "Токен, скоупы, правила доступа."),
        ("2a14ebad-afa7-4eff-85ce-3d32af98006a", "мкпСериализация", "1cmcp. Сериализация", "Типы 1С ↔ JSON."),
        ("d236f13c-2d7d-4d99-ab86-ae7f320ab599", "мкпИнтроспекция", "1cmcp. Интроспекция", "Метаданные и семантический словарь."),
        ("2295b973-d72d-4b26-a9eb-afc88be2d529", "мкпДанные", "1cmcp. Данные", "Чтение справочников, документов, регистров."),
    ]
    # Keep existing router UUID; only write new modules
    for uuid, name, syn, comment in modules[1:]:
        common_module(ROOT / "CommonModules" / f"{name}.xml", uuid, name, syn, comment)


if __name__ == "__main__":
    main()
