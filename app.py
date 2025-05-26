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

@app.route('/settings')
def settings():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.first_name, u.last_name, u.email, u.phone_no
        FROM users u
        JOIN authentication a ON u.user_id = a.user_id
        WHERE a.username = %s
    """, (username,))
    
    user_info = cur.fetchone()
    cur.close()
    conn.close()

    if user_info:
        first_name, last_name, email, phone_no = user_info
        return render_template(
            'settings.html',
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_no=phone_no
        )
    else:
        flash("❌ Could not load account info.")
        return redirect('/dashboard')
    
@app.route('/update_account', methods=['POST'])
def update_account():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    field = request.form['field']
    new_value = request.form.get(field)

    allowed_fields = ['first_name', 'last_name', 'email', 'phone_no', 'username', 'password']
    if field not in allowed_fields:
        flash("❌ Invalid field.")
        return redirect('/settings')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get the user_id from the session username
        cur.execute("""
            SELECT u.user_id FROM users u
            JOIN authentication a ON u.user_id = a.user_id
            WHERE a.username = %s
        """, (username,))
        user_id_result = cur.fetchone()

        if not user_id_result:
            flash("❌ User not found.")
            return redirect('/settings')

        user_id = user_id_result[0]

        if field == 'password':
            # Hash the new password before storing
            import bcrypt
            hashed_pw = bcrypt.hashpw(new_value.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("UPDATE authentication SET passkey = %s WHERE user_id = %s", (hashed_pw, user_id))
        elif field == 'username':
            cur.execute("UPDATE authentication SET username = %s WHERE user_id = %s", (new_value, user_id))
            session['username'] = new_value  # update session
        else:
            # Other fields go to the users table
            cur.execute(f"UPDATE users SET {field} = %s WHERE user_id = %s", (new_value, user_id))

        conn.commit()
        flash(f"✅ {field.replace('_', ' ').title()} updated successfully!")

    except Exception as e:
        conn.rollback()
        flash(f"❌ Error updating {field}: {str(e)}")

    finally:
        cur.close()
        conn.close()

    return redirect('/settings')


@app.route('/logout')
def logout():
    session.clear()
    flash("👋 You have been logged out.")
    return redirect('/')






if __name__ == '__main__':
    app.run(debug=True)
