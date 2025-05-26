import bcrypt
import getpass

def login(cur):
    print("\n--- Login ---")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    cur.execute("SELECT passkey FROM authentication WHERE username = %s", (username,))
    result = cur.fetchone()

    if result:
        stored_hash = result[0].encode('utf-8')
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            print("✅ Login successful!")
        else:
            print("❌ Invalid password.")
            for i in range(1,5):
                i = i + 1
                password = getpass.getpass("Please Try Again: ")
                cur.execute("SELECT passkey FROM authentication WHERE username = %s", (username,))
                result = cur.fetchone()
                if result:
                    stored_hash = result[0].encode('utf-8')
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                        print("✅ Login successful!")
                        break
    else:
        print("❌ Username not found.")