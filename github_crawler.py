from github import Github
import sqlite3
import time
import github_credentials
from datetime import datetime

con = sqlite3.connect('db.sqlite3')
cur = con.cursor()
create_repos_table = """
CREATE TABLE IF NOT EXISTS repos (
    repo_id integer PRIMARY KEY,
    full_name text NOT NULL,
    html_url text NOT NULL,
    is_fork integer NOT NULL,
    repo_license text NOT NULL)"""
cur.execute(create_repos_table)

# Get latest ID
get_latest_repo_id = "SELECT max(repo_id) FROM repos"
cur.execute(get_latest_repo_id)
latest_repo_id_in_database = 0
get_latest_repo_id_result = cur.fetchone()[0]
if get_latest_repo_id_result is not None:
    latest_repo_id_in_database = get_latest_repo_id_result

g = Github(login_or_token=github_credentials.access_token, per_page=200)

# It will take too long to collect all repos, so jump over many of them
# to get a sampling from a different time period
repo_id_step_size = 1000000
repo_id_to_start = latest_repo_id_in_database + repo_id_step_size
for repo in g.get_repos(since=repo_id_to_start, visibility="public"):
    rate_limit_remaining = g.rate_limiting[0]
    if rate_limit_remaining < 5:
        current_time = datetime.now().strftime("%H:%M:%S")
        print("Rate limit reached on %s, pausing for 1 hour" % current_time)
        con.commit()
        time.sleep(3600)
    # Commit to database every 10 requests
    if rate_limit_remaining % 10 == 0:
        con.commit()

    repo_id = repo.id
    full_name = repo.full_name
    html_url = repo.html_url
    is_fork = int(repo.fork)
    repo_license = "unknown"
    try:
        repo_license = repo.get_license().license.key
    except:
        pass

    print("id: " + str(repo_id))
    try:
        # Insert repo to database
        insert_repo_sql = """
        INSERT INTO repos (repo_id, full_name, html_url, is_fork, repo_license)
        VALUES (?, ?, ?, ?, ?)"""
        cur.execute(insert_repo_sql, (repo_id, full_name, html_url, is_fork, repo_license))
    except:
        pass

con.commit()
con.close()
