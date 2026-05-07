import sqlite3
c = sqlite3.connect(r'D:\LLM\workflows\research-pipeline-v2\local\market_data.db')
for t in c.execute('SELECT name FROM sqlite_master WHERE type=chr(39)+chr(116)+chr(97)+chr(98)+chr(108)+chr(101)+chr(39)').fetchall():
    print(t[0], c.execute('SELECT COUNT(*) FROM '+t[0]).fetchone()[0])