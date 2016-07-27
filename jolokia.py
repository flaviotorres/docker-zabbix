#!/usr/bin/env python
# Flavio Torres, flavio.torres@walmart.com
# Jul, 2016
# Read statistics from an deployed jolokia app inside docker container and send to zabbix

from docker_service import DockerService
from pyjolokia import Jolokia
import re
import json
import socket 

parser = DockerService.OptionParser()
parser.add_option('-u', '--url', default='unix://var/run/docker.sock', help='URL for Docker service (Unix or TCP socket).')
parser.add_option('-l', action="store_true", dest="list", default=False)
(opts, args) = parser.parse_args()

hostname = socket.gethostname().split('.')[0]

# Docker access
docker_service = DockerService.DockerService(opts.url)
containerslist = docker_service.list_containers()
## TODO: implement None return handle
if opts.list:
    con_list = []
    ## TODO: implement None return handle
    ## list of containers
    for container in containerslist:
        Name = container['Names']
        Ports = container['Ports'][0]
        Name = re.sub('/|_[0-9].*','', Name[0])
	Name = hostname+'_'+Name
	
        if not Name in [hostname+'_twemproxy']:
            Port = Ports['PublicPort']
            con_list.append({'{#NAME}': Name+"_java"})
    con_dict = {}
    con_dict['data'] = con_list
    print(json.dumps(con_dict))
else:
    for container in containerslist:
        # Anda pelos containers, se nao for twemproxy (porque nao tem porta publica) pega a porta para conectar local do container/jolokia
        Name = container['Names']
        Ports = container['Ports'][0]
        Name = re.sub('/|_[0-9].*','', Name[0])
	Name = hostname+'_'+Name

        if not Name in [hostname+'_twemproxy']:
            Port = Ports['PublicPort']
            j4p = Jolokia('http://localhost:'+ str(Port) + '/jolokia/')

            j4p.add_request(type = 'read', mbean='java.lang:type=Memory')
            j4p.add_request(type = 'read', mbean='java.lang:type=Threading', attribute='ThreadCount')

            try: 
                bulkdata = j4p.getRequests()
                # print bulkdata

                # preparing key name
                key_NonHeapMemoryUsageMax = 'user.docker.java[NonHeapMemoryUsageMax]'
                key_NonHeapMemoryCommitted = 'user.docker.java[NonHeapMemoryCommitted]'
                key_NonHeapMemoryInit = 'user.docker.java[NonHeapMemoryInit]'
                key_NonHeapMemoryUsed = 'user.docker.java[NonHeapMemoryUsed]'

                key_HeapMemoryUsageMax = 'user.docker.java[HeapMemoryUsageMax]'
                key_HeapMemoryCommitted = 'user.docker.java[HeapMemoryCommitted]'
                key_HeapMemoryInit = 'user.docker.java[HeapMemoryInit]'
                key_HeapMemoryUsed = 'user.docker.java[HeapMemoryUsed]'
                key_threadNumber = 'user.docker.java[threadNumber]'

                # grab key values
                NonHeapMemoryUsageMax = bulkdata[0]['value']['NonHeapMemoryUsage']['max']
                NonHeapMemoryCommitted = bulkdata[0]['value']['NonHeapMemoryUsage']['committed']
                NonHeapMemoryInit = bulkdata[0]['value']['NonHeapMemoryUsage']['init']
                NonHeapMemoryUsed = bulkdata[0]['value']['NonHeapMemoryUsage']['used']

                HeapMemoryUsageMax = bulkdata[0]['value']['HeapMemoryUsage']['max']
                HeapMemoryCommitted = bulkdata[0]['value']['HeapMemoryUsage']['committed']
                HeapMemoryInit = bulkdata[0]['value']['HeapMemoryUsage']['init']
                HeapMemoryUsed = bulkdata[0]['value']['HeapMemoryUsage']['used']

                threadNumber = bulkdata[1]['value']


                packet = [
                    DockerService.ZabbixMetric(Name, key_NonHeapMemoryUsageMax, NonHeapMemoryUsageMax),
                    DockerService.ZabbixMetric(Name, key_NonHeapMemoryCommitted, NonHeapMemoryCommitted),
                    DockerService.ZabbixMetric(Name, key_NonHeapMemoryInit, NonHeapMemoryInit),
                    DockerService.ZabbixMetric(Name, key_NonHeapMemoryUsed, NonHeapMemoryUsed),

                    DockerService.ZabbixMetric(Name, key_HeapMemoryUsageMax, HeapMemoryUsageMax),
                    DockerService.ZabbixMetric(Name, key_HeapMemoryCommitted, HeapMemoryCommitted),
                    DockerService.ZabbixMetric(Name, key_HeapMemoryInit, HeapMemoryInit),
                    DockerService.ZabbixMetric(Name, key_HeapMemoryUsed, HeapMemoryUsed),

                    DockerService.ZabbixMetric(Name, key_threadNumber, threadNumber),
                ]

                ## DEBUG
                #print packet
                result = DockerService.ZabbixSender(use_config=True).send(packet)
                #print result

            except:
                print "Could not connect. Got error HTTP Error 404: Not Found %s", Name
