from fastapi import APIRouter

from app.database.session import SessionLocal
from app.models.business import Business
from app.models.user import User
from app.models.review import Review


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/test-counts")
def test_counts():
	session = SessionLocal()
	try:
		return {
			"businesses": session.query(Business).count(),
			"users": session.query(User).count(),
			"reviews": session.query(Review).count(),
		}
	finally:
		session.close()
