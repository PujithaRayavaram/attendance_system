from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "smartattendancekey"
DB = "attendance.db"

# ==========================
# DATABASE INITIALIZATION
# ==========================
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Faculty Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS faculty(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        subject TEXT,
        branch TEXT,
        year TEXT,
        sem TEXT,
        section TEXT
    )
    """)

    # Students Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_no TEXT,
        branch TEXT,
        year TEXT,
        sem TEXT,
        section TEXT
    )
    """)

    # Attendance Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        faculty_id INTEGER,
        date TEXT,
        status TEXT,
        UNIQUE(student_id, date)
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ==========================
# ADD SAMPLE STUDENTS
# ==========================
def add_sample_students():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Clear old students for fresh testing
    cur.execute("DELETE FROM students")

    branches = ["CSE", "ECE", "EEE", "MECH", "CIVIL"]
    years = ["I", "II", "III", "IV"]
    sems = ["I", "II"]
    sections = ["A", "B", "C", "D"]

    for branch in branches:
        for year in years:
            for sem in sems:
                for section in sections:
                    for i in range(1, 61):  # 60 students per class
                        reg_no = f"{year}{branch}{section}{sem}{i:03}"
                        cur.execute(
                            "INSERT INTO students(reg_no, branch, year, sem, section) VALUES (?,?,?,?,?)",
                            (reg_no, branch, year, sem, section)
                        )
    conn.commit()
    conn.close()

add_sample_students()

# ==========================
# FACULTY LOGIN
# ==========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        subject = request.form["subject"]
        branch = request.form["branch"]
        year = request.form["year"]
        sem = request.form["sem"]
        section = request.form["section"]

        # Insert faculty
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO faculty(name, subject, branch, year, sem, section)
        VALUES(?,?,?,?,?,?)
        """, (name, subject, branch, year, sem, section))
        conn.commit()
        faculty_id = cur.lastrowid
        conn.close()

        # Save session
        session["faculty_id"] = faculty_id
        session["branch"] = branch
        session["year"] = year
        session["sem"] = sem
        session["section"] = section

        return redirect("/index")
    return render_template("login.html")

# ==========================
# DASHBOARD
# ==========================
@app.route("/index", methods=["GET", "POST"])
def index():
    if "faculty_id" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    faculty_id = session["faculty_id"]
    branch = session["branch"]
    year = session["year"]
    sem = session["sem"]
    section = session["section"]
    today = str(date.today())

    # ===== FETCH STUDENTS =====
    cur.execute("""
        SELECT id, reg_no FROM students
        WHERE branch=? AND year=? AND sem=? AND section=?
    """, (branch, year, sem, section))
    students = cur.fetchall()

    # ===== FETCH TODAY'S ATTENDANCE =====
    cur.execute("""
        SELECT student_id, status FROM attendance
        WHERE date=? AND faculty_id=?
    """, (today, faculty_id))
    rows = cur.fetchall()
    attendance_data = {str(row[0]): row[1] for row in rows}

    already_marked = len(attendance_data) > 0

    # ===== SAVE ATTENDANCE =====
    if request.method == "POST" and not already_marked:
        for student_id in request.form:
            status = request.form[student_id]
            cur.execute("""
                INSERT OR REPLACE INTO attendance(student_id, faculty_id, date, status)
                VALUES(?,?,?,?)
            """, (student_id, faculty_id, today, status))
        conn.commit()
        return redirect("/index")

    # ===== COUNT =====
    total = len(students)
    present = sum(1 for s in attendance_data.values() if s == "Present")
    absent = sum(1 for s in attendance_data.values() if s == "Absent")
    if len(attendance_data) == 0:
        present = total
        absent = 0

    # ===== PRESENT / ABSENT STUDENTS LIST =====
    present_students = [s for s in students if attendance_data.get(str(s[0]), "Present") == "Present"]
    absent_students = [s for s in students if attendance_data.get(str(s[0]), "Present") == "Absent"]

    conn.close()

    # ===== Pass the faculty selected class to template =====
    class_name = f"{year} Year {branch} {section}"

    return render_template(
        "index.html",
        students=students,
        total=total,
        present=present,
        absent=absent,
        attendance_data=attendance_data,
        already_marked=already_marked,
        branch=branch,
        year=year,
        section=section,
        sem=sem,
        class_name=class_name,
        present_students=present_students,
        absent_students=absent_students
    )

# ==========================
# LOGOUT
# ==========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":

    app.run(debug=True)
