from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.user import User
from app.security import hash_password

DEMO_USERS = [
    ("admin@lotto.local", "admin12345", "Admin", "admin"),
    ("demo@lotto.local", "demo12345", "Demo User", "user"),
]


def ensure_demo_users(db: Session) -> None:
    for email, password, display_name, role in DEMO_USERS:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is None:
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    display_name=display_name,
                    role=role,
                )
            )
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as s:
        ensure_demo_users(s)
        print("Demo users ensured: admin@lotto.local / demo@lotto.local")
