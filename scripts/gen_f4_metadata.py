#!/usr/bin/env python3
"""UUID обработки администрирования Ф4 зафиксированы в XML. Скрипт — справочник, не перезаписывает файлы."""

from __future__ import annotations

IDS = {
    "processor": "34a6d85e-d5ae-49da-8cf9-f6a8d2494ed4",
    "object_type": "b22a8b15-5e3b-4f4a-9b6f-05966cd75953",
    "object_value": "b06a7c37-26c4-476d-9a00-0f3ab7a7aa8d",
    "manager_type": "894895b7-ae66-4ed6-b821-a279f55838a2",
    "manager_value": "f9e2f018-40af-408b-9910-a27789e4546f",
    "form": "fa2c6bcc-3880-43bc-82b2-e8ae42b3d0fa",
    "http_diag_template": "12b02d96-7ebd-4b80-8610-1a72b2cf7376",
    "http_diag_get": "a77f7461-c3fb-403c-a909-257a03f171d0",
}


if __name__ == "__main__":
    for key, value in IDS.items():
        print(key, value)
