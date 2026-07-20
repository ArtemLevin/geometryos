from scripts.export_tutorboard_contracts import contracts_are_fresh


def test_tutorboard_contract_fixtures_are_fresh() -> None:
    assert contracts_are_fresh()
