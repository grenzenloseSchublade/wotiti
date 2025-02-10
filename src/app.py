from tkinter import Button, Text, Scrollbar, VERTICAL, END, Frame
import sys
import time
from db_helper import create_connection, create_table, insert_data

class App:
    def __init__(self, master):
        print("Initializing the application GUI...")
        self.master = master
        master.title("Fancy GUI App")
        master.configure(bg='#2e2e2e')

        self.frame = Frame(master, bg='#2e2e2e')
        self.frame.grid(padx=10, pady=10, sticky="nsew")

        self.button = Button(self.frame, text="Click Me", command=self.on_button_click, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.button.grid(row=0, column=0, pady=5, padx=5, sticky="ew")

        self.insert_button = Button(self.frame, text="Insert Default Entry", command=self.insert_default_entry, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.insert_button.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

        self.console_frame = Frame(self.frame, bg='#2e2e2e')
        self.console_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.console = Text(self.console_frame, wrap='word', state='disabled', height=10, bg='#1e1e1e', fg='white', font=('Courier', 10))
        self.console.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = Scrollbar(self.console_frame, orient=VERTICAL, command=self.console.yview, bg='#2e2e2e')
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.console['yscrollcommand'] = self.scrollbar.set

        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        self.console_frame.grid_rowconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)

        sys.stdout = self
        sys.stderr = self

        print("Connecting to the database...")
        self.db_conn = create_connection("src/database/app_database.db")
        if self.db_conn:
            create_table(self.db_conn)
            print("Database connected and table created.")

    def on_button_click(self):
        print("Button clicked!")

    def insert_default_entry(self):
        if self.db_conn:
            print("Inserting default entry into the database...")
            insert_data(self.db_conn, "Default Entry")
            print("Default entry inserted into the database.")

    def write(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if message.strip():
            message = f"[{timestamp}] {message}"
        self.console.configure(state='normal')
        self.console.insert(END, message)
        self.console.configure(state='disabled')
        self.console.see(END)

    def flush(self):
        pass
