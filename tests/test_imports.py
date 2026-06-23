def test_public_packages_import() -> None:
    import gir_ai
    import gir_api
    import gir_benchmarks
    import gir_cli
    import gir_core
    import gir_render

    assert gir_ai is not None
    assert gir_api is not None
    assert gir_benchmarks is not None
    assert gir_cli is not None
    assert gir_core is not None
    assert gir_render is not None
