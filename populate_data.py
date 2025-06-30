import sqlite3

# Connect to your existing database
conn = sqlite3.connect("formulas.db")
cursor = conn.cursor()

# Step 1: Add the party
party_name = "ABC"
cursor.execute("INSERT OR IGNORE INTO Parties (Party_Name) VALUES (?)", (party_name,))
conn.commit()

# Step 2: Get Party_ID
cursor.execute("SELECT Party_ID FROM Parties WHERE Party_Name=?", (party_name,))
party_id = cursor.fetchone()[0]

# Step 3: Define formula
grade_name = "250R"
formula = [
    ("Resin China", 12.5, "kg"),
    ("Resin Shree Ram", 12.5, "kg"),
    ("Yamuna", 10, "kg"),
    ("CPW", 10, "kg"),
    ("DBP", 10, "kg"),
    ("DOP", 10, "kg"),
    ("FW", 500, "g"),
    ("DHRUV", 120, "g"),
    ("OBSH", 200, "g"),
    ("Stabilizer", 1050, "g"),
    ("Euamol", 200, "g"),
    ("G-3", 250, "g"),
    ("TT", 1800, "g"),
    ("OB", 10, "g"),
    ("Toner", 50, "g"),
    ("Steric Acid", 300, "g"),
]

# Step 4: Insert formula rows
for compound, qty, unit in formula:
    cursor.execute("""
        INSERT OR IGNORE INTO Formulas (Party_ID, Grade, Compound_Name, Quantity, Unit)
        VALUES (?, ?, ?, ?, ?)
    """, (party_id, grade_name, compound, qty, unit))

conn.commit()
conn.close()
print("✅ Formula for ABC / 250R inserted successfully.")
