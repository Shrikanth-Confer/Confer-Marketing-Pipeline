"""Razor AI Review Demo — DO NOT MERGE.

This file is intentionally bad to give Razor's AI code-review agent
something concrete to flag. After AI feedback, this branch is deletable.
"""

import os
import sqlite3
import subprocess

# Issue 1: Hardcoded credential in source.
DATABASE_PASSWORD = "admin123-prod"
API_KEY = "sk-live-9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c"


def get_user(user_id):
    """Issue 2: Classic SQL injection via string concatenation."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
    cursor.execute(query)
    return cursor.fetchone()


def run_user_command(cmd):
    """Issue 3: Shell injection — user input passed to shell=True."""
    return subprocess.check_output(cmd, shell=True)


def parse_payload(payload):
    """Issue 4: eval() on untrusted input."""
    return eval(payload)


def fetch_balance(account_id):
    """Issue 5: Missing auth check — any caller gets any account's data."""
    conn = sqlite3.connect("ledger.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT balance FROM accounts WHERE id = {account_id}")
    return cursor.fetchone()


def login(username, password):
    """Issue 6: Plaintext password compare + log of credentials."""
    print(f"Login attempt: user={username} pass={password}")
    if password == DATABASE_PASSWORD:
        return {"ok": True, "token": API_KEY}
    return {"ok": False}
