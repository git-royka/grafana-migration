#!/usr/bin/python3

"""
Everyday Error rate summary sender
Example item for Zabbix:
logs-stat-sender.py[--elastic,"elastic:80",--doc_type,"prod-zabbix-mail",--kibana,"https://kibana.com",--src,"noreply@mail.com", --to "error@mail.com" --api_url "http://mail.com/api" --user "user" --pswd "password" --key "false"]
"""

import argparse
from collections import OrderedDict
from datetime import datetime, timedelta
from urllib import parse

import requests
from elasticsearch5 import Elasticsearch

parser = argparse.ArgumentParser()

parser.add_argument("--elastic", required=True,
                    help='Elasticsearch host:port')
parser.add_argument("--es_version", default=6,
                    help='Elasticsearch version. 5 or 6')
parser.add_argument("--kibana", required=True,
                    help='Kibana endpoint in format "https://kibana.com"')
parser.add_argument("--doc_type", required=True,
                    help='Analog fields.document_type in Elasticsearch')

parser.add_argument("--index", default='filebeat-',
                    help='Index prefix where logs locate (default: \'filebeat-\')')
parser.add_argument("--top", default='5',
                    help='How many top messages need collect (default: 5)')

parser.add_argument("--api_url", required=True, help='Mail API url')
parser.add_argument("--user", required=True, help='Mail API user')
parser.add_argument("--pswd", required=True, help='Mauil API password')
parser.add_argument("--src", required=True, help='Email in "From" field')
parser.add_argument("--to", required=True, help='Email in "To" field')
parser.add_argument("--sender_tpl", default='test_error_rate_reporting',
                    help='template_name')
parser.add_argument("--key", default='false',
                    help='Filter text fields by .keyword')


args = parser.parse_args()


ES = Elasticsearch(args.elastic)

INDEX_DATE = '{0:%Y.%m.%d}'.format(datetime.now() - timedelta(1))
INDEX = args.index + INDEX_DATE

if args.key == "true":
  suffix = ".keyword"
else:
  suffix = ""

BODY = {
    "size": 0,
    "query": {
        "bool": {
            "must": [
                {"term": {"fields.document_type" + suffix: args.doc_type}}
            ]
        }
    },
    "aggs": {
        "group_by_state": {
            "terms": {
                "field": "json.level_name" + suffix,
                "size": 10000
            },
            "aggs": {
                "level_name": {
                    "terms": {
                        "field": "json.message" + suffix,
                        "size": args.top
                    }
                }
            }
        }
    }
}

ES_DATA = ES.search(index=INDEX, body=BODY)


logs_count = OrderedDict([
    ('EMERGENCY', 0),
    ('ALERT', 0),
    ('CRITICAL', 0),
    ('EXCEPTION', 0),
    ('ERROR', 0),
    ('WARNING', 0),
    ('NOTICE', 0),
    ('INFO', 0),
    ('DEBUG', 0),
])

top_logs = OrderedDict([])


# Path to log level name key
for i in ES_DATA['aggregations']['group_by_state']['buckets']:
    log_type = i['key']
    logs_count[log_type] = i['doc_count']
    top_logs[log_type] = {}

    # Path to log level top logs
    for j in i['level_name']['buckets']:
        top_logs[log_type].update({
            j['key']: j['doc_count']
        })

    top_logs[log_type] = sorted(top_logs[log_type].items(), key=lambda t: t[1], reverse=True)



# Add Summary
url = {
    '6': "href=\"{kibana_endpoint}/app/kibana#/discover?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-1d%2Fd,mode:relative,to:now-1d%2Fd))&_a=(columns:!(_source),filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,key:fields.document_type,negate:!f,params:(query:{doc_type},type:phrase),type:phrase,value:{doc_type}),query:(match:(fields.document_type:(query:{doc_type},type:phrase))))),index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,interval:auto,query:(language:lucene,query:''),sort:!('@timestamp',desc))\" target=\"_blank\">{doc_type}".format(kibana_endpoint=args.kibana, doc_type=args.doc_type),
    '5': "href=\"{kibana_endpoint}/app/kibana#/discover?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-2d%2Fd,mode:relative,to:now))&_a=(columns:!(_source),filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'filebeat-*',key:fields.document_type,negate:!f,value:{doc_type}),query:(match:(fields.document_type:(query:{doc_type},type:phrase))))),index:'filebeat-*',interval:auto,query:(query_string:(analyze_wildcard:!t,query:'*')),sort:!('@timestamp',desc))\" target=\"_blank\">{doc_type}".format(kibana_endpoint=args.kibana, doc_type=args.doc_type),
}

email = list([
    EMAIL_BODY_START,
    url[str(args.es_version)],
    EMAIL_BODY_START2
])

