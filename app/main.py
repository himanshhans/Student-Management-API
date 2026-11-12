from fastapi import FastAPI
from app.routers import students, marks, reports, auth

app = FastAPI()

app.include_router(auth.router)
app.include_router(students.router) #accepts only one router at a time
app.include_router(marks.router)
app.include_router(reports.router)
