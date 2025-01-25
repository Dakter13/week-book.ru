import logging
import os

import requests
from dotenv import load_dotenv
from request import add_book, add_review, add_user, check_book, check_user
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (ApplicationBuilder, CallbackContext,
                          CallbackQueryHandler, CommandHandler, MessageHandler,
                          filters)

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "telegram_bot_token")
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "google_book_api_key")

# Dictionary to store reviews
REVIEWS = {}

# Configure logging to write to a file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),  # Logs to a file
        logging.StreamHandler(),  # Also logs to console
    ],
)

# Start command handler


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Добро пожаловать! Отправьте мне название книги или имя автора, и я найду для вас книги."
    )


# Function to search for books via Google Books API
def search_books(query):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "key": GOOGLE_BOOKS_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        return []


# Handle incoming messages
async def handle_message(update: Update, context: CallbackContext):
    query = update.message.text
    books = search_books(query)

    if not books:
        await update.message.reply_text(
            "Извините, я не смог найти книги, соответствующие вашему запросу."
        )
        return

    context.user_data["books"] = books

    message_text = "Выберите книгу для обзора:\n\n"
    keyboard = []
    row = []

    for i, book in enumerate(books, start=1):
        title = book["volumeInfo"].get("title", "Неизвестное название")
        authors = ", ".join(book["volumeInfo"].get("authors", ["Неизвестный автор"]))

        message_text += f"{i}. {title} - {authors}\n\n"

        row.append(InlineKeyboardButton(str(i), callback_data=f"book_{i - 1}"))

        if i % 5 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message_text, reply_markup=reply_markup)


# Handle button clicks
async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("book_"):  # Handle book selection
        index = int(data.split("_")[1])
        books = context.user_data.get("books", [])

        if books and 0 <= index < len(books):
            book = books[index]
            title = book["volumeInfo"].get("title", "Неизвестное название")
            authors = ", ".join(
                book["volumeInfo"].get("authors", ["Неизвестный автор"])
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "Добавить отзыв", callback_data=f"review_{index}"
                    ),
                    InlineKeyboardButton(
                        "Посмотреть отзывы", callback_data=f"showR_{index}"
                    ),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text(
                f"Вы выбрали: {title} - {authors}\nЧто вы хотите сделать?",
                reply_markup=reply_markup,
            )

    elif data.startswith("review_"):  # Handle adding a review
        await handle_review_request(update, context)

    elif data.startswith("showR_"):  # Handle showing reviews
        await show_reviews(update, context)

    else:
        await query.message.reply_text("Неизвестная команда.")


# Handle review requests
async def handle_review_request(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("review_"):  # Handle review logic
        index = int(data.split("_")[1])  # Extract the book index
        books = context.user_data.get("books", [])

        if books and 0 <= index < len(books):
            book = books[index]
            book_id = book["id"]
            # Store current book ID
            context.user_data["current_book_id"] = book_id

            # Send rating options
            keyboard = [
                [
                    InlineKeyboardButton(str(i), callback_data=f"rate_{i}")
                    for i in range(1, 6)
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text(
                "Оцените книгу от 1 до 5:",
                reply_markup=reply_markup,
            )
        else:
            await query.message.reply_text("Извините, выбранная книга недоступна.")


async def handle_rating(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("rate_"):  # Handle rating logic
        rating = int(data.split("_")[1])
        context.user_data["current_rating"] = rating  # Save the rating

        # Set review mode flag
        context.user_data["review_mode"] = True

        await query.message.reply_text(
            "Вы можете оставить отзыв для этой книги. Напишите свой отзыв."
        )


# Handle review submissions
async def handle_review_submission(update: Update, context: CallbackContext):
    if context.user_data.get("review_mode"):
        review = update.message.text
        google_book_id = context.user_data.get("current_book_id")
        rating = context.user_data.get("current_rating")
        tg_user_id = update.effective_user.id
        logging.info(f"id пользователя: {tg_user_id}")

        if google_book_id and rating:
            book_id = check_book(google_book_id)
            if book_id:
                logging.info(f"id book: {book_id}")
            else:
                book_id = add_book(google_book_id)
                logging.info(f"id book: {book_id}")

            reviews = context.user_data.setdefault("reviews", {})
            reviews[book_id] = reviews.get(book_id, []) + [
                {"rating": rating, "review": review}
            ]
            user_id = check_user(tg_user_id)
            if user_id:
                logging.info(f"id пользователя: {user_id}")
            else:
                user_id = add_user(tg_user_id)
                logging.info(f"id пользователя: {user_id}")
            response = add_review(book_id, user_id, rating, review)
            if response:
                logging.info(f"Отзыв добавлен в базу: {response}")
            else:
                logging.info(f"Не удалось добавить отзыв: {response}")
                logging.info(f"Не удалось добавить book_id: {book_id}")
                logging.info(f"Не удалось добавить user_id: {user_id}")
                logging.info(f"Не удалось добавить rating: {rating}")
                logging.info(f"Не удалось добавить review: {review}")

            # Reset the review mode flag
            context.user_data["review_mode"] = False
            context.user_data.pop("current_rating", None)
            print("user_id", update.effective_user.id)
            await update.message.reply_text("Ваш отзыв успешно сохранен!")
        else:
            await update.message.reply_text("Произошла ошибка. Попробуйте снова.")
    else:
        await handle_message(update, context)


# Show reviews for a book
async def show_reviews(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("showR_"):
        index = int(data.split("_")[1])
        books = context.user_data.get("books", [])

        if books and 0 <= index < len(books):
            book = books[index]
            book_id = book["id"]

            reviews = REVIEWS.get(book_id, [])
            if not reviews:
                await query.message.reply_text("Для этой книги пока нет отзывов.")
                return

            review_text = "\n\n".join([f"\u2022 {review}" for review in reviews])
            await query.message.reply_text(f"Отзывы для книги:\n\n{review_text}")
        else:
            await query.message.reply_text("Извините, выбранная книга недоступна.")


# Main function
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))

    # Register specific CallbackQueryHandlers
    app.add_handler(
        CallbackQueryHandler(handle_button, pattern="^(book_|review_|showR_)")
    )
    app.add_handler(CallbackQueryHandler(handle_rating, pattern="^rate_"))
    # Register MessageHandler for review submissions
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review_submission)
    )

    # Register fallback MessageHandler for other text input (search books)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Бот запущен...")

    app.run_polling()


if __name__ == "__main__":
    main()
