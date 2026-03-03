import psycopg2
conn=psycopg2.connect('postgresql://postgres:root@localhost:5432/gestiqclouddb_dev')
cur=conn.cursor()
cur.execute("select field, required from sector_field_defaults where module='imports_expenses' and sector='global' order by ord")
print(cur.fetchall())
cur.close(); conn.close()
