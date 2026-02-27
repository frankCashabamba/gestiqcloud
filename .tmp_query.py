import psycopg2
conn=psycopg2.connect("postgresql://postgres:root@localhost:5432/gestiqclouddb_dev")
cur=conn.cursor()
cur.execute("select module,count(*) from sector_field_defaults where module like 'imports_%' group by 1 order by 1")
print('sector_field_defaults:',cur.fetchall())
cur.execute("select module,count(*) from tenant_field_configs where module like 'imports_%' group by 1 order by 1")
print('tenant_field_configs:',cur.fetchall())
cur.close();conn.close()
