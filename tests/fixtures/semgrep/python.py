# Semgrep test target for app/scanners/rules/semgrep/python.yml.
# Annotations: "ruleid:" must match on the next line, "ok:" must not.
import os
import pickle
import subprocess

import requests
import yaml


def dynamic(user_input, cursor, payload, user_id):
    # ruleid: rsa-python-eval-exec
    eval(user_input)
    # ruleid: rsa-python-eval-exec
    exec(user_input)
    # ok: rsa-python-eval-exec
    eval("1 + 1")

    # ruleid: rsa-python-subprocess-shell-true
    subprocess.run(f"ls {user_input}", shell=True)
    # ruleid: rsa-python-subprocess-shell-true
    subprocess.Popen(user_input, shell=True)
    # ok: rsa-python-subprocess-shell-true
    subprocess.run(["ls", user_input])
    # ok: rsa-python-subprocess-shell-true
    subprocess.run("ls -la", shell=True)

    # ruleid: rsa-python-os-system
    os.system("rm " + user_input)
    # ok: rsa-python-os-system
    os.system("clear")

    # ruleid: rsa-python-sql-string-building
    cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
    # ruleid: rsa-python-sql-string-building
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    # ruleid: rsa-python-sql-string-building
    cursor.execute("SELECT * FROM users WHERE name = '" + user_input + "'")
    # ruleid: rsa-python-sql-string-building
    cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
    # ok: rsa-python-sql-string-building
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

    # ruleid: rsa-python-pickle-load
    pickle.loads(payload)

    # ruleid: rsa-python-yaml-unsafe-load
    yaml.load(payload)
    # ruleid: rsa-python-yaml-unsafe-load
    yaml.load(payload, Loader=yaml.Loader)
    # ok: rsa-python-yaml-unsafe-load
    yaml.load(payload, Loader=yaml.SafeLoader)
    # ok: rsa-python-yaml-unsafe-load
    yaml.safe_load(payload)

    # ruleid: rsa-python-tls-verification-disabled
    requests.get("https://example.com", verify=False)
    # ok: rsa-python-tls-verification-disabled
    requests.get("https://example.com")
