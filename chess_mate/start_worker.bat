@echo off
set PYTHONPATH=%PYTHONPATH%;%~dp0
python -c "from rq import Connection, Worker; from redis import Redis; redis_conn = Redis(); w = Worker(['default'], connection=redis_conn); w.work()" 