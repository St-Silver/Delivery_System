import pytest, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import init_db, get_connection
from models import Customer, Order
from data_export import (
    export_orders_to_json, export_orders_to_xml,
    import_orders_from_json, import_orders_from_xml
)

@pytest.fixture(autouse=True)
def setup():
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM order_items")
    conn.execute("DELETE FROM orders")
    conn.execute("DELETE FROM customers")
    conn.commit()
    conn.close()
    # Добавим клиента и заказ
    c = Customer(name="Экспортный", phone="999", address="адр")
    c.save()
    Order(customer_id=c.id, order_date="2025-05-01", status="новый", total=123,
          items=[{"product_name":"Item1","quantity":1,"price":123}]).save()
    yield

def test_export_import_json():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    try:
        export_orders_to_json(tmp.name)
        # очистим БД и импортируем
        conn = get_connection()
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.commit()
        conn.close()
        cnt = import_orders_from_json(tmp.name)
        assert cnt == 1
        orders = Order.get_all()
        assert len(orders) == 1
        assert orders[0].total == 123
    finally:
        os.unlink(tmp.name)

def test_export_import_xml():
    tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
    tmp.close()
    try:
        export_orders_to_xml(tmp.name)
        conn = get_connection()
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.commit()
        conn.close()
        cnt = import_orders_from_xml(tmp.name)
        assert cnt == 1
        orders = Order.get_all()
        assert len(orders) == 1
    finally:
        os.unlink(tmp.name)