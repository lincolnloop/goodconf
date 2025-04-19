from goodconf import Field, GoodConf


def test_list_field(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "*")

    class Config(GoodConf):
        allowed_hosts: list[str] = Field(
            description="E.g. ALLOWED_HOSTS=localhost,acme.test"
        )

    config = Config()
    config.load()
    assert config.allowed_hosts == ["*"]
