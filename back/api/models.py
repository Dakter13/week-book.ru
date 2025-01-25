from api.database import Base
from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Column, Date,
                        DateTime, ForeignKey, Integer, String, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Books(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    genre = Column(String(100))
    published_date = Column(String(10))
    isbn = Column(String(20), unique=True)
    google_book_id = Column(String(12), nullable=False)
    # Relationship to reviews
    reviews = relationship("Reviews", back_populates="book")


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    banned = Column(Boolean, default=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    # Relationship to reviews
    reviews = relationship("Reviews", back_populates="user")


class Reviews(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, CheckConstraint(
        "rating BETWEEN 1 AND 5"), nullable=False)
    review_text = Column(Text)
    public = Column(Boolean, default=False)
    #created_at = Column(DateTime, server_default=func.now())

    # Relationships
    book = relationship("Books", back_populates="reviews")
    user = relationship("Users", back_populates="reviews")
