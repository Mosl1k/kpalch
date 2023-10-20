
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

cursor.execute("""select * from sqlite_master
            where type = 'table'""")
tables = cursor.fetchall()

for table in tables:
    print(table)  # информация о таблицах
#  print(table[1]) #названия таблиц

