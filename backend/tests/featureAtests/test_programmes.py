
import sqlite3
import app.api.programmes as programmes


#test 1 -> programmes are returned in alphabetical order
def test_programmes_alphabetical_order(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"

    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE programmes (
            id INTEGER,
            redbrick_name TEXT,
            redbrick_uuid TEXT
        )
    """)

    con.executemany(
        "INSERT INTO programmes VALUES (?, ?, ?)",
        [
            (1, "Computer Science", "uuid-1"),
            (2, "Accounting", "uuid-2"),
            (3, "Business Studies", "uuid-3")
        ]
    )
    con.commit()
    con.close()

    #temporarily changes programmes.DB_PATH to point to
    #the temporary db that we created above
    monkeypatch.setattr(programmes, "DB_PATH", str(db_path))

    result = programmes.get_programmes()

    assert result == [
        {"redbrick_name": "Accounting", "redbrick_uuid": "uuid-2"},
        {"redbrick_name": "Business Studies", "redbrick_uuid": "uuid-3"},
        {"redbrick_name": "Computer Science", "redbrick_uuid": "uuid-1"}
    ]


#test 2 -> empty database table returns an empty list
def test_programmes_empty_table(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"

    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE programmes (
            id INTEGER,
            redbrick_name TEXT,
            redbrick_uuid TEXT
        )
    """)
    con.commit()
    con.close()

    monkeypatch.setattr(programmes, "DB_PATH", str(db_path))

    result = programmes.get_programmes()

    assert result == []


#test 3 -> only the programme name and UUID are returned
def test_programmes_only_required_fields(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"

    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE programmes (
            id INTEGER,
            redbrick_name TEXT,
            extra_information TEXT,
            redbrick_uuid TEXT
        )
    """)

    con.execute(
        "INSERT INTO programmes VALUES (?, ?, ?, ?)",
        (1, "Computer Science", "Not needed", "uuid-123")
    )
    con.commit()
    con.close()

    monkeypatch.setattr(programmes, "DB_PATH", str(db_path))

    result = programmes.get_programmes()

    assert result == [
        {"redbrick_name": "Computer Science", "redbrick_uuid": "uuid-123"}
    ]

    assert len(result[0]) == 2


#test 4 -> a single programme is returned correctly
def test_programmes_single_programme(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"

    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE programmes (
            id INTEGER,
            redbrick_name TEXT,
            redbrick_uuid TEXT
        )
    """)

    con.execute(
        "INSERT INTO programmes VALUES (?, ?, ?)",
        (1, "Computing for Business", "uuid-456")
    )
    con.commit()
    con.close()

    monkeypatch.setattr(programmes, "DB_PATH", str(db_path))

    result = programmes.get_programmes()

    assert result == [
        {"redbrick_name": "Computing for Business", "redbrick_uuid": "uuid-456"}
    ]
