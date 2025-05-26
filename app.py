from flask import Flask, render_template, request, redirect, flash, session, url_for
import psycopg2
import bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # used for flashing messages

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        dbname="fitness",
        user="postgres",
        host="localhost",
        port="5432"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    conn = get_db_connection()
    cur = conn.cursor()

    # Get form data
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone_no = request.form['phone_no'] or None
    username = request.form['username']
    password = request.form['password']

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        # Insert into users table and get user_id
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, phone_no)
            VALUES (%s, %s, %s, %s) RETURNING user_id;
        """, (first_name, last_name, email, phone_no))
        user_id = cur.fetchone()[0]

        # Insert into authentication table
        cur.execute("""
            INSERT INTO authentication (user_id, login_time, status, passkey, username)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, datetime.now(), True, hashed_password.decode('utf-8'), username))

        conn.commit()
        flash("✅ Account created successfully!")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Signup failed: {str(e)}")
    finally:
        cur.close()
        conn.close()

    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT passkey FROM authentication WHERE username = %s", (username,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if result:
        stored_hash = result[0].encode('utf-8')
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            # ✅ Store username in session and redirect to dashboard
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid password.")
    else:
        flash("❌ Username not found.")

    return redirect('/')

@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')
    return render_template('dashboard.html', username=username)

if __name__ == '__main__':
    app.run(debug=True)
