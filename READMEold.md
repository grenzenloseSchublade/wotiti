
# WOTITI - Work Time Timer

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#wotiti---work-time-timer)

WOTITI is a simple Python application that features a graphical user interface (GUI) to track work time. It integrates an SQLite database to store and manage user sessions, and provides statistical analysis and visualization capabilities using Plotly Dash.

## Features

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#features)

- **Start/Stop Session**: Log the start and stop times of work sessions.
- **Update Timer**: Calculate and display the total duration of sessions.
- **Multiple Users**: Support for multiple users with individual session tracking.
- **Database Integration**: Store session data in an SQLite database.
- **Console Output**: Display messages and errors in a console within the GUI.
- **Set Today's Date**: Quickly set the date entry to today's date with a button click.
- **Statistical Analysis**: Provides insights into user work patterns.
- **Interactive Visualizations**: Uses Plotly Dash to create interactive plots and charts.

## Project Structure

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#project-structure)

```
wotiti
├── src
│   ├── main.py          # Entry point of the application
│   ├── app.py           # Contains the GUI implementation
│   ├── db_helper.py     # Database helper functions
│   ├── config.py        # Configuration file
│   ├── stats_helper.py  # Functions for generating and handling sample data
├── tests                # Test files
│   ├── test_app.py      # Tests for the GUI application
│   ├── test_db_helper.py# Tests for the database helper functions
├── pyproject.toml       # Poetry configuration file
└── README.md            # Project documentation
```

## Setup Instructions

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#setup-instructions)

1. Clone the repository or download the project files.
2. Navigate to the project directory.
3. Install the required dependencies by running:
    
    ```
    poetry install
    ```
    

## Usage

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#usage)

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

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#todo)

### Baseline MVP

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#baseline-mvp)

4. create devcontainer CHECK
5. test app CHECK
6. create Repo CHECK
7. git login credentials setzen CHECK
8. use poetry CHECK
9. make standalone app (linux, später: windows) -> ubuntu: CHECK
10. make standalone app with database CHECK
11. develop logic + create fancy gui (database table, etc. ) CHECK
12. create multiple users CHECK
13. Debug and test CHECK
14. **Datenaufbereitung**: Pandas + NumPy.
    1. Daten einlesen und bereinigen
    2. Daten transformieren und aggregieren
15. **Statistische Analyse**: SciPy/StatsModels für Hypothesentests, Scikit-learn für ML-Modelle.
    1. Hypothesentests (z.B. t-Tests, ANOVA) CHECK
    2. Regressionsanalysen (z.B. lineare Regression) CHECK
    3. Klass
16. Stastiken -> plotly dash
    4. create dummy data in database CHECK
    5. create gui plots -> plotly dash CHECK
    6. use pandas scipy to make fancy statistics
        1. Triviale Berechnungen (Summen, Durchschnitte etc.) CHECK
        2. Triviale Zusammenhänge (Korrelationen etc.)
        3. Komplexe Berechnungen und Zusammenhänge (Regressionen, ML etc.)
    7. Eiene Datei / eigenes Dashboard: Mache ein krassen Plot für einen user (beispiele aus dem internet anschauen)

### Improvements and Features

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#improvements-and-features)

17. GUI so einfach wie möglich halten -> Was wenn vergessen wurde Zeit zu stoppen???
    - 1. Reiter: Eingabe -> Name, Datum, Projekt
    - 2. Reiter: Ausgabe
    - 3. Reiter: Statistiken
18. Was wenn vergessen wurde Zeit zu stoppen??? -> Einträge bearbeiten können (neuer reiter)
19. Performance: Timer asynchron machen und Datenbankzugriff nur dann wenn nötig
20. make further fancy data analysis and further plots

## Functionality

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#functionality)

### GUI Components

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#gui-components)

- **Start Button**: Starts a new session for the specified user, project, and date.
- **Stop Button**: Stops the current session for the specified user, project, and date.
- **Update Timer Button**: Calculates and displays the total duration of sessions.
- **Set Today's Date Button**: Sets the date entry to today's date.
- **Clear Console Button**: Clears the console output.
- **Console**: Displays messages and errors.

### Database

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#database)

The application uses an SQLite database to store session data. The database file is located at `src/database/app_database.db`. When running the standalone executable, the database will be created and used in the same location relative to the executable.

## Dependencies

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#dependencies)

- `tkinter`: For creating the GUI.
- `sqlite3`: For database operations.
- `poetry`: For managing dependencies and virtual environments.

## Build Executable

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#build-executable)

### Using Poetry - Easy

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#using-poetry---easy)

21. Run:
    
    ```
    poetry run pyinstaller --onefile --windowed src/main.py
    ```
    

### Using pip

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#using-pip)

22. Use `"image": "mcr.microsoft.com/devcontainers/python:3.10-bullseye"` - Debian 11 (GLIBC 2.31). Any newer GLIBC versions will cause troubles on OS.
23. Install pyinstaller:
    
    ```
    pip install pyinstaller==6.12
    ```
    
24. Run:
    
    ```
    pyinstaller --windowed --onefile src/main.py
    ```
    

### Alternative using Poetry

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#alternative-using-poetry)

25. Add the Poetry shell plugin:
    
    ```
    poetry self add poetry-plugin-shell
    ```
    
26. Enter the Poetry shell:
    
    ```
    poetry shell
    ```
    
27. Run the PyInstaller command in the Poetry shell:
    
    ```
    pyinstaller --windowed --onefile src/main.py
    ```
    

## Using Poetry

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#using-poetry)

To manage dependencies and virtual environments, this project uses Poetry. Here are some essential commands:

28. **Install dependencies**:
    
    ```
    poetry install
    ```
    
29. **Show detailed information about installed packages**:
    
    ```
    poetry show -v
    ```
    
30. **Set the Python interpreter in VSCode to the created virtual environment**:
    
    - Open the command palette (Ctrl+Shift+P).
    - Select `Python: Select Interpreter`.
    - Choose the interpreter from the `.venv` directory created by Poetry.

For more information, refer to the [Poetry documentation](https://python-poetry.org/docs/) and [Poetry Usage](https://python-poetry.org/docs/basic-usage).

## Testing

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#testing)

This project includes tests for both the GUI application and the database helper functions. To run the tests, use the following command:

```
poetry run pytest
```

### Test Files

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#test-files)

- `tests/test_app.py`: Contains tests for the GUI application.
- `tests/test_db_helper.py`: Contains tests for the database helper functions.

## Generating Sample Data

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#generating-sample-data)

The `stats_helper.py` module includes functions to generate sample data for testing and development purposes.

### `generate_sample_data()`

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#generate_sample_data)

This function generates sample data based on the specified parameters:

- **num_users**: Number of users to generate data for.
- **storage_type**: Type of storage ('csv', 'db', or 'both').
- **timeblock_min**: Minimum time block in minutes between start and stop times.
- **start_date**: Start date for the entries (format: 'dd-mm-yyyy').
- **end_date**: End date for the entries (format: 'dd-mm-yyyy').
- **project_max**: Maximum number of projects to generate.
- **fixed_interval**: Fixed time interval per day for start and stop times (format: 'HH:MM-HH:MM').
- **path_to_save**: Path to save the generated data.
- **add_to_existing**: Whether to add to existing data or overwrite.

#### Features and Usage

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#features-and-usage)

- **Flexible Data Generation**: Allows you to specify the number of users, the number of entries per user, and the date range for the entries.
- **Randomized Projects**: Generates random project names in the format "projekt_{number}".
- **Fixed or Random Intervals**: You can specify a fixed time interval for start and stop times or let the function generate random times within the day.
- **Storage Options**: Choose to store the generated data in a CSV file, a database, or both.
- **Appending Data**: Optionally add to existing data instead of overwriting it.

### `generate_random_sample_data()`

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#generate_random_sample_data)

This function generates sample data with random values for start_date, end_date, and fixed_interval. It creates a directory for the generated data and saves the parameters used for generation in a JSON file. This is useful for quickly generating diverse datasets for testing and development.

#### Features and Usage

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#features-and-usage-1)

- **Randomized Parameters**: Automatically generates random values for the number of users, entries per user, date range, and time intervals.
- **Directory Creation**: Creates a new directory for each run to store the generated data and parameters.
- **Parameter Logging**: Saves the parameters used for data generation in a JSON file, making it easy to reproduce or analyze the generated data.

#### Sample Data Representation

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#sample-data-representation)

Here is an example of what the generated data might look like:

|user|project|event_type|timestamp|date|
|---|---|---|---|---|
|user_1|projekt_3|start|01-01-2023 09:00:00|01-01-2023|
|user_1|projekt_3|stop|01-01-2023 10:30:00|01-01-2023|
|user_2|projekt_1|start|01-01-2023 11:00:00|01-01-2023|
|user_2|projekt_1|stop|01-01-2023 12:45:00|01-01-2023|
|user_1|projekt_2|start|02-01-2023 08:15:00|02-01-2023|
|user_1|projekt_2|stop|02-01-2023 09:45:00|02-01-2023|

This table shows the user, project, event type (start or stop), timestamp of the event, and the date of the event.

## Statistics and Data Analysis

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#statistics-and-data-analysis)

## Plots and Visualizations

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#plots-and-visualizations)

## Contributing

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#contributing)

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

[](https://github.com/grenzenloseSchublade/wotiti?tab=readme-ov-file#license)

This project is licensed under the MIT License. See the [LICENSE](https://github.com/grenzenloseSchublade/wotiti/blob/main/LICENSE) file for details.