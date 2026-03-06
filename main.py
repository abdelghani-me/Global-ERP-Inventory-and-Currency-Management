import customtkinter as ctk
from tkinter import messagebox, ttk
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ProfessionalTradeSystem(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Global ERP Inventory & Currency Pro v4.0")
        self.geometry("1200x850")
        
        self.init_db()

        self.tabview = ctk.CTkTabview(self, width=1150, height=780)
        self.tabview.pack(padx=20, pady=20)
        
        self.tab_calc = self.tabview.add("Global Calculator")
        self.tab_inventory = self.tabview.add("Inventory & Sales")
        self.tab_reports = self.tabview.add("Analytics")

        self.setup_calc_tab()
        self.setup_inventory_tab()
        self.setup_reports_tab()

    def init_db(self):
        conn = sqlite3.connect("trade_data.db")
        cursor = conn.cursor()
        # Full structure with min_stock and original currency info
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory 
                          (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER, 
                          cost_unit REAL, total_cost REAL, min_stock INTEGER, date TEXT)''')
        conn.commit()
        conn.close()

    # --- 1. CALCULATOR WITH CURRENCY LOGIC ---
    def setup_calc_tab(self):
        frame = ctk.CTkFrame(self.tab_calc)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Shipment & Currency Analysis", font=("Roboto", 24, "bold")).grid(row=0, column=0, columnspan=2, pady=15)

        # Inputs
        fields = [
            ("Product Name", "PName"), 
            ("Source Cost (e.g. Yuan)", "SCost"), 
            ("Exchange Rate (1 Source = ? USD)", "ExRate"),
            ("Quantity", "Qty"), 
            ("Weight/Unit (kg)", "Weight"), 
            ("Ship Fee/kg ($)", "Ship"), 
            ("Customs (%)", "Cust"), 
            ("Profit Margin (%)", "Marg"), 
            ("Min Stock Alert", "MinS")
        ]
        
        self.entries = {}
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(frame, text=label).grid(row=i+1, column=0, padx=20, pady=5, sticky="w")
            entry = ctk.CTkEntry(frame, width=250)
            if key == "ExRate": entry.insert(0, "0.14") # Example Yuan to USD
            entry.grid(row=i+1, column=1, padx=20, pady=5)
            self.entries[key] = entry

        self.save_var = ctk.StringVar(value="on")
        ctk.CTkCheckBox(frame, text="Save to Inventory", variable=self.save_var).grid(row=10, column=0, columnspan=2, pady=10)

        ctk.CTkButton(frame, text="Calculate & Process", command=self.calculate_all, height=40, fg_color="#27ae60").grid(row=11, column=0, columnspan=2, pady=10)
        
        self.res_display = ctk.CTkLabel(frame, text="Results Summary", font=("Consolas", 15), justify="left", fg_color="#2c3e50", corner_radius=10, padx=20, pady=20)
        self.res_display.grid(row=1, column=2, rowspan=9, padx=40, sticky="nsew")

    def calculate_all(self):
        try:
            e = self.entries
            # Currency conversion logic
            usd_unit_cost = float(e["SCost"].get()) * float(e["ExRate"].get())
            qty = int(e["Qty"].get())
            
            shipping = (qty * float(e["Weight"].get())) * float(e["Ship"].get())
            customs = (usd_unit_cost * qty) * (float(e["Cust"].get())/100)
            total_landed = (usd_unit_cost * qty) + shipping + customs
            cpu_usd = total_landed / qty
            sell_price = cpu_usd / (1 - (float(e["Marg"].get())/100))

            res = (f"--- USD CALCULATIONS ---\n\n"
                   f"Landed Cost/Unit: ${cpu_usd:,.2f}\n"
                   f"Recommended Price: ${sell_price:,.2f}\n"
                   f"Total Investment: ${total_landed:,.2f}\n"
                   f"Break-even: ${cpu_usd:,.2f}")
            
            self.res_display.configure(text=res)

            if self.save_var.get() == "on":
                self.save_data(e["PName"].get(), qty, cpu_usd, total_landed, int(e["MinS"].get()))
                messagebox.showinfo("Inventory", "Data stored successfully!")

        except ValueError:
            messagebox.showerror("Error", "Please fill all fields with numbers.")

    # --- 2. INVENTORY & SALES SYSTEM ---
    def setup_inventory_tab(self):
        control_frame = ctk.CTkFrame(self.tab_inventory)
        control_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(control_frame, text="Stock Operations:").pack(side="left", padx=10)
        ctk.CTkButton(control_frame, text="Register Sale (-1)", fg_color="#e67e22", command=self.make_sale).pack(side="left", padx=5)
        ctk.CTkButton(control_frame, text="Delete Product", fg_color="#c0392b", command=self.delete_item).pack(side="left", padx=5)
        ctk.CTkButton(control_frame, text="Refresh Table", command=self.refresh_table).pack(side="right", padx=10)

        # Table with correct column IDs
        cols = ("id", "name", "qty", "cost", "total", "min", "status")
        self.tree = ttk.Treeview(self.tab_inventory, columns=cols, show='headings')
        
        titles = {"id": "ID", "name": "Product", "qty": "Qty", "cost": "Cost/U ($)", "total": "Total Val", "min": "Alert", "status": "Status"}
        for c in cols:
            self.tree.heading(c, text=titles[c])
            self.tree.column(c, width=120, anchor="center")
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh_table()

    def save_data(self, n, q, c, t, ms):
        conn = sqlite3.connect("trade_data.db")
        conn.execute("INSERT INTO inventory (name, qty, cost_unit, total_cost, min_stock, date) VALUES (?,?,?,?,?,?)",
                     (n, q, c, t, ms, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        self.refresh_table()

    def make_sale(self):
        selected = self.tree.selection()
        if not selected: return
        item_id = self.tree.item(selected[0])['values'][0]
        conn = sqlite3.connect("trade_data.db")
        conn.execute("UPDATE inventory SET qty = qty - 1 WHERE id = ? AND qty > 0", (item_id,))
        conn.commit()
        conn.close()
        self.refresh_table()

    def delete_item(self):
        selected = self.tree.selection()
        if not selected: return
        item_id = self.tree.item(selected[0])['values'][0]
        if messagebox.askyesno("Confirm", "Delete this item?"):
            conn = sqlite3.connect("trade_data.db")
            conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            self.refresh_table()

    def refresh_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = sqlite3.connect("trade_data.db")
        cursor = conn.execute("SELECT id, name, qty, cost_unit, total_cost, min_stock FROM inventory")
        for row in cursor:
            # Smart Alert Logic
            status = "HEALTHY" if row[2] > row[5] else "LOW STOCK"
            tag = "ok" if status == "HEALTHY" else "alert"
            self.tree.insert("", "end", values=(*row, status), tags=(tag,))
        conn.close()
        self.tree.tag_configure("alert", foreground="#e74c3c")

    # --- 3. ANALYTICS ---
    def setup_reports_tab(self):
        ctk.CTkButton(self.tab_reports, text="Generate Stock Chart", command=self.update_chart).pack(pady=10)
        self.chart_frame = ctk.CTkFrame(self.tab_reports)
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def update_chart(self):
        conn = sqlite3.connect("trade_data.db")
        data = conn.execute("SELECT name, qty FROM inventory").fetchall()
        conn.close()
        if not data: return
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar([d[0] for d in data], [d[1] for d in data], color='#3498db')
        ax.set_title("Current Stock Levels", color="white")
        
        for w in self.chart_frame.winfo_children(): w.destroy()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

if __name__ == "__main__":
    app = ProfessionalTradeSystem()
    app.mainloop()