from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth
from app.api.routes import businesses
from app.api.routes import recomendations
from app.api.routes import reviews
from app.api.routes import users
from app.database.base import Base
from app.database.session import engine


app = FastAPI(title="SISREC API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://127.0.0.1:5173",
		"http://localhost:5173",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/")
def root():
	return {"message": "SISREC API online"}


@app.on_event("startup")
def startup_create_tables():
	Base.metadata.create_all(bind=engine)


app.include_router(reviews.router)
app.include_router(users.router)
app.include_router(businesses.router)
app.include_router(recomendations.router)
app.include_router(auth.router)
