from etcd3 import client
from socket import gethostname, gethostbyname
from ipaddress import ip_network
from itertools import islice
from subprocess import run
from json import dump
from os import chmod, environ
from jinja2 import Environment, FileSystemLoader

ETCD_HOST = environ['ETCD_HOST']
CNI_VERSION = environ['CNI_VERSION']
CNI_NAME = environ['CNI_NAME']
CNI_TYPE = environ['CNI_TYPE']
BRIDGE_NAME = environ['BRIDGE_NAME']
IP_SUBNET = environ['IP_SUBNET']
IP_SUBNET_MARGIN = int(environ['IP_SUBNET_MARGIN'])
ETCD_PREFIX = environ['ETCD_PREFIX']
ETCD_COUNTER_KEY = environ['ETCD_COUNTER_KEY']
CNI_CONFIG_LOCATION = environ['CNI_CONFIG_LOCATION']
CNI_PLUGIN_LOCATION = environ['CNI_PLUGIN_LOCATION']

etcd_client = client(host=ETCD_HOST)


def counter(client_obj, key):
    client_obj.put(key, str())
    _, counter_metadata = etcd_client.get(key)
    return counter_metadata.version


def get_hosts(client_obj):
    return {metadata.key.decode().replace(f'{ETCD_PREFIX}/', ""): value.decode() for value, metadata in
            client_obj.get_prefix(ETCD_PREFIX)}


def create_routes(hosts, bridge_subnet):
    for key, value in hosts.items():
        print()
        if value != bridge_subnet:
            run(
                ['bash', '-c', f'ip route add {value} via {gethostbyname(key)}'])


def get_host_subnet(client_obj, key):
    host_subnet, _ = client_obj.get(key)
    if not host_subnet:
        count = counter(client_obj, ETCD_COUNTER_KEY)
        client_obj.put_if_not_exists(key, str(next(
            islice(ip_network(IP_SUBNET).subnets(prefixlen_diff=IP_SUBNET_MARGIN), count, None))))
        host_subnet, _ = client_obj.get(key)
    return host_subnet.decode()


def create_bridge(bridge_subnet):
    run(['bash', '-c', f'brctl addbr {BRIDGE_NAME}'])
    run(['bash', '-c', f'ip link set {BRIDGE_NAME} up'])
    run(['bash', '-c', f'ip addr add {bridge_subnet} dev {BRIDGE_NAME}'])


def write_config(bridge_subnet):
    with open(CNI_CONFIG_LOCATION, 'w', encoding='utf-8') as f:
        dump(
            {
                "cniVersion": CNI_VERSION,
                "name": CNI_NAME,
                "type": CNI_TYPE,
                "network": IP_SUBNET,
                "subnet": bridge_subnet
            }, f, ensure_ascii=False, indent=4)

        chmod(CNI_CONFIG_LOCATION, 0o600)


def write_plugin(bridge_subnet):
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("plugin.j2")
    content = template.render(CNI_VERSION=CNI_VERSION, BRIDGE_NAME=BRIDGE_NAME, bridge_subnet=bridge_subnet)
    with open(CNI_PLUGIN_LOCATION, mode="w", encoding="utf-8") as file:
        file.write(content)
    chmod(CNI_PLUGIN_LOCATION, 0o700)


current_host_subnet = get_host_subnet(etcd_client, f'{ETCD_PREFIX}/{gethostname()}')
create_bridge(current_host_subnet)
create_routes(get_hosts(etcd_client), current_host_subnet)
write_config(current_host_subnet)
write_plugin(current_host_subnet)

events_iterator, cancel = etcd_client.watch_prefix(ETCD_PREFIX)
for event in events_iterator:
    event_key = event.key.decode().replace(f'{ETCD_PREFIX}/', "")
    event_value = event.value.decode()
    create_routes({event_key: event_value}, current_host_subnet)
