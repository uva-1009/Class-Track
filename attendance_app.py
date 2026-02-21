import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

# Fix working directory to script's location so CSV files are always found
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # __file__ not defined in some IDEs (e.g. IDLE) — fall back to current dir
    script_dir = os.path.abspath(os.getcwd())

os.chdir(script_dir)

STUDENTS_FILE = "students.csv"
ATTENDANCE_FILE = "attendance.csv"


# --- File Setup / Self-Healing ---
def ensure_files():
    if not os.path.exists(STUDENTS_FILE) or os.path.getsize(STUDENTS_FILE) == 0:
        with open(STUDENTS_FILE, "w", newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["RollNo", "Name", "Class"])

    if not os.path.exists(ATTENDANCE_FILE) or os.path.getsize(ATTENDANCE_FILE) == 0:
        with open(ATTENDANCE_FILE, "w", newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["Date", "RollNo", "Status"])


# --- Read students safely ---
def read_students():
    ensure_files()
    students = []
    with open(STUDENTS_FILE, newline='', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM
        r = csv.DictReader(f)
        if r.fieldnames is None or "RollNo" not in r.fieldnames:
            return []
        for row in r:
            students.append(row)
    return students


# --- Add Student ---
def add_student(roll, name, cls):
    students = read_students()
    for s in students:
        if s["RollNo"] == roll:
            return False
    with open(STUDENTS_FILE, "a", newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([roll, name, cls])
    return True


# --- Mark Attendance ---
def record_attendance(att_date, roll, status):
    with open(ATTENDANCE_FILE, "a", newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([att_date, roll, status])


# --- GUI Application ---
class AttendanceApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Smart Attendance App - Class 12 Project")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        ensure_files()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_add_student_tab()
        self.create_mark_attendance_tab()
        self.create_report_tab()

        # Auto-reload attendance list when switching to that tab
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self.attendance_vars = {}

        self.create_debug_tab()

    def _on_tab_change(self, event):
        selected = self.notebook.index(self.notebook.select())
        if selected == 1:
            self.load_attendance_marking()

    # ── TAB 1: Add Student ────────────────────────────────────────────────────
    def create_add_student_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Add Student  ")

        frame = ttk.LabelFrame(tab, text="Student Details", padding=20)
        frame.pack(padx=30, pady=30, fill="x")

        ttk.Label(frame, text="Roll No:").grid(row=0, column=0, sticky="w", pady=8)
        self.roll_entry = ttk.Entry(frame, width=30)
        self.roll_entry.grid(row=0, column=1, pady=8, padx=10)

        ttk.Label(frame, text="Name:").grid(row=1, column=0, sticky="w", pady=8)
        self.name_entry = ttk.Entry(frame, width=30)
        self.name_entry.grid(row=1, column=1, pady=8, padx=10)

        ttk.Label(frame, text="Class:").grid(row=2, column=0, sticky="w", pady=8)
        self.class_entry = ttk.Entry(frame, width=30)
        self.class_entry.grid(row=2, column=1, pady=8, padx=10)

        ttk.Button(tab, text="Add Student", command=self.add_student_action).pack(pady=10)

    def add_student_action(self):
        roll = self.roll_entry.get().strip()
        name = self.name_entry.get().strip()
        cls = self.class_entry.get().strip()

        if not roll or not name or not cls:
            messagebox.showerror("Error", "All fields are required.")
            return

        if add_student(roll, name, cls):
            messagebox.showinfo("Success", f"Student '{name}' added successfully.")
            self.roll_entry.delete(0, tk.END)
            self.name_entry.delete(0, tk.END)
            self.class_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", f"Roll number '{roll}' already exists.")

    # ── TAB 2: Mark Attendance ────────────────────────────────────────────────
    def create_mark_attendance_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Mark Attendance  ")
        self._attendance_tab = tab

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=20, pady=10)

        ttk.Label(top, text="Date (YYYY-MM-DD):").pack(side="left")
        self.date_entry = ttk.Entry(top, width=15)
        self.date_entry.pack(side="left", padx=8)
        self.date_entry.insert(0, date.today().isoformat())

        ttk.Button(top, text="Reload Students", command=self.load_attendance_marking).pack(side="left", padx=5)
        ttk.Button(top, text="Save Attendance", command=self.save_attendance).pack(side="left", padx=5)

        # Scrollable area for student list
        container = ttk.Frame(tab)
        container.pack(fill="both", expand=True, padx=20, pady=5)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.attendance_frame = ttk.Frame(canvas)

        self.attendance_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.attendance_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.attendance_vars = {}

    def load_attendance_marking(self):
        for widget in self.attendance_frame.winfo_children():
            widget.destroy()
        self.attendance_vars = {}

        students = read_students()

        if not students:
            ttk.Label(self.attendance_frame,
                      text="No students found. Please add students first.",
                      foreground="red").grid(row=0, column=0, columnspan=3, pady=20)
            return

        # Header row
        ttk.Label(self.attendance_frame, text="Roll No", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ttk.Label(self.attendance_frame, text="Name", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        ttk.Label(self.attendance_frame, text="Status", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=10, pady=5, sticky="w")

        for i, s in enumerate(students, start=1):
            ttk.Label(self.attendance_frame, text=s['RollNo']).grid(row=i, column=0, padx=10, pady=3, sticky="w")
            ttk.Label(self.attendance_frame, text=s['Name']).grid(row=i, column=1, padx=10, pady=3, sticky="w")

            var = tk.StringVar(value="P")
            self.attendance_vars[s['RollNo']] = var
            ttk.OptionMenu(self.attendance_frame, var, "P", "P", "A").grid(row=i, column=2, padx=10, pady=3)

    def save_attendance(self):
        if not self.attendance_vars:
            messagebox.showwarning("Warning", "No students loaded. Please reload students first.")
            return

        att_date = self.date_entry.get().strip()

        try:
            datetime.fromisoformat(att_date)
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
            return

        for roll, var in self.attendance_vars.items():
            record_attendance(att_date, roll, var.get())

        messagebox.showinfo("Saved", f"Attendance for {att_date} saved successfully.")

    # ── TAB 3: Reports ────────────────────────────────────────────────────────
    def create_report_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Reports  ")

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=20, pady=10)

        ttk.Label(top, text="Roll No:").pack(side="left")
        self.report_roll = ttk.Entry(top, width=15)
        self.report_roll.pack(side="left", padx=8)
        ttk.Button(top, text="Show Report", command=self.show_report).pack(side="left", padx=5)
        ttk.Button(top, text="Show All Students", command=self.show_all_students).pack(side="left", padx=5)

        frame = ttk.Frame(tab)
        frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.report_box = tk.Text(frame, height=20, font=("Courier New", 10))
        scrollbar = ttk.Scrollbar(frame, command=self.report_box.yview)
        self.report_box.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.report_box.pack(side="left", fill="both", expand=True)

    def show_report(self):
        roll = self.report_roll.get().strip()
        if not roll:
            messagebox.showerror("Error", "Please enter a Roll No.")
            return

        students = {s["RollNo"]: s for s in read_students()}

        if roll not in students:
            messagebox.showerror("Error", f"Roll No '{roll}' not found.")
            return

        if not os.path.exists(ATTENDANCE_FILE):
            messagebox.showinfo("Info", "No attendance recorded yet.")
            return

        with open(ATTENDANCE_FILE, newline='', encoding='utf-8-sig') as f:
            r = csv.DictReader(f)
            if r.fieldnames is None or "RollNo" not in r.fieldnames:
                messagebox.showinfo("Info", "Attendance file is empty or corrupted.")
                return
            rows = [x for x in r if x["RollNo"] == roll]

        self.report_box.delete(1.0, tk.END)

        if not rows:
            self.report_box.insert(tk.END, "No attendance records found for this student.")
            return

        rows.sort(key=lambda x: x["Date"])
        present = sum(1 for row in rows if row["Status"] == "P")
        total = len(rows)
        pct = present / total * 100

        text = f"{'='*45}\n"
        text += f"  Attendance Report\n"
        text += f"  Name  : {students[roll]['Name']}\n"
        text += f"  Roll  : {roll}\n"
        text += f"  Class : {students[roll]['Class']}\n"
        text += f"{'='*45}\n"
        text += f"  Present : {present}/{total} days ({pct:.1f}%)\n"
        text += f"  Absent  : {total - present}/{total} days\n"
        text += f"{'='*45}\n\n"
        text += f"  {'Date':<15} Status\n"
        text += f"  {'-'*25}\n"
        for row in rows:
            status_label = "✓ Present" if row["Status"] == "P" else "✗ Absent"
            text += f"  {row['Date']:<15} {status_label}\n"

        self.report_box.insert(tk.END, text)

    def show_all_students(self):
        students = read_students()
        self.report_box.delete(1.0, tk.END)

        if not students:
            self.report_box.insert(tk.END, "No students registered yet.")
            return

        text = f"{'='*45}\n"
        text += f"  All Registered Students ({len(students)} total)\n"
        text += f"{'='*45}\n"
        text += f"  {'Roll':<10} {'Name':<20} Class\n"
        text += f"  {'-'*40}\n"
        for s in students:
            text += f"  {s['RollNo']:<10} {s['Name']:<20} {s['Class']}\n"

        self.report_box.insert(tk.END, text)


    # ── TAB 4: Debug ─────────────────────────────────────────────────────────
    def create_debug_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  🔍 Debug  ")

        ttk.Button(tab, text="Run Diagnostics", command=self.run_diagnostics).pack(pady=10)

        self.debug_box = tk.Text(tab, height=25, font=("Courier New", 10))
        sb = ttk.Scrollbar(tab, command=self.debug_box.yview)
        self.debug_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.debug_box.pack(fill="both", expand=True, padx=10, pady=5)

    def run_diagnostics(self):
        lines = []
        lines.append("=== DIAGNOSTICS ===\n")
        lines.append(f"script_dir resolved to:\n  {script_dir}\n")

        # Working directory
        cwd = os.getcwd()
        lines.append(f"Working directory:\n  {cwd}\n")

        # Script location
        try:
            script_path = os.path.abspath(__file__)
            lines.append(f"Script location:\n  {script_path}\n")
        except Exception as e:
            lines.append(f"Script location: ERROR - {e}\n")

        # Students file
        sf = os.path.abspath(STUDENTS_FILE)
        lines.append(f"Students file path:\n  {sf}")
        if os.path.exists(sf):
            size = os.path.getsize(sf)
            lines.append(f"  ✓ File EXISTS ({size} bytes)\n")
            try:
                with open(sf, encoding='utf-8-sig') as f:
                    content = f.read()
                lines.append(f"  Raw content:\n{content}\n")
            except Exception as e:
                lines.append(f"  ERROR reading: {e}\n")
        else:
            lines.append(f"  ✗ File NOT FOUND\n")

        # Try reading students
        lines.append("--- read_students() result ---\n")
        try:
            students = read_students()
            if students:
                for s in students:
                    lines.append(f"  {s}\n")
            else:
                lines.append("  Returned EMPTY LIST\n")
                # Extra check: manually parse
                lines.append("\n--- Manual parse attempt ---\n")
                if os.path.exists(sf):
                    with open(sf, 'rb') as f:
                        raw = f.read()
                    lines.append(f"  Raw bytes (first 200): {raw[:200]}\n")
                    # Try different encodings
                    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                        try:
                            decoded = raw.decode(enc)
                            first_line = decoded.split('\n')[0]
                            lines.append(f"  [{enc}] First line: {repr(first_line)}\n")
                        except Exception as e:
                            lines.append(f"  [{enc}] Error: {e}\n")
        except Exception as e:
            lines.append(f"  EXCEPTION: {e}\n")

        self.debug_box.delete(1.0, tk.END)
        self.debug_box.insert(tk.END, "".join(lines))


# --- Run App ---
if __name__ == "__main__":
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()
