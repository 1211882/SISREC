from fastapi import APIRouter, Query

from app.database.session import SessionLocal
from app.models.user import User


router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(
	limit: int = Query(default=20, ge=1, le=100),
	offset: int = Query(default=0, ge=0),
):
	session = SessionLocal()
	try:
		users = session.query(User).offset(offset).limit(limit).all()

		return [
			{
				"user_id": user.user_id,
				"name": user.name,
				"age": user.age,
				"gender": user.gender,
			}
			for user in users
		]
	finally:
		session.close()
