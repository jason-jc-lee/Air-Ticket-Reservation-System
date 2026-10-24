# app.py
from flask import Flask, request, render_template, redirect, url_for, session, flash
import pymysql
from pymysql.cursors import DictCursor
from hashlib import md5
from datetime import date, datetime, timedelta
import re
import math

app = Flask(__name__)

# ---------- DB connection ----------
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="root",
        database="airline",
        cursorclass=DictCursor,
        autocommit=False,
        port = 8889
    )

# ---------- helper utilities ----------
def hash_md5(password: str) -> str:
    return md5(password.encode()).hexdigest()

def ensure_ratings_table():
    """Create ratings table if it doesn't exist (assignment needs ratings feature)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS Ratings (
              id INT PRIMARY KEY AUTO_INCREMENT,
              customer_email VARCHAR(100) NOT NULL,
              flight_number VARCHAR(10) NOT NULL,
              rating TINYINT NOT NULL,
              comment TEXT,
              created_at DATETIME NOT NULL,
              FOREIGN KEY (customer_email) REFERENCES Customer(email),
              FOREIGN KEY (flight_number) REFERENCES Flight(flight_number)
            )""")
        conn.commit()
    finally:
        conn.close()

def require_login(role=None):
    """Return True if current session has a logged-in user with optional role; else redirect."""
    if role is None:
        return "email" in session or "username" in session
    if role == "customer":
        return "email" in session
    if role == "staff":
        return "username" in session and session.get("role") == "staff"
    return False

# ensure ratings table exists for rating functionality
ensure_ratings_table()

# ---------- public homepage / search ----------
@app.route("/")
def index():
    # public home: show search form & links to register/login
    return render_template("index.html")

