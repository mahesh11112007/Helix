import sqlite3

conn = sqlite3.connect('kiraak_study.db')
c = conn.cursor()

# 1. Find orphaned topics
c.execute("DELETE FROM topics WHERE name LIKE 'Topic %' OR name LIKE 'Topic%'")

# 2. Find subjects named 'Weakest Topic' and delete them and their cascading dependencies
c.execute("SELECT id FROM subjects WHERE name = 'Weakest Topic'")
bad_subjects = c.fetchall()

for (subj_id,) in bad_subjects:
    # Delete topics in units of this subject
    c.execute("DELETE FROM topics WHERE unit_id IN (SELECT id FROM units WHERE subject_id = ?)", (subj_id,))
    # Delete units
    c.execute("DELETE FROM units WHERE subject_id = ?", (subj_id,))
    # Delete subject
    c.execute("DELETE FROM subjects WHERE id = ?", (subj_id,))

# Delete orphaned units
c.execute("DELETE FROM units WHERE subject_id IS NULL OR subject_id = ''")

# Delete orphaned topics
c.execute("DELETE FROM topics WHERE unit_id IS NULL OR unit_id = ''")

conn.commit()
print("Cleaned up dummy topics!")
conn.close()
