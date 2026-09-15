import sqlite3
import pandas as pd

conn = sqlite3.connect("stabil.db")

query = "SELECT * FROM sessions"

df = pd.read_sql_query(query, conn)

print(df.head())

conn.close()