@app.route("/search", methods=["GET"])
def public_search():
    src = request.args.get("src", "").strip()
    dst = request.args.get("dst", "").strip()
    depart_date = request.args.get("depart_date", "").strip()
    trip_type = request.args.get("trip_type", "oneway")
    return_date = request.args.get("return_date", "").strip()

    # --- Validate dates ---
    depart_date_obj = None
    return_date_obj = None

    if depart_date:
        try:
            depart_date_obj = datetime.strptime(depart_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid departure date format. Use YYYY-MM-DD.")
            return redirect(url_for("public_search"))

    if return_date:
        try:
            return_date_obj = datetime.strptime(return_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid return date format. Use YYYY-MM-DD.")
            return redirect(url_for("public_search"))

    # --- Check date logic ---
    today = datetime.today().date()
    if depart_date_obj and depart_date_obj < today:
        flash("Cannot search for past departure dates.")
        return redirect(url_for("public_search"))

    if trip_type == "roundtrip" and depart_date_obj and return_date_obj:
        if return_date_obj < depart_date_obj:
            flash("Return date must be after departure date.")
            return redirect(url_for("public_search"))

    outgoing = []
    returns = []

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # --- Outgoing flights ---
            sql_out = """
                SELECT f.*, a1.city AS src_city, a2.city AS dst_city, al.name AS airline
                FROM Flight f
                LEFT JOIN Airport a1 ON f.depart_airport_code = a1.code
                LEFT JOIN Airport a2 ON f.arrival_airport_code = a2.code
                LEFT JOIN Airline al ON f.airline_name = al.name
                WHERE f.departure_datetime >= NOW()
            """
            params_out = []

            if src:
                sql_out += " AND (a1.city LIKE %s OR a1.code LIKE %s)"
                params_out += [f"%{src}%", f"%{src}%"]
            if dst:
                sql_out += " AND (a2.city LIKE %s OR a2.code LIKE %s)"
                params_out += [f"%{dst}%", f"%{dst}%"]
            if depart_date_obj:
                sql_out += " AND DATE(f.departure_datetime) = %s"
                params_out.append(depart_date_obj)

            sql_out += " ORDER BY f.departure_datetime LIMIT 500"
            cur.execute(sql_out, params_out)
            outgoing = cur.fetchall()

            # --- Return flights ---
            if trip_type == "roundtrip" and return_date_obj:
                sql_ret = """
                    SELECT f.*, a1.city AS src_city, a2.city AS dst_city, al.name AS airline
                    FROM Flight f
                    LEFT JOIN Airport a1 ON f.depart_airport_code = a1.code
                    LEFT JOIN Airport a2 ON f.arrival_airport_code = a2.code
                    LEFT JOIN Airline al ON f.airline_name = al.name
                    WHERE f.departure_datetime >= NOW()
                """
                params_ret = []

                # reverse src/dst
                if dst:
                    sql_ret += " AND (a1.city LIKE %s OR a1.code LIKE %s)"
                    params_ret += [f"%{dst}%", f"%{dst}%"]
                if src:
                    sql_ret += " AND (a2.city LIKE %s OR a2.code LIKE %s)"
                    params_ret += [f"%{src}%", f"%{src}%"]

                sql_ret += " AND DATE(f.departure_datetime) = %s"
                params_ret.append(return_date_obj)

                sql_ret += " ORDER BY f.departure_datetime LIMIT 500"
                cur.execute(sql_ret, params_ret)
                returns = cur.fetchall()

    finally:
        conn.close()

    # --- Flash messages if no flights found ---
    if not outgoing:
        flash("No outgoing flights found matching your search criteria.")
    if trip_type == "roundtrip" and return_date_obj and not returns:
        flash("No return flights found matching your search criteria.")

    return render_template(
        "search_results.html",
        outgoing=outgoing,
        returns=returns,
        trip_type=trip_type,
        src=src,
        dst=dst,
        depart_date=depart_date,
        return_date=return_date
    )


# ---------- registration ----------
@app.route("/register/customer", methods=["GET", "POST"])
def register_customer():
    if request.method == "GET":
        return render_template("register_customer.html")
    # POST
    email = request.form.get("email", "").strip().lower()
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")
    if not email or not password or not name:
        flash("Email, name and password are required.")
        return redirect(url_for("register_customer"))
    pw_md5 = hash_md5(password)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # ensure email unique
            cur.execute("SELECT email FROM Customer WHERE email=%s", (email,))
            if cur.fetchone():
                flash("Email already registered.")
                return redirect(url_for("register_customer"))
            cur.execute("""
                INSERT INTO Customer (email, name, date_of_birth, password, phone_number)
                VALUES (%s, %s, NULL, %s, NULL)
            """, (email, name, pw_md5))
        conn.commit()
        flash("Customer registered. Please login.")
        return redirect(url_for("login"))
    except Exception as e:
        conn.rollback()
        flash("Registration failed: " + str(e))
        return redirect(url_for("register_customer"))
    finally:
        conn.close()

@app.route("/register/staff", methods=["GET", "POST"])
def register_staff():
    if request.method == "GET":
        # need list of airlines for staff signup
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM Airline ORDER BY name")
                airlines = cur.fetchall()
        finally:
            conn.close()
        return render_template("register_staff.html", airlines=airlines)
    # POST
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    airline_name = request.form.get("airline_name")
    if not username or not password or not first_name or not airline_name:
        flash("username, password, first name and airline are required.")
        return redirect(url_for("register_staff"))
    pw_md5 = hash_md5(password)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username FROM Airline_Staff WHERE username=%s OR email=%s", (username, email))
            if cur.fetchone():
                flash("Username or email already exists.")
                return redirect(url_for("register_staff"))
            cur.execute("""
                INSERT INTO Airline_Staff (username, password, first_name, last_name, email, date_of_birth, phone_number, airline_name)
                VALUES (%s,%s,%s,%s,%s,NULL,NULL,%s)
            """, (username, pw_md5, first_name, last_name, email, airline_name))
        conn.commit()
        flash("Airline staff registered. Please login.")
        return redirect(url_for("login", role = "staff"))
    except Exception as e:
        conn.rollback()
        flash("Registration failed: " + str(e))
        return redirect(url_for("register_staff"))
    finally:
        conn.close()

# ---------- login / logout ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        role = request.args.get("role", "customer")
        if role == "customer":
            return render_template("login_customer.html")
        else:
            return render_template("login_staff.html")
       
    role = request.form.get("role", "customer")  # 'customer' or 'staff'
    identifier = request.form.get("identifier", "").strip()  # email for customer, username for staff
    password = request.form.get("password", "")
    if not identifier or not password:
        flash("Provide credentials.")
        return redirect(url_for("login", role = role))
    pw_md5 = hash_md5(password)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if role == "customer":
                cur.execute("SELECT email, name FROM Customer WHERE email=%s AND password=%s", (identifier, pw_md5))
                user = cur.fetchone()
                if user:
                    session.clear()
                    session["email"] = user["email"]
                    session["name"] = user["name"]
                    session["role"] = "customer"
                    flash("Logged in as customer.")
                    return redirect(url_for("customer_home"))
            else:
                cur.execute("SELECT username, first_name, airline_name FROM Airline_Staff WHERE username=%s AND password=%s", (identifier, pw_md5))
                staff = cur.fetchone()
                if staff:
                    session.clear()
                    session["username"] = staff["username"]
                    session["name"] = staff["first_name"]
                    session["role"] = "staff"
                    session["airline_name"] = staff["airline_name"]
                    flash("Logged in as staff.")
                    return redirect(url_for("staff_home"))
        flash("Login failed.")
        return redirect(url_for("login", role = role))
    finally:
        conn.close()

@app.route("/logout")
def logout():
    #determine role before clear session
    role = session.get("role", "customer") #default val is customer
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login", role = role))

# ---------- customer home / my flights ----------
@app.route("/customer_home")
def customer_home():
    if not require_login("customer"):
        flash("Please login as customer.")
        return redirect(url_for("login"))
    email = session["email"]
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # show future flights purchased
            cur.execute("""
                SELECT t.ticket_id, t.purchase_datetime, t.qty, f.flight_number, f.departure_datetime, f.arrival_datetime, f.base_price, f.depart_airport_code, f.arrival_airport_code, f.status
                FROM Ticket t JOIN Flight f ON t.flight_number = f.flight_number
                WHERE t.customer_email = %s AND f.departure_datetime >= NOW()
                ORDER BY f.departure_datetime
            """, (email,))
            upcoming = cur.fetchall()
            # past flights
            cur.execute("""
                 SELECT t.ticket_id, t.purchase_datetime, t.qty, f.flight_number, f.departure_datetime, f.arrival_datetime, f.base_price, f.depart_airport_code, f.arrival_airport_code, f.status
                 FROM Ticket t JOIN Flight f ON t.flight_number = f.flight_number
                 WHERE t.customer_email = %s AND f.departure_datetime < NOW()
                 ORDER BY f.departure_datetime DESC
            """, (email,))
            past = cur.fetchall()

    finally:
        conn.close()
    return render_template("customer_home.html", upcoming=upcoming, past = past)

# ---------- purchase ticket ----------
@app.route("/purchase/<flight_number>", methods=["GET", "POST"])
def purchase(flight_number):
    # Must be logged in
    if not require_login("customer"):
        flash("Please login as customer.")
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Fetch flight FIRST
            cur.execute("SELECT * FROM Flight WHERE flight_number=%s", (flight_number,))
            flight = cur.fetchone()

            if not flight:
                flash("Flight not found.")
                return redirect(url_for("public_search"))

            # 2. Convert MySQL datetime → Python datetime
            flight_departure = flight["departure_datetime"]
            if isinstance(flight_departure, str):  
                flight_departure = datetime.strptime(flight_departure, "%Y-%m-%d %H:%M:%S")

            # 3. Block past flights
            now = datetime.now()
            if flight_departure < now:
                flash("You cannot purchase a past flight.")
                return redirect(url_for("public_search"))

            # 4. Seats total (if airplane_id exists)
            seats_total = None
            if flight.get("airplane_id"):
                cur.execute("SELECT num_of_seats FROM Airplane WHERE airplane_id=%s",
                            (flight["airplane_id"],))
                airplane = cur.fetchone()
                if airplane:
                    seats_total = airplane.get("num_of_seats")

            # 5. Seats sold (SUM qty)
            cur.execute("""
                SELECT COALESCE(SUM(qty),0) AS sold
                FROM Ticket
                WHERE flight_number=%s
            """, (flight_number,))
            sold = cur.fetchone()["sold"] or 0

       # -------------------------
        # POST → Purchase Ticket
        # -------------------------
        if request.method == "POST":
            qty = int(request.form.get("qty", 1))

    # capacity check
            if seats_total is not None and sold + qty > seats_total:
                flash("Not enough seats available.")
                return redirect(url_for("purchase", flight_number=flight_number))

    # payment info
            card_type = request.form.get("card_type")
            card_number = request.form.get("card_number").strip()
            name_on_card = request.form.get("name_on_card").strip()
            expiration_raw = request.form.get("expiration_date")

    # --- Validate card type ---
            if card_type not in ("Credit", "Debit"):
                flash("Invalid card type.")
                return redirect(url_for("purchase", flight_number=flight_number))

    # --- Validate card number (digits only, 13–16) ---
            if not re.fullmatch(r"\d{13,16}", card_number):
                flash("Invalid card number.")
                return redirect(url_for("purchase", flight_number=flight_number))

    # --- Mask and store only last 4 digits ---
            card_last4 = card_number[-4:]

    # --- Validate expiration date ---
            try:
                year, month = map(int, expiration_raw.split("-"))
                exp_date = date(year, month, 1)
            except Exception:
                flash("Invalid expiration date.")
                return redirect(url_for("purchase", flight_number=flight_number))

            if exp_date < date.today().replace(day=1):
                flash("Card is expired.")
                return redirect(url_for("purchase", flight_number=flight_number))

    # --- Insert ticket with masked card ---
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(ticket_id),0) + 1 AS nextid FROM Ticket")
                nextid = cur.fetchone()["nextid"]

                now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                cur.execute("""
                INSERT INTO Ticket (
                ticket_id, card_type, card_number, name_on_card,
                expiration_date, purchase_datetime, customer_email, flight_number, qty
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (nextid, card_type, card_last4, name_on_card,
                exp_date, now_str, session["email"], flight_number, qty))

            conn.commit()
            flash(f"Purchase complete! Ticket ID: {nextid}")
            return redirect(url_for("public_search"))


        # -------------------------
        # GET → Show confirmation page
        # -------------------------
        return render_template(
            "purchase_confirm.html",
            flight=flight,
            sold=sold,
            seats_total=seats_total
        )

    except Exception:
        conn.rollback()
        flash("Purchase failed.")
        return redirect(url_for("public_search"))

    finally:
        conn.close()


# ---------- rate flight (customer) ----------
@app.route("/rate", methods=["GET", "POST"])
def rate():
    if not require_login("customer"):
        flash("Please login as customer.")
        return redirect(url_for("login"))

    email = session["email"]
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if request.method == "POST":
                # --- Get POST data ---
                flight_number = request.form.get("flight_number")
                try:
                    rating_val = int(request.form.get("rating"))
                except (TypeError, ValueError):
                    flash("Invalid rating value.")
                    return redirect(url_for("rate"))
                
                comment = request.form.get("comment", "").strip()

                # --- Validate rating ---
                if rating_val < 1 or rating_val > 5:
                    flash("Rating must be between 1 and 5.")
                    return redirect(url_for("rate"))

                # --- Ensure customer took the flight ---
                cur.execute("""
                    SELECT COUNT(*) AS cnt 
                    FROM Ticket t 
                    JOIN Flight f ON t.flight_number=f.flight_number
                    WHERE t.customer_email=%s 
                      AND t.flight_number=%s 
                      AND f.departure_datetime < NOW()
                """, (email, flight_number))
                if cur.fetchone()["cnt"] == 0:
                    flash("You may only rate flights you have taken.")
                    return redirect(url_for("rate"))

                # --- Insert rating ---
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute("""
                    INSERT INTO Ratings (customer_email, flight_number, rating, comment, created_at)
                    VALUES (%s,%s,%s,%s,%s)
                """, (email, flight_number, rating_val, comment, now))
                conn.commit()
                flash(f"Rating submitted for flight {flight_number}.")
                return redirect(url_for("rate"))

            else:
                # --- GET: list past flights eligible to rate ---
                cur.execute("""
                    SELECT DISTINCT f.flight_number, f.departure_datetime, f.arrival_datetime, f.depart_airport_code, f.arrival_airport_code
                    FROM Ticket t 
                    JOIN Flight f ON t.flight_number = f.flight_number
                    WHERE t.customer_email=%s AND f.departure_datetime < NOW()
                    ORDER BY f.departure_datetime DESC
                """, (email,))
                past_flights = cur.fetchall()
                return render_template("rate_form.html", past_flights=past_flights)
    finally:
        conn.close()

# ---------- staff home & functions ----------
@app.route("/staff_home", methods=["GET", "POST"])
def staff_home():
    if not require_login("staff"):
        flash("Please login as staff.")
        return redirect(url_for("login"))

    airline = session.get("airline_name")
    today = datetime.today().date()
    next_30_days = today + timedelta(days=30)

    # --- Handle creating new flight ---
    if request.method == "POST":
        flight_number = request.form.get("flight_number", "").strip()
        depart_code = request.form.get("depart_code", "").strip()
        arrival_code = request.form.get("arrival_code", "").strip()
        depart_dt = request.form.get("depart_datetime", "").strip()
        arrive_dt = request.form.get("arrival_datetime", "").strip()
        base_price = float(request.form.get("base_price", "0"))
        airplane_id = request.form.get("airplane_id") or None

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Prevent duplicate flight number
                cur.execute("SELECT flight_number FROM Flight WHERE flight_number=%s", (flight_number,))
                if cur.fetchone():
                    flash("Flight number already exists.")
                    return redirect(url_for("staff_home"))

                # Insert new flight
                cur.execute("""
                    INSERT INTO Flight (flight_number, departure_datetime, arrival_datetime, base_price,
                                        status, airplane_id, depart_airport_code, arrival_airport_code, airline_name)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (flight_number, depart_dt, arrive_dt, base_price, "On Time", airplane_id,
                      depart_code, arrival_code, airline))
            conn.commit()
            flash("Flight created successfully.")
        finally:
            conn.close()
        return redirect(url_for("staff_home"))

    # --- GET: read filter parameters ---
    src = request.args.get("src", "").strip()
    dst = request.args.get("dst", "").strip()
    start_date_str = request.args.get("start_date", today.strftime("%Y-%m-%d"))
    end_date_str = request.args.get("end_date", next_30_days.strftime("%Y-%m-%d"))

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.")
        start_date, end_date = today, next_30_days


    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # --- Upcoming flights ---
            sql_up = """
                SELECT f.*, a1.city AS src_city, a2.city AS dst_city
                FROM Flight f
                LEFT JOIN Airport a1 ON f.depart_airport_code = a1.code
                LEFT JOIN Airport a2 ON f.arrival_airport_code = a2.code
                WHERE f.airline_name=%s
                  AND f.departure_datetime >= %s
                  AND DATE(f.departure_datetime) BETWEEN %s AND %s
            """
            params_up = [airline, today, start_date, end_date]
            if src:
                sql_up += " AND (a1.city LIKE %s OR a1.code LIKE %s)"
                params_up += [f"%{src}%", f"%{src}%"]
            if dst:
                sql_up += " AND (a2.city LIKE %s OR a2.code LIKE %s)"
                params_up += [f"%{dst}%", f"%{dst}%"]
            sql_up += " ORDER BY f.departure_datetime"
            cur.execute(sql_up, params_up)
            upcoming_flights = cur.fetchall()

            # --- Past flights ---
            sql_past = """
                SELECT f.*, a1.city AS src_city, a2.city AS dst_city
                FROM Flight f
                LEFT JOIN Airport a1 ON f.depart_airport_code = a1.code
                LEFT JOIN Airport a2 ON f.arrival_airport_code = a2.code
                WHERE f.airline_name=%s
                  AND f.departure_datetime < %s
                  AND DATE(f.departure_datetime) BETWEEN %s AND %s
            """
            params_past = [airline, today, start_date, end_date]
            if src:
                sql_past += " AND (a1.city LIKE %s OR a1.code LIKE %s)"
                params_past += [f"%{src}%", f"%{src}%"]
            if dst:
                sql_past += " AND (a2.city LIKE %s OR a2.code LIKE %s)"
                params_past += [f"%{dst}%", f"%{dst}%"]
            sql_past += " ORDER BY f.departure_datetime DESC"
            cur.execute(sql_past, params_past)
            past_flights = cur.fetchall()
    finally:
        conn.close()

    # --- Fetch airplanes for dropdown ---
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT airplane_id, manufacturer, num_of_seats, age
                FROM Airplane
                WHERE airline_name=%s
            """, (airline,))
            airplanes = cur.fetchall()
    finally:
        conn.close()


    return render_template(
        "staff_home.html",
        username=session.get("username"),
        upcoming_flights=upcoming_flights,
        past_flights=past_flights,
        request_args=request.args,
        airplanes = airplanes
    )







@app.route("/staff/create_flight", methods=["GET", "POST"])
def staff_create_flight():
    if not require_login("staff"):
        flash("Please login as staff.")
        return redirect(url_for("login"))
    airline = session.get("airline_name")
    conn = get_db_connection()
    try:
        if request.method == "POST":
            flight_number = request.form.get("flight_number").strip()
            depart_code = request.form.get("depart_code").strip()
            arrival_code = request.form.get("arrival_code").strip()
            depart_dt = request.form.get("depart_datetime").strip()
            arrive_dt = request.form.get("arrival_datetime").strip()
            base_price = float(request.form.get("base_price", "0"))
            airplane_id = request.form.get("airplane_id") or None
            # If flight_number exists, block
            with conn.cursor() as cur:
                cur.execute("SELECT flight_number FROM Flight WHERE flight_number=%s", (flight_number,))
                if cur.fetchone():
                    flash("Flight number already exists.")
                    return redirect(url_for("staff_create_flight"))
                cur.execute("""
                    INSERT INTO Flight (flight_number, departure_datetime, arrival_datetime, base_price, status, airplane_id, depart_airport_code, arrival_airport_code, airline_name)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (flight_number, depart_dt, arrive_dt, base_price, "On Time", airplane_id, depart_code, arrival_code, airline))
            conn.commit()
            flash("Flight created.")
            return redirect(url_for("staff_home"))
        # GET: need list of airports and airplanes
        with conn.cursor() as cur:
            cur.execute("SELECT code, city FROM Airport ORDER BY city")
            airports = cur.fetchall()
            cur.execute("SELECT airplane_id, manufacturer, num_of_seats FROM Airplane WHERE airline_name=%s", (airline,))
            airplanes = cur.fetchall()
        return render_template("create_flight.html", airports=airports, airplanes=airplanes)
    finally:
        conn.close()
