import re
from datetime import datetime, date

from app.database import get_connection


def clean_text(value):
    if value is None:
        return None

    value = value.strip()

    if value.lower() in ("", "n/a", "-", "null", "none"):
        return None

    return value.title()


def clean_roll_no(value):
    if not value:
        return None

    value = str(value).strip().upper()
    value = re.sub(r"^(ROLL|R)\s*-?\s*", "", value)

    if re.fullmatch(r"\d+(\.0+)?", value):
        return int(float(value))

    return None


def clean_school_code(value):
    if not value:
        return None

    value = re.sub(r"[^A-Z]", "", value.upper())

    if value in ("GPS", "GREENFIELD", "GREENFIELDPUBLIC"):
        return "GPS"

    if value in ("SVS", "SUNRISE", "SUNRISEVALLEY"):
        return "SVS"

    return None


def clean_name(first_name, last_name):
    first_name = clean_text(first_name)
    last_name = clean_text(last_name)

    if not first_name:
        return None, last_name

    if not last_name and len(first_name.split()) > 1:
        parts = first_name.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:])

    return first_name, last_name


def clean_father_name(value):
    value = clean_text(value)

    if not value:
        return None

    value = re.sub(r"^(Mr\.?|Mrs\.?|Shri|Late)\s+", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip()

    return value.title()


def clean_class(value):
    if not value:
        return None

    value = value.strip().upper()

    classes = {
        "IX": "9",
        "X": "10",
        "XI": "11",
        "XII": "12"
    }

    if value in classes:
        return classes[value]

    match = re.search(r"\d+", value)

    if match:
        number = int(match.group())
        if 1 <= number <= 12:
            return str(number)

    return None


def clean_section(value):
    if not value:
        return None

    match = re.search(r"[A-D]", value.upper())

    if match:
        return match.group()

    return None


def clean_email(value):
    value = clean_text(value)

    if not value:
        return None

    value = value.lower()

    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if re.fullmatch(pattern, value):
        return value

    return None


def clean_dob(value):
    value = clean_text(value)

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%B %d %Y",
        "%b %d %Y",
        "%y.%m.%d"
    ]

    for fmt in formats:
        try:
            dob = datetime.strptime(value, fmt).date()

            if dob <= date.today():
                return dob

        except ValueError:
            pass

    return None


def clean_raw_data():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, code FROM schools")
    schools = {
        row["code"]: row["id"]
        for row in cursor.fetchall()
    }

    cursor.execute("SELECT * FROM raw_students ORDER BY raw_id")
    raw_students = cursor.fetchall()

    cursor.execute("DELETE FROM marks")
    cursor.execute("DELETE FROM rejected_students")
    cursor.execute("DELETE FROM students")

    seen_students = set()

    rows_read = 0
    cleaned_count = 0
    duplicate_count = 0
    rejected_count = 0

    for row in raw_students:
        rows_read += 1

        raw_id = row["raw_id"]
        school_code = clean_school_code(row["school_code"])
        roll_no = clean_roll_no(row["roll_no"])

        if not school_code or school_code not in schools:
            reason = "Invalid school code"
        elif roll_no is None:
            reason = "Invalid roll number"
        else:
            reason = None

        if reason:
            cursor.execute(
                "INSERT INTO rejected_students (raw_id, reason) VALUES (%s, %s)",
                (raw_id, reason)
            )
            rejected_count += 1
            continue

        school_id = schools[school_code]
        student_key = (school_id, roll_no)

        if student_key in seen_students:
            duplicate_count += 1
            continue

        first_name, last_name = clean_name(
            row["first_name"], row["last_name"]
        )

        father_name = clean_father_name(row["father_name"])
        class_value = clean_class(row["class"])
        section = clean_section(row["section"])
        email = clean_email(row["email"])
        dob = clean_dob(row["date_of_birth"])

        if not first_name:
            reason = "Missing first name"
        elif not class_value:
            reason = "Invalid class"
        elif not section:
            reason = "Invalid section"
        else:
            reason = None

        if reason:
            cursor.execute(
                "INSERT INTO rejected_students (raw_id, reason) VALUES (%s, %s)",
                (raw_id, reason)
            )
            rejected_count += 1
            continue

        cursor.execute(
            """
            INSERT INTO students
            (school_id, roll_no, first_name, last_name, father_name,
             class, section, email, date_of_birth)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                school_id, roll_no, first_name, last_name,
                father_name, class_value, section, email, dob
            )
        )

        seen_students.add(student_key)
        cleaned_count += 1

    connection.commit()
    cursor.close()
    connection.close()

    print("\nDATA CLEANING SUMMARY")
    print("Records read:", rows_read)
    print("Cleaned:", cleaned_count)
    print("Duplicates:", duplicate_count)
    print("Rejected:", rejected_count)


if __name__ == "__main__":
    clean_raw_data()
