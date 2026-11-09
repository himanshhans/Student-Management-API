from fastapi import APIRouter, HTTPException
from app.database import get_connection
from app.schemas.marks import MarksCreate, MarksOut, MarksUpdate
import mysql.connector

router = APIRouter(
    tags=["Marks"]
)

@router.post("/students/{student_id}/marks", response_model=MarksOut, status_code=201) #this establishes an api level relationship between marks and students
def enter_marks(student_id: int, marks: MarksCreate):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        is_student = cursor.fetchone()
        if is_student is None:
            raise HTTPException(
                status_code=404,
                detail="Student doesn't exist"
            )
        cursor.execute("INSERT INTO marks (student_id, subject, exam, marks_obtained, max_marks, is_absent) VALUES (%s, %s, %s, %s, %s, %s);", (student_id, marks.subject, marks.exam, marks.marks_obtained, marks.max_marks, marks.is_absent))
        connection.commit()
        inserted_marks_id = cursor.lastrowid
        cursor.execute("SELECT * FROM marks WHERE id = %s;", (inserted_marks_id, ))
        inserted_marks = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return inserted_marks

@router.get("/students/{student_id}/marks", response_model=list[MarksOut])
def get_marks(student_id: int):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        is_student = cursor.fetchone()
        if is_student is None:
            raise HTTPException(
                status_code=404,
                detail="Student doesn't exist"
            )
        cursor.execute("SELECT * FROM marks WHERE student_id = %s;", (student_id,))
        marks_list = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    return marks_list

@router.patch("/marks/{id}", response_model=MarksOut)
def update_marks(id: int, marks: MarksUpdate):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM marks WHERE id = %s;", (id,))
        is_marks =  cursor.fetchone()
        if is_marks is None:
            raise HTTPException(
                status_code=404,
                detail="Record doesn't exist"
            )
        updated_data = marks.model_dump(exclude_unset=True)
        if not updated_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        if "marks_obtained" in updated_data:
            final_marks_obtained = updated_data["marks_obtained"]
        else:
            final_marks_obtained = is_marks["marks_obtained"]

        if "max_marks" in updated_data:
            final_max_marks = updated_data["max_marks"]
        else:
            final_max_marks = is_marks["max_marks"]

        # Validate max_marks
        if final_max_marks is None:
            raise HTTPException(
                status_code=422,
                detail="Maximum marks cannot be NULL"
            )

        # Validate obtained marks
        if final_marks_obtained is not None:
            if final_marks_obtained > final_max_marks:
                raise HTTPException(
                    status_code=422,
                    detail="Marks obtained cannot be greater than maximum marks!"
                )
        updated_details = []
        updated_values = []
        for key, value in updated_data.items():
            updated_details.append(f"{key} = %s")
            updated_values.append(value)
        fields = ", ".join(updated_details)
        updated_values.append(id)
        query = f"UPDATE marks SET {fields} WHERE id = %s;"
        cursor.execute(query, tuple(updated_values))
        connection.commit()
        cursor.execute("SELECT * FROM marks WHERE id = %s;", (id,))
        updated_marks = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return updated_marks

@router.delete("/marks/{id}", status_code=204)
def delete_marks(id: int):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM marks WHERE id = %s;", (id,))
        is_marks =  cursor.fetchone()
        if is_marks is None:
            raise HTTPException(
                status_code=404,
                detail="Record doesn't exist"
            )
        cursor.execute("DELETE FROM marks WHERE id = %s;", (id,))
        connection.commit()
    finally:
        cursor.close()
        connection.close()
