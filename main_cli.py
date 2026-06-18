import argparse
from database import init_db
from models import Order, Customer
from data_export import (
    export_orders_to_json, export_orders_to_xml,
    import_orders_from_json, import_orders_from_xml
)
from logger_config import setup_logger

logger = setup_logger("cli")

def report(args):
    period = args.period
    print(f"=== Отчёт за период: {period} ===")
    print("\nЗаказы по статусам:")
    status_counts = Order.count_by_status()
    for s, cnt in status_counts.items():
        print(f"  {s}: {cnt}")
    print("\nТоп-3 клиента по сумме заказов:")
    top = Order.top_customers(3)
    for c in top:
        print(f"  {c['name']}: {c['total']:.2f} руб.")
    print(f"\nОбщая выручка: {Order.revenue(period):.2f} руб.")

def export_cmd(args):
    file = args.file
    if file.endswith(".json"):
        export_orders_to_json(file)
    elif file.endswith(".xml"):
        export_orders_to_xml(file)
    else:
        print("Укажите файл с расширением .json или .xml")

def import_cmd(args):
    file = args.file
    if file.endswith(".json"):
        cnt = import_orders_from_json(file)
        print(f"Импортировано заказов: {cnt}")
    elif file.endswith(".xml"):
        cnt = import_orders_from_xml(file)
        print(f"Импортировано заказов: {cnt}")
    else:
        print("Укажите файл с расширением .json или .xml")

def main():
    init_db()
    parser = argparse.ArgumentParser(description="Система учёта заказов Быстрая доставка")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rep = subparsers.add_parser("report", help="Отчёт о заказах")
    rep.add_argument("--period", choices=["day","week","month"], default="month")
    rep.set_defaults(func=report)

    exp = subparsers.add_parser("export", help="Экспорт заказов")
    exp.add_argument("--file", required=True)
    exp.set_defaults(func=export_cmd)

    imp = subparsers.add_parser("import", help="Импорт заказов")
    imp.add_argument("--file", required=True)
    imp.set_defaults(func=import_cmd)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()