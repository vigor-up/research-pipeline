import sqlite3
c=sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
print(c.execute('SELECT kpi_id,value,region FROM market_kpi WHERE species=chr(102)+chr(105)+chr(110)+chr(105)+chr(115)+chr(104)+chr(101)+chr(114)+chr(95)+chr(112)+chr(105)+chr(103) AND kpi_id LIKE chr(37)+chr(102)+chr(99)+chr(114)+chr(37) ORDER BY credibility DESC LIMIT 5').fetchall())