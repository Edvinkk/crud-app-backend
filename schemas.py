from pydantic import BaseModel

# Base schema with common attributes
class ItemBase(BaseModel):
    name: str
    description: str = None

# Schema for creating a new item
class ItemCreate(ItemBase):
    pass

# Schema for reading/returning an item (includes id)
class Item(ItemBase):
    id: int

    class Config:
        orm_mode = True