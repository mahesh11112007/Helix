import sqlite3

conn = sqlite3.connect('kiraak_study.db')
c = conn.cursor()
c.execute("""
SELECT t.name, u.name, s.name 
FROM topics t
LEFT JOIN units u ON t.unit_id = u.id
LEFT JOIN subjects s ON u.subject_id = s.id
WHERE t.name LIKE 'Topic %' OR t.name LIKE 'Topic%'
""")
rows = c.fetchall()
for r in rows:
    print(r)
conn.close()
