DB_NAME=app_db
DB_USER=app_user
DB_PASS=xL4noaDNexXCSseoqWHE
DB_HOST=10.104.0.6
DB_PORT=3306

# Local connection options on this machine
# 1) TCP via intranet IP: available
LOCAL_TCP_HOST=10.104.0.6

# 2) Socket/default local route via localhost: available
LOCALHOST_HOST=localhost

# 3) TCP via loopback 127.0.0.1: unavailable now
# Reason: MySQL bind-address is set to 10.104.0.6, not 127.0.0.1
LOOPBACK_HOST=127.0.0.1
LOOPBACK_AVAILABLE=false

# Example commands
# mysql -h 10.104.0.6 -P 3306 -u app_user -pxL4noaDNexXCSseoqWHE app_db
# mysql -h localhost -u app_user -pxL4noaDNexXCSseoqWHE app_db

