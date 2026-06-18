from database import get_connection
from logger_config import setup_logger
import sqlite3

logger = setup_logger("models")

class Customer:
    def __init__(self, id: int = None, name: str = "", phone: str = "", address: str = ""):
        self.id = id
        self.name = name
        self.phone = phone
        self.address = address

    @staticmethod
    def get_all() -> list["Customer"]:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
        conn.close()
        return [Customer(r["id"], r["name"], r["phone"], r["address"]) for r in rows]

    @staticmethod
    def get_by_id(customer_id: int) -> "Customer":
        conn = get_connection()
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        conn.close()
        if row is None:
            raise ValueError(f"Клиент с id={customer_id} не найден")
        return Customer(row["id"], row["name"], row["phone"], row["address"])

    def save(self) -> None:
        conn = get_connection()
        if self.id is None:
            cur = conn.execute(
                "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
                (self.name, self.phone, self.address)
            )
            self.id = cur.lastrowid
            logger.info(f"Добавлен клиент id={self.id} - {self.name}")
        else:
            conn.execute(
                "UPDATE customers SET name=?, phone=?, address=? WHERE id=?",
                (self.name, self.phone, self.address, self.id)
            )
            logger.info(f"Обновлён клиент id={self.id}")
        conn.commit()
        conn.close()

    def delete(self) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM customers WHERE id=?", (self.id,))
            conn.commit()
            logger.info(f"Удалён клиент id={self.id}")
        except sqlite3.IntegrityError as e:
            raise RuntimeError("Невозможно удалить клиента, у которого есть заказы") from e
        finally:
            conn.close()

    def has_orders(self) -> bool:
        conn = get_connection()
        row = conn.execute("SELECT COUNT(*) FROM orders WHERE customer_id=?", (self.id,)).fetchone()
        conn.close()
        return row[0] > 0

class Order:
    def __init__(self, id: int = None, customer_id: int = None, order_date: str = "",
                 status: str = "новый", total: float = 0.0, items: list = None):
        self.id = id
        self.customer_id = customer_id
        self.order_date = order_date
        self.status = status
        self.total = total
        self.items = items if items else []

    @staticmethod
    def get_all(status_filter: str = None, date_from: str = None, date_to: str = None) -> list["Order"]:
        conn = get_connection()
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        if date_from:
            query += " AND order_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND order_date <= ?"
            params.append(date_to)
        query += " ORDER BY order_date DESC"
        rows = conn.execute(query, params).fetchall()
        orders = []
        for r in rows:
            items = Order._get_items(conn, r["id"])
            orders.append(Order(r["id"], r["customer_id"], r["order_date"],
                                r["status"], r["total"], items))
        conn.close()
        return orders

    @staticmethod
    def get_by_id(order_id: int) -> "Order":
        conn = get_connection()
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            conn.close()
            raise ValueError(f"Заказ с id={order_id} не найден")
        items = Order._get_items(conn, order_id)
        conn.close()
        return Order(row["id"], row["customer_id"], row["order_date"],
                     row["status"], row["total"], items)

    @staticmethod
    def _get_items(conn, order_id: int) -> list[dict]:
        rows = conn.execute(
            "SELECT product_name, quantity, price FROM order_items WHERE order_id=?",
            (order_id,)
        ).fetchall()
        return [{"product_name": r["product_name"], "quantity": r["quantity"], "price": r["price"]} for r in rows]

    def save(self) -> None:
        conn = get_connection()
        if self.id is None:
            cur = conn.execute(
                "INSERT INTO orders (customer_id, order_date, status, total) VALUES (?, ?, ?, ?)",
                (self.customer_id, self.order_date, self.status, self.total)
            )
            self.id = cur.lastrowid
        else:
            conn.execute(
                "UPDATE orders SET customer_id=?, order_date=?, status=?, total=? WHERE id=?",
                (self.customer_id, self.order_date, self.status, self.total, self.id)
            )
            # Удаляем старые позиции и вставляем новые
            conn.execute("DELETE FROM order_items WHERE order_id=?", (self.id,))
        # Вставка позиций
        for item in self.items:
            conn.execute(
                "INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)",
                (self.id, item["product_name"], item["quantity"], item["price"])
            )
        conn.commit()
        conn.close()
        logger.info(f"Сохранён заказ id={self.id}")

    def delete(self) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM orders WHERE id=?", (self.id,))
        conn.commit()
        conn.close()
        logger.info(f"Удалён заказ id={self.id}")

    # Методы для отчётов
    @staticmethod
    def count_by_status() -> dict:
        conn = get_connection()
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
        ).fetchall()
        conn.close()
        return {row["status"]: row["cnt"] for row in rows}

    @staticmethod
    def top_customers(limit: int = 3) -> list[dict]:
        conn = get_connection()
        rows = conn.execute("""
            SELECT c.name, SUM(o.total) as total_sum
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            GROUP BY c.id
            ORDER BY total_sum DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [{"name": r["name"], "total": r["total_sum"]} for r in rows]

    @staticmethod
    def revenue(period: str) -> float:
        from datetime import datetime, timedelta
        conn = get_connection()
        now = datetime.now()
        if period == "day":
            start = now.strftime("%Y-%m-%d")
        elif period == "week":
            start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        elif period == "month":
            start = now.strftime("%Y-%m-01")
        else:
            raise ValueError("Период может быть day/week/month")
        row = conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM orders WHERE order_date >= ? AND status != 'отменён'",
            (start,)
        ).fetchone()
        conn.close()
        return row[0]