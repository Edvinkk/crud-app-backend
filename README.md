# CRUD App Backend

FastAPI and SQLite backend for creating, reading, updating, and deleting items, with CSV import.

## Run locally

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs for the API documentation.

The app creates `test.db` and writes activity to `server.log`. Neither file is committed to Git.

## CSV format

Send a UTF-8 CSV file to `POST /items/import-csv` with the `Content-Type: text/csv` header:

```csv
name,description
Apple,A red fruit
Banana,A yellow fruit
```

## Tests

```powershell
python -m unittest test_csv_import -v
```
