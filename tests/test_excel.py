from pathlib import Path

from openpyxl import Workbook, load_workbook

from zabbix_catalog_generator.excel import generate_catalogue
from zabbix_catalog_generator.models import ProbeDefinition, TriggerDefinition


def test_catalogue_creates_one_row_per_trigger(tmp_path: Path) -> None:
    model = tmp_path / "model.xlsx"
    output = tmp_path / "catalogue.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Database"
    sheet.append(["Ressource", "Clef", "Description", "LLD", "Triger Name", "Sévérité"])
    sheet.append([None] * 6)
    sheet.append(["style"] * 6)
    workbook.save(model)

    probe = ProbeDefinition(
        template_name="Oracle",
        template_description="",
        name="Sessions",
        key="oracle.sessions",
        description="Session count",
        delay="5m",
        item_type="ZABBIX_ACTIVE",
        value_type="UNSIGNED",
        units="",
        history="7d",
        trends="365d",
        triggers=(
            TriggerDefinition("Warning", severity="WARNING"),
            TriggerDefinition("High", severity="HIGH"),
        ),
    )

    generate_catalogue(model, output, [probe])

    result = load_workbook(output).active
    assert result.cell(3, 1).value == "Sessions"
    assert result.cell(4, 1).value == "Sessions"
    assert result.cell(3, 5).value == "Warning"
    assert result.cell(4, 5).value == "High"
