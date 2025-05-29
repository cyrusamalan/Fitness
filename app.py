from flask import Flask, render_template, request, redirect, flash, session, url_for
import psycopg2
import bcrypt
from datetime import datetime
from functools import wraps
from flask import make_response
from calendar import monthrange, Calendar
from datetime import datetime

def insert_goals(cur, user_id, weight, height_ft, height_in, age, gender, goal_type, activity_level):
    total_height_cm = height_ft * 30.48 + height_in * 2.54
    weight_kg = weight * 0.453592

    if gender == 'M':
        bmr = 10 * weight_kg + 6.25 * total_height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * total_height_cm - 5 * age - 161

    activity_factors = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    multiplier = activity_factors.get(activity_level, 1.55)
    maintenance_calories = int(bmr * multiplier)

    # Adjust daily calories based on goal type (even though it's not stored)
    if goal_type == 'cut':
        daily_calories = maintenance_calories - 500
    elif goal_type == 'bulk':
        daily_calories = maintenance_calories + 500
    else:
        daily_calories = maintenance_calories

    # Macronutrient distribution
    daily_protein = int(weight * 0.7)  
    daily_fats = int((daily_calories * 0.2) / 9)   # 20% of calories → grams of fat
    daily_carbs = int((daily_calories * 0.25) / 4) 

    # Insert into or update goals table
    cur.execute("""
        INSERT INTO goals (
            user_id, daily_calories, daily_protein, daily_carbs, daily_fats,
            maintenance_calories, gain_weight_calories, lose_weight_calories
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET
            daily_calories = EXCLUDED.daily_calories,
            daily_protein = EXCLUDED.daily_protein,
            daily_carbs = EXCLUDED.daily_carbs,
            daily_fats = EXCLUDED.daily_fats,
            maintenance_calories = EXCLUDED.maintenance_calories,
            gain_weight_calories = EXCLUDED.gain_weight_calories,
            lose_weight_calories = EXCLUDED.lose_weight_calories;
    """, (
        user_id,
        daily_calories,
        daily_protein,
        daily_carbs,
        daily_fats,
        maintenance_calories,
        maintenance_calories + 500,
        maintenance_calories - 500
    ))


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

    conn = get_db_connection()
    cur = conn.cursor()

    # Get user_id
    cur.execute("""
        SELECT user_id FROM authentication WHERE username = %s
    """, (username,))
    user_row = cur.fetchone()
    if not user_row:
        flash("❌ User not found.")
        return redirect('/')
    user_id = user_row[0]

    # After getting user_id
    cur.execute("""
        SELECT daily_calories FROM goals WHERE user_id = %s
    """, (user_id,))
    goal_row = cur.fetchone()
    daily_calories = goal_row[0] if goal_row else 0

    cur.execute("""
        SELECT COALESCE(SUM(calories), 0)
        FROM macros
        WHERE user_id = %s AND date_added = CURRENT_DATE
    """, (user_id,))
    total_row = cur.fetchone()
    total_calories = total_row[0]

    remaining_calories = max(0, daily_calories - total_calories)
    today_str = datetime.today().strftime("%B %d")  # e.g., "May 28"


    # Get goal calories
    cur.execute("SELECT daily_calories FROM goals WHERE user_id = %s", (user_id,))
    goal_row = cur.fetchone()
    daily_calories = goal_row[0] if goal_row else 0

    # ✅ Get total calories logged today
    cur.execute("""
        SELECT SUM(calories)
        FROM macros
        WHERE user_id = %s AND date_added = CURRENT_DATE
    """, (user_id,))
    result = cur.fetchone()
    current_calories = result[0] if result[0] is not None else 0

    percent_eaten = round(current_calories / daily_calories * 100, 1) if daily_calories else 0

    cur.close()
    conn.close()

    return render_template('dashboard.html',
                           username=username,
                           current_calories=current_calories,
                           daily_calories=daily_calories,
                           percent_eaten=percent_eaten,
                           remaining_calories=remaining_calories,
                           today_str=today_str
                           )



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

            insert_goals(
            cur,
            user_id=user_id,
            weight=int(weight),
            height_ft=int(height_ft),
            height_in=int(height_in),
            age=int(age),
            gender=gender,
            goal_type=goal_type,  # still used for calculation
            activity_level=activity_level
            )

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



            insert_goals(
            cur,
            user_id=user_id,
            weight=int(weight),
            height_ft=int(height_ft),
            height_in=int(height_in),
            age=int(age),
            gender=gender,
            goal_type=goal_type,  # still used for calculation
            activity_level=activity_level
            )

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
    
