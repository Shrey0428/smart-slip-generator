import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ------------------------
# Database Setup
# ------------------------
conn = sqlite3.connect("formulas.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS Parties (
    Party_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Party_Name TEXT NOT NULL,
    Email TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Formulas (
    Party_ID INTEGER,
    Grade TEXT,
    Compound_Name TEXT,
    Quantity REAL,
    Unit TEXT,
    PRIMARY KEY (Party_ID, Grade, Compound_Name),
    FOREIGN KEY (Party_ID) REFERENCES Parties(Party_ID)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Custom_Grades (
    Grade_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Party_ID INTEGER,
    Grade_Name TEXT,
    Based_On TEXT,
    Created_At TEXT,
    FOREIGN KEY (Party_ID) REFERENCES Parties(Party_ID)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Custom_Formula_Entries (
    Grade_ID INTEGER,
    Compound_Name TEXT,
    Quantity REAL,
    Unit TEXT,
    FOREIGN KEY (Grade_ID) REFERENCES Custom_Grades(Grade_ID)
)
''')

conn.commit()

# ------------------------
# Helper Functions
# ------------------------
def get_party_names():
    cursor.execute("SELECT Party_Name FROM Parties")
    return [row[0] for row in cursor.fetchall()]

def get_party_id(name):
    name = name.strip()
    cursor.execute("SELECT Party_ID FROM Parties WHERE Party_Name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        st.error(f"❌ Party '{name}' not found in database.")
        return None

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
        grade_id = row[0]
        cursor.execute("SELECT Compound_Name, Quantity, Unit FROM Custom_Formula_Entries WHERE Grade_ID=?", (grade_id,))
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
    try:
        st.info(f"Deleting Party ID: {party_id}")
        cursor.execute("DELETE FROM Custom_Formula_Entries WHERE Grade_ID IN (SELECT Grade_ID FROM Custom_Grades WHERE Party_ID=?)", (party_id,))
        cursor.execute("DELETE FROM Custom_Grades WHERE Party_ID=?", (party_id,))
        cursor.execute("DELETE FROM Formulas WHERE Party_ID=?", (party_id,))
        cursor.execute("DELETE FROM Parties WHERE Party_ID=?", (party_id,))
        conn.commit()
        st.success("✅ Party deleted from database.")
    except Exception as e:
        st.error(f"Error during deletion: {e}")

unit_multipliers = {"kg": 1000, "g": 1, "mg": 0.001}

compound_template = [
    ("Resin", ["Resin China", "Resin Shree Ram"]),
    ("Plasticizer", ["CPW", "DBP", "DOP"]),
    ("Stabilizer", ["Stabilizer Yamuna", "Stabilizer Nova", "Stabilizer Rejoice"]),
    ("Blowing Agent", ["OBSH"]),
    ("Filler", ["FW", "DHRUV"]),
    ("Color Additives", ["Toner", "OB"]),
    ("Other Additives", ["G-3", "TT", "Steric Acid", "Euamol"])
]

# ------------------------
# Streamlit UI
# ------------------------
st.set_page_config(layout="wide")
st.title("📦 Smart Slip Generator")

# ------------------------
# Add New Party
# ------------------------
with st.expander("➕ Add New Party (Admin Only)"):
    password = st.text_input("Enter Admin Password", type="password")
    if password == "Ashu10":
        st.success("Access granted")
        new_party = st.text_input("New Party Name")
        new_email = st.text_input("Email (optional)")
        new_grade = st.text_input("Initial Grade Name")

        st.write("### Fill Formula (Enter quantity & unit)")
        new_formula_data = []
        for category, options in compound_template:
            st.markdown(f"**{category}**")
            for option in options:
                col1, col2 = st.columns([2, 1])
                with col1:
                    qty = st.number_input(f"{option} (Qty)", min_value=0.0, step=0.1, key=f"qty_{option}")
                with col2:
                    unit = st.selectbox("Unit", ["kg", "g", "mg"], key=f"unit_{option}")
                if qty > 0:
                    new_formula_data.append({"Compound": option, "Quantity": qty, "Unit": unit})

        if st.button("Create Party"):
            if new_party and new_grade and new_formula_data:
                new_party_id = add_new_party(new_party, new_email)
                df_to_save = pd.DataFrame(new_formula_data)
                save_base_formula(new_party_id, new_grade, df_to_save)
                st.success(f"✅ Party '{new_party}' with grade '{new_grade}' created.")
                st.experimental_rerun()
            else:
                st.warning("Fill all fields and enter at least one formula entry.")
    elif password:
        st.error("Incorrect password")

# ------------------------
# Delete Party
# ------------------------
with st.expander("🗑️ Delete Party (Admin Only)"):
    del_pass = st.text_input("Admin Password to Delete Party", type="password", key="delete_party_pass")
    if del_pass == "Ashu10":
        st.success("Access granted")
        party_list = get_party_names()
        if party_list:
            del_party_name = st.selectbox("Select Party to Delete", party_list, key="party_to_delete")

            if st.button("Delete Selected Party"):
                if del_party_name and st.checkbox(f"⚠️ Confirm deletion of '{del_party_name}' and all related data"):
                    delete_party_by_name(del_party_name)
                    st.experimental_rerun()
    elif del_pass:
        st.error("Incorrect password")

# ------------------------
# Slip Generator
# ------------------------
party_list = get_party_names()
party_name = st.selectbox("Select Party", party_list)

if party_name:
    party_id = get_party_id(party_name)
    grade_list = get_grades_for_party(party_id)
    grade = st.selectbox("Select Grade", grade_list)

    if "load_formula" not in st.session_state:
        st.session_state.load_formula = False

    if st.button("Load Formula"):
        st.session_state.load_formula = True

    if st.session_state.load_formula:
        formula = get_formulas(party_id, grade)
        if not formula:
            st.warning("No formula found for this grade.")
        else:
            if "edited_formula" not in st.session_state:
                st.session_state.edited_formula = pd.DataFrame(formula, columns=["Compound", "Quantity", "Unit"])

            st.subheader("📋 Editable Formula")
            edited_df = st.data_editor(st.session_state.edited_formula, key="formula_editor", num_rows="dynamic")
            st.session_state.edited_formula = edited_df

            st.subheader("📦 Order Details")
            weight = st.number_input("Total Weight to Produce", min_value=1.0, step=1.0)
            output_unit = st.selectbox("Display Output In", ["kg", "g", "mg"])
            order_type = st.radio("Order Type", ["Standard", "Custom"])
            new_grade_name = st.text_input("New Grade Name (if saving custom)")

            if st.button("Save Custom Grade"):
                if new_grade_name.strip():
                    save_custom_grade(party_id, grade, new_grade_name, edited_df)
                    st.success(f"Custom grade '{new_grade_name}' saved.")
                else:
                    st.warning("Enter a valid name.")

            if st.button("Generate Slip"):
                def calc_scaled(row):
                    qty = row["Quantity"]
                    unit = row["Unit"]
                    qty_g = qty * unit_multipliers[unit]
                    total_g = qty_g * weight
                    final = total_g / unit_multipliers[output_unit]
                    if output_unit == "kg" and final < 1:
                        return f"{final:.2f} kg ({total_g:.0f} g)"
                    elif output_unit == "g" and final < 1000:
                        return f"{final:.2f} g ({total_g:.0f} mg)"
                    elif output_unit == "mg" and final < 1000000:
                        return f"{final:.2f} mg ({total_g / 1000:.2f} g)"
                    return f"{final:.2f} {output_unit}"

                scaled_df = edited_df.copy()
                scaled_df["Final Quantity"] = scaled_df.apply(calc_scaled, axis=1)
                today = datetime.now().strftime("%d.%m.%y")
                st.markdown(f"### 🧾 Grade: `{grade}`, {today}`")
                st.dataframe(scaled_df[["Compound", "Final Quantity"]])

conn.close()