for log_level_name in logs_count:
    url = {
        '6': "href=\"{kibana_endpoint}/app/kibana#/discover?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-1d%2Fd,mode:relative,to:now-1d%2Fd))&_a=(columns:!(_source),filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,key:fields.document_type,negate:!f,params:(query:{doc_type},type:phrase),type:phrase,value:{doc_type}),query:(match:(fields.document_type:(query:{doc_type},type:phrase)))),('$state':(store:appState),meta:(alias:!n,disabled:!f,index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,key:json.level_name,negate:!f,params:(query:{log_level_name},type:phrase),type:phrase,value:{log_level_name}),query:(match:(json.level_name:(query:{log_level_name},type:phrase))))),index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,interval:auto,query:(language:lucene,query:''),sort:!('@timestamp',desc))\" target=\"_blank\">".format(kibana_endpoint=args.kibana, doc_type=args.doc_type, log_level_name=log_level_name),
        '5': "href=\"{kibana_endpoint}/app/kibana#/discover?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-2d%2Fd,mode:relative,to:now))&_a=(columns:!(_source),filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'filebeat-*',key:fields.document_type,negate:!f,value:{doc_type}),query:(match:(fields.document_type:(query:{doc_type},type:phrase)))),('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'filebeat-*',key:json.level_name,negate:!f,value:{log_level_name}),query:(match:(json.level_name:(query:{log_level_name},type:phrase))))),index:'filebeat-*',interval:auto,query:(query_string:(analyze_wildcard:!t,query:'*')),sort:!('@timestamp',desc))\" target=\"_blank\">".format(kibana_endpoint=args.kibana, doc_type=args.doc_type, log_level_name=log_level_name),
    }

    email.extend([
        COUNT_START,
        log_level_name,
        COUNT_CENTER,
        COUNT_COLOR[log_level_name],
        COUNT_CENTER2,
        url[str(args.es_version)],
        str(logs_count[log_level_name]),
        COUNT_END
    ])

# Add Details
email.append(EMAIL_BODY_CENTER)

for log_level_name in logs_count:
    try:
        top_logs[log_level_name]
    except KeyError:
        continue

    email.extend([
        TOP_ERRORS_START,
        log_level_name,
        TOP_ERRORS_CENTER
    ])

    log = top_logs[log_level_name]
    for i in range(len(log)):

        if 'Stack trace' not in log[i][0]:
            url_log = parse.quote(log[i][0])
        else:
            # Truncate all what can't understand ES
            url_log = '*' + log[i][0].split(':', 1)[1]
            url_log = url_log.split('Stack trace', 1)[0] + '*'
            url_log = parse.quote(url_log)


        url = {
            '6': "href=\"{kibana_endpoint}/app/kibana#/discover?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-1d%2Fd,mode:relative,to:now-1d%2Fd))&_a=(columns:!(_source),filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,key:fields.document_type,negate:!f,params:(query:{doc_type},type:phrase),type:phrase,value:{doc_type}),query:(match:(fields.document_type:(query:{doc_type},type:phrase)))),('$state':(store:appState),meta:(alias:!n,disabled:!f,index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,key:json.level_name,negate:!f,params:(query:{log_level_name},type:phrase),type:phrase,value:{log_level_name}),query:(match:(json.level_name:(query:{log_level_name},type:phrase)))),('$state':(store:appState),meta:(alias:!n,disabled:!f,index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,key:query,negate:!f,type:custom,value:'{url_log}'),query:(wildcard:(json.message:'{url_log}')))),index:ff9eedc0-9ef2-11e8-ac1a-ddecd52d1644,interval:auto,query:(language:lucene,query:''),sort:!('@timestamp',desc))\" target=\"_blank\">".format(kibana_endpoint=args.kibana, doc_type=args.doc_type, log_level_name=log_level_name, url_log=url_log),
            '5': "href=\"{kibana_endpoint}/app/kibana#/discover?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-2d%2Fd,mode:relative,to:now))&_a=(columns:!(_source),filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'filebeat-*',key:fields.document_type,negate:!f,value:{doc_type}),query:(match:(fields.document_type:(query:{doc_type},type:phrase)))),('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'filebeat-*',key:json.level_name,negate:!f,value:{log_level_name}),query:(match:(json.level_name:(query:{log_level_name},type:phrase)))),('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'filebeat-*',key:query,negate:!f,value:'%7B%22wildcard%22:%7B%22json.message%22:%22{url_log}%22%7D%7D'),query:(wildcard:(json.message:'{url_log}')))),index:'filebeat-*',interval:auto,query:(query_string:(analyze_wildcard:!t,query:'*')),sort:!('@timestamp',desc))\" target=\"_blank\">".format(kibana_endpoint=args.kibana, doc_type=args.doc_type, log_level_name=log_level_name, url_log=url_log),
        }

        email.extend([
            TOP_ERR_START,
            url[str(args.es_version)],
            str(log[i][1]),
            TOP_ERR_CENTER,
            log[i][0].split('Stack trace', 1)[0], # Truncate useless data
            TOP_ERR_END
        ])

    email.append(TOP_ERRORS_END)

email.append(EMAIL_BODY_END)


# Send message
MESSAGE = ''.join(email)

HEADERS = {"Content-Type": "application/json"}
DATA = {
    "category_id": 1,
    "headers": {
        "from": 'Error Rate Reporting <{}>'.format(args.src),
    },
    "to": {
        "email": args.to,
    },
    "template_name": args.sender_tpl,
    "message": MESSAGE
}

RESPONSE = requests.post(
    args.api_url, headers=HEADERS,
    auth=(args.user, args.pswd), json=DATA
)

RESPONSE.raise_for_status()
print(RESPONSE.json())