@app.route("/staff/view_customers/<flight_number>")
def staff_view_customers(flight_number):
    if not require_login("staff"):
        flash("Please login as staff.")
        return redirect(url_for("login"))

    airline = session.get("airline_name")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Ensure staff only sees flights of their airline
            cur.execute("SELECT airline_name FROM Flight WHERE flight_number=%s", (flight_number,))
            flight = cur.fetchone()
            if not flight or flight["airline_name"] != airline:
                flash("Unauthorized or flight not found.")
                return redirect(url_for("staff_home"))

            # Get all customers who purchased tickets
            cur.execute("""
                SELECT t.customer_email, c.name, t.qty, t.purchase_datetime
                FROM Ticket t
                JOIN Customer c ON t.customer_email = c.email
                WHERE t.flight_number=%s
                ORDER BY t.purchase_datetime DESC
            """, (flight_number,))
            customers = cur.fetchall()

        return render_template("staff_view_customers.html",
                               flight_number=flight_number,
                               customers=customers)
    finally:
        conn.close()



@app.route("/staff_change_status/<flight_number>", methods=["GET", "POST"])
def staff_change_status(flight_number):
    if not require_login("staff"):
        flash("Please login as staff.")
        return redirect(url_for("login"))

    airline = session.get("airline_name")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Fetch the flight to make sure it belongs to this airline
            cur.execute("""
                SELECT flight_number, status 
                FROM Flight 
                WHERE flight_number=%s AND airline_name=%s
            """, (flight_number, airline))
            flight = cur.fetchone()
            if not flight:
                flash("Flight not found or unauthorized access.")
                return redirect(url_for("staff_home"))

            if request.method == "POST":
                new_status = request.form.get("status")
                if new_status not in ["On Time", "Delayed"]:
                    flash("Invalid status selected.")
                else:
                    cur.execute("""
                        UPDATE Flight SET status=%s
                        WHERE flight_number=%s
                    """, (new_status, flight_number))
                    conn.commit()
                    flash(f"Flight {flight_number} status updated to {new_status}.")
                    return redirect(url_for("staff_home"))
    finally:
        conn.close()

    return render_template("staff_change_status.html", flight=flight)

