# WOTITI - Work Time Timer

WOTITI is a simple Python application that features a graphical user interface (GUI) to track work time. It integrates an SQLite database to store and manage user sessions.

## Features

- **Start/Stop Session**: Log the start and stop times of work sessions.
- **Update Timer**: Calculate and display the total duration of sessions.
- **Multiple Users**: Support for multiple users with individual session tracking.
- **Database Integration**: Store session data in an SQLite database.
- **Console Output**: Display messages and errors in a console within the GUI.
- **Set Today's Date**: Quickly set the date entry to today's date with a button click.

## Project Structure

```
wotiti
├── src
│   ├── main.py          # Entry point of the application
│   ├── app.py           # Contains the GUI implementation
│   ├── db_helper.py     # Database helper functions
│   ├── config.py        # Configuration file
├── tests                # Test files
│   ├── test_app.py      # Tests for the GUI application
│   ├── test_db_helper.py# Tests for the database helper functions
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
or use the build file in the dist folder.
```
./main
```

This will launch the GUI application. Use the buttons to start/stop sessions, update the timer, and interact with the SQLite database.


## TODO 

### Baseline MVP
1. create devcontainer CHECK 
2. test app CHECK 
3. create Repo CHECK 
4. git login credentials setzen CHECK 
5. use poetry CHECK 
6. make standalone app (linux, später: windows) -> ubuntu: CHECK
7. make standalone app with database CHECK 
8. develop logic + create fancy gui (database table, etc. ) CHECK
9. create multiple users CHECK 
10. Debug and test CHECK 
11. Stastiken (neuer Reiter oder qt window?) -> plotly, pandas???
12. create dummy data in database 
13. use plotly to make fancy statistics?
14. create gui plots -> plotly, matplotlib ? 

### Improvements and Features
15. GUI so einfach wie möglich halten -> Was wenn vergessen wurde Zeit zu stoppen???
    - 1. Reiter: Eingabe -> Name, Datum, Projekt
    - 2. Reiter: Ausgabe
    - 3. Reiter: Statistiken
16. Was wenn vergessen wurde Zeit zu stoppen??? -> Einträge bearbeiten können (neuer reiter)
17. Performance: Timer asynchron machen und Datenbankzugriff nur dann wenn nötig
18. make further fancy data analysis and further plots 
19. 

## Functionality

### GUI Components

- **Start Button**: Starts a new session for the specified user, project, and date.
- **Stop Button**: Stops the current session for the specified user, project, and date.
- **Update Timer Button**: Calculates and displays the total duration of sessions.
- **Set Today's Date Button**: Sets the date entry to today's date.
- **Clear Console Button**: Clears the console output.
- **Console**: Displays messages and errors.

### Database

The application uses an SQLite database to store session data. The database file is located at `src/database/app_database.db`. When running the standalone executable, the database will be created and used in the same location relative to the executable.

## Dependencies

- `tkinter`: For creating the GUI.
- `sqlite3`: For database operations.
- `poetry`: For managing dependencies and virtual environments.

## Build Executable 

### Using Poetry - Easy 

1. Run:
   ```
   poetry run pyinstaller --onefile --windowed src/main.py
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

## Testing

This project includes tests for both the GUI application and the database helper functions. To run the tests, use the following command:
```
poetry run pytest
```

### Test Files

- `tests/test_app.py`: Contains tests for the GUI application.
- `tests/test_db_helper.py`: Contains tests for the database helper functions.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

