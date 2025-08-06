import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
# -------------------------
# Session Initialization
# -------------------------
# Ensure session state is initialized

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "login_failed" not in st.session_state:
    st.session_state.login_failed = False

# ---------- USER ROLES ----------
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "ashu": {"password": "Ashu10", "role": "supervisor"},
    "employee": {"password": "emp2025", "role": "employee"},
}

# ---------- LOGIN PAGE ----------
def login_page():
    st.set_page_config(page_title="ASHUZ LOGIN", layout="centered")
    st.markdown(
        """
        <style>
            html, body, .stApp {
                background-color: #000814 !important;
            }
            .title {
                text-align: center;
                color: #00f9ff;
                text-shadow: 0 0 15px #00f9ff;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<h1 class='title'>ASHUZ</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='title'>POLYMERS & PLASTICS</h3>", unsafe_allow_html=True)
    st.markdown("<h4 class='title'>WELCOME BACK</h4>", unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        USERS = {
            "admin": {"password": "admin123", "role": "admin"},
            "ashu": {"password": "Ashu10", "role": "supervisor"},
            "employee": {"password": "emp2025", "role": "employee"},
        }

        if username in USERS and password == USERS[username]["password"]:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.session_state.role = USERS[username]["role"]
            st.success(f"✅ Logged in as {st.session_state.role.capitalize()}")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

# ---------- MAIN APP ----------
def main_app():
    st.set_page_config(layout="wide")
    st.sidebar.title(f"Welcome, {st.session_state.user}")
    st.sidebar.success(f"Role: {st.session_state.role.capitalize()}")

    if st.sidebar.button("🚪 Logout"):
        for key in ["logged_in", "user", "role"]:
            if key in st.session_state:
                del st.session_state[key]

    st.title("📦 Smart Slip Generator")

    conn = sqlite3.connect("formulas.db")
    cursor = conn.cursor()

    # Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS Parties (
        Party_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Party_Name TEXT NOT NULL,
        Email TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Formulas (
        Party_ID INTEGER,
        Grade TEXT,
        Compound_Name TEXT,
        Quantity REAL,
        Unit TEXT,
        PRIMARY KEY (Party_ID, Grade, Compound_Name),
        FOREIGN KEY (Party_ID) REFERENCES Parties(Party_ID)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Custom_Grades (
        Grade_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Party_ID INTEGER,
        Grade_Name TEXT,
        Based_On TEXT,
        Created_At TEXT,
        FOREIGN KEY (Party_ID) REFERENCES Parties(Party_ID)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Custom_Formula_Entries (
        Grade_ID INTEGER,
        Compound_Name TEXT,
        Quantity REAL,
        Unit TEXT,
        FOREIGN KEY (Grade_ID) REFERENCES Custom_Grades(Grade_ID)
    )''')
    conn.commit()

    def get_party_names():
        cursor.execute("SELECT Party_Name FROM Parties")
        return [row[0] for row in cursor.fetchall()]

    def get_party_id(name):
        cursor.execute("SELECT Party_ID FROM Parties WHERE Party_Name = ?", (name.strip(),))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_grades_for_party(party_id):
        cursor.execute("SELECT DISTINCT Grade FROM Formulas WHERE Party_ID=?", (party_id,))
        base = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT Grade_Name FROM Custom_Grades WHERE Party_ID=?", (party_id,))
        custom = [r[0] for r in cursor.fetchall()]
        return base + custom

    def get_formulas(party_id, grade):
        cursor.execute("SELECT Compound_Name, Quantity, Unit FROM Formulas WHERE Party_ID=? AND Grade=?", (party_id, grade))
        result = cursor.fetchall()
        if result:
            return result
        cursor.execute("SELECT Grade_ID FROM Custom_Grades WHERE Party_ID=? AND Grade_Name=?", (party_id, grade))
        row = cursor.fetchone()
        if row:
            cursor.execute("SELECT Compound_Name, Quantity, Unit FROM Custom_Formula_Entries WHERE Grade_ID=?", (row[0],))
            return cursor.fetchall()
        return []

    def save_custom_grade(party_id, base_grade, new_grade_name, df):
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO Custom_Grades (Party_ID, Grade_Name, Based_On, Created_At) VALUES (?, ?, ?, ?)",
                       (party_id, new_grade_name, base_grade, created))
        grade_id = cursor.lastrowid
        for _, row in df.iterrows():
            cursor.execute("INSERT INTO Custom_Formula_Entries (Grade_ID, Compound_Name, Quantity, Unit) VALUES (?, ?, ?, ?)",
                           (grade_id, row["Compound"], row["Quantity"], row["Unit"]))
        conn.commit()

    def add_new_party(party_name, email):
        cursor.execute("INSERT INTO Parties (Party_Name, Email) VALUES (?, ?)", (party_name, email))
        conn.commit()
        return get_party_id(party_name)

    def save_base_formula(party_id, grade, df):
        for _, row in df.iterrows():
            cursor.execute("INSERT INTO Formulas (Party_ID, Grade, Compound_Name, Quantity, Unit) VALUES (?, ?, ?, ?, ?)",
                           (party_id, grade, row["Compound"], row["Quantity"], row["Unit"]))
        conn.commit()

    def delete_party_by_name(name):
        party_id = get_party_id(name)
        if not party_id:
            return
        cursor.execute("DELETE FROM Custom_Formula_Entries WHERE Grade_ID IN (SELECT Grade_ID FROM Custom_Grades WHERE Party_ID=?)", (party_id,))
        cursor.execute("DELETE FROM Custom_Grades WHERE Party_ID=?", (party_id,))
        cursor.execute("DELETE FROM Formulas WHERE Party_ID=?", (party_id,))
        cursor.execute("DELETE FROM Parties WHERE Party_ID=?", (party_id,))
        conn.commit()

    compound_template = [
        ("Resin", ["Resin China", "Resin Shree Ram"]),
        ("Plasticizer", ["CPW", "DBP", "DOP"]),
        ("Stabilizer", ["Stabilizer Yamuna", "Stabilizer Nova", "Stabilizer Rejoice"]),
        ("Blowing Agent", ["OBSH"]),
        ("Filler", ["FW", "DHRUV"]),
        ("Color Additives", ["Toner", "OB"]),
        ("Other Additives", ["G-3", "TT", "Steric Acid", "Euamol"])
    ]
    unit_multipliers = {"kg": 1000, "g": 1, "mg": 0.001}

    # Admin-only: Add Party
    if st.session_state.role in ["admin", "supervisor"]:
        with st.expander("➕ Add New Party"):
            new_party = st.text_input("New Party Name")
            new_email = st.text_input("Email (optional)")
            new_grade = st.text_input("Initial Grade Name")
            new_formula_data = []

            st.write("### Fill Formula")
            for category, options in compound_template:
                st.markdown(f"**{category}**")
                for option in options:
                    col1, col2 = st.columns([2, 1])
                    qty = col1.number_input(f"{option} Qty", min_value=0.0, step=0.1, key=f"qty_{option}")
                    unit = col2.selectbox("Unit", ["kg", "g", "mg"], key=f"unit_{option}")
                    if qty > 0:
                        new_formula_data.append({"Compound": option, "Quantity": qty, "Unit": unit})

            if st.button("Create Party"):
                if new_party and new_grade and new_formula_data:
                    pid = add_new_party(new_party, new_email)
                    save_base_formula(pid, new_grade, pd.DataFrame(new_formula_data))
                    st.success("✅ Party Created")

    # Admin-only: Delete Party
    if st.session_state.role == "admin":
        with st.expander("🗑️ Delete Party"):
            party_list = get_party_names()
            del_party = st.selectbox("Select Party", party_list)
            if st.button("Delete Party"):
                delete_party_by_name(del_party)
                st.success("✅ Deleted. Please refresh.")

    # Slip Generator (All Roles)
    party_list = get_party_names()
    selected_party = st.selectbox("Select Party", party_list,key="party_selector")

    if selected_party:
        pid = get_party_id(selected_party)
        grade_list = get_grades_for_party(pid)
        selected_grade = st.selectbox("Select Grade", grade_list)

        if st.button("Load Formula"):
            formula = get_formulas(pid, selected_grade)
            if not formula:
                st.warning("No formula found.")
            else:
                df = pd.DataFrame(formula, columns=["Compound", "Quantity", "Unit"])
                edited_df = st.data_editor(df, key="formula_editor", num_rows="dynamic")

                st.subheader("📦 Order Details")
                weight = st.number_input("Total Weight", min_value=1.0)
                output_unit = st.selectbox("Display Output In", ["kg", "g", "mg"])
                order_type = st.radio("Order Type", ["Standard", "Custom"])
                new_grade_name = st.text_input("New Grade Name (if saving custom)")

                if st.button("Save Custom Grade") and new_grade_name.strip():
                    save_custom_grade(pid, selected_grade, new_grade_name, edited_df)
                    st.success("✅ Saved.")

                if st.button("Generate Slip"):
                    def calc(row):
                        q = row["Quantity"] * unit_multipliers[row["Unit"]]
                        total = q * weight
                        final = total / unit_multipliers[output_unit]
                        return f"{final:.2f} {output_unit}"


    conn.close()

# ---------- BOOTSTRAP ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    main_app()
