from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    osu_user_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(String, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    token = relationship(
        "Token", back_populates="owner", uselist=False, cascade="all, delete-orphan"
    )
    submissions = relationship(
        "Submission", back_populates="user", cascade="all, delete-orphan"
    )

    def __init__(self, osu_user_id: int, username: str, is_active: bool = True):
        super().__init__()
        self.osu_user_id = osu_user_id
        self.username = username
        self.is_active = is_active
