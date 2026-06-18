import pytest
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import init_db, get_connection

def test_init_and_connection():
    init_db()
    conn = get_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    assert "customers" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names
    conn.close()