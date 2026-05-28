from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import hash_password

db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@appristine.in").first()

admin.password_hash = hash_password("Test@12345")

db.commit()
db.close()

print("Admin password reset done")