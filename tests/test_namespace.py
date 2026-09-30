def test_official_sdk_namespaces_are_not_shadowed() -> None:
    import agents
    import mcp

    import ayorai_attractor

    assert "site-packages" in agents.__file__
    assert "site-packages" in mcp.__file__
    assert "ayorai_attractor" in ayorai_attractor.__file__
