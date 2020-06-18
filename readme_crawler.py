import sqlite3
import base64
import re

print("Connecting to database")
con = sqlite3.connect('db.sqlite3')
cur = con.cursor()

get_all_readme_with_unknown_license = """
SELECT repo_id, readme
FROM repos
WHERE repo_license='unknown'
AND readme IS NOT NULL
AND readme != ''
"""
cur.execute(get_all_readme_with_unknown_license)
all_readme_with_unknown_license = cur.fetchall()

repos_with_license_in_readme = []
for repo_id, readme in all_readme_with_unknown_license:
    try:
        readme_text = base64.b64decode(readme).decode('utf-8')
        if re.search('license', readme_text, re.IGNORECASE):
            update_license_type = """
            UPDATE repos
            SET repo_license = 'readme'
            WHERE repo_id = %s
            """ % repo_id
            cur.execute(update_license_type)
            con.commit()
            print(repo_id)
    except Exception as e:
        print(e)

cur.close()
con.close()
