from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="My Backend API")


class Item(BaseModel):
    name: str
    price: float


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/version")
def health_check():
    return {"version": "0.1.0"}


@app.post("/items", response_model=Item)
def create_item(item: Item) -> Item:
    return item