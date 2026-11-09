from pydantic import BaseModel, ConfigDict, Field, model_validator

class MarksCreate(BaseModel):
    subject: str = Field(min_length=2)
    exam: str = Field(min_length=2)
    marks_obtained: float | None = Field(ge=0, le=100, default=None)
    max_marks: float = Field(gt=0)
    is_absent: bool

    @model_validator(mode="after")
    def validate_marks(self):
        if self.marks_obtained is not None:
            if self.marks_obtained > self.max_marks:
                raise ValueError("Error! Marks obtained cannot be greater than maximum marks")
        return self

class MarksOut(MarksCreate):
    id: int
    student_id: int
    model_config = ConfigDict(from_attributes=True)

class MarksUpdate(BaseModel):
    subject: str | None = Field(min_length=2, default = None)
    exam: str | None = Field(min_length=2, default = None)
    marks_obtained: float | None = Field(ge=0, le=100, default=None)
    max_marks: float | None = Field(gt=0, default = None)
    is_absent: bool | None = None
