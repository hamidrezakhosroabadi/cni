#!/usr/bin/python3
from os import environ
from json import dumps
import random
from subprocess import check_output

CNI_COMMAND = environ['CNI_COMMAND']
CNI_NETNS = environ['CNI_NETNS'].split('/')[-1]
CNI_IFNAME = environ["CNI_IFNAME"]
CNI_BR_NAME = "cni0"

if CNI_COMMAND == "VERSION":
    print(dumps({
        "cniVersion": "0.0.1",
        "supportedVersions": ["0.0.1"]
    }))

if CNI_COMMAND == "ADD":
	random_name = str(random.randint(0,100000))
	random_ip = f'192.168.10.{random.randint(0, 255)}/24'
	check_output(['bash','-c', f'ip link add {CNI_IFNAME} type veth peer name cni-veth-{random_name}'])
	check_output(['bash','-c', f'ip link set {CNI_IFNAME} netns {CNI_NETNS}'])
	check_output(['bash','-c', f'ip link set cni-veth-{random_name} master {CNI_BR_NAME}'])
	check_output(['bash','-c', f'ip -n {CNI_NETNS} addr add {random_ip} dev {CNI_IFNAME}'])
	check_output(['bash','-c', f'ip -n {CNI_NETNS} link set {CNI_IFNAME} up'])
	check_output(['bash','-c', f'ip link set cni-veth-{random_name} up'])

	print(dumps({
		"cniVersion": "0.0.1",
		"interfaces": [
			{
				"name": CNI_IFNAME,
				"mac": "02:00:00:%02x:%02x:%02x" % (random.randint(0, 255),
								random.randint(0, 255),
								random.randint(0, 255)),
				"sandbox": CNI_NETNS
			}
		],
		"ips": [
			{
				"version": "4",
				"address": random_ip,
				"gateway": "192.168.10.1",
				"interface": 0
			}
		]
	}))
if CNI_COMMAND == "GET":
    print("GET is not supported!")

if CNI_COMMAND == "DEL":
    print("DEL is not supported!")
