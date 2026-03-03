import psycopg2
conn=psycopg2.connect('postgresql://postgres:root@localhost:5432/gestiqclouddb_dev')
cur=conn.cursor()
cur.execute("select id, tenant_id, source_type, template_id, file_name, status, created_at from imports_batches order by created_at desc limit 5")
for r in cur.fetchall():
    print(r)
cur.close(); conn.close()
