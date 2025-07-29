from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    username: str
    osu_user_id: int


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
