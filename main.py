import psycopg2
from acc import account, create_acc
from login import login


# ---------------- Main Program ----------------

conn = psycopg2.connect(
    dbname="fitness",
    user="postgres",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

print("Welcome to the Fitness Tracker!")
print("1. Create account and log in")
print("2. Log in to existing account")
choice = input("Choose an option (1 or 2): ")

if choice == '1':
    user_id = account(cur)
    create_acc(cur, user_id)
    conn.commit()
    login(cur)
elif choice == '2':
    login(cur)
else:
    print("❌ Invalid option. Please run the program again and choose 1 or 2.")

cur.close()
conn.close()
