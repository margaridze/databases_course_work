import customtkinter as ctk
import psycopg2
from tkinter import messagebox, ttk, Listbox
from datetime import datetime, date

# КОНФИГУРАЦИЯ БД
DB_CONFIG = {
    "dbname": "Dogs",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
    "client_encoding": "UTF8"
}

def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        messagebox.showerror("Ошибка БД", str(e))
        return None

def gender_to_db(gender_ru):
    return 'M' if gender_ru == 'М' else 'F'

def gender_to_ru(gender_db):
    return 'М' if gender_db == 'M' else 'Ж'

def format_date(d):
    if isinstance(d, (datetime, date)):
        return d.strftime("%Y-%m-%d")
    return str(d) if d else ""

def medal_to_ru(medal):

    if medal is None:
        return "нет"
    m = str(medal).lower()
    if m == "gold":
        return "золотая"
    elif m == "silver":
        return "серебряная"
    elif m == "bronze":
        return "бронзовая"
    return m

# ГЛАВНОЕ ПРИЛОЖЕНИЕ
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Кинологический клуб - Учёт собак")
        self.geometry("1300x800")

        # Левая панель с кнопками
        left_frame = ctk.CTkFrame(self, width=250)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)
        left_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text="Управление", font=("Arial", 16, "bold")).pack(pady=10)

        # Кнопки навигации
        nav_buttons = [
            ("Собаки", self.show_dogs_view),
            ("Породы", lambda: self.show_table_view("breeds", "Породы")),
            ("Владельцы", lambda: self.show_table_view("owners", "Владельцы")),
            ("Выставки", lambda: self.show_table_view("exhibitions", "Выставки")),
            ("Болезни", lambda: self.show_table_view("diseases", "Болезни")),
            ("История болезней", lambda: self.show_table_view("medical_history", "История болезней")),
            ("Родители", self.show_parentage_view),
            ("Владелец + собаки (1:М)", self.show_owner_dogs_form),
            ("Отчёт: вязка", lambda: self.show_report("Вязка")),
            ("Отчёт: элитная вязка", lambda: self.show_report("Элитная вязка")),
            ("Отчёт: служебные", lambda: self.show_report("Служебные")),
        ]

        for text, cmd in nav_buttons:
            btn = ctk.CTkButton(left_frame, text=text, command=cmd)
            btn.pack(pady=5, padx=10, fill="x")

        # Центральная область
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.current_view = None
        self.show_dogs_view()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # ПРОСМОТР ТАБЛИЦ С РЕДАКТИРОВАНИЕМ
    def show_table_view(self, table_name, title):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text=title, font=("Arial", 18, "bold")).pack(pady=10)

        # Таблица Treeview
        frame = ctk.CTkFrame(self.content_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        columns, data = self.fetch_table_data(table_name)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")
        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        # Загрузка данных
        def reload():
            nonlocal data
            _, data = self.fetch_table_data(table_name)
            for item in tree.get_children():
                tree.delete(item)
            for row in data:
                tree.insert("", "end", values=row)

        reload()

        # Обработка двойного клика
        def on_double_click(event):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            self.edit_record_dialog(table_name, title, values, reload)

        tree.bind("<Double-1>", on_double_click)

        # Кнопки управления
        btn_frame = ctk.CTkFrame(self.content_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Добавить запись", command=lambda: self.add_record_dialog(table_name, title, reload)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Обновить", command=reload).pack(side="left", padx=5)

    def fetch_table_data(self, table_name):
        conn = get_connection()
        if not conn:
            return [], []
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        # Преобразование для выставок
        if table_name == "exhibitions":
            new_rows = []
            try:
                date_idx = col_names.index("exhibition_date")
                medal_idx = col_names.index("medal")
            except ValueError:
                date_idx = medal_idx = -1
            for row in rows:
                row_list = list(row)
                if date_idx != -1 and isinstance(row_list[date_idx], (datetime, date)):
                    row_list[date_idx] = format_date(row_list[date_idx])
                if medal_idx != -1:
                    medal_val = row_list[medal_idx]
                    if isinstance(medal_val, str):
                        row_list[medal_idx] = medal_to_ru(medal_val)
                    else:
                        row_list[medal_idx] = "нет"
                new_rows.append(tuple(row_list))
            rows = new_rows
        elif table_name == "medical_history":
            new_rows = []
            try:
                ill_idx = col_names.index("illness_date")
                rec_idx = col_names.index("recovery_date")
            except ValueError:
                ill_idx = rec_idx = -1
            for row in rows:
                row_list = list(row)
                if ill_idx != -1 and isinstance(row_list[ill_idx], (datetime, date)):
                    row_list[ill_idx] = format_date(row_list[ill_idx])
                if rec_idx != -1 and isinstance(row_list[rec_idx], (datetime, date)):
                    row_list[rec_idx] = format_date(row_list[rec_idx])
                new_rows.append(tuple(row_list))
            rows = new_rows
        return col_names, rows

    def edit_record_dialog(self, table_name, title, values, reload_callback):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Редактировать запись в {title}")
        dialog.geometry("400x300")

        # Получаем список колонок и текущие значения
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name} LIMIT 0")
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        # Создаём поля для редактирования
        entries = []
        for i, col in enumerate(columns):
            ctk.CTkLabel(dialog, text=col).pack(pady=2)
            entry = ctk.CTkEntry(dialog)
            entry.insert(0, str(values[i]) if values[i] is not None else "")
            entry.pack(pady=2)
            entries.append(entry)

        def save():
            new_values = [e.get() for e in entries]
            set_clause = ", ".join([f"{col}=%s" for col in columns[1:]])
            values_to_update = new_values[1:] + [new_values[0]]
            try:
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute(f"UPDATE {table_name} SET {set_clause} WHERE {columns[0]}=%s", values_to_update)
                    conn.commit()
                    messagebox.showinfo("Успех", "Запись обновлена")
                    dialog.destroy()
                    reload_callback()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                if conn:
                    cur.close()
                    conn.close()

        def delete_record():
            if messagebox.askyesno("Удаление", f"Удалить запись {values[0]}?"):
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(f"DELETE FROM {table_name} WHERE {columns[0]}=%s", (values[0],))
                        conn.commit()
                        messagebox.showinfo("Успех", "Запись удалена")
                        dialog.destroy()
                        reload_callback()
                    except Exception as e:
                        messagebox.showerror("Ошибка", str(e))
                    finally:
                        cur.close()
                        conn.close()

        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Сохранить", command=save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Удалить", command=delete_record).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Отмена", command=dialog.destroy).pack(side="left", padx=5)

    def add_record_dialog(self, table_name, title, reload_callback):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Добавить запись в {title}")
        dialog.geometry("400x500")
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name} LIMIT 0")
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        entries = {}
        # Пропускаем первый столбец (первичный ключ), он автоинкремент
        for col in columns[1:]:
            ctk.CTkLabel(dialog, text=col).pack(pady=2)
            entry = ctk.CTkEntry(dialog)
            entry.pack(pady=2)
            entries[col] = entry

        def save():
            col_names = list(entries.keys())
            values = [entries[col].get() for col in col_names]
            placeholders = ",".join(["%s"]*len(values))
            query = f"INSERT INTO {table_name} ({','.join(col_names)}) VALUES ({placeholders})"
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                try:
                    cur.execute(query, values)
                    conn.commit()
                    messagebox.showinfo("Успех", "Запись добавлена")
                    dialog.destroy()
                    reload_callback()
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))
                finally:
                    cur.close()
                    conn.close()
        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=20)

    #  ОТДЕЛЬНО ДЛЯ РОДИТЕЛЕЙ (ПОКАЗ ИМЁН)
    def show_parentage_view(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Родители", font=("Arial", 18, "bold")).pack(pady=10)

        frame = ctk.CTkFrame(self.content_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        columns = ("Собака", "Отец", "Мать")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="center")
        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        def reload():
            conn = get_connection()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("""
                SELECT d1.dog_name, COALESCE(d2.dog_name, 'неизвестен'), COALESCE(d3.dog_name, 'неизвестна')
                FROM parentage p
                JOIN dogs d1 ON p.dog_id = d1.dog_id
                LEFT JOIN dogs d2 ON p.father_id = d2.dog_id
                LEFT JOIN dogs d3 ON p.mother_id = d3.dog_id
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            for item in tree.get_children():
                tree.delete(item)
            for row in rows:
                tree.insert("", "end", values=row)

        reload()

        def on_double_click(event):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            dog_name = values[0]
            conn = get_connection()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("SELECT dog_id FROM dogs WHERE dog_name = %s", (dog_name,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                dog_id = row[0]
                self.edit_parentage_record(dog_id, reload)
        tree.bind("<Double-1>", on_double_click)

        btn_frame = ctk.CTkFrame(self.content_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Добавить родителей", command=lambda: self.add_parentage_dialog(reload)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Обновить", command=reload).pack(side="left", padx=5)

    def edit_parentage_record(self, dog_id, reload_callback):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Редактировать родителей собаки ID {dog_id}")
        dialog.geometry("400x300")

        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT father_id, mother_id FROM parentage WHERE dog_id = %s", (dog_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT dog_id, dog_name FROM dogs ORDER BY dog_name")
        all_dogs = cur.fetchall()
        cur.close()
        conn.close()

        ctk.CTkLabel(dialog, text="Отец:").pack(pady=5)
        father_var = ctk.StringVar()
        father_combo = ctk.CTkComboBox(dialog, values=[f"{d[0]} - {d[1]}" for d in all_dogs] + ["Не указан"], variable=father_var, state="readonly")
        father_combo.pack(pady=5)
        if row and row[0]:
            father_name = next((d[1] for d in all_dogs if d[0] == row[0]), "")
            father_var.set(f"{row[0]} - {father_name}")
        else:
            father_var.set("Не указан")

        ctk.CTkLabel(dialog, text="Мать:").pack(pady=5)
        mother_var = ctk.StringVar()
        mother_combo = ctk.CTkComboBox(dialog, values=[f"{d[0]} - {d[1]}" for d in all_dogs] + ["Не указан"], variable=mother_var, state="readonly")
        mother_combo.pack(pady=5)
        if row and row[1]:
            mother_name = next((d[1] for d in all_dogs if d[0] == row[1]), "")
            mother_var.set(f"{row[1]} - {mother_name}")
        else:
            mother_var.set("Не указан")

        def save():
            father = None if father_var.get() == "Не указан" else int(father_var.get().split(" - ")[0])
            mother = None if mother_var.get() == "Не указан" else int(mother_var.get().split(" - ")[0])
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                try:
                    cur.execute("DELETE FROM parentage WHERE dog_id = %s", (dog_id,))
                    if father or mother:
                        cur.execute("INSERT INTO parentage (dog_id, father_id, mother_id) VALUES (%s, %s, %s)",
                                    (dog_id, father, mother))
                    conn.commit()
                    messagebox.showinfo("Успех", "Родители обновлены")
                    dialog.destroy()
                    reload_callback()
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))
                finally:
                    cur.close()
                    conn.close()
        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=20)

    def add_parentage_dialog(self, reload_callback):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить запись о родителях")
        dialog.geometry("400x350")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT dog_id, dog_name FROM dogs ORDER BY dog_name")
        all_dogs = cur.fetchall()
        cur.close()
        conn.close()

        ctk.CTkLabel(dialog, text="Собака:").pack(pady=5)
        dog_var = ctk.StringVar()
        dog_combo = ctk.CTkComboBox(dialog, values=[f"{d[0]} - {d[1]}" for d in all_dogs], variable=dog_var, state="readonly")
        dog_combo.pack(pady=5)

        ctk.CTkLabel(dialog, text="Отец (необязательно):").pack(pady=5)
        father_var = ctk.StringVar()
        father_combo = ctk.CTkComboBox(dialog, values=["Не указан"] + [f"{d[0]} - {d[1]}" for d in all_dogs], variable=father_var, state="readonly")
        father_combo.pack(pady=5)

        ctk.CTkLabel(dialog, text="Мать (необязательно):").pack(pady=5)
        mother_var = ctk.StringVar()
        mother_combo = ctk.CTkComboBox(dialog, values=["Не указан"] + [f"{d[0]} - {d[1]}" for d in all_dogs], variable=mother_var, state="readonly")
        mother_combo.pack(pady=5)

        def save():
            dog_id = int(dog_var.get().split(" - ")[0])
            father = None if father_var.get() == "Не указан" else int(father_var.get().split(" - ")[0])
            mother = None if mother_var.get() == "Не указан" else int(mother_var.get().split(" - ")[0])
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO parentage (dog_id, father_id, mother_id) VALUES (%s, %s, %s)", (dog_id, father, mother))
                    conn.commit()
                    messagebox.showinfo("Успех", "Запись добавлена")
                    dialog.destroy()
                    reload_callback()
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))
                finally:
                    cur.close()
                    conn.close()
        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=20)

    # ОСНОВНАЯ ТАБЛИЦА СОБАК
    def show_dogs_view(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Управление собаками", font=("Arial", 18, "bold")).pack(pady=10)

        # Панель фильтров
        filter_frame = ctk.CTkFrame(self.content_frame)
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Поиск по кличке
        ctk.CTkLabel(filter_frame, text="Поиск по кличке:").grid(row=0, column=0, padx=5, pady=5)
        self.search_entry = ctk.CTkEntry(filter_frame, width=200)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(filter_frame, text="Найти", command=self.search_dogs).grid(row=0, column=2, padx=5)

        # Фильтр по любому полю
        ctk.CTkLabel(filter_frame, text="Фильтр по полю:").grid(row=1, column=0, padx=5, pady=5)
        self.filter_field_var = ctk.StringVar()
        filter_fields = ["(нет)", "dog_name", "breed_name", "owner_name", "gender", "mental_test_score", "is_alive"]
        self.filter_field_combo = ctk.CTkComboBox(filter_frame, values=filter_fields, variable=self.filter_field_var, state="readonly", width=150)
        self.filter_field_combo.grid(row=1, column=1, padx=5, pady=5)
        self.filter_value_entry = ctk.CTkEntry(filter_frame, width=150)
        self.filter_value_entry.grid(row=1, column=2, padx=5, pady=5)
        ctk.CTkButton(filter_frame, text="Применить фильтр", command=self.filter_dogs).grid(row=1, column=3, padx=5)
        ctk.CTkButton(filter_frame, text="Сбросить фильтр", command=self.reset_filter).grid(row=1, column=4, padx=5)

        # Таблица собак
        dogs_frame = ctk.CTkFrame(self.content_frame)
        dogs_frame.pack(fill="both", expand=True, padx=10, pady=10)
        columns = ("ID", "Кличка", "Порода", "Владелец", "Дата рождения", "Пол", "Психика", "Жива")
        self.dogs_tree = ttk.Treeview(dogs_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.dogs_tree.heading(col, text=col)
            self.dogs_tree.column(col, width=100, anchor="center")
        self.dogs_tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(dogs_frame, orient="vertical", command=self.dogs_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.dogs_tree.configure(yscrollcommand=scrollbar.set)
        self.dogs_tree.bind("<Double-1>", self.on_dog_double_click)

        # Кнопки управления собаками
        btn_frame = ctk.CTkFrame(self.content_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Добавить собаку", command=self.add_dog_dialog).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Обновить список", command=self.load_dogs_table).pack(side="left", padx=5)

        # Панель сортировки
        sort_frame = ctk.CTkFrame(self.content_frame)
        sort_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(sort_frame, text="Сортировка по полю:").pack(side="left", padx=5)
        sort_fields = ["dog_id", "dog_name", "breed_name", "owner_name", "birth_date", "gender", "mental_test_score",
                       "is_alive"]
        self.sort_field_var = ctk.StringVar(value="dog_id")
        self.sort_combo = ctk.CTkComboBox(sort_frame, values=sort_fields, variable=self.sort_field_var,
                                          state="readonly", width=150)
        self.sort_combo.pack(side="left", padx=5)
        self.sort_order_var = ctk.StringVar(value="ASC")
        ctk.CTkOptionMenu(sort_frame, values=["ASC", "DESC"], variable=self.sort_order_var).pack(side="left", padx=5)
        ctk.CTkButton(sort_frame, text="Применить сортировку", command=self.sort_dogs).pack(side="left", padx=5)

        # Сохраняем текущие фильтры и переменные сортировки
        self.current_search_text = None
        self.current_custom_filter = None
        self.current_sort_field = "dog_id"
        self.current_sort_order = "ASC"

        self.load_dogs_table()


    def load_dogs_table(self):
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        query = """
            SELECT d.dog_id, d.dog_name, b.breed_name, o.last_name || ' ' || o.first_name,
                   d.birth_date, d.gender, d.mental_test_score, d.is_alive
            FROM dogs d
            JOIN breeds b ON d.breed_id = b.breed_id
            JOIN owners o ON d.owner_id = o.owner_id
        """
        where = []
        params = []
        if self.current_search_text:
            where.append("d.dog_name ILIKE %s")
            params.append(f"%{self.current_search_text}%")
        if self.current_custom_filter:
            field, value = self.current_custom_filter
            if field == "breed_name":
                where.append("b.breed_name ILIKE %s")
                params.append(f"%{value}%")
            elif field == "owner_name":
                where.append("(o.last_name || ' ' || o.first_name) ILIKE %s")
                params.append(f"%{value}%")
            elif field == "gender":
                where.append("d.gender = %s")
                params.append(gender_to_db(value))
            elif field == "mental_test_score":
                where.append("d.mental_test_score = %s")
                params.append(int(value))
            elif field == "is_alive":
                where.append("d.is_alive = %s")
                params.append(value.lower() == "да")
            else:
                where.append(f"d.{field} ILIKE %s")
                params.append(f"%{value}%")
        if where:
            query += " WHERE " + " AND ".join(where)

        # --- БЛОК СОРТИРОВКИ (новый) ---
        sort_mapping = {
            "dog_id": "d.dog_id",
            "dog_name": "d.dog_name",
            "breed_name": "b.breed_name",
            "owner_name": "o.last_name || ' ' || o.first_name",
            "birth_date": "d.birth_date",
            "gender": "d.gender",
            "mental_test_score": "d.mental_test_score",
            "is_alive": "d.is_alive",
        }
        if hasattr(self, 'current_sort_field') and self.current_sort_field:
            sort_field_sql = sort_mapping.get(self.current_sort_field, "d.dog_id")
            sort_order_sql = self.current_sort_order if hasattr(self, 'current_sort_order') else "ASC"
            query += f" ORDER BY {sort_field_sql} {sort_order_sql}"
        else:
            query += " ORDER BY d.dog_id"
        # --- КОНЕЦ БЛОКА ---

        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        for item in self.dogs_tree.get_children():
            self.dogs_tree.delete(item)
        for row in rows:
            gender = gender_to_ru(row[5])
            alive = "Да" if row[7] else "Нет"
            birth = format_date(row[4]) if row[4] else "—"
            mental = row[6] if row[6] else "—"
            self.dogs_tree.insert("", "end", values=(row[0], row[1], row[2], row[3], birth, gender, mental, alive))

    def search_dogs(self):
        self.current_search_text = self.search_entry.get().strip()
        self.load_dogs_table()

    def filter_dogs(self):
        field = self.filter_field_var.get()
        value = self.filter_value_entry.get().strip()
        if field != "(нет)" and value:
            self.current_custom_filter = (field, value)
        else:
            self.current_custom_filter = None
        self.load_dogs_table()

    def reset_filter(self):
        self.search_entry.delete(0, "end")
        self.filter_field_var.set("(нет)")
        self.filter_value_entry.delete(0, "end")
        self.current_search_text = None
        self.current_custom_filter = None
        self.load_dogs_table()

    def sort_dogs(self):
        self.current_sort_field = self.sort_field_var.get()
        self.current_sort_order = self.sort_order_var.get()
        self.load_dogs_table()

    def on_dog_double_click(self, event):
        selected = self.dogs_tree.selection()
        if not selected:
            return
        values = self.dogs_tree.item(selected[0], "values")
        dog_id = values[0]
        self.show_dog_card(dog_id)

    def show_dog_card(self, dog_id):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text=f"Карточка собаки ID {dog_id}", font=("Arial", 18, "bold")).pack(pady=10)

        # Основная информация
        info_frame = ctk.CTkFrame(self.content_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        self.load_dog_info_to_frame(info_frame, dog_id)

        # Родители
        parents_frame = ctk.CTkFrame(self.content_frame)
        parents_frame.pack(fill="x", padx=10, pady=5)
        self.load_parents_to_frame(parents_frame, dog_id)

        # Выставки
        exhib_frame = ctk.CTkFrame(self.content_frame)
        exhib_frame.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(exhib_frame, text="Выставки", font=("Arial", 14, "bold")).pack(anchor="w")
        exhib_text = ctk.CTkTextbox(exhib_frame, height=100)
        exhib_text.pack(fill="both", expand=True, pady=5)
        self.load_exhibitions_to_text(exhib_text, dog_id)

        # Болезни
        disease_frame = ctk.CTkFrame(self.content_frame)
        disease_frame.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(disease_frame, text="История болезней", font=("Arial", 14, "bold")).pack(anchor="w")
        disease_text = ctk.CTkTextbox(disease_frame, height=100)
        disease_text.pack(fill="both", expand=True, pady=5)
        self.load_diseases_to_text(disease_text, dog_id)

        # Кнопки
        btn_frame = ctk.CTkFrame(self.content_frame)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="Добавить выставку", command=lambda: self.add_exhibition_for_dog(dog_id, exhib_text)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Добавить болезнь", command=lambda: self.add_disease_for_dog(dog_id, disease_text)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Редактировать родителей", command=lambda: self.edit_parents_for_dog(dog_id, parents_frame)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Удалить собаку", command=lambda: self.delete_dog(dog_id)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Назад к списку", command=self.show_dogs_view).pack(side="left", padx=5)

    def load_dog_info_to_frame(self, frame, dog_id):
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("""
            SELECT d.dog_name, b.breed_name, o.last_name || ' ' || o.first_name,
                   d.birth_date, d.gender, d.mental_test_score, d.is_alive
            FROM dogs d
            JOIN breeds b ON d.breed_id = b.breed_id
            JOIN owners o ON d.owner_id = o.owner_id
            WHERE d.dog_id = %s
        """, (dog_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            gender = gender_to_ru(row[4])
            info = f"Кличка: {row[0]}\nПорода: {row[1]}\nВладелец: {row[2]}\nДата рождения: {format_date(row[3]) if row[3] else 'не указана'}\nПол: {gender}\nТест психики: {row[5] if row[5] else 'нет'}\nЖива: {'Да' if row[6] else 'Нет'}"
            label = ctk.CTkLabel(frame, text=info, justify="left")
            label.pack(anchor="w", padx=10, pady=5)

    def load_parents_to_frame(self, frame, dog_id):
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("""
            SELECT father_id, mother_id FROM parentage WHERE dog_id = %s
        """, (dog_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        text = "Родители: "
        if row and (row[0] or row[1]):
            father_name = self.get_dog_name(row[0]) if row[0] else "неизвестен"
            mother_name = self.get_dog_name(row[1]) if row[1] else "неизвестна"
            text += f"отец {father_name}, мать {mother_name}"
        else:
            text += "не указаны"
        label = ctk.CTkLabel(frame, text=text)
        label.pack(anchor="w", padx=10, pady=5)

    def get_dog_name(self, dog_id):
        conn = get_connection()
        if not conn:
            return "?"
        cur = conn.cursor()
        cur.execute("SELECT dog_name FROM dogs WHERE dog_id = %s", (dog_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res[0] if res else "?"

    def load_exhibitions_to_text(self, text_widget, dog_id):
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("""
            SELECT exhibition_date, score, medal FROM exhibitions
            WHERE dog_id = %s ORDER BY exhibition_date DESC
        """, (dog_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows:
            text_widget.insert("end", "Нет записей о выставках.")
        else:
            for d, s, m in rows:
                medal = medal_to_ru(m)
                text_widget.insert("end", f"Дата: {format_date(d)} | Оценка: {s} | Медаль: {medal}\n")
        text_widget.configure(state="disabled")

    def load_diseases_to_text(self, text_widget, dog_id):
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("""
            SELECT dis.disease_name, m.illness_date, m.recovery_date
            FROM medical_history m
            JOIN diseases dis ON m.disease_id = dis.disease_id
            WHERE m.dog_id = %s
            ORDER BY m.illness_date DESC
        """, (dog_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows:
            text_widget.insert("end", "Нет записей о болезнях.")
        else:
            for name, ill, rec in rows:
                rec_str = format_date(rec) if rec else "ещё болеет"
                text_widget.insert("end", f"Болезнь: {name} | Заболел: {format_date(ill)} | Выздоровел: {rec_str}\n")
        text_widget.configure(state="disabled")

    def add_exhibition_for_dog(self, dog_id, text_widget):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить выставку")
        dialog.geometry("350x300")
        ctk.CTkLabel(dialog, text="Дата (ГГГГ-ММ-ДД):").pack(pady=5)
        date_entry = ctk.CTkEntry(dialog)
        date_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Оценка (1-5):").pack(pady=5)
        score_entry = ctk.CTkEntry(dialog)
        score_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Медаль (gold/silver/bronze/пусто):").pack(pady=5)
        medal_entry = ctk.CTkEntry(dialog)
        medal_entry.pack(pady=5)

        def save():
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                try:
                    medal = medal_entry.get().strip()
                    if medal == "":
                        medal = None
                    cur.execute("""
                        INSERT INTO exhibitions (dog_id, exhibition_date, score, medal)
                        VALUES (%s, %s, %s, %s)
                    """, (dog_id, date_entry.get(), int(score_entry.get()), medal))
                    conn.commit()
                    messagebox.showinfo("Успех", "Выставка добавлена")
                    dialog.destroy()
                    self.load_exhibitions_to_text(text_widget, dog_id)
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))
                finally:
                    cur.close()
                    conn.close()
        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=20)

    def add_disease_for_dog(self, dog_id, text_widget):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить болезнь")
        dialog.geometry("400x400")
        ctk.CTkLabel(dialog, text="Название болезни:").pack(pady=5)
        disease_name_entry = ctk.CTkEntry(dialog, width=300)
        disease_name_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Дата заболевания (ГГГГ-ММ-ДД):").pack(pady=5)
        illness_entry = ctk.CTkEntry(dialog)
        illness_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Дата выздоровления (необязательно):").pack(pady=5)
        recovery_entry = ctk.CTkEntry(dialog)
        recovery_entry.pack(pady=5)

        def save():
            disease_name = disease_name_entry.get().strip()
            if not disease_name:
                messagebox.showerror("Ошибка", "Введите название болезни")
                return
            conn = get_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                cur.execute("SELECT disease_id FROM diseases WHERE disease_name ILIKE %s", (disease_name,))
                row = cur.fetchone()
                if row:
                    disease_id = row[0]
                else:
                    cur.execute("INSERT INTO diseases (disease_name) VALUES (%s) RETURNING disease_id", (disease_name,))
                    disease_id = cur.fetchone()[0]
                recovery = recovery_entry.get().strip()
                if recovery == "":
                    recovery = None
                cur.execute("""
                    INSERT INTO medical_history (dog_id, disease_id, illness_date, recovery_date)
                    VALUES (%s, %s, %s, %s)
                """, (dog_id, disease_id, illness_entry.get(), recovery))
                conn.commit()
                messagebox.showinfo("Успех", "Болезнь добавлена")
                dialog.destroy()
                self.load_diseases_to_text(text_widget, dog_id)
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                cur.close()
                conn.close()
        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=20)

    def edit_parents_for_dog(self, dog_id, parents_frame):
        self.edit_parentage_record(dog_id, lambda: self.load_parents_to_frame(parents_frame, dog_id))

    def delete_dog(self, dog_id):
        if messagebox.askyesno("Удаление", f"Вы уверены, что хотите удалить собаку ID {dog_id}?"):
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                try:
                    cur.execute("DELETE FROM dogs WHERE dog_id = %s", (dog_id,))
                    conn.commit()
                    messagebox.showinfo("Успех", "Собака удалена")
                    self.show_dogs_view()
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))
                finally:
                    cur.close()
                    conn.close()

    def add_dog_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить собаку")
        dialog.geometry("450x500")
        ctk.CTkLabel(dialog, text="Кличка:").pack(pady=5)
        name_entry = ctk.CTkEntry(dialog)
        name_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Порода:").pack(pady=5)
        breed_entry = ctk.CTkEntry(dialog)
        breed_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Владелец (ФИО):").pack(pady=5)
        owner_entry = ctk.CTkEntry(dialog)
        owner_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Пол (М/Ж):").pack(pady=5)
        gender_var = ctk.StringVar(value="М")
        gender_menu = ctk.CTkOptionMenu(dialog, values=["М", "Ж"], variable=gender_var)
        gender_menu.pack(pady=5)
        ctk.CTkLabel(dialog, text="Дата рождения (ГГГГ-ММ-ДД):").pack(pady=5)
        birth_entry = ctk.CTkEntry(dialog)
        birth_entry.pack(pady=5)
        ctk.CTkLabel(dialog, text="Оценка психики (1-5):").pack(pady=5)
        mental_entry = ctk.CTkEntry(dialog)
        mental_entry.pack(pady=5)

        def save():
            dog_name = name_entry.get().strip()
            breed_name = breed_entry.get().strip()
            owner_name = owner_entry.get().strip()
            if not dog_name or not breed_name or not owner_name:
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            conn = get_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                # Порода
                cur.execute("SELECT breed_id FROM breeds WHERE breed_name ILIKE %s", (breed_name,))
                row = cur.fetchone()
                if row:
                    breed_id = row[0]
                else:
                    cur.execute("INSERT INTO breeds (breed_name) VALUES (%s) RETURNING breed_id", (breed_name,))
                    breed_id = cur.fetchone()[0]
                # Владелец
                cur.execute("SELECT owner_id FROM owners WHERE (last_name || ' ' || first_name) = %s", (owner_name,))
                row = cur.fetchone()
                if row:
                    owner_id = row[0]
                else:
                    parts = owner_name.split()
                    last = parts[0] if len(parts) > 0 else ""
                    first = parts[1] if len(parts) > 1 else ""
                    middle = parts[2] if len(parts) > 2 else ""
                    cur.execute("INSERT INTO owners (last_name, first_name, middle_name) VALUES (%s, %s, %s) RETURNING owner_id",
                                (last, first, middle))
                    owner_id = cur.fetchone()[0]
                gender = gender_to_db(gender_var.get())
                birth = birth_entry.get().strip() or None
                mental = None
                if mental_entry.get().strip():
                    mental = int(mental_entry.get())
                cur.execute("""
                    INSERT INTO dogs (dog_name, breed_id, owner_id, gender, birth_date, mental_test_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (dog_name, breed_id, owner_id, gender, birth, mental))
                conn.commit()
                messagebox.showinfo("Успех", "Собака добавлена")
                dialog.destroy()
                self.show_dogs_view()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
            finally:
                cur.close()
                conn.close()
        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=20)

    # ---------- ФОРМА 1:М ----------
    def show_owner_dogs_form(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Добавить владельца и его собак", font=("Arial", 18, "bold")).pack(pady=10)

        # Данные владельца
        owner_frame = ctk.CTkFrame(self.content_frame)
        owner_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(owner_frame, text="Данные владельца", font=("Arial", 14, "bold")).pack(anchor="w")
        self.owner_last = ctk.CTkEntry(owner_frame, placeholder_text="Фамилия")
        self.owner_last.pack(pady=2, fill="x")
        self.owner_first = ctk.CTkEntry(owner_frame, placeholder_text="Имя")
        self.owner_first.pack(pady=2, fill="x")
        self.owner_middle = ctk.CTkEntry(owner_frame, placeholder_text="Отчество")
        self.owner_middle.pack(pady=2, fill="x")
        self.owner_phone = ctk.CTkEntry(owner_frame, placeholder_text="Телефон")
        self.owner_phone.pack(pady=2, fill="x")
        self.owner_email = ctk.CTkEntry(owner_frame, placeholder_text="Email")
        self.owner_email.pack(pady=2, fill="x")
        self.owner_address = ctk.CTkEntry(owner_frame, placeholder_text="Адрес")
        self.owner_address.pack(pady=2, fill="x")

        # Собаки
        dogs_frame = ctk.CTkFrame(self.content_frame)
        dogs_frame.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(dogs_frame, text="Собаки (можно добавить несколько)", font=("Arial", 14, "bold")).pack(anchor="w")
        self.dogs_entries = []
        self.dogs_container = ctk.CTkFrame(dogs_frame)
        self.dogs_container.pack(fill="both", expand=True)
        self.add_dog_row()

        ctk.CTkButton(dogs_frame, text="Добавить ещё собаку", command=self.add_dog_row).pack(pady=5)
        ctk.CTkButton(self.content_frame, text="Сохранить всех", command=self.save_owner_dogs).pack(pady=10)

    def add_dog_row(self):
        row_frame = ctk.CTkFrame(self.dogs_container)
        row_frame.pack(fill="x", pady=2)
        name = ctk.CTkEntry(row_frame, placeholder_text="Кличка", width=150)
        name.pack(side="left", padx=5)
        breed = ctk.CTkEntry(row_frame, placeholder_text="Порода", width=120)
        breed.pack(side="left", padx=5)
        gender_var = ctk.StringVar(value="М")
        gender_menu = ctk.CTkOptionMenu(row_frame, values=["М", "Ж"], variable=gender_var, width=60)
        gender_menu.pack(side="left", padx=5)
        birth = ctk.CTkEntry(row_frame, placeholder_text="Дата рожд.", width=100)
        birth.pack(side="left", padx=5)
        mental = ctk.CTkEntry(row_frame, placeholder_text="Психика (1-5)", width=80)
        mental.pack(side="left", padx=5)
        del_btn = ctk.CTkButton(row_frame, text="Удалить", command=lambda: row_frame.destroy(), width=60)
        del_btn.pack(side="left", padx=5)
        self.dogs_entries.append((name, breed, gender_var, birth, mental, row_frame))

    def save_owner_dogs(self):
        if not self.owner_last.get() or not self.owner_first.get():
            messagebox.showerror("Ошибка", "Фамилия и имя владельца обязательны")
            return
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO owners (last_name, first_name, middle_name, phone, email, address)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING owner_id
            """, (self.owner_last.get(), self.owner_first.get(), self.owner_middle.get(),
                  self.owner_phone.get(), self.owner_email.get(), self.owner_address.get()))
            owner_id = cur.fetchone()[0]
            for name_e, breed_e, gender_var, birth_e, mental_e, _ in self.dogs_entries:
                dog_name = name_e.get().strip()
                if not dog_name:
                    continue
                breed_name = breed_e.get().strip()
                if not breed_name:
                    messagebox.showerror("Ошибка", "Для собаки укажите породу")
                    continue
                cur.execute("SELECT breed_id FROM breeds WHERE breed_name ILIKE %s", (breed_name,))
                row = cur.fetchone()
                if row:
                    breed_id = row[0]
                else:
                    cur.execute("INSERT INTO breeds (breed_name) VALUES (%s) RETURNING breed_id", (breed_name,))
                    breed_id = cur.fetchone()[0]
                gender = gender_to_db(gender_var.get())
                birth = birth_e.get().strip() or None
                mental = None
                if mental_e.get().strip():
                    mental = int(mental_e.get())
                cur.execute("""
                    INSERT INTO dogs (dog_name, breed_id, owner_id, gender, birth_date, mental_test_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (dog_name, breed_id, owner_id, gender, birth, mental))
            conn.commit()
            messagebox.showinfo("Успех", "Владелец и собаки добавлены")
            self.show_dogs_view()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            cur.close()
            conn.close()

    # ---------- ОТЧЁТЫ ----------
    def show_report(self, report_type):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text=f"Отчёт: {report_type}", font=("Arial", 18, "bold")).pack(pady=10)

        param_frame = ctk.CTkFrame(self.content_frame)
        param_frame.pack(fill="x", padx=10, pady=5)

        self.report_params = {}
        if report_type == "Вязка":
            ctk.CTkLabel(param_frame, text="Минимальная оценка родителей:").pack(pady=2)
            min_score_entry = ctk.CTkEntry(param_frame)
            min_score_entry.insert(0, "4")
            min_score_entry.pack(pady=2)
            self.report_params["min_score"] = min_score_entry
            alive_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(param_frame, text="Только живые", variable=alive_var).pack(pady=2)
            self.report_params["alive_only"] = alive_var
        elif report_type == "Элитная вязка":
            ctk.CTkLabel(param_frame, text="Минимальная оценка щенков:").pack(pady=2)
            min_pup_entry = ctk.CTkEntry(param_frame)
            min_pup_entry.insert(0, "5")
            min_pup_entry.pack(pady=2)
            self.report_params["min_pup"] = min_pup_entry
            need_medal_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(param_frame, text="У родителей есть медаль", variable=need_medal_var).pack(pady=2)
            self.report_params["need_medal"] = need_medal_var
        elif report_type == "Служебные":
            ctk.CTkLabel(param_frame, text="Минимальный тест психики:").pack(pady=2)
            min_mental_entry = ctk.CTkEntry(param_frame)
            min_mental_entry.insert(0, "5")
            min_mental_entry.pack(pady=2)
            self.report_params["min_mental"] = min_mental_entry
            ctk.CTkLabel(param_frame, text="Исключить болезнь:").pack(pady=2)
            exclude_entry = ctk.CTkEntry(param_frame)
            exclude_entry.insert(0, "Чумка")
            exclude_entry.pack(pady=2)
            self.report_params["exclude_disease"] = exclude_entry
            ctk.CTkLabel(param_frame, text="Макс. болезней за 2 года:").pack(pady=2)
            max_ill_entry = ctk.CTkEntry(param_frame)
            max_ill_entry.insert(0, "1")
            max_ill_entry.pack(pady=2)
            self.report_params["max_ill"] = max_ill_entry

        self.report_output = ctk.CTkTextbox(self.content_frame, wrap="word")
        self.report_output.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkButton(self.content_frame, text="Сформировать отчёт", command=lambda: self.generate_report(report_type)).pack(pady=5)

    def generate_report(self, report_type):
        self.report_output.configure(state="normal")
        self.report_output.delete("1.0", "end")
        conn = get_connection()
        if not conn:
            return
        try:
            if report_type == "Вязка":
                min_score = int(self.report_params["min_score"].get())
                alive = self.report_params["alive_only"].get()
                query = f"""
                    WITH eligible AS (
                        SELECT d.dog_id, d.dog_name, d.gender, b.breed_name
                        FROM dogs d
                        JOIN breeds b ON d.breed_id = b.breed_id
                        WHERE ({'d.is_alive = true' if alive else '1=1'})
                          AND NOT EXISTS (SELECT 1 FROM exhibitions e WHERE e.dog_id = d.dog_id AND e.score < {min_score})
                    )
                    SELECT e1.breed_name, e1.dog_name, e2.dog_name
                    FROM eligible e1, eligible e2
                    WHERE e1.gender = 'M' AND e2.gender = 'F'
                      AND NOT EXISTS (SELECT 1 FROM parentage p WHERE (p.father_id=e1.dog_id AND p.mother_id=e2.dog_id)
                                   OR (p.father_id=e2.dog_id AND p.mother_id=e1.dog_id))
                    ORDER BY e1.breed_name
                """
                cur = conn.cursor()
                cur.execute(query)
                rows = cur.fetchall()
                self.report_output.insert("end", f"ОТЧЁТ: Подбор пар для вязки (мин. оценка {min_score}, {'только живые' if alive else 'все'})\n\n")
                if not rows:
                    self.report_output.insert("end", "Нет подходящих пар.\n")
                else:
                    current_breed = None
                    breed_count = 0
                    total = 0
                    for breed, male, female in rows:
                        if breed != current_breed:
                            if current_breed:
                                self.report_output.insert("end", f"Всего пар в породе {current_breed}: {breed_count}\n\n")
                            self.report_output.insert("end", f"=== Порода: {breed} ===\n")
                            current_breed = breed
                            breed_count = 0
                        self.report_output.insert("end", f"{male} (М) + {female} (Ж)\n")
                        breed_count += 1
                        total += 1
                    if current_breed:
                        self.report_output.insert("end", f"Всего пар в породе {current_breed}: {breed_count}\n")
                    self.report_output.insert("end", f"\nИТОГО подходящих пар: {total}\n")
                cur.close()
            elif report_type == "Элитная вязка":
                min_pup = int(self.report_params["min_pup"].get())
                need_medal = self.report_params["need_medal"].get()
                medal_condition = "AND e.medal IS NOT NULL" if need_medal else ""
                query = f"""
                    WITH medal_parents AS (
                        SELECT d.dog_id, d.dog_name, d.gender, b.breed_name
                        FROM dogs d
                        JOIN breeds b ON d.breed_id = b.breed_id
                        WHERE EXISTS (SELECT 1 FROM exhibitions e WHERE e.dog_id = d.dog_id {medal_condition})
                    ),
                    good_offspring AS (
                        SELECT father_id, mother_id
                        FROM parentage p
                        JOIN exhibitions e ON p.dog_id = e.dog_id
                        WHERE e.score >= {min_pup}
                    )
                    SELECT mp1.breed_name, mp1.dog_name, mp2.dog_name
                    FROM medal_parents mp1, medal_parents mp2
                    WHERE mp1.gender = 'M' AND mp2.gender = 'F'
                      AND EXISTS (SELECT 1 FROM good_offspring go WHERE go.father_id = mp1.dog_id AND go.mother_id = mp2.dog_id)
                    ORDER BY mp1.breed_name
                """
                cur = conn.cursor()
                cur.execute(query)
                rows = cur.fetchall()
                self.report_output.insert("end", f"ЭЛИТНЫЕ ПАРЫ (оценка щенков >= {min_pup}, родители {'с медалями' if need_medal else 'без требования'})\n\n")
                if not rows:
                    self.report_output.insert("end", "Нет пар.\n")
                else:
                    current_breed = None
                    breed_count = 0
                    total = 0
                    for breed, male, female in rows:
                        if breed != current_breed:
                            if current_breed:
                                self.report_output.insert("end", f"Всего пар в породе {current_breed}: {breed_count}\n\n")
                            self.report_output.insert("end", f"=== Порода: {breed} ===\n")
                            current_breed = breed
                            breed_count = 0
                        self.report_output.insert("end", f"{male} (М) + {female} (Ж)\n")
                        breed_count += 1
                        total += 1
                    if current_breed:
                        self.report_output.insert("end", f"Всего пар в породе {current_breed}: {breed_count}\n")
                    self.report_output.insert("end", f"\nИТОГО элитных пар: {total}\n")
                cur.close()
            elif report_type == "Служебные":
                min_mental = int(self.report_params["min_mental"].get())
                exclude_disease = self.report_params["exclude_disease"].get()
                max_ill = int(self.report_params["max_ill"].get())
                query = f"""
                    WITH eligible AS (
                        SELECT d.dog_id, d.dog_name, d.gender, b.breed_name
                        FROM dogs d
                        JOIN breeds b ON d.breed_id = b.breed_id
                        WHERE d.mental_test_score >= {min_mental}
                          AND d.is_alive = true
                          AND NOT EXISTS (SELECT 1 FROM medical_history m JOIN diseases dis ON m.disease_id=dis.disease_id WHERE m.dog_id=d.dog_id AND dis.disease_name='{exclude_disease}')
                          AND (SELECT COUNT(*) FROM medical_history m WHERE m.dog_id=d.dog_id AND m.illness_date > CURRENT_DATE - INTERVAL '2 years') <= {max_ill}
                    )
                    SELECT e1.breed_name, e1.dog_name, e2.dog_name
                    FROM eligible e1, eligible e2
                    WHERE e1.gender = 'M' AND e2.gender = 'F'
                      AND NOT EXISTS (SELECT 1 FROM parentage p WHERE (p.father_id=e1.dog_id AND p.mother_id=e2.dog_id)
                                   OR (p.father_id=e2.dog_id AND p.mother_id=e1.dog_id))
                    ORDER BY e1.breed_name
                """
                cur = conn.cursor()
                cur.execute(query)
                rows = cur.fetchall()
                self.report_output.insert("end", f"СЛУЖЕБНЫЕ ПАРЫ (тест >= {min_mental}, не болели '{exclude_disease}', болезней за 2 года <= {max_ill})\n\n")
                if not rows:
                    self.report_output.insert("end", "Нет пар.\n")
                else:
                    current_breed = None
                    breed_count = 0
                    total = 0
                    for breed, male, female in rows:
                        if breed != current_breed:
                            if current_breed:
                                self.report_output.insert("end", f"Всего пар в породе {current_breed}: {breed_count}\n\n")
                            self.report_output.insert("end", f"=== Порода: {breed} ===\n")
                            current_breed = breed
                            breed_count = 0
                        self.report_output.insert("end", f"{male} (М) + {female} (Ж)\n")
                        breed_count += 1
                        total += 1
                    if current_breed:
                        self.report_output.insert("end", f"Всего пар в породе {current_breed}: {breed_count}\n")
                    self.report_output.insert("end", f"\nИТОГО служебных пар: {total}\n")
                cur.close()
        except Exception as e:
            self.report_output.insert("end", f"Ошибка выполнения отчёта: {e}")
        finally:
            conn.close()
            self.report_output.configure(state="disabled")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
