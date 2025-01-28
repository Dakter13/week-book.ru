import logging
import os
from datetime import datetime
from typing import Annotated, List, Optional

import requests
from api import models
from api.database import SessionLocal, engine
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),  # Logs to a file
        logging.StreamHandler(),  # Also logs to console
    ],
)

load_dotenv()
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "google_book_api_key")

app = FastAPI()
models.Base.metadata.create_all(bind=engine)


class BookBase(BaseModel):
    id: int
    title: str
    author: str
    genre: Optional[str]
    published_date: Optional[str]
    google_book_id: str
    isbn: str

    class Config:
        orm_mode = True
        from_attributes = True


class CreateBook(BaseModel):
    google_book_id: str


class UserBase(BaseModel):
    id: int
    telegram_id: int
    banned: bool

    class Config:
        orm_mode = True
        from_attributes = True


class UserCreate(BaseModel):
    telegram_id: int


class ReviewBase(BaseModel):
    id: int
    book_id: int
    user_id: int
    rating: int
    review_text: Optional[str]
    public: bool
    # created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class ReviewCreate(BaseModel):
    book_id: int
    user_id: int
    rating: int
    review_text: Optional[str]
    public: bool
    # created_at: datetime


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
# Utility Function to Fetch Book Data from Google Books API


def fetch_book_data(google_book_id: str):
    url = f"""https://www.googleapis.com/books/v1/volumes/{
        google_book_id}?key={GOOGLE_BOOKS_API_KEY}"""
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(
            status_code=404, detail="Book not found in Google Books API"
        )

    data = response.json()
    volume_info = data.get("volumeInfo", {})

    return {
        "title": volume_info.get("title"),
        "author": ", ".join(volume_info.get("authors", [])),
        "genre": ", ".join(volume_info.get("categories", [])),
        "published_date": volume_info.get("publishedDate"),
        "google_book_id": google_book_id,
        "isbn": next(
            (
                identifier.get("identifier")
                for identifier in volume_info.get("industryIdentifiers", [])
                if identifier.get("type") == "ISBN_13"
            ),
            "Unknown",
        ),
    }


# Endpoint to Add Book to Database
@app.post("/api/books/", response_model=BookBase)
def add_book(create_book: CreateBook, db: Session = Depends(get_db)):
    book_data = fetch_book_data(create_book.google_book_id)

    db_book = (
        db.query(models.Books)
        .filter(models.Books.google_book_id == create_book.google_book_id)
        .first()
    )
    if db_book:
        raise HTTPException(
            status_code=400, detail="Book already exists in the database"
        )

    new_book = models.Books(
        title=book_data["title"],
        author=book_data["author"],
        genre=book_data.get("genre"),
        published_date=book_data.get("published_date"),
        google_book_id=book_data["google_book_id"],
        isbn=book_data["isbn"],
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    return new_book


@app.post("/api/review/", status_code=status.HTTP_201_CREATED)
async def create_reviews(review: ReviewCreate, db: db_dependency):
    book = db.query(models.Books).filter(models.Books.id == review.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    user = db.query(models.Users).filter(models.Users.id == review.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.banned:
        raise HTTPException(status_code=403, detail="User is banned")

    # Create a new review
    new_review = models.Reviews(
        book_id=review.book_id,
        user_id=review.user_id,
        rating=review.rating,
        review_text=review.review_text,
        public=review.public,
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return {"message": "Review created successfully", "review": new_review}


@app.post("/api/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: db_dependency):
    existing_user = (
        db.query(models.Users)
        .filter(models.Users.telegram_id == user.telegram_id)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this Telegram ID already exists.",
        )

    new_user = models.Users(telegram_id=user.telegram_id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserBase.from_orm(new_user)


@app.get("/books/{google_book_id}", status_code=status.HTTP_201_CREATED)
async def read_book(google_book_id: str, db: db_dependency):
    book = (
        db.query(models.Books)
        .filter(models.Books.google_book_id == google_book_id)
        .first()
    )
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.get("/api/users/{telegram_id}", status_code=status.HTTP_200_OK)
async def find_user(telegram_id: str, db: db_dependency):
    user = (
        db.query(models.Users).filter(models.Users.telegram_id == telegram_id).first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return user


@app.get("/reviews", response_model=List[ReviewBase])
def get_reviews(db: Session = Depends(get_db)):
    reviews = db.query(models.Reviews).all()
    return reviews
