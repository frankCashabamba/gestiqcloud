import psycopg2
conn=psycopg2.connect('postgresql://postgres:root@localhost:5432/gestiqclouddb_dev')
cur=conn.cursor()
cur.execute("select tablename from pg_tables where schemaname='public' and tablename like 'imports_%' order by 1")
print([r[0] for r in cur.fetchall()])
cur.close(); conn.close()
