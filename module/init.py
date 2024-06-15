from module.cloudflare.storage_mgmt import start_bandwidth_push, start_status_push
from module.cloudflare.proxy_load_balancing import init_node
from module.timed_backup.timed_backup import start_timed_backup


def init_task(app):
    start_timed_backup(app)
    start_bandwidth_push(app)
    start_status_push(app)
    init_node(app)