@app.route("/staff_add_airplane", methods=["GET", "POST"])
def staff_add_airplane():
    if not require_login("staff"):
        flash("Please login as staff.")
        return redirect(url_for("login"))

    airline = session.get("airline_name")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if request.method == "POST":
                airplane_id = request.form.get("airplane_id", "").strip()
                num_of_seats = request.form.get("num_of_seats", "").strip()
                manufacturer = request.form.get("manufacturer", "").strip()
                age = request.form.get("age", "").strip()

                # --- Validate required fields ---
                if not airplane_id or not num_of_seats or not manufacturer or not age:
                    flash("All fields are required.")
                    return redirect(url_for("staff_add_airplane"))

                # --- Prevent duplicate airplane ID ---
                cur.execute("SELECT airplane_id FROM Airplane WHERE airplane_id=%s", (airplane_id,))
                if cur.fetchone():
                    flash("Airplane ID already exists.")
                    return redirect(url_for("staff_add_airplane"))

                # --- Insert new airplane ---
                cur.execute("""
                    INSERT INTO Airplane (airplane_id, num_of_seats, manufacturer, age, airline_name)
                    VALUES (%s, %s, %s, %s, %s)
                """, (airplane_id, num_of_seats, manufacturer, age, airline))
                conn.commit()
                flash("Airplane added successfully.")
                return redirect(url_for("staff_add_airplane"))

            # --- GET: show all airplanes for this airline ---
            cur.execute("SELECT * FROM Airplane WHERE airline_name=%s", (airline,))
            airplanes = cur.fetchall()
    finally:
        conn.close()

    return render_template("staff_add_airplane.html", username=session.get("username"), airplanes=airplanes)


