import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime
import os


class ForensicsDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Forensics Dashboard")

        # Set up database paths
        db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database')
        self.email_db = sqlite3.connect(os.path.join(db_dir, "emails.db"))
        self.evidence_db = sqlite3.connect(os.path.join(db_dir, "evidence.db"))

        self.setup_ui()

    def setup_ui(self):
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, expand=True)

        overview_frame = ttk.Frame(notebook)
        email_frame = ttk.Frame(notebook)
        file_frame = ttk.Frame(notebook)
        custody_frame = ttk.Frame(notebook)

        notebook.add(overview_frame, text="Evidence Overview")
        notebook.add(email_frame, text="Email Evidence")
        notebook.add(file_frame, text="File Evidence")
        notebook.add(custody_frame, text="Chain of Custody")

        self.setup_overview_tab(overview_frame)
        self.setup_email_tab(email_frame)
        self.setup_file_tab(file_frame)
        self.setup_custody_tab(custody_frame)

    def setup_overview_tab(self, parent):
        stats_frame = ttk.LabelFrame(parent, text="Evidence Statistics")
        stats_frame.pack(pady=10, padx=10, fill="x")
        ttk.Label(stats_frame, text=f"Total Emails: {self.get_email_count()}").pack(pady=5)
        ttk.Label(stats_frame, text=f"Total Files: {self.get_file_count()}").pack(pady=5)

    def setup_email_tab(self, parent):
        tree = ttk.Treeview(parent, columns=("Sender", "Subject", "Date", "Security"), show="headings")
        tree.heading("Sender", text="Sender")
        tree.heading("Subject", text="Subject")
        tree.heading("Date", text="Date")
        tree.heading("Security", text="Security Status")
        tree.pack(pady=10, padx=10, fill="both", expand=True)
        self.populate_email_tree(tree)

    def setup_file_tab(self, parent):
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True)

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(side="left", fill="both", expand=True)

        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(search_frame, text="Search", command=lambda: self.search_files(self.file_tree)).pack(side="left")

        self.file_tree = ttk.Treeview(list_frame, columns=("Filename", "Type", "Size", "Modified"), show="headings")
        for col in ("Filename", "Type", "Size", "Modified"):
            self.file_tree.heading(col, text=col)
        self.file_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.file_tree.bind('<<TreeviewSelect>>', self.on_file_select)

        details_frame = ttk.LabelFrame(main_frame, text="File Details")
        details_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        self.details_text = tk.Text(details_frame, wrap=tk.WORD, width=40)
        self.details_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.populate_file_tree(self.file_tree)

    def setup_custody_tab(self, parent):
        custody_frame = ttk.LabelFrame(parent, text="Chain of Custody Log")
        custody_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.custody_text = tk.Text(custody_frame, height=10)
        self.custody_text.pack(pady=5, padx=5, fill="both", expand=True)
        ttk.Button(custody_frame, text="Add Custody Entry", command=self.add_custody_entry).pack(pady=5)

    def get_email_count(self):
        try:
            cursor = self.email_db.cursor()
            cursor.execute("SELECT COUNT(*) FROM email_metadata")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def get_file_count(self):
        try:
            cursor = self.evidence_db.cursor()
            cursor.execute("SELECT COUNT(*) FROM file_metadata")
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def populate_email_tree(self, tree):
        try:
            cursor = self.email_db.cursor()
            cursor.execute("""
                SELECT sender, subject, date, 
                       CASE 
                           WHEN spf_pass + dkim_pass + dmarc_pass = 3 THEN 'Secure'
                           WHEN spf_pass + dkim_pass + dmarc_pass >= 1 THEN 'Partial'
                           ELSE 'Unsecure'
                       END as security
                FROM email_metadata
            """)
            for row in cursor.fetchall():
                tree.insert("", "end", values=row)
        except sqlite3.OperationalError:
            pass

    def populate_file_tree(self, tree):
        try:
            cursor = self.evidence_db.cursor()
            cursor.execute("SELECT file_name, file_size, hash_sha256, last_modified FROM file_metadata")
            for row in cursor.fetchall():
                tree.insert("", "end", values=row)
        except sqlite3.OperationalError:
            pass

    def on_file_select(self, event):
        selection = self.file_tree.selection()
        if not selection:
            return
        item = self.file_tree.item(selection[0])
        file_name = item['values'][0]
        cursor = self.evidence_db.cursor()
        cursor.execute("""
            SELECT fm.*, fa.file_type, fa.mime_type, fa.content_preview, fa.extracted_text, im.exif_data
            FROM file_metadata fm
            LEFT JOIN file_analysis fa ON fm.id = fa.file_id
            LEFT JOIN image_metadata im ON fm.id = im.file_id
            WHERE fm.file_name = ?
        """, (file_name,))
        result = cursor.fetchone()
        if result:
            self.details_text.delete(1.0, tk.END)
            details = f"""File: {result[1]}
Type: {result[6]}
MIME Type: {result[7]}
Size: {result[3]} bytes
Last Modified: {result[5]}
Content Preview:
{result[8] if result[8] else 'No preview available'}
Extracted Text:
{result[9] if result[9] else 'No text extracted'}
Image Metadata:
{result[10] if result[10] else 'No image metadata'}"""
            self.details_text.insert(1.0, details)

    def search_files(self, tree):
        keyword = self.search_var.get()
        for item in tree.get_children():
            tree.delete(item)
        cursor = self.evidence_db.cursor()
        cursor.execute("""
            SELECT fm.file_name, fa.file_type, fm.file_size, fm.last_modified
            FROM file_metadata fm
            JOIN file_analysis fa ON fm.id = fa.file_id
            WHERE fm.file_name LIKE ? OR fa.extracted_text LIKE ?
        """, (f'%{keyword}%', f'%{keyword}%'))
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)

    def add_custody_entry(self):
        timestamp = datetime.now().isoformat()
        entry = f"[{timestamp}] Evidence accessed by [USER]\n"
        self.custody_text.insert("end", entry)


if __name__ == "__main__":
    root = tk.Tk()
    app = ForensicsDashboard(root)
    root.mainloop()
