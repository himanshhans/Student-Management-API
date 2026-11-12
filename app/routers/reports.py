from fastapi import APIRouter, HTTPException, Query, Depends

from app.database import get_connection
from app.utils.grading import calculate_grade, calculate_percentage
from app.utils.security import get_authenticated_user


router = APIRouter(tags=["Reports"])


# 1. STUDENT REPORT CARD

@router.get("/students/{student_id}/report-card")
def get_report_card(
    student_id: int,
    exam: str = Query(...),
    user=Depends(get_authenticated_user)
):
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        # Verify student belongs to authenticated school
        cursor.execute(
            """
            SELECT * FROM students
            WHERE id = %s
            AND school_id = %s
            AND is_active = 1;
            """,
            (student_id, user["school_id"])
        )

        student = cursor.fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        cursor.execute(
            """
            SELECT subject, marks_obtained, max_marks, is_absent
            FROM marks
            WHERE student_id = %s AND exam = %s;
            """,
            (student_id, exam)
        )

        subjects = cursor.fetchall()

        if not subjects:
            raise HTTPException(
                status_code=404,
                detail="No marks found for this exam"
            )

        total_obtained = 0
        total_maximum = 0
        subject_results = []
        passed = True

        for subject in subjects:

            obtained = subject["marks_obtained"]
            maximum = float(subject["max_marks"])

            if subject["is_absent"] or obtained is None:
                obtained = 0
            else:
                obtained = float(obtained)

            percentage = calculate_percentage(obtained, maximum)
            grade = calculate_grade(percentage)

            if percentage < 33:
                passed = False

            total_obtained += obtained
            total_maximum += maximum

            subject_results.append({
                "subject": subject["subject"],
                "marks_obtained": obtained,
                "max_marks": maximum,
                "percentage": percentage,
                "grade": grade,
                "result": "Pass" if percentage >= 33 else "Fail"
            })

        overall_percentage = calculate_percentage(
            total_obtained,
            total_maximum
        )

        return {
            "student": student,
            "exam": exam,
            "subjects": subject_results,
            "total_obtained": total_obtained,
            "total_maximum": total_maximum,
            "percentage": overall_percentage,
            "grade": calculate_grade(overall_percentage),
            "result": "Pass" if passed else "Fail"
        }

    finally:
        cursor.close()
        connection.close()


# 2. CLASS TOPPERS

@router.get("/reports/toppers")
def get_toppers(
    exam: str = Query(...),
    limit: int = Query(default=3, ge=1, le=100),
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            WITH student_percentages AS (
                SELECT
                    s.id,
                    s.first_name,
                    s.last_name,
                    s.class,
                    s.section,

                    SUM(
                        CASE
                            WHEN m.is_absent = 1
                            OR m.marks_obtained IS NULL
                            THEN 0
                            ELSE m.marks_obtained
                        END
                    ) AS total_obtained,

                    SUM(m.max_marks) AS total_maximum,

                    ROUND(
                        SUM(
                            CASE
                                WHEN m.is_absent = 1
                                OR m.marks_obtained IS NULL
                                THEN 0
                                ELSE m.marks_obtained
                            END
                        ) / NULLIF(SUM(m.max_marks), 0) * 100,
                        2
                    ) AS percentage

                FROM students s
                JOIN marks m ON s.id = m.student_id

                WHERE m.exam = %s
                AND s.school_id = %s
                AND s.is_active = 1

                GROUP BY
                    s.id, s.first_name, s.last_name,
                    s.class, s.section
            ),

            ranked_students AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY class
                        ORDER BY percentage DESC, id ASC
                    ) AS position
                FROM student_percentages
            )

            SELECT *
            FROM ranked_students
            WHERE position <= %s
            ORDER BY class, position;
            """,
            (exam, user["school_id"], limit)
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# 3. SUBJECT TOPPERS

@router.get("/reports/subject-toppers")
def get_subject_toppers(
    exam: str = Query(...),
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            WITH subject_scores AS (
                SELECT
                    s.id,
                    s.first_name,
                    s.last_name,
                    s.class,
                    m.subject,

                    ROUND(
                        CASE
                            WHEN m.is_absent = 1
                            OR m.marks_obtained IS NULL
                            THEN 0
                            ELSE m.marks_obtained /
                                 NULLIF(m.max_marks, 0) * 100
                        END,
                        2
                    ) AS percentage

                FROM students s
                JOIN marks m ON s.id = m.student_id

                WHERE m.exam = %s
                AND s.school_id = %s
                AND s.is_active = 1
            ),

            ranked_scores AS (
                SELECT *,
                    RANK() OVER (
                        PARTITION BY subject
                        ORDER BY percentage DESC
                    ) AS position
                FROM subject_scores
            )

            SELECT *
            FROM ranked_scores
            WHERE position = 1
            ORDER BY subject;
            """,
            (exam, user["school_id"])
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# 4. CLASS AVERAGE

@router.get("/reports/class-average")
def get_class_average(
    class_name: int = Query(..., alias="class", ge=1, le=12),
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                m.subject,

                AVG(
                    CASE
                        WHEN m.is_absent = 1
                        OR m.marks_obtained IS NULL
                        THEN 0
                        ELSE m.marks_obtained
                    END
                ) AS average_marks,

                AVG(m.max_marks) AS average_max_marks

            FROM marks m
            JOIN students s ON s.id = m.student_id

            WHERE s.class = %s
            AND s.school_id = %s
            AND s.is_active = 1

            GROUP BY m.subject
            ORDER BY m.subject;
            """,
            (str(class_name), user["school_id"])
        )

        results = cursor.fetchall()

        for row in results:
            row["average_marks"] = round(
                float(row["average_marks"]), 2
            )

            row["average_max_marks"] = round(
                float(row["average_max_marks"]), 2
            )

        return results

    finally:
        cursor.close()
        connection.close()


# 5. CLASS RANK LIST

@router.get("/reports/rank-list")
def get_rank_list(
    class_name: int = Query(..., alias="class", ge=1, le=12),
    exam: str = Query(...),
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            WITH student_percentages AS (
                SELECT
                    s.id,
                    s.first_name,
                    s.last_name,
                    s.roll_no,
                    s.class,

                    SUM(
                        CASE
                            WHEN m.is_absent = 1
                            OR m.marks_obtained IS NULL
                            THEN 0
                            ELSE m.marks_obtained
                        END
                    ) AS total_obtained,

                    SUM(m.max_marks) AS total_maximum,

                    ROUND(
                        SUM(
                            CASE
                                WHEN m.is_absent = 1
                                OR m.marks_obtained IS NULL
                                THEN 0
                                ELSE m.marks_obtained
                            END
                        ) / NULLIF(SUM(m.max_marks), 0) * 100,
                        2
                    ) AS percentage

                FROM students s
                JOIN marks m ON s.id = m.student_id

                WHERE s.class = %s
                AND m.exam = %s
                AND s.school_id = %s
                AND s.is_active = 1

                GROUP BY
                    s.id, s.first_name, s.last_name,
                    s.roll_no, s.class
            )

            SELECT *,
                RANK() OVER (
                    ORDER BY percentage DESC
                ) AS student_rank

            FROM student_percentages
            ORDER BY student_rank, roll_no;
            """,
            (str(class_name), exam, user["school_id"])
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# 6. FAILING STUDENTS

@router.get("/reports/failing")
def get_failing_students(
    exam: str = Query(...),
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                s.id,
                s.first_name,
                s.last_name,
                s.class,
                s.section,
                m.subject,
                m.marks_obtained,
                m.max_marks,

                CASE
                    WHEN m.is_absent = 1
                    OR m.marks_obtained IS NULL
                    THEN 0

                    ELSE ROUND(
                        m.marks_obtained /
                        NULLIF(m.max_marks, 0) * 100,
                        2
                    )
                END AS percentage

            FROM students s
            JOIN marks m ON s.id = m.student_id

            WHERE m.exam = %s
            AND s.school_id = %s
            AND s.is_active = 1

            AND (
                m.is_absent = 1
                OR m.marks_obtained IS NULL
                OR m.marks_obtained /
                   NULLIF(m.max_marks, 0) * 100 < 33
            )

            ORDER BY s.class, s.roll_no;
            """,
            (exam, user["school_id"])
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# 7. STUDENT IMPROVEMENT

@router.get("/reports/improvement")
def get_improvement(
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                s.id,
                s.first_name,
                s.last_name,
                s.class,

                ROUND(
                    SUM(
                        CASE
                            WHEN m.exam = 'Mid-Term'
                            AND m.is_absent = 0
                            AND m.marks_obtained IS NOT NULL
                            THEN m.marks_obtained
                            ELSE 0
                        END
                    ) /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN m.exam = 'Mid-Term'
                                THEN m.max_marks
                                ELSE 0
                            END
                        ),
                        0
                    ) * 100,
                    2
                ) AS midterm_percentage,

                ROUND(
                    SUM(
                        CASE
                            WHEN m.exam = 'Final'
                            AND m.is_absent = 0
                            AND m.marks_obtained IS NOT NULL
                            THEN m.marks_obtained
                            ELSE 0
                        END
                    ) /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN m.exam = 'Final'
                                THEN m.max_marks
                                ELSE 0
                            END
                        ),
                        0
                    ) * 100,
                    2
                ) AS final_percentage

            FROM students s
            JOIN marks m ON s.id = m.student_id

            WHERE s.school_id = %s
            AND s.is_active = 1
            AND m.exam IN ('Mid-Term', 'Final')

            GROUP BY
                s.id, s.first_name, s.last_name, s.class

            HAVING midterm_percentage IS NOT NULL
            AND final_percentage IS NOT NULL
            AND final_percentage > midterm_percentage

            ORDER BY
                (final_percentage - midterm_percentage) DESC;
            """,
            (user["school_id"],)
        )

        results = cursor.fetchall()

        for row in results:
            row["improvement"] = round(
                float(row["final_percentage"]) -
                float(row["midterm_percentage"]),
                2
            )

        return results

    finally:
        cursor.close()
        connection.close()


# 8. STUDENTS WITHOUT MARKS

@router.get("/reports/no-marks")
def get_students_without_marks(
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                s.id,
                s.roll_no,
                s.first_name,
                s.last_name,
                s.father_name,
                s.class,
                s.section

            FROM students s
            LEFT JOIN marks m ON s.id = m.student_id

            WHERE s.is_active = 1
            AND s.school_id = %s
            AND m.id IS NULL

            ORDER BY s.class, s.roll_no;
            """,
            (user["school_id"],)
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# 9. DATA QUALITY REPORT

@router.get("/reports/data-quality")
def get_data_quality(
    user=Depends(get_authenticated_user)
):

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_students,

                SUM(
                    CASE
                        WHEN last_name IS NULL
                        OR TRIM(last_name) = ''
                        THEN 1 ELSE 0
                    END
                ) AS missing_last_name,

                SUM(
                    CASE
                        WHEN father_name IS NULL
                        OR TRIM(father_name) = ''
                        THEN 1 ELSE 0
                    END
                ) AS missing_father_name,

                SUM(
                    CASE
                        WHEN email IS NULL
                        OR TRIM(email) = ''
                        THEN 1 ELSE 0
                    END
                ) AS missing_email

            FROM students
            WHERE school_id = %s;
            """,
            (user["school_id"],)
        )

        student_quality = cursor.fetchone()

        # NOTE:
        # rejected_students is not school-scoped here because
        # its table schema has not been provided.
        # Do not expose this global count in a multi-school API.

        return {
            "student_data_quality": student_quality
        }

    finally:
        cursor.close()
        connection.close()