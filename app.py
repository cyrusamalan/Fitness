from flask import Flask, render_template, request, redirect, flash, session, url_for
import psycopg2
import bcrypt
from datetime import datetime
from functools import wraps
from flask import make_response

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

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response
    return no_cache


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
@nocache
def dashboard():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')
    return render_template('dashboard.html', username=username)

@app.route('/settings')
@nocache
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

@app.route('/profile', methods=['GET', 'POST'])
@nocache
def profile():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    # Get user_id
    cur.execute("""
        SELECT u.user_id FROM users u
        JOIN authentication a ON u.user_id = a.user_id
        WHERE a.username = %s
    """, (username,))
    user_row = cur.fetchone()

    if not user_row:
        flash("❌ User not found.")
        return redirect('/dashboard')

    user_id = user_row[0]

    if request.method == 'POST':
        height_ft = request.form['height_ft']
        height_in = request.form['height_in']
        weight = request.form['weight']
        age = request.form['age']
        gender = request.form['gender'].upper()
        goal_weight = request.form['goal_weight']
        goal_type = request.form['goal_type']
        activity_level = request.form['activity_level']

        try:
            cur.execute("""
                INSERT INTO profile (user_id, height_ft, height_in, weight, age, gender, goal_weight, goal_type, activity_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET height_ft = EXCLUDED.height_ft,
                            height_in = EXCLUDED.height_in,
                            weight = EXCLUDED.weight,
                            age = EXCLUDED.age,
                            gender = EXCLUDED.gender,
                            goal_weight = EXCLUDED.goal_weight,
                            goal_type = EXCLUDED. goal_type,
                            activity_level = EXCLUDED.activity_level;
            """, (user_id, height_ft, height_in, weight, age, gender, goal_weight, goal_type, activity_level))
            conn.commit()
            flash("✅ Profile saved successfully!")
        except Exception as e:
            conn.rollback()
            flash(f"❌ Error saving profile: {str(e)}")
        finally:
            cur.close()
            conn.close()

        return redirect('/profile')

    # Handle GET: check if profile exists
    cur.execute("SELECT height_ft, height_in, weight, age, gender, goal_weight FROM profile WHERE user_id = %s", (user_id,))
    profile_row = cur.fetchone()
    cur.close()
    conn.close()

    if profile_row:
        height_ft, height_in, weight, age, gender, goal_weight= profile_row
        return render_template(
            'profile_view.html',
            username=username,
            height_ft=height_ft,
            height_in=height_in,
            weight=weight,
            age=age,
            gender=gender,
            goal_weight=goal_weight
        )
    else:
        return render_template('profile_form.html', username=username)


@app.route('/edit_profile', methods=['GET', 'POST'])
@nocache
def edit_profile():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    # Get user_id
    cur.execute("""
        SELECT u.user_id FROM users u
        JOIN authentication a ON u.user_id = a.user_id
        WHERE a.username = %s
    """, (username,))
    user_row = cur.fetchone()

    if not user_row:
        flash("❌ User not found.")
        return redirect('/dashboard')

    user_id = user_row[0]

    if request.method == 'POST':
        height_ft = request.form['height_ft']
        height_in = request.form['height_in']
        weight = request.form['weight']
        age = request.form['age']
        gender = request.form['gender'].upper()
        goal_weight = request.form['goal_weight']
        goal_type = request.form['goal_type']
        activity_level = request.form['activity_level']


        try:
            cur.execute("""
                UPDATE profile
                SET height_ft = %s,
                    height_in = %s,
                    weight = %s,
                    age = %s,
                    gender = %s,
                    goal_weight = %s,
                    goal_type = %s,
                    activity_level = %s
                WHERE user_id = %s
            """, (height_ft, height_in, weight, age, gender, goal_weight, goal_type, activity_level, user_id))
            conn.commit()
            flash("✅ Profile updated successfully!")
        except Exception as e:
            conn.rollback()
            flash(f"❌ Error updating profile: {str(e)}")
        finally:
            cur.close()
            conn.close()

        return redirect('/profile')

    # GET request: Pre-fill the form
    cur.execute("""
        SELECT height_ft, height_in, weight, age, gender, goal_weight
        FROM profile
        WHERE user_id = %s
    """, (user_id,))
    profile = cur.fetchone()
    cur.close()
    conn.close()

    if profile:
        return render_template(
            'profile_edit_form.html',
            username=username,
            height_ft=profile[0],
            height_in=profile[1],
            weight=profile[2],
            age=profile[3],
            gender=profile[4],
            goal_weight=profile[5]
        )
    else:
        flash("❌ No profile data to edit.")
        return redirect('/profile')
    


if __name__ == '__main__':
    app.run(debug=True)
