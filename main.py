import sqlite3
import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime

# --- БАЗА ДАНИХ ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("lumastock_db.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.setup()

    def setup(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, brand TEXT, item_name TEXT, supplier TEXT,
            supplier_link TEXT, price_goods REAL, price_delivery REAL,
            total_price REAL, quantity REAL, unit TEXT, unit_price REAL, 
            ml_capacity REAL, date_added TEXT
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER, item_info TEXT, used_qty REAL, 
            unit TEXT, reason TEXT, date_used TEXT
        )''')
        self.conn.commit()

    def add_item(self, category, brand, name, supplier, link, p_goods, p_del, qty, unit, ml=0):
        total = p_goods + p_del
        u_price = total / qty if qty > 0 else 0
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute("""INSERT INTO inventory 
            (category, brand, item_name, supplier, supplier_link, price_goods, price_delivery, total_price, quantity, unit, unit_price, ml_capacity, date_added) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (category, brand, name, supplier, link, p_goods, p_del, total, qty, unit, u_price, ml, date_now))
        self.conn.commit()

    def get_filtered_items(self, search_query=""):
        query = "SELECT * FROM inventory"
        params = []
        if search_query:
            query += " WHERE category LIKE ? OR brand LIKE ? OR item_name LIKE ? OR supplier LIKE ?"
            like_val = f"%{search_query}%"
            params = [like_val] * 4
        query += " ORDER BY date_added DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_items_by_category(self, category):
        self.cursor.execute("SELECT DISTINCT item_name FROM inventory WHERE category = ?", (category,))
        return [row["item_name"] for row in self.cursor.fetchall()]

    def get_last_price_and_ml(self, item_name):
        self.cursor.execute("SELECT unit_price, ml_capacity FROM inventory WHERE item_name = ? ORDER BY id DESC LIMIT 1", (item_name,))
        result = self.cursor.fetchone()
        return (result["unit_price"], result["ml_capacity"]) if result else (0, 0)

    def delete_item(self, item_id):
        self.cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        self.conn.commit()

    def get_all_items_for_list(self):
        self.cursor.execute("SELECT id, item_name, brand, quantity, unit FROM inventory WHERE quantity > 0")
        return self.cursor.fetchall()

    def log_usage(self, item_id, qty, reason):
        self.cursor.execute("SELECT item_name, brand, unit, quantity FROM inventory WHERE id = ?", (item_id,))
        item = self.cursor.fetchone()
        if item and item['quantity'] >= qty:
            date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
            info = f"{item['item_name']} ({item['brand']})"
            self.cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (qty, item_id))
            self.cursor.execute("INSERT INTO usage_logs (item_id, item_info, used_qty, unit, reason, date_used) VALUES (?,?,?,?,?,?)",
                                (item_id, info, qty, item['unit'], reason, date_now))
            self.conn.commit()
            return True
        return False

# --- ГОЛОВНИЙ ДОДАТОК ---
class LumaStockApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title("LumaStock ERP")
        self.geometry("1450x950")
        ctk.set_appearance_mode("light")

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#F1F5F9")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(self.sidebar, text="LumaStock", font=("Segoe UI", 28, "bold"), text_color="#3B8ED0").pack(pady=40)
        self.create_nav_btn("➕ Нова закупівля", "add")
        self.create_nav_btn("📦 Великий склад", "stock")
        self.create_nav_btn("🧮 Конструктор", "calc")
        self.create_nav_btn("📉 Списання", "usage")

        self.container = ctk.CTkFrame(self, corner_radius=15, fg_color="white")
        self.container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.frames = {}
        self.setup_add_frame()
        self.setup_stock_frame()
        self.setup_calc_frame()
        self.setup_usage_frame()
        self.show_frame("add")

    def create_nav_btn(self, text, target):
        ctk.CTkButton(self.sidebar, text=text, font=("Segoe UI", 15), fg_color="transparent", text_color="#334155", 
                      hover_color="#E2E8F0", anchor="w", height=45, command=lambda: self.show_frame(target)).pack(fill="x", padx=15, pady=5)

    # --- ЗАКУПІВЛЯ ---
    def setup_add_frame(self):
        frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["add"] = frame
        ctk.CTkLabel(frame, text="Нова поставка", font=("Segoe UI", 30, "bold")).pack(pady=20)
        main_form = ctk.CTkFrame(frame, fg_color="transparent"); main_form.pack(padx=60, fill="x")

        box_left = ctk.CTkFrame(main_form, fg_color="#F8FAFC", corner_radius=12, border_width=1, border_color="#E2E8F0")
        box_left.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        
        self.create_form_entry(box_left, "Категорія товару:", "combo", ["Віск", "Аромка", "Гніт", "Тара", "Кришка", "Упаковка", "Декор"], "e_cat")
        self.e_cat.configure(command=self.update_fields)
        self.create_form_entry(box_left, "Назва товару:", "entry", None, "e_name")
        self.create_form_entry(box_left, "Магазин (Постачальник):", "entry", None, "e_supp")
        self.create_form_entry(box_left, "Посилання на товар:", "entry", None, "e_link")

        box_right = ctk.CTkFrame(main_form, fg_color="#F8FAFC", corner_radius=12, border_width=1, border_color="#E2E8F0")
        box_right.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        
        self.create_form_entry(box_right, "Ціна за товар (грн):", "entry", None, "e_price")
        self.create_form_entry(box_right, "Вартість доставки (грн):", "entry", None, "e_del")
        
        lbl_qty = ctk.CTkLabel(box_right, text="Кількість та одиниці виміру:", font=("Segoe UI", 13, "bold"), text_color="#475569")
        lbl_qty.pack(padx=20, pady=(10, 2), anchor="w")
        row_qty = ctk.CTkFrame(box_right, fg_color="transparent"); row_qty.pack(fill="x", padx=20, pady=(0, 10))
        self.e_qty = ctk.CTkEntry(row_qty, height=40, placeholder_text="0"); self.e_qty.pack(side="left", expand=True, fill="x")
        self.e_unit = ctk.CTkComboBox(row_qty, values=["г", "мл", "шт"], height=40, width=80); self.e_unit.set("г"); self.e_unit.pack(side="left", padx=(10, 0))

        # СПЕЦІАЛЬНИЙ БЛОК (Динамічний текст)
        self.spec_box = ctk.CTkFrame(frame, fg_color="#F1F5F9", corner_radius=12); self.spec_box.pack(padx=70, fill="x", pady=10)
        self.spec_content = ctk.CTkFrame(self.spec_box, fg_color="transparent"); self.spec_content.pack(expand=True, pady=10)
        
        # Повертаємо текстову мітку, яка буде мінятися
        self.lbl_dynamic = ctk.CTkLabel(self.spec_content, text="Оберіть вид воску:", font=("Segoe UI", 13, "bold"), text_color="#475569")
        self.lbl_dynamic.pack(side="left", padx=10)
        
        self.e_brand_entry = ctk.CTkEntry(self.spec_content, height=40, width=250, placeholder_text="Напр. Kerax")
        self.e_brand_wax = ctk.CTkComboBox(self.spec_content, values=["Соєвий віск", "Кокосовий віск", "Пальмовий віск", "Бджолиний віск", "Парафін", "Інше"], height=40, width=200, command=self.check_wax_type); self.e_brand_wax.set("")
        self.e_wax_other = ctk.CTkEntry(self.spec_content, height=40, width=150, placeholder_text="Який саме?")
        self.e_ml = ctk.CTkEntry(self.spec_content, height=40, width=80, placeholder_text="0"); self.lbl_ml = ctk.CTkLabel(self.spec_content, text="мл")

        ctk.CTkButton(frame, text="ЗБЕРЕГТИ У СКЛАД", fg_color="#3B8ED0", height=55, width=400, font=("bold", 18), command=self.save_purchase).pack(pady=20)
        self.update_fields("Віск")

    def create_form_entry(self, parent, label_text, type, values, attr_name):
        lbl = ctk.CTkLabel(parent, text=label_text, font=("Segoe UI", 13, "bold"), text_color="#475569")
        lbl.pack(padx=20, pady=(10, 2), anchor="w")
        if type == "combo":
            widget = ctk.CTkComboBox(parent, values=values, height=40)
            widget.set("")
        else:
            widget = ctk.CTkEntry(parent, height=40)
        widget.pack(fill="x", padx=20, pady=(0, 10))
        setattr(self, attr_name, widget)

    def check_wax_type(self, choice):
        if choice == "Інше": self.e_wax_other.pack(side="left", padx=5)
        else: self.e_wax_other.pack_forget()

    def update_fields(self, choice):
        """Оновлення тексту та полів залежно від категорії"""
        for w in [self.e_brand_entry, self.e_brand_wax, self.e_wax_other, self.e_ml, self.lbl_ml]: w.pack_forget()
        
        if choice == "Віск": 
            self.lbl_dynamic.configure(text="Оберіть вид воску:")
            self.e_brand_wax.pack(side="left", padx=10)
            self.e_unit.set("г")
        elif choice == "Тара": 
            self.lbl_dynamic.configure(text="Бренд та об'єм тари:")
            self.e_brand_entry.pack(side="left", padx=10)
            self.e_ml.pack(side="left", padx=5); self.lbl_ml.pack(side="left")
            self.e_unit.set("шт")
        else: 
            self.lbl_dynamic.configure(text="Вкажіть бренд:")
            self.e_brand_entry.pack(side="left", padx=10)
            if choice == "Аромка": self.e_unit.set("г")
            elif choice in ["Гніт", "Кришка", "Упаковка"]: self.e_unit.set("шт")

    def save_purchase(self):
        try:
            cat = self.e_cat.get()
            brand = self.e_brand_entry.get() if cat != "Віск" else (f"Інше: {self.e_wax_other.get()}" if self.e_brand_wax.get() == "Інше" else self.e_brand_wax.get())
            ml_val = float(self.e_ml.get() or 0) if cat == "Тара" else 0
            self.db.add_item(cat, brand, self.e_name.get(), self.e_supp.get(), self.e_link.get(), float(self.e_price.get()), float(self.e_del.get() or 0), float(self.e_qty.get()), self.e_unit.get(), ml_val)
            messagebox.showinfo("LumaStock", "Успішно додано!"); self.update_stock_table()
        except: messagebox.showerror("Помилка", "Заповніть ціну та кількість числами")

    # --- КОНСТРУКТОР ---
    def setup_calc_frame(self):
        frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["calc"] = frame
        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent"); scroll.pack(fill="both", expand=True, padx=20, pady=10)
        ctk.CTkLabel(scroll, text="🧮 Конструктор собівартості", font=("Segoe UI", 26, "bold")).pack(pady=10)

        # Секції конструктора
        sec_tara = self.create_calc_section(scroll, "🏺 ТАРА ТА ОСНОВА")
        self.c_tara = self.create_calc_input(sec_tara, "Оберіть тару (із закупленого):", is_combo=True, cat="Тара")
        self.e_tara_price = self.create_calc_input(sec_tara, "Ціна за 1 тару (грн):")
        self.e_tara_ml = self.create_calc_input(sec_tara, "Об'єм тари (мл):")
        self.c_lid = self.create_calc_input(sec_tara, "Оберіть кришку:", is_combo=True, cat="Кришка")
        self.e_lid_price = self.create_calc_input(sec_tara, "Ціна кришки (грн):", "0")
        self.e_batch = self.create_calc_input(sec_tara, "Свічок у партії (шт):", "10")

        sec_wax = self.create_calc_section(scroll, "🕯️ ВІСК")
        self.c_wax_item = self.create_calc_input(sec_wax, "Оберіть віск:", is_combo=True, cat="Віск")
        self.e_wax_kg_price = self.create_calc_input(sec_wax, "Ціна за 1 кг воску (грн):")
        
        sec_oil = self.create_calc_section(scroll, "💧 АРОМАОЛІЇ")
        self.e_oil_perc = self.create_calc_input(sec_oil, "% вводу аромки (напр. 10):", "10")
        self.c_oil_item = self.create_calc_input(sec_oil, "Оберіть аромку:", is_combo=True, cat="Аромка")
        self.e_oil_bottle_price = self.create_calc_input(sec_oil, "Ціна флакону (грн):")
        self.c_oil_size = self.create_calc_input(sec_oil, "Вага флакону (г):", is_combo=True, values=["10", "30", "50", "100"])

        sec_wick = self.create_calc_section(scroll, "🧵 ГНІТ ТА ДЕТАЛІ")
        self.c_wick_item = self.create_calc_input(sec_wick, "Оберіть гніт:", is_combo=True, cat="Гніт")
        self.e_wick_price = self.create_calc_input(sec_wick, "Ціна за 1 шт (грн):")
        self.e_wick_count = self.create_calc_input(sec_wick, "К-сть гнотів на 1 свічку:", "1")
        self.e_decor_price = self.create_calc_input(sec_wick, "Декор на 1 свічку (грн):", "0")

        sec_pack = self.create_calc_section(scroll, "🎁 ПАКУВАННЯ")
        self.c_pack_item = self.create_calc_input(sec_pack, "Оберіть пакування:", is_combo=True, cat="Упаковка")
        self.e_pack_price = self.create_calc_input(sec_pack, "Ціна упаковки (грн/шт):", "0")

        ctk.CTkButton(scroll, text="📊 РОЗРАХУВАТИ ПРИБУТОК", height=60, font=("bold", 20), fg_color="#10B981", command=self.perform_full_calculation).pack(pady=30, fill="x")
        self.res_box = ctk.CTkFrame(scroll, fg_color="#F1F5F9", corner_radius=15, border_width=2, border_color="#3B8ED0")
        self.res_box.pack(fill="x", pady=20); self.lbl_res = ctk.CTkLabel(self.res_box, text="Результати з'являться тут...", font=("Segoe UI", 16)); self.lbl_res.pack(pady=20)

    def create_calc_section(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=10, border_width=1, border_color="#E2E8F0")
        f.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(f, text=title, font=("bold", 14), text_color="#3B8ED0").pack(pady=5, padx=15, anchor="w")
        return f

    def create_calc_input(self, parent, label, default="", is_combo=False, values=None, cat=None):
        row = ctk.CTkFrame(parent, fg_color="transparent"); row.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(row, text=label, width=300, anchor="w").pack(side="left")
        if is_combo:
            w = ctk.CTkComboBox(row, values=(values if values else []), width=250); w.set("") 
            if cat: w.configure(command=lambda choice, c=cat: self.auto_fill_calc(choice, c))
        else:
            w = ctk.CTkEntry(row, width=250); w.insert(0, default)
        w.pack(side="right")
        return w

    def auto_fill_calc(self, choice, cat):
        price, ml = self.db.get_last_price_and_ml(choice)
        if cat == "Тара":
            self.e_tara_price.delete(0, 'end'); self.e_tara_price.insert(0, f"{price:.2f}")
            self.e_tara_ml.delete(0, 'end'); self.e_tara_ml.insert(0, str(int(ml)))
        elif cat == "Віск":
            self.e_wax_kg_price.delete(0, 'end'); self.e_wax_kg_price.insert(0, f"{price*1000:.2f}")
        elif cat == "Аромка":
            self.e_oil_bottle_price.delete(0, 'end'); self.e_oil_bottle_price.insert(0, f"{price:.2f}")
        elif cat == "Кришка":
            self.e_lid_price.delete(0, 'end'); self.e_lid_price.insert(0, f"{price:.2f}")
        elif cat == "Гніт":
            self.e_wick_price.delete(0, 'end'); self.e_wick_price.insert(0, f"{price:.2f}")
        elif cat == "Упаковка":
            self.e_pack_price.delete(0, 'end'); self.e_pack_price.insert(0, f"{price:.2f}")

    def perform_full_calculation(self):
        try:
            ml = float(self.e_tara_ml.get()); batch = float(self.e_batch.get()); oil_perc = float(self.e_oil_perc.get()) / 100
            total_g = ml * 0.9; oil_g = total_g * oil_perc; wax_g = total_g - oil_g
            c_wax = (float(self.e_wax_kg_price.get()) / 1000) * wax_g
            c_oil = (float(self.e_oil_bottle_price.get()) / float(self.c_oil_size.get())) * oil_g
            unit_cost = c_wax + c_oil + float(self.e_tara_price.get()) + float(self.e_lid_price.get()) + (float(self.e_wick_price.get()) * float(self.e_wick_count.get())) + float(self.e_decor_price.get()) + float(self.e_pack_price.get())
            self.lbl_res.configure(text=f"Собівартість 1 свічки: {unit_cost:.2f} грн\nВитрати на партію: {unit_cost * batch:.2f} грн", font=("bold", 18))
        except: messagebox.showerror("Помилка", "Перевірте правильність цифр")

    # --- СКЛАД ТА СПИСАННЯ ---
    def setup_stock_frame(self):
        frame = ctk.CTkFrame(self.container, fg_color="transparent"); self.frames["stock"] = frame
        top = ctk.CTkFrame(frame, fg_color="transparent"); top.pack(fill="x", padx=30, pady=15)
        self.e_search = ctk.CTkEntry(top, placeholder_text="🔍 Пошук по складу...", height=45, width=600); self.e_search.pack(side="left")
        ctk.CTkButton(top, text="🗑️ Видалити", fg_color="#FEE2E2", text_color="#EF4444", width=100, command=self.delete_selected).pack(side="right")
        self.tree = ttk.Treeview(frame, columns=("ID", "Cat", "Item", "Stock", "UnitP"), show='headings')
        for k, v in [("ID", "ID"), ("Cat", "Категорія"), ("Item", "Товар"), ("Stock", "Залишок"), ("UnitP", "Ціна/Од")]:
            self.tree.heading(k, text=v); self.tree.column(k, width=120, anchor="center")
        self.tree.pack(expand=True, fill="both", padx=30, pady=10)

    def setup_usage_frame(self):
        frame = ctk.CTkFrame(self.container, fg_color="transparent"); self.frames["usage"] = frame
        main_box = ctk.CTkFrame(frame, fg_color="transparent"); main_box.pack(fill="both", expand=True, padx=30)
        left = ctk.CTkFrame(main_box, fg_color="#FFF1F2", width=350); left.pack(side="left", fill="y", padx=10, pady=20)
        ctk.CTkLabel(left, text="Списання матеріалів", font=("bold", 16)).pack(pady=10)
        self.usage_cb = ctk.CTkComboBox(left, width=300); self.usage_cb.set(""); self.usage_cb.pack(pady=10)
        self.usage_qty = ctk.CTkEntry(left, width=300, placeholder_text="Кількість списання"); self.usage_qty.pack(pady=10)
        self.usage_reason = ctk.CTkComboBox(left, values=["На замовлення", "Брак", "Тести"], width=300); self.usage_reason.set("На замовлення"); self.usage_reason.pack(pady=10)
        ctk.CTkButton(left, text="ПІДТВЕРДИТИ СПИСАННЯ", fg_color="#E11D48", command=self.confirm_usage).pack(pady=20)
        self.usage_tree = ttk.Treeview(main_box, columns=("D", "I", "Q", "R"), show='headings')
        for k, v in [("D", "Дата"), ("I", "Товар"), ("Q", "К-сть"), ("R", "Причина")]:
            self.usage_tree.heading(k, text=v); self.usage_tree.column(k, width=150)
        self.usage_tree.pack(side="right", expand=True, fill="both", pady=20)

    def update_stock_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in self.db.get_filtered_items(self.e_search.get()):
            self.tree.insert("", "end", values=(r['id'], r['category'], f"{r['item_name']} ({r['brand']})", f"{r['quantity']} {r['unit']}", f"{r['unit_price']:.2f}"))

    def confirm_usage(self):
        try:
            item_id = int(self.usage_cb.get().split(" | ")[0])
            if self.db.log_usage(item_id, float(self.usage_qty.get()), self.usage_reason.get()):
                messagebox.showinfo("LumaStock", "Успішно списано!"); self.show_frame("usage")
        except: messagebox.showerror("Помилка", "Оберіть товар")

    def delete_selected(self):
        sel = self.tree.selection()
        if sel: self.db.delete_item(self.tree.item(sel[0])['values'][0]); self.update_stock_table()

    def show_frame(self, page_name):
        if page_name == "calc":
            self.c_tara.configure(values=self.db.get_items_by_category("Тара"))
            self.c_wax_item.configure(values=self.db.get_items_by_category("Віск"))
            self.c_oil_item.configure(values=self.db.get_items_by_category("Аромка"))
            self.c_lid.configure(values=self.db.get_items_by_category("Кришка"))
            self.c_wick_item.configure(values=self.db.get_items_by_category("Гніт"))
            self.c_pack_item.configure(values=self.db.get_items_by_category("Упаковка"))
        if page_name == "stock": self.update_stock_table()
        if page_name == "usage":
            items = self.db.get_all_items_for_list()
            self.usage_cb.configure(values=[f"{i[0]} | {i[1]} ({i[2]})" for i in items])
        for f in self.frames.values(): f.pack_forget()
        self.frames[page_name].pack(fill="both", expand=True)

if __name__ == "__main__":
    app = LumaStockApp()
    app.mainloop()