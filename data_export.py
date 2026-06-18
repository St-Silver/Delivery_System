import json
import xml.etree.ElementTree as ET
from models import Order, Customer
from logger_config import setup_logger

logger = setup_logger("export")

def export_orders_to_json(filepath: str) -> None:
    orders = Order.get_all()
    data = []
    for o in orders:
        cust = Customer.get_by_id(o.customer_id)
        data.append({
            "id": o.id,
            "customer": {"id": cust.id, "name": cust.name, "phone": cust.phone, "address": cust.address},
            "order_date": o.order_date,
            "status": o.status,
            "total": o.total,
            "items": o.items
        })
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Экспортировано {len(data)} заказов в JSON: {filepath}")

def export_orders_to_xml(filepath: str) -> None:
    orders = Order.get_all()
    root = ET.Element("orders")
    for o in orders:
        cust = Customer.get_by_id(o.customer_id)
        order_el = ET.SubElement(root, "order", id=str(o.id))
        customer_el = ET.SubElement(order_el, "customer", id=str(cust.id))
        ET.SubElement(customer_el, "name").text = cust.name
        ET.SubElement(customer_el, "phone").text = cust.phone or ""
        ET.SubElement(customer_el, "address").text = cust.address or ""
        ET.SubElement(order_el, "order_date").text = o.order_date
        ET.SubElement(order_el, "status").text = o.status
        ET.SubElement(order_el, "total").text = str(o.total)
        items_el = ET.SubElement(order_el, "items")
        for item in o.items:
            item_el = ET.SubElement(items_el, "item")
            ET.SubElement(item_el, "product_name").text = item["product_name"]
            ET.SubElement(item_el, "quantity").text = str(item["quantity"])
            ET.SubElement(item_el, "price").text = str(item["price"])
    tree = ET.ElementTree(root)
    tree.write(filepath, encoding="utf-8", xml_declaration=True)
    logger.info(f"Экспортировано {len(orders)} заказов в XML: {filepath}")

def import_orders_from_json(filepath: str) -> int:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for entry in data:
        # Найти или создать клиента
        customer = _find_or_create_customer(entry["customer"])
        order = Order(
            customer_id=customer.id,
            order_date=entry["order_date"],
            status=entry["status"],
            total=entry["total"],
            items=entry["items"]
        )
        order.save()
        count += 1
    logger.info(f"Импортировано {count} заказов из JSON")
    return count

def import_orders_from_xml(filepath: str) -> int:
    tree = ET.parse(filepath)
    root = tree.getroot()
    count = 0
    for order_el in root.findall("order"):
        customer_el = order_el.find("customer")
        cust_data = {
            "id": int(customer_el.get("id")),
            "name": customer_el.find("name").text,
            "phone": customer_el.find("phone").text,
            "address": customer_el.find("address").text
        }
        customer = _find_or_create_customer(cust_data)
        items = []
        items_el = order_el.find("items")
        if items_el is not None:
            for item_el in items_el.findall("item"):
                items.append({
                    "product_name": item_el.find("product_name").text,
                    "quantity": int(item_el.find("quantity").text),
                    "price": float(item_el.find("price").text)
                })
        order = Order(
            customer_id=customer.id,
            order_date=order_el.find("order_date").text,
            status=order_el.find("status").text,
            total=float(order_el.find("total").text),
            items=items
        )
        order.save()
        count += 1
    logger.info(f"Импортировано {count} заказов из XML")
    return count

def _find_or_create_customer(cust_dict: dict) -> Customer:
    # Ищем по id, если есть и существует
    if "id" in cust_dict and cust_dict["id"]:
        try:
            return Customer.get_by_id(cust_dict["id"])
        except ValueError:
            pass
    # Ищем по имени и телефону (простейшая дедупликация)
    all_customers = Customer.get_all()
    for c in all_customers:
        if c.name == cust_dict["name"] and (c.phone == cust_dict.get("phone", "") or not cust_dict.get("phone")):
            return c
    # Создаём нового
    new_cust = Customer(name=cust_dict["name"], phone=cust_dict.get("phone", ""), address=cust_dict.get("address", ""))
    new_cust.save()
    return new_cust