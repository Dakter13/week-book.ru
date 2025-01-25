from datetime import datetime

import requests

# URL of your FastAPI app
BASE_URL = "http://fast-api:80"


def add_book(google_book_id):
    endpoint = f"{BASE_URL}/api/books/"
    payload = {"google_book_id": google_book_id}

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        book_data = response.json()
        return book_data.get("id")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def check_book(google_book_id):
    endpoint = f"{BASE_URL}/books/{google_book_id}"

    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        book_data = response.json()
        return book_data.get("id")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def add_user(tg_user_id):
    endpoint = f"{BASE_URL}/api/users/"
    payload = {"telegram_id": tg_user_id}

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        user_data = response.json()
        return user_data.get("id")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def check_user(tg_user_id):
    endpoint = f"{BASE_URL}/api/users/{tg_user_id}"

    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        user_data = response.json()
        return user_data.get("id")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def add_review(book_id, user_id, rating, review_text, public=True):
    endpoint = f"{BASE_URL}/api/review/"

    payload = {
        "book_id": book_id,
        "user_id": user_id,
        "rating": rating,
        "review_text": review_text,
        "public": public,
    }

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if e.response:
            print(f"Error: {e.response.status_code} - {e.response.text}")
        else:
            print(f"Error: {e}")
        return None