@app.route("/staff/view_ratings/<flight_number>")
def staff_view_ratings(flight_number):
    if not require_login("staff"):
        flash("Please login as staff.")
        return redirect(url_for("login"))

    airline = session.get("airline_name")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Ensure staff's airline owns this flight
            cur.execute("SELECT airline_name FROM Flight WHERE flight_number=%s", (flight_number,))
            flight = cur.fetchone()
            if not flight or flight["airline_name"] != airline:
                flash("Unauthorized or flight not found.")
                return redirect(url_for("staff_home"))

            # Fetch all ratings for this flight
            cur.execute("""
                SELECT r.customer_email, c.name, r.rating, r.comment, r.created_at
                FROM Ratings r
                JOIN Customer c ON r.customer_email = c.email
                WHERE r.flight_number=%s
                ORDER BY r.created_at DESC
            """, (flight_number,))
            ratings = cur.fetchall()

            # Compute average rating
            cur.execute("SELECT AVG(rating) AS avg_rating FROM Ratings WHERE flight_number=%s", (flight_number,))
            avg = cur.fetchone()["avg_rating"]

    finally:
        conn.close()

    return render_template("view_ratings.html", ratings=ratings, avg=avg, flight_number=flight_number)
@app.route("/staff_reports", methods=["GET", "POST"])
def staff_reports():
    if not require_login("staff"):
        flash("Please login as staff.")
        return redirect(url_for("login"))

    airline = session.get("airline_name")
    today = datetime.today().date()

    # Check for quick-filter buttons
    date_range = request.args.get("range")

    if date_range == "last_month":
        start_date_obj = (today - timedelta(days=30))
        end_date_obj = today

    elif date_range == "last_year":
        start_date_obj = today.replace(year=today.year - 1)
        end_date_obj = today

    elif date_range == "this_year":
        start_date_obj = today.replace(month=1, day=1)
        end_date_obj = today

    else:
        # Manual date input OR default
        start_date = request.args.get("start_date", (today - timedelta(days=30)).strftime("%Y-%m-%d"))
        end_date = request.args.get("end_date", today.strftime("%Y-%m-%d"))

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Using last 30 days.")
            start_date_obj = today - timedelta(days=30)
            end_date_obj = today

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Total tickets sold
            cur.execute("""
                SELECT SUM(T.qty * F.base_price) AS total_amount,
                       SUM(T.qty) AS total_tickets
                FROM Ticket T
                JOIN Flight F ON T.flight_number = F.flight_number
                WHERE F.airline_name=%s
                  AND DATE(T.purchase_datetime) BETWEEN %s AND %s
            """, (airline, start_date_obj, end_date_obj))
            totals = cur.fetchone()

            # Month-wise summary
            cur.execute("""
                SELECT DATE_FORMAT(T.purchase_datetime, '%%Y-%%m') AS month,
                       SUM(T.qty) AS tickets_sold,
                       SUM(T.qty * F.base_price) AS total_amount
                FROM Ticket T
                JOIN Flight F ON T.flight_number = F.flight_number
                WHERE F.airline_name=%s
                  AND DATE(T.purchase_datetime) BETWEEN %s AND %s
                GROUP BY month
                ORDER BY month
            """, (airline, start_date_obj, end_date_obj))
            monthly_data = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "staff_reports.html",
        username=session.get("username"),
        totals=totals,
        monthly_data=monthly_data,
        start_date=start_date_obj,
        end_date=end_date_obj
    )



# ---------- run ----------
if __name__ == "__main__":
    app.run(debug=True)
