# Student Management API

A FastAPI backend for managing student records and marks, with student search,
pagination, filtering, and academic reports. The project also includes a script
for cleaning raw student data before it is used by the API.

## Features

- Create, retrieve, update, and soft-delete student records.
- Search and filter students by name, class, and section, with pagination and
  sorting.
- Add, list, correct, and remove student marks.
- Generate report cards and reports for toppers, subject toppers, class
  averages, rank lists, failing students, improvement, students without marks,
  and data quality.
- Validate student and marks input with Pydantic.
- Clean raw student data, normalize common fields, reject invalid rows with a
  reason, and print a processing summary.

## Tech stack

- Python 3.12+
- FastAPI and Uvicorn
- MySQL (`mysql-connector-python`)
- Pydantic
- pytest

> The current application connects to MySQL.

## Project layout

```text
app/
  main.py                 FastAPI application and router registration
  database.py             MySQL connection helper
  routers/                Student, marks, and report endpoints
  schemas/                Pydantic request and response models
  services/                Business logic
  repositories/            Data access
  integration/              Integration code
  utils/                   Grading and logging helpers
scripts/
  clean_raw_data.py        Raw student data cleaning
sql/
  students.sql             Raw student data
  schemas.sql              Database schema placeholder
tests/                     Project tests
```

## Setup

1. Install Python 3.12 or later and run a MySQL server.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv env
   .\env\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and configure the MySQL connection:

   ```dotenv
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=your_mysql_user
   DB_PASSWORD=your_mysql_password
   DB_NAME=student_management
   ```

5. Create the database tables expected by the application, and load the raw
   student data into `raw_students` before running the cleaning script.

   The current `sql/schemas.sql` file is empty, so database tables must be
   provisioned separately before the API and cleaning script can run.

Do not commit `.env` or database credentials.

## Run the API

From the project root:

```powershell
uvicorn app.main:app --reload
```

The interactive API documentation is available at
[`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs).

## API endpoints

All routes are currently registered at the application root (there is no
`/api/v1` prefix).

### Students

| Method | Path | Description |
|---|---|---|
| `POST` | `/students/` | Create a student |
| `GET` | `/students/` | List students |
| `GET` | `/students/{student_id}` | Get a student |
| `PUT` | `/students/{student_id}` | Replace a student's fields |
| `PATCH` | `/students/{student_id}` | Update selected student fields |
| `DELETE` | `/students/{student_id}` | Soft-delete a student |

The list endpoint supports `page`, `limit`, `search`, `class`, `section`,
`sort`, and `include_inactive` query parameters.

### Marks

| Method | Path | Description |
|---|---|---|
| `POST` | `/students/{student_id}/marks` | Add marks for a student |
| `GET` | `/students/{student_id}/marks` | List a student's marks |
| `PATCH` | `/marks/{id}` | Correct a marks entry |
| `DELETE` | `/marks/{id}` | Delete a marks entry |

### Reports

| Method | Path | Description |
|---|---|---|
| `GET` | `/students/{student_id}/report-card?exam=Final` | Get a report card |
| `GET` | `/reports/toppers?exam=Final&limit=3` | Get class toppers |
| `GET` | `/reports/subject-toppers?exam=Final` | Get subject toppers |
| `GET` | `/reports/class-average?class=10` | Get class averages by subject |
| `GET` | `/reports/rank-list?class=10&exam=Final` | Get a class rank list |
| `GET` | `/reports/failing?exam=Final` | Find students failing a subject |
| `GET` | `/reports/improvement` | Find students improving between exams |
| `GET` | `/reports/no-marks` | Find active students with no marks |
| `GET` | `/reports/data-quality` | Summarize selected data-quality gaps |

## Clean raw student data

After configuring MySQL and loading `raw_students`, run the cleaner from the
project root:

```powershell
python -m scripts.clean_raw_data
```

The script normalizes names, roll numbers, school codes, class and section
values, email addresses, and dates of birth. Rows that cannot be accepted are
recorded in `rejected_students` with a reason.

**Duplicate handling:** a student is identified by the pair `(school_id,
roll_no)`. The cleaner processes raw rows in ascending `raw_id` order, keeps
the first valid occurrence of each pair, and counts later occurrences as
duplicates rather than merging their fields.

**Caution:** each cleaning run deletes the existing records from `students`,
`marks`, and `rejected_students` before rebuilding the cleaned student records.
Back up any data you need before running it again.

## Development status

The repository currently implements student, marks, and report routes backed by
MySQL. Authentication, school-level request isolation, exports/imports, email
and webhook delivery, and holiday lookup are not currently wired into the API.