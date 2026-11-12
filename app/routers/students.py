from fastapi import APIRouter, HTTPException, Query, Depends
from app.database import get_connection
from app.schemas.student import StudentCreate, StudentOut, StudentUpdate, StudentListResponse
from app.utils.logger import logger
from app.utils.security import get_authenticated_user, require_admin
import mysql.connector

router = APIRouter(
    prefix="/students",
    tags=["Students"]
)

@router.post("/", response_model=StudentOut, status_code=201)
def create_student(student: StudentCreate, user = Depends(require_admin)):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("INSERT INTO students (school_id, roll_no, first_name, last_name, father_name, `class`, section, email, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);", (student.school_id, student.roll_no, student.first_name, student.last_name, student.father_name, student.class_name, student.section, student.email, student.date_of_birth)) #we use placeholders as %s and insert values in a tuple to prevent sql injection attacks, we can use a list as well
        connection.commit() # Saves changes permanently
        student_id = cursor.lastrowid
        logger.info(f"Student Record with ID: {student_id} Created successfully")
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        new_student = cursor.fetchone()
    except Exception as e:
        logger.exception("Failed to create Student Record")
        raise HTTPException(status_code=500)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    return new_student

@router.get("/", response_model=StudentListResponse)
def get_all_students(page: int = Query(default=1, ge=1),
                    limit: int = Query(default=20, ge=1, le=100),
                    search: str | None = Query(default=None),
                    class_name: int | None = Query(default=None, alias="class", ge=1, le=12),
                    section: str | None = Query(default=None),
                    sort: str = Query(default="id"),
                    include_inactive: bool = Query(default=False),
                    authenticated_user = Depends(get_authenticated_user)
                ):
    connection = None
    cursor = None
    try:
        conditions = []
        values = []
        conditions.append("school_id = %s")
        values.append(authenticated_user["school_id"])
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        asc_or_dsc = "ASC"
        sort_by = ("id", "first_name", "last_name", "roll_no")
        sort_dsc = sort.strip().startswith("-") #this is a flag
        sort_col_name = sort.strip().lstrip("-")
        if sort_dsc is True:
            asc_or_dsc = "DESC"
        if sort_col_name not in sort_by:
            logger.warning(f"User tried to sort by {sort_col_name} which is invalid!")
            raise HTTPException(
                status_code=400,
                detail="You can only sort by id, first_name, last_name or roll_no"
            )
        if search is not None:
            search_term = f"%{search}%"
            conditions.append("(first_name LIKE %s OR last_name LIKE %s OR father_name LIKE %s)")
            values.extend([search_term]*3)
        if class_name is not None:
            conditions.append("`class` = %s")
            values.append(str(class_name))
        if section is not None:
            conditions.append("section = %s")
            values.append(section.capitalize())
        if include_inactive is False:
            conditions.append("is_active = 1")
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        offset = (page -1) * limit
        cursor.execute(f"SELECT * FROM students {where_clause} ORDER BY {sort_col_name} {asc_or_dsc} LIMIT %s OFFSET %s;", (tuple(values)+(limit, offset)))
        items = cursor.fetchall()
        cursor.execute(f"SELECT COUNT(*) AS total FROM students {where_clause};", tuple(values))
        total_dict = cursor.fetchone()
        total = total_dict["total"]
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    logger.info(f"User successfully accessed page: {page} and a total of {total} records were retrieved")
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total
    }

@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, user = Depends(get_authenticated_user)):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id = %s AND school_id = %s;", (student_id, user["school_id"]))
        student = cursor.fetchone()
    except Exception as e:
        logger.exception("Failed to fetch Student Record")
        raise HTTPException(status_code=500)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    if student is None:
        logger.warning("Student doesn't exist!")
        raise HTTPException(
            status_code=404,
            detail="Student Not Found"
        )
    logger.info(f"Student record with {student_id} retrieved successfully!")
    return student

@router.put("/{student_id}", response_model=StudentOut)
def update_student_completely(student_id: int, student: StudentCreate, user = Depends(require_admin)):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        is_student = cursor.fetchone()
        if is_student is None:
            logger.warning("Student record doesn't exist!")
            raise HTTPException(
                status_code=404,
                detail="Student Not Found"
            )
        cursor.execute("UPDATE students SET school_id = %s, roll_no = %s, first_name = %s, last_name = %s, father_name = %s, `class` = %s, section = %s, email = %s, date_of_birth = %s WHERE id = %s;", (student.school_id, student.roll_no, student.first_name, student.last_name, student.father_name, student.class_name, student.section, student.email, student.date_of_birth, student_id))
        connection.commit()
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        updated_student = cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    logger.info(f"Student Record with ID: {student_id} updated successfully!")
    return updated_student

@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, student: StudentUpdate, user = Depends(require_admin)):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        is_student = cursor.fetchone()
        if is_student is None:
            raise HTTPException(
                status_code=404,
                detail="Student Not Found"
            )
        update_data = student.model_dump(exclude_unset=True) #this allows us to input only the fields entered by the user
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )
        updated_fields = []
        updated_values = []
        for key, value in update_data.items():
            updated_fields.append(f"{key} = %s")
            updated_values.append(value)
        fields = ", ".join(updated_fields)
        updated_values.append(student_id)
        query = f"UPDATE students SET {fields} WHERE id = %s;"
        cursor.execute(query, tuple(updated_values))
        connection.commit()
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        updated_student = cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    logger.info(f"Student Record with ID: {student_id} updated successfully!")
    return updated_student

@router.delete("/{student_id}", status_code=200)
def soft_delete(student_id: int, user = Depends(require_admin)):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        is_student = cursor.fetchone()
        if is_student is None:
            logger.warning("Student doesn't exist!")
            raise HTTPException(
                status_code=404,
                detail="Student Not Found"
            )
        elif is_student["is_active"] == 0:
            logger.warning("Student is already inactive!")
            HTTPException(
            status_code=409,
            detail="Student is already inactive"
        )
        else:
            cursor.execute("UPDATE students SET is_active = 0 WHERE id = %s;", (student_id,))
            connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    logger.info(f"Student Record with ID: {student_id} set to inactive successfully!")
    return {"message": "Student deleted successfully"}