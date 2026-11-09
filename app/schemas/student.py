from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import date

class StudentCreate(BaseModel):
    school_id: int
    roll_no: int
    first_name: str
    last_name: str | None = None
    father_name: str | None = None
    class_name: str
    section: str
    email: EmailStr | None = None
    date_of_birth: date | None = None

    @field_validator("date_of_birth", mode="after")
    def validate_dob(cls, date_of_birth: date):
        if date_of_birth is not None:
            if date_of_birth > date.today():
                raise ValueError("Error! Date of Birth Cannot be in Future!")
        return date_of_birth

class StudentOut(StudentCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True, populate_by_name=True) #Read data from Python object attributes
    class_name: str = Field(alias="class") #Accept the Python field name even when an alias exists

class StudentUpdate(BaseModel):
    school_id: int | None = None
    roll_no: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    father_name: str | None = None
    class_name: str | None = None
    section: str | None = None
    email: EmailStr | None = None
    date_of_birth: date | None = None

    @field_validator("date_of_birth", mode="after")
    def validate_dob(cls, date_of_birth: date):
        if date_of_birth is not None:
            if date_of_birth > date.today():
                raise ValueError("Error! Date of Birth Cannot be in Future!")
        return date_of_birth

class StudentListResponse(BaseModel):
    items: list[StudentOut]
    page: int
    limit: int
    total: int