from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_osu_id(db: Session, osu_user_id: int):
    return db.query(User).filter(User.osu_user_id == osu_user_id).first()


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(osu_user_id=user.osu_user_id, username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
