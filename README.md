# My Python GUI App

This project is a simple Python application that features a graphical user interface (GUI) with a single button. It integrates an SQLite database to demonstrate basic database operations.

## TODO 

1. create devcontainer CHECK 
2. test app CHECK 
3. create Repo CHECK 
4. git login credentials setzen CHECK 
5. use poetry CHECK 
6. make standalone app (linux, später: windows) -> ubuntu: CHECK
7. make standalone app with database CHECK 
8. develop logic + create fancy gui (database table, etc. ) CHECK
9. Debug and test CHECK 
10. create dummy data in database 
11. use plotly to make fancy statistics 
11. create gui plots -> plotly ? 
12. create multiple users 
13. make fancy data analysis and further plots 

## Project Structure

```
my-python-gui-app
├── src
│   ├── main.py          # Entry point of the application
│   ├── gui
│   │   └── app.py       # Contains the GUI implementation
│   ├── database
│   │   └── db_helper.py # Database helper functions
│   ├── config.py        # Configuration file
├── requirements.txt     # Project dependencies
├── pyproject.toml       # Poetry configuration file
└── README.md            # Project documentation
```

## Setup Instructions

1. Clone the repository or download the project files.
2. Navigate to the project directory.
3. Install the required dependencies by running:
   ```
   poetry install
   ```

## Usage

To run the application, execute the following command in your terminal:
```
poetry run python src/main.py
```

This will launch the GUI application. Click the button to trigger the associated action, which interacts with the SQLite database.

## Functionality

The application provides a simple GUI with the following features:
- **Click Me Button**: Displays a message in the console when clicked.
- **Insert Default Entry Button**: Inserts a default entry into the SQLite database.
- **Clear Console Button**: Clears the console output.

### Database

The application uses an SQLite database to store data. The database file is located at `src/database/app_database.db`. When running the standalone executable, the database will be created and used in the same location relative to the executable.

## Dependencies

- `tkinter`: For creating the GUI.
- `sqlite3`: For database operations.
- `poetry`: For managing dependencies and virtual environments.

## Build / Executable 

### Using Poetry - Easy 

1. Run:
   ```
   poetry run pyinstaller --add-data "src/database/app_database.db:data" --onefile --windowed src/main.py
   ```

### Using pip

1. Use `"image": "mcr.microsoft.com/devcontainers/python:3.10-bullseye"` - Debian 11 (GLIBC 2.31). Any newer GLIBC versions will cause troubles on OS.
2. Install pyinstaller:
   ```
   pip install pyinstaller==6.12
   ```
3. Run:
   ```
   pyinstaller --windowed --onefile src/main.py
   ```

### Alternative using Poetry

1. Add the Poetry shell plugin:
   ```
   poetry self add poetry-plugin-shell
   ```
2. Enter the Poetry shell:
   ```
   poetry shell
   ```
3. Run the PyInstaller command in the Poetry shell:
   ```
   pyinstaller --windowed --onefile src/main.py
   ```

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

For more information, refer to the [Poetry documentation](https://python-poetry.org/docs/) and [Poetry Usage](https://python-poetry.org/docs/basic-usage).

