# My Python GUI App

This project is a simple Python application that features a graphical user interface (GUI) with a single button. It integrates an SQLite database to demonstrate basic database operations.

## TODO 

1. create devcontainer CHECK
2. test app CHECK
3. create Repo CHECK
4. git login credentials setzen CHECK
5. use poetry CHECK
6. make standalone app (linux, windows) 
7. create fancy gui 
8. create dummy data in database 
9. use plotly to make fancy statistics 
10. create gui plots -> plotly ?
11. create multiple users 
12. make fancy data analysis and further plots
13. 

## Project Structure

```
my-python-gui-app
├── src
│   ├── main.py          # Entry point of the application
│   ├── gui
│   │   └── app.py      # Contains the GUI implementation
│   ├── database
│   │   └── db_helper.py # Database helper functions
├── requirements.txt     # Project dependencies
└── README.md            # Project documentation
```

## Setup Instructions

1. Clone the repository or download the project files.
2. Navigate to the project directory.
3. Install the required dependencies by running:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the application, execute the following command in your terminal:
```
python src/main.py
```

This will launch the GUI application. Click the button to trigger the associated action, which interacts with the SQLite database.

## Dependencies

- `tkinter`: For creating the GUI.
- `sqlite3`: For database operations.

## Using Poetry

To manage dependencies and virtual environments, this project uses Poetry. Here are some essential commands:

1. **Install dependencies**:
   ```
   poetry install
   ```

2. **Show detailed information about installed packages**:
   ```
   poetry show -v
   ```

3. **Set the Python interpreter in VSCode to the created virtual environment**:
   - Open the command palette (Ctrl+Shift+P).
   - Select `Python: Select Interpreter`.
   - Choose the interpreter from the `.venv` directory created by Poetry.

For more information, refer to the [Poetry documentation](https://python-poetry.org/docs/).