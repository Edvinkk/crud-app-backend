import logging
import csv
import io
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
import models, schemas
from database import SessionLocal, engine
from fastapi.middleware.cors import CORSMiddleware

# Write logs beside this file, regardless of where the server is started.
logging.basicConfig(
    filename=Path(__file__).with_name("server.log"),
    encoding="utf-8",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
)

# Create all tables in the database
models.Base.metadata.create_all(bind=engine)

# Create the FastAPI application
app = FastAPI()

# Add CORS middleware to allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React's default port
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE - Add a new item
@app.post("/items/", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = models.Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    logging.info("CREATE: id=%s, item=%s", db_item.id, item)
    return db_item

# Upload a CSV with name and description columns.
@app.post("/items/import-csv", response_model=list[schemas.Item], status_code=201)
def import_csv(content: bytes = Body(media_type="text/csv"), db: Session = Depends(get_db)):
    try:
        # Turn the uploaded bytes into text. utf-8-sig also handles an Excel UTF-8 marker.
        text = content.decode("utf-8-sig")
        # Use the first line as column names, so each row has "name" and "description" keys.
        reader = csv.DictReader(io.StringIO(text), strict=True)
        # Check that the file has the two expected columns in this order.
        if reader.fieldnames != ["name", "description"]:
            raise ValueError("Use name,description as the first line")

        items = []
        for row in reader:
            # Read both values and remove spaces from the beginning and end.
            name = (row["name"] or "").strip()
            description = (row["description"] or "").strip()
            # Reject empty values or extra columns (DictReader stores extra columns under None).
            if not name or not description or None in row:
                raise ValueError("Each row needs a name and description")
            # Prepare a database item. It is not saved yet.
            items.append(models.Item(name=name, description=description))

        # A file with only headers has no items to import.
        if not items:
            raise ValueError("The CSV has no items")
    except (ValueError, csv.Error):
        # Send an error response if the CSV cannot be read or has invalid values.
        raise HTTPException(status_code=400, detail="Invalid CSV. Use name,description and fill in both values.")

    try:
        # Save all the prepared items together, after the whole file has been checked.
        db.add_all(items)
        db.commit()
    except Exception:
        # Undo this import if the database save fails.
        db.rollback()
        raise

    # Record the import and send the saved items back to React.
    logging.info("CSV IMPORT: imported %s items", len(items))
    return items


# READ - Get all items
@app.get("/items/", response_model=list[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(models.Item).offset(skip).limit(limit).all()
    logging.info("READ ALL: skip=%s, limit=%s, returned=%s", skip, limit, len(items))
    return items

# READ - Get a single item by ID
@app.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item is None:
        logging.warning("READ: item id=%s not found", item_id)
        raise HTTPException(status_code=404, detail="Item not found")
    logging.info("READ: id=%s", item_id)
    return item

# UPDATE - Update an existing item
@app.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item is None:
        logging.warning("UPDATE: item id=%s not found", item_id)
        raise HTTPException(status_code=404, detail="Item not found")

    for field, value in item.dict().items()
        setattr(db_item, field, value)

    db.commit()
    db.refresh(db_item)
    logging.info("UPDATE: id=%s, item=%s", item_id, item)
    return db_item

# DELETE - Remove an item
@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item is None:
        logging.warning("DELETE: item id=%s not found", item_id)
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    logging.info("DELETE: id=%s", item_id)
    return {"message": "Item deleted successfully"}
