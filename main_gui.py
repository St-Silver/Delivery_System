import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from models import Customer, Order
from database import init_db
from data_export import export_orders_to_json, export_orders_to_xml, import_orders_from_json, import_orders_from_xml
from logger_config import setup_logger

logger = setup_logger("gui")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Быстрая доставка – управление заказами")
        self.root.geometry("1000x600")

        self.status_filter = tk.StringVar()

        self._create_widgets()
        self.refresh_orders()

    def _create_widgets(self):
        # Панель фильтра
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Фильтр по статусу:").pack(side=tk.LEFT, padx=5)
        self.status_combo = ttk.Combobox(filter_frame, textvariable=self.status_filter,
                                         values=["Все","новый","в доставке","выполнен","отменён"],
                                         state="readonly")
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Применить", command=self.refresh_orders).pack(side=tk.LEFT, padx=5)

        # Таблица заказов
        self.tree = ttk.Treeview(self.root, columns=("ID","Клиент","Дата","Статус","Сумма"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Клиент", text="Клиент")
        self.tree.heading("Дата", text="Дата")
        self.tree.heading("Статус", text="Статус")
        self.tree.heading("Сумма", text="Сумма")
        self.tree.column("ID", width=40)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Кнопки управления
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Добавить заказ", command=self.add_order).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_order).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_order).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Клиенты", command=self.manage_customers).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Отчёт", command=self.show_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Экспорт JSON", command=lambda: self.export("json")).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text="Экспорт XML", command=lambda: self.export("xml")).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text="Импорт JSON", command=lambda: self.import_orders("json")).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text="Импорт XML", command=lambda: self.import_orders("xml")).pack(side=tk.RIGHT, padx=2)

    def refresh_orders(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        status = self.status_filter.get()
        if status == "Все":
            status = None

        orders = Order.get_all(status_filter=status)
        for o in orders:
            try:
                cust = Customer.get_by_id(o.customer_id)
                cust_name = cust.name
            except ValueError:
                cust_name = "???"
            self.tree.insert("", "end", values=(o.id, cust_name, o.order_date, o.status, f"{o.total:.2f}"))

    def add_order(self):
        OrderDialog(self.root, on_save=self.refresh_orders)

    def edit_order(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите заказ для редактирования")
            return
        order_id = self.tree.item(selected[0])["values"][0]
        order = Order.get_by_id(order_id)
        OrderDialog(self.root, order=order, on_save=self.refresh_orders)

    def delete_order(self):
        selected = self.tree.selection()
        if not selected:
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранный заказ?"):
            order_id = self.tree.item(selected[0])["values"][0]
            order = Order.get_by_id(order_id)
            order.delete()
            self.refresh_orders()

    def manage_customers(self):
        CustomerWindow(self.root)

    def show_report(self):
        ReportWindow(self.root)

    def export(self, fmt):
        from tkinter import filedialog
        ext = ".json" if fmt == "json" else ".xml"
        filepath = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[(f"{fmt.upper()} files", f"*{ext}")])
        if filepath:
            if fmt == "json":
                export_orders_to_json(filepath)
            else:
                export_orders_to_xml(filepath)
            messagebox.showinfo("Успех", f"Заказы экспортированы в {filepath}")
    
    def import_orders(self, fmt):
        from tkinter import filedialog
        ext = ".json" if fmt == "json" else ".xml"
        filepath = filedialog.askopenfilename(
            filetypes=[(f"{fmt.upper()} files", f"*{ext}"), ("All files", "*.*")]
        )
        if not filepath:
            return
        try:
            if fmt == "json":
                cnt = import_orders_from_json(filepath)
            else:
                cnt = import_orders_from_xml(filepath)
            messagebox.showinfo("Импорт завершён", f"Импортировано заказов: {cnt}")
            self.refresh_orders()  # обновить таблицу
        except Exception as e:
            logger.exception("Ошибка импорта")
            messagebox.showerror("Ошибка импорта", str(e))

class OrderDialog(tk.Toplevel):
    def __init__(self, parent, order=None, on_save=None):
        super().__init__(parent)
        self.order = order
        self.on_save = on_save
        self.title("Заказ" if order else "Новый заказ")
        self.geometry("400x400")

        self.cust_var = tk.StringVar()
        self.date_var = tk.StringVar(value=order.order_date if order else "")
        self.status_var = tk.StringVar(value=order.status if order else "новый")
        self.total_var = tk.DoubleVar(value=order.total if order else 0.0)

        # Выбор клиента
        ttk.Label(self, text="Клиент:").pack(pady=2)
        customers = Customer.get_all()
        cust_names = [c.name for c in customers]
        self.cust_combo = ttk.Combobox(self, textvariable=self.cust_var, values=cust_names, state="readonly")
        if order:
            try:
                cust = Customer.get_by_id(order.customer_id)
                self.cust_var.set(cust.name)
            except:
                pass
        self.cust_combo.pack()

        ttk.Label(self, text="Дата (ГГГГ-ММ-ДД):").pack()
        ttk.Entry(self, textvariable=self.date_var).pack()

        ttk.Label(self, text="Статус:").pack()
        ttk.Combobox(self, textvariable=self.status_var, values=["новый","в доставке","выполнен","отменён"], state="readonly").pack()

        ttk.Label(self, text="Итоговая сумма:").pack()
        ttk.Entry(self, textvariable=self.total_var).pack()

        # Позиции (упрощённо)
        self.items_text = tk.Text(self, height=6)
        self.items_text.pack(pady=5, fill=tk.BOTH, expand=True)
        if order and order.items:
            lines = [f"{it['product_name']},{it['quantity']},{it['price']}" for it in order.items]
            self.items_text.insert("1.0", "\n".join(lines))

        ttk.Label(self, text="Позиции: название,кол-во,цена (одна на строку)").pack()

        ttk.Button(self, text="Сохранить", command=self.save).pack(pady=10)

    def save(self):
        cust_name = self.cust_var.get()
        if not cust_name:
            messagebox.showerror("Ошибка", "Выберите клиента")
            return
        customers = Customer.get_all()
        cust = next((c for c in customers if c.name == cust_name), None)
        if not cust:
            messagebox.showerror("Ошибка", "Клиент не найден")
            return

        items = []
        raw = self.items_text.get("1.0", tk.END).strip()
        if raw:
            for line in raw.split("\n"):
                parts = line.split(",")
                if len(parts) == 3:
                    items.append({
                        "product_name": parts[0].strip(),
                        "quantity": int(parts[1].strip()),
                        "price": float(parts[2].strip())
                    })

        order_data = {
            "customer_id": cust.id,
            "order_date": self.date_var.get(),
            "status": self.status_var.get(),
            "total": self.total_var.get(),
            "items": items
        }

        if self.order:
            self.order.customer_id = order_data["customer_id"]
            self.order.order_date = order_data["order_date"]
            self.order.status = order_data["status"]
            self.order.total = order_data["total"]
            self.order.items = order_data["items"]
            self.order.save()
        else:
            new_order = Order(**order_data)
            new_order.save()

        if self.on_save:
            self.on_save()
        self.destroy()

class CustomerWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Управление клиентами")
        self.geometry("500x400")
        self.tree = ttk.Treeview(self, columns=("ID","Имя","Телефон","Адрес"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Имя", text="Имя")
        self.tree.heading("Телефон", text="Телефон")
        self.tree.heading("Адрес", text="Адрес")
        self.tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Добавить", command=self.add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete).pack(side=tk.LEFT, padx=2)

        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for c in Customer.get_all():
            self.tree.insert("", "end", values=(c.id, c.name, c.phone, c.address))

    def add(self):
        CustomerEditDialog(self, on_save=self.refresh)

    def edit(self):
        sel = self.tree.selection()
        if not sel: return
        cid = self.tree.item(sel[0])["values"][0]
        cust = Customer.get_by_id(cid)
        CustomerEditDialog(self, customer=cust, on_save=self.refresh)

    def delete(self):
        sel = self.tree.selection()
        if not sel: return
        cid = self.tree.item(sel[0])["values"][0]
        cust = Customer.get_by_id(cid)
        try:
            cust.delete()
            self.refresh()
        except RuntimeError as e:
            messagebox.showerror("Ошибка", str(e))

class CustomerEditDialog(tk.Toplevel):
    def __init__(self, parent, customer=None, on_save=None):
        super().__init__(parent)
        self.customer = customer
        self.on_save = on_save
        self.title("Клиент")
        self.name_var = tk.StringVar(value=customer.name if customer else "")
        self.phone_var = tk.StringVar(value=customer.phone if customer else "")
        self.addr_var = tk.StringVar(value=customer.address if customer else "")

        ttk.Label(self, text="Имя").pack()
        ttk.Entry(self, textvariable=self.name_var).pack()
        ttk.Label(self, text="Телефон").pack()
        ttk.Entry(self, textvariable=self.phone_var).pack()
        ttk.Label(self, text="Адрес").pack()
        ttk.Entry(self, textvariable=self.addr_var).pack()

        ttk.Button(self, text="Сохранить", command=self.save).pack(pady=10)

    def save(self):
        if self.customer:
            self.customer.name = self.name_var.get()
            self.customer.phone = self.phone_var.get()
            self.customer.address = self.addr_var.get()
            self.customer.save()
        else:
            c = Customer(name=self.name_var.get(), phone=self.phone_var.get(), address=self.addr_var.get())
            c.save()
        if self.on_save:
            self.on_save()
        self.destroy()

class ReportWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Отчёт")
        self.geometry("400x300")
        status_counts = Order.count_by_status()
        top = Order.top_customers(3)
        revenue_month = Order.revenue("month")

        text = tk.Text(self)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", "=== Заказы по статусам ===\n")
        for s, c in status_counts.items():
            text.insert(tk.END, f"{s}: {c}\n")
        text.insert(tk.END, "\n=== Топ-3 клиента ===\n")
        for c in top:
            text.insert(tk.END, f"{c['name']}: {c['total']:.2f} руб.\n")
        text.insert(tk.END, f"\nОбщая выручка за месяц: {revenue_month:.2f} руб.\n")
        text.config(state=tk.DISABLED)

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = App(root)
    root.mainloop()