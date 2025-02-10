import tkinter as tk
from tkinter import messagebox
from app import App

def main():
    try:
        print("Starting the application...")
        root = tk.Tk()
        app = App(root)
        print("Application started successfully.")
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
