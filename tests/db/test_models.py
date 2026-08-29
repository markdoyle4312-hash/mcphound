from mcphound.db.models import Base, Finding, Hash, Scan, Server, Version


def test_all_five_tables_are_registered():
    table_names = set(Base.metadata.tables.keys())
    assert table_names == {"servers", "versions", "hashes", "scans", "findings"}


def test_versions_natural_key_constraint_columns():
    versions_table = Base.metadata.tables["versions"]
    constraint = next(
        c for c in versions_table.constraints if getattr(c, "name", None) == "uq_versions_natural_key"
    )
    assert {col.name for col in constraint.columns} == {
        "server_id",
        "version",
        "registry_type",
        "identifier",
    }


def test_model_classes_map_to_expected_tables():
    assert Server.__tablename__ == "servers"
    assert Version.__tablename__ == "versions"
    assert Hash.__tablename__ == "hashes"
    assert Scan.__tablename__ == "scans"
    assert Finding.__tablename__ == "findings"