@app.route('/log_food', methods=['GET', 'POST'])
@nocache
def log_food():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    # Get user_id from session username
    cur.execute("""
        SELECT user_id FROM authentication WHERE username = %s
    """, (username,))
    user_row = cur.fetchone()
    if not user_row:
        flash("❌ User not found.")
        return redirect('/dashboard')
    user_id = user_row[0]

    if request.method == 'POST':
        item = request.form['item']
        calories = request.form['calories']
        protein = request.form['protein']
        carbs = request.form['carbs']
        fat = request.form['fat']

        try:
            cur.execute("""
                INSERT INTO macros (user_id, item, calories, protein, carbs, fat, date_added)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (user_id, item, calories, protein, carbs, fat))
            conn.commit()
            flash("✅ Food logged successfully!")
            return redirect('/dashboard')
        except Exception as e:
            conn.rollback()
            flash(f"❌ Error logging food: {str(e)}")
        finally:
            cur.close()
            conn.close()
        return redirect('/log_food')  # Ensures you return after POST

    # ✅ GET: Fetch recent items to display as quick-add
    cur.execute("""
    SELECT DISTINCT ON (item) item, calories, protein, carbs, fat
    FROM macros
    WHERE user_id = %s
    ORDER BY item, date_added DESC
    """, (user_id,))
    recent_items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('log_food.html', recent_items=recent_items)

@app.route('/diary')
@nocache
def diary():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    # Get user_id
    cur.execute("""
        SELECT user_id FROM authentication WHERE username = %s
    """, (username,))
    user_row = cur.fetchone()
    if not user_row:
        flash("❌ User not found.")
        return redirect('/dashboard')
    user_id = user_row[0]

    # ✅ This is the query you're asking about — put it here:
    cur.execute("""
        SELECT item, calories, protein, carbs, fat, date_added, macro_id
        FROM macros
        WHERE user_id = %s AND date_added = CURRENT_DATE
        ORDER BY macro_id DESC
    """, (user_id,))
    entries = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('diary.html', username=username, entries=entries)


@app.route('/delete_food/<int:macro_id>', methods=['POST'])
def delete_food(macro_id):
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Optional: ensure only that user can delete their own entry
        cur.execute("""
            DELETE FROM macros
            WHERE macro_id = %s AND user_id = (
                SELECT user_id FROM authentication WHERE username = %s
            )
        """, (macro_id, username))
        conn.commit()
        flash("🗑️ Entry deleted.")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Could not delete entry: {str(e)}")
    finally:
        cur.close()
        conn.close()

    return redirect('/diary')

@app.route('/nutrition')
@nocache
def nutrition():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id FROM authentication WHERE username = %s
    """, (username,))
    user_id = cur.fetchone()[0]

    cur.execute("""
        SELECT daily_protein, daily_carbs, daily_fats FROM goals WHERE user_id = %s
    """, (user_id,))
    goals = cur.fetchone()

    cur.execute("""
        SELECT COALESCE(SUM(protein), 0), COALESCE(SUM(carbs), 0), COALESCE(SUM(fat), 0)
        FROM macros WHERE user_id = %s AND date_added = CURRENT_DATE
    """, (user_id,))
    totals = cur.fetchone()

    conn.close()

    nutrients = [
        {
            'name': 'Protein',
            'total': totals[0],
            'goal': goals[0],
            'remaining': max(0, goals[0] - totals[0]),
            'percent': min(100, int((totals[0] / goals[0]) * 100)),
            'class': 'protein'
        },
        {
            'name': 'Carbohydrates',
            'total': totals[1],
            'goal': goals[1],
            'remaining': max(0, goals[1] - totals[1]),
            'percent': min(100, int((totals[1] / goals[1]) * 100)),
            'class': 'carbs'
        },
        {
            'name': 'Fats',
            'total': totals[2],
            'goal': goals[2],
            'remaining': max(0, goals[2] - totals[2]),
            'percent': min(100, int((totals[2] / goals[2]) * 100)),
            'class': 'fat'
        },
    ]

    return render_template('nutrition.html', nutrients=nutrients)

@app.route('/calendar')
@nocache
def calendar():
    username = session.get('username')
    if not username:
        flash("❌ You must log in first.")
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()

    # Get user_id
    cur.execute("SELECT user_id FROM authentication WHERE username = %s", (username,))
    user_row = cur.fetchone()
    if not user_row:
        cur.close()
        conn.close()
        flash("❌ User not found.")
        return redirect('/')
    user_id = user_row[0]

    today = datetime.today()
    year = today.year
    month = today.month
    cal = Calendar()
    days_in_month = monthrange(year, month)[1]

    # Fetch daily goals
    cur.execute("SELECT daily_calories, daily_protein FROM goals WHERE user_id = %s", (user_id,))
    goal_row = cur.fetchone()
    goal_calories, goal_protein = goal_row if goal_row else (0, 0)

    # Get actual daily totals
    cur.execute("""
        SELECT date_added, SUM(calories), SUM(protein)
        FROM macros
        WHERE user_id = %s AND date_added BETWEEN %s AND %s
        GROUP BY date_added
    """, (
        user_id,
        f"{year}-{month:02d}-01",
        f"{year}-{month:02d}-{days_in_month}"
    ))
    results = cur.fetchall()
    today_str = datetime.today().strftime("%B %d")  # e.g., "May 28"


    daily_data = {}
    for row in results:
        date_str = row[0].strftime('%Y-%m-%d')
        calories, protein = row[1], row[2]

        if abs(calories - goal_calories) <= 100 and abs(protein - goal_protein) <= 20:
            color = 'green'
        elif abs(calories - goal_calories) <= 100:
            color = 'orange'
        else:
            color = 'red'

        daily_data[date_str] = {
            'calories': calories,
            'protein': protein,
            'color': color
        }
    

    # Build calendar weeks
    month_days = list(cal.itermonthdays(year, month))
    weeks = [month_days[i:i + 7] for i in range(0, len(month_days), 7)]

    cur.close()
    conn.close()

    return render_template(
        'calendar.html',
        year=year,
        month=month,
        weeks=weeks,
        daily_data=daily_data,
        goal_calories=goal_calories,
        goal_protein=goal_protein,
        today_str=today_str
    )





if __name__ == '__main__':
    app.run(debug=True)
