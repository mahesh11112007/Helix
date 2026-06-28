import sqlite3

conn = sqlite3.connect('kiraak_study.db')
cursor = conn.cursor()
cursor.execute("SELECT content FROM notes WHERE content LIKE '%Calculate the Sum of Numbers%' LIMIT 1;")
row = cursor.fetchone()
if row:
    print(repr(row[0][:1000]))
else:
    print("No notes found")
conn.close()
