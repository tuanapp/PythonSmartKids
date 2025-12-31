import os
import re
import sys
import psycopg2

UID = sys.argv[1] if len(sys.argv) > 1 else 'zTCNkGbtvPRscMo98innxe1gqI73'

# locate .env.production at repo root (one level up)
here = os.path.dirname(__file__)
env_path = os.path.abspath(os.path.join(here, '..', '.env.production'))

if not os.path.exists(env_path):
    print(f'.env.production not found at {env_path}')
    sys.exit(2)

creds = {}
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            creds[k.strip()] = v.strip().strip('"').strip("'")

required = ['NEON_DBNAME', 'NEON_USER', 'NEON_PASSWORD', 'NEON_HOST', 'NEON_SSLMODE']
for r in required:
    if r not in creds:
        print(f'Missing {r} in .env.production')
        sys.exit(3)

print('Connecting to:', creds['NEON_HOST'], 'db:', creds['NEON_DBNAME'], 'user:', creds['NEON_USER'])

try:
    conn = psycopg2.connect(
        dbname=creds['NEON_DBNAME'],
        user=creds['NEON_USER'],
        password=creds['NEON_PASSWORD'],
        host=creds['NEON_HOST'],
        sslmode=creds.get('NEON_SSLMODE', 'require')
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM performance_reports WHERE uid = %s", (UID,))
    count = cur.fetchone()[0]
    print('Found count:', count)

    cur.execute("SELECT id, uid, report_content, success, created_at FROM performance_reports WHERE uid = %s ORDER BY created_at DESC LIMIT 10", (UID,))
    rows = cur.fetchall()
    if not rows:
        print('No rows returned')
    else:
        for r in rows:
            print('---')
            print('id:', r[0])
            print('uid:', r[1])
            # print truncated report content
            content = (r[2] or '')
            print('report_content (first 200 chars):')
            print(content[:200].replace('\n', '\\n'))
            print('success:', r[3])
            print('created_at:', r[4])
    cur.close()
    conn.close()
except Exception as e:
    print('ERROR:', e)
    sys.exit(4)
