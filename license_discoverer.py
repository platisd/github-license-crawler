import datetime
import os
import sqlite3
import tempfile
import time
import urllib.request
from github import Github
import github_credentials
import zipfile
import pathlib
import shutil

print("Connecting to database")
con = sqlite3.connect('db.sqlite3')
cur = con.cursor()

print("Connecting to GitHub")
g = Github(login_or_token=github_credentials.access_token, per_page=200)

get_all_repos_and_url_with_unknown_license = """
SELECT repo_id, html_url
FROM random_unknown_repos
WHERE repo_license='unknown'
"""
cur.execute(get_all_repos_and_url_with_unknown_license)
repositories = cur.fetchall()

temp_dir = tempfile.gettempdir()

for repo_id, url in repositories:
    try:
        rate_limit_remaining = g.rate_limiting[0]
        if rate_limit_remaining < 5:
            current_time = datetime.now().strftime("%H:%M:%S")
            print("Rate limit reached on %s, pausing for 10 minutes " % current_time)
            con.commit()
            time.sleep(600)

        print("Repo id %d" % repo_id)

        # Download the repo as an archive
        branch = g.get_repo(repo_id).default_branch
        zip_url = url + "/archive/" + branch + ".zip"
        zip_local_path = os.path.join(temp_dir, str(repo_id) + ".zip")
        urllib.request.urlretrieve(zip_url, zip_local_path)

        # Unzip the archive
        extracted_repo_path = os.path.join(temp_dir, str(repo_id) + "-contents")
        with zipfile.ZipFile(zip_local_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_repo_path)

        # Check each file in repo for licensing information
        p = pathlib.Path(extracted_repo_path)
        license_detected = False
        for file in p.glob('**/*'):
            find_license = "askalono id --optimize " + str(file) + " > /dev/null 2>&1"
            license_detected = os.system(find_license) == 0
            print(".", end='', flush=True)
            if license_detected:
                update_license_type = """
                UPDATE random_unknown_repos
                SET repo_license = 'file'
                WHERE repo_id = %s
                """ % repo_id
                cur.execute(update_license_type)
                con.commit()
                print(" ficense found: " + str(file))
                break
        if not license_detected:
            update_license_type = """
            UPDATE random_unknown_repos
            SET repo_license = 'no-license'
            WHERE repo_id = %s
            """ % repo_id
            cur.execute(update_license_type)
            con.commit()
            print(" license NOT found")

        # Remove downloaded repository sources and archive
        if os.path.exists(zip_local_path):
            os.remove(zip_local_path)
            shutil.rmtree(extracted_repo_path, ignore_errors=True)

    except Exception as e:
        print(e)
        print("Zip URL: %s" % zip_url)
