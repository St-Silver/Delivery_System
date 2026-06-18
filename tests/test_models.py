import pytest, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import init_db, get_connection
from models import Customer, Order

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    # очистка
    conn = get_connection()
    conn.execute("DELETE FROM order_items")
    conn.execute("DELETE FROM orders")
    conn.execute("DELETE FROM customers")
    conn.commit()
    conn.close()
    yield

def test_customer_crud():
    c = Customer(name="Тест", phone="123", address="ул. Тестовая")
    c.save()
    assert c.id is not None
    c2 = Customer.get_by_id(c.id)
    assert c2.name == "Тест"
    c2.name = "Обновлён"
    c2.save()
    c3 = Customer.get_by_id(c.id)
    assert c3.name == "Обновлён"
    # удаление без заказов – должно работать
    c3.delete()
    with pytest.raises(ValueError):
        Customer.get_by_id(c.id)

def test_customer_delete_restrict():
    c = Customer(name="С заказом", phone="2", address="a")
    c.save()
    o = Order(customer_id=c.id, order_date="2025-01-01", status="новый", total=100, items=[])
    o.save()
    with pytest.raises(RuntimeError):
        c.delete()

def test_order_crud_and_filter():
    c = Customer(name="Для заказа", phone="3", address="b")
    c.save()
    o = Order(customer_id=c.id, order_date="2025-03-15", status="новый", total=250,
              items=[{"product_name":"Товар", "quantity":2, "price":125}])
    o.save()
    orders = Order.get_all(status_filter="новый")
    assert len(orders) == 1
    assert orders[0].total == 250.0
    assert len(orders[0].items) == 1

def test_reports():
    from datetime import datetime
    c = Customer(name="Топ", phone="x", address="y")
    c.save()

    # Даты в текущем месяце, чтобы попасть в отчёт за "month"
    today = datetime.now()
    first_day_of_month = today.strftime("%Y-%m-01")
    mid_month = today.strftime("%Y-%m-15")

    Order(customer_id=c.id, order_date=first_day_of_month, status="выполнен", total=5000, items=[]).save()
    Order(customer_id=c.id, order_date=mid_month, status="новый", total=200, items=[]).save()

    counts = Order.count_by_status()
    assert counts.get("новый", 0) >= 1
    top = Order.top_customers(3)
    assert len(top) >= 1
    assert top[0]["name"] == "Топ"
    assert Order.revenue("month") > 0