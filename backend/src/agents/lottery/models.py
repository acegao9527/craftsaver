from typing import List
from pydantic import BaseModel

class ParticipantList(BaseModel):
    names: List[str]

class WinnerList(BaseModel):
    winners: List[str]
