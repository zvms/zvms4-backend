from enum import Enum
from bson import ObjectId
from pydantic import BaseModel


class UserSex(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class UserPosition(str, Enum):
    student = "student"
    secretary = "secretary"
    department = "department"
    auditor = "auditor"
    admin = "admin"
    system = "system"


class UserLogin(BaseModel):
    id: str
    credential: str


class User(BaseModel):
    _id: str
    id: int
    name: str
    sex: UserSex
    group: list[str]


class UserActivityTimeSums(BaseModel):
    onCampus: float
    offCampus: float
    socialPractice: float
    trophy: float
