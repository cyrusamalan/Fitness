import bcrypt
import getpass
from datetime import datetime

def account(cur):
    first_name = input("First Name: ")
    last_name = input("Last Name: ")
    email = input("Email: ")
    phone_no = input("Phone Number (optional): ")
    if phone_no == '':
        phone_no = None

    cur.execute(
        "INSERT INTO users (first_name, last_name, email, phone_no) VALUES (%s, %s, %s, %s) RETURNING user_id;",
        (first_name, last_name, email, phone_no)
    )
    user_id = cur.fetchone()[0]
    return user_id

def create_acc(cur, user_id):
    username = input("Create your username: ")
    password = getpass.getpass("Create you1r password: ")
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    cur.execute(
        "INSERT INTO authentication (user_id, login_time, status, passkey, username) VALUES (%s, %s, %s, %s, %s)",
        (user_id, datetime.now(), True, hashed_password.decode('utf-8'), username)
    )
