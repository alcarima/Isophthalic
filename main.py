import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from database import initialize_database, add_expense, get_all_expenses, delete_expense
from analysis import total_by_category, total_expenses, total_by_supplier


CATEGORIES = [
    "Alimentari",
    "Ristoranti / Aperitivi",
    "Casa / Pulizia",
    "Cura personale",
    "Farmacia",
    "Animali",
    "Luce",
    "Gas",
    "Acqua",
    "Telefono / Internet",
    "Assicurazioni",
    "Auto / Trasporti",
    "Abbonamenti",
    "Manutenzione casa",
    "Scuola / Famiglia",
    "Altro",
]

PAYMENT_METHODS = [
    "",
    "Contanti",
    "Carta",
    "Bancomat",
    "Bonifico",
    "Addebito automatico",
]


class HomeCostApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ottimizzazione Spese Casa")
        self.root.geometry("1150x720")

        initialize_database()

        self.create_layout()
        self.refresh_table()
        self.refresh_summary()

    def create_layout(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        input_frame = tk.LabelFrame(main_frame, text="Inserisci nuova spesa", padx=10, pady=10)
        input_frame.pack(side="left", fill="y", padx=(0, 10))

        table_frame = tk.Frame(main_frame)
        table_frame.pack(side="right", fill="both", expand=True)

        # Input fields
        tk.Label(input_frame, text="Data").grid(row=0, column=0, sticky="w")
        self.date_var = tk.StringVar(value=date.today().isoformat())
        tk.Entry(input_frame, textvariable=self.date_var, width=25).grid(row=1, column=0, pady=(0, 8))

        tk.Label(input_frame, text="Categoria").grid(row=2, column=0, sticky="w")
        self.category_var = tk.StringVar(value="Alimentari")
        ttk.Combobox(
            input_frame,
            textvariable=self.category_var,
            values=CATEGORIES,
            width=23,
            state="readonly"
        ).grid(row=3, column=0, pady=(0, 8))

        tk.Label(input_frame, text="Fornitore / Negozio").grid(row=4, column=0, sticky="w")
        self.supplier_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=self.supplier_var, width=25).grid(row=5, column=0, pady=(0, 8))

        tk.Label(input_frame, text="Descrizione").grid(row=6, column=0, sticky="w")
        self.description_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=self.description_var, width=25).grid(row=7, column=0, pady=(0, 8))

        tk.Label(input_frame, text="Importo (€)").grid(row=8, column=0, sticky="w")
        self.amount_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=self.amount_var, width=25).grid(row=9, column=0, pady=(0, 8))

        tk.Label(input_frame, text="Metodo pagamento").grid(row=10, column=0, sticky="w")
        self.payment_var = tk.StringVar()
        ttk.Combobox(
            input_frame,
            textvariable=self.payment_var,
            values=PAYMENT_METHODS,
            width=23,
            state="readonly"
        ).grid(row=11, column=0, pady=(0, 8))

        self.recurring_var = tk.IntVar(value=0)
        tk.Checkbutton(
            input_frame,
            text="Spesa ricorrente",
            variable=self.recurring_var
        ).grid(row=12, column=0, sticky="w", pady=(0, 8))

        tk.Label(input_frame, text="Note").grid(row=13, column=0, sticky="w")
        self.notes_text = tk.Text(input_frame, width=25, height=5)
        self.notes_text.grid(row=14, column=0, pady=(0, 8))

        tk.Button(
            input_frame,
            text="Salva spesa",
            command=self.save_expense,
            width=22
        ).grid(row=15, column=0, pady=(10, 5))

        tk.Button(
            input_frame,
            text="Cancella spesa selezionata",
            command=self.delete_selected_expense,
            width=22
        ).grid(row=16, column=0, pady=5)

        # Table
        columns = (
            "id",
            "date",
            "category",
            "supplier",
            "description",
            "amount",
            "payment",
            "recurring",
            "notes"
        )

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)

        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Data")
        self.tree.heading("category", text="Categoria")
        self.tree.heading("supplier", text="Fornitore")
        self.tree.heading("description", text="Descrizione")
        self.tree.heading("amount", text="Importo")
        self.tree.heading("payment", text="Pagamento")
        self.tree.heading("recurring", text="Ricorrente")
        self.tree.heading("notes", text="Note")

        self.tree.column("id", width=40)
        self.tree.column("date", width=90)
        self.tree.column("category", width=140)
        self.tree.column("supplier", width=140)
        self.tree.column("description", width=180)
        self.tree.column("amount", width=80, anchor="e")
        self.tree.column("payment", width=120)
        self.tree.column("recurring", width=80)
        self.tree.column("notes", width=180)

        self.tree.pack(fill="both", expand=True)

        # Summary
        self.summary_text = tk.Text(table_frame, height=12)
        self.summary_text.pack(fill="x", pady=(10, 0))

    def save_expense(self):
        expense_date = self.date_var.get().strip()
        category = self.category_var.get().strip()
        supplier = self.supplier_var.get().strip()
        description = self.description_var.get().strip()
        amount_text = self.amount_var.get().strip().replace(",", ".")
        payment_method = self.payment_var.get().strip()
        recurring = self.recurring_var.get()
        notes = self.notes_text.get("1.0", "end").strip()

        if not expense_date:
            messagebox.showerror("Errore", "Inserire la data.")
            return

        if not category:
            messagebox.showerror("Errore", "Inserire la categoria.")
            return

        if not amount_text:
            messagebox.showerror("Errore", "Inserire l'importo.")
            return

        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Errore", "Importo non valido.")
            return

        add_expense(
            expense_date=expense_date,
            category=category,
            supplier=supplier,
            description=description,
            amount=amount,
            payment_method=payment_method,
            recurring=recurring,
            notes=notes,
            document_path=""
        )

        self.clear_form()
        self.refresh_table()
        self.refresh_summary()

    def clear_form(self):
        self.date_var.set(date.today().isoformat())
        self.category_var.set("Alimentari")
        self.supplier_var.set("")
        self.description_var.set("")
        self.amount_var.set("")
        self.payment_var.set("")
        self.recurring_var.set(0)
        self.notes_text.delete("1.0", "end")

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = get_all_expenses()

        for row in rows:
            recurring_text = "Sì" if row[7] else "No"
            amount_text = f"{row[5]:.2f}"

            self.tree.insert(
                "",
                "end",
                values=(
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    amount_text,
                    row[6],
                    recurring_text,
                    row[8],
                )
            )

    def refresh_summary(self):
        self.summary_text.delete("1.0", "end")

        total = total_expenses()
        category_totals = total_by_category()
        supplier_totals = total_by_supplier()

        self.summary_text.insert("end", f"Totale registrato: {total:.2f} €\n\n")

        self.summary_text.insert("end", "Totale per categoria:\n")
        for category, amount in category_totals.items():
            self.summary_text.insert("end", f"- {category}: {amount:.2f} €\n")

        self.summary_text.insert("end", "\nTotale per fornitore:\n")
        for supplier, amount in supplier_totals.items():
            self.summary_text.insert("end", f"- {supplier}: {amount:.2f} €\n")

    def delete_selected_expense(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning("Attenzione", "Selezionare una spesa da cancellare.")
            return

        item = self.tree.item(selected[0])
        expense_id = item["values"][0]

        confirm = messagebox.askyesno(
            "Conferma cancellazione",
            "Vuoi cancellare la spesa selezionata?"
        )

        if confirm:
            delete_expense(expense_id)
            self.refresh_table()
            self.refresh_summary()


if __name__ == "__main__":
    root = tk.Tk()
    app = HomeCostApp(root)
    root.mainloop()
