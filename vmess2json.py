#!/usr/bin/env python3
import os
import sys
import json
import base64
import pprint
import argparse
import random
import hashlib
import binascii
import traceback
import urllib.request
import urllib.parse

vmscheme = "vmess://"
ssscheme = "ss://"

TPL = {}
TPL["CLIENT"] = """
{
  "log": {
    "access": "",
    "error": "",
    "loglevel": "error"
  },
  "inbounds": [
  ],
  "outbounds": [
    {
      "protocol": "vmess",
      "settings": {
        "vnext": [
          {
            "address": "host.host",
            "port": 1234,
            "users": [
              {
                "email": "user@v2ray.com",
                "id": "",
                "alterId": 0,
                "security": "auto"
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp"
      },
      "mux": {
        "enabled": true
      },
      "tag": "proxy"
    },
    {
      "protocol": "freedom",
      "tag": "direct",
      "settings": {
        "domainStrategy": "UseIP"
      }
    }
  ],
  "dns": {
    "servers": [
      "1.0.0.1",
      "localhost"
    ]
  },
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "type": "field",
        "ip": [
          "geoip:private",
          "geoip:cn"
        ],
        "outboundTag": "direct"
      },
      {
        "type": "field",
        "domain": [
          "geosite:cn"
        ],
        "outboundTag": "direct"
      }
    ]
  }
}
"""

# tcpSettings
TPL["http"] = """
{
    "header": {
        "type": "http",
        "request": {
            "version": "1.1",
            "method": "GET",
            "path": [
                "/"
            ],
            "headers": {
                "Host": [
                    "www.cloudflare.com",
                    "www.amazon.com"
                ],
                "User-Agent": [
                    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0"
                ],
                "Accept": [
                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
                ],
                "Accept-language": [
                    "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4"
                ],
                "Accept-Encoding": [
                    "gzip, deflate, br"
                ],
                "Cache-Control": [
                    "no-cache"
                ],
                "Pragma": "no-cache"
            }
        }
    }
}
"""

# kcpSettings
TPL["kcp"] = """
{
    "mtu": 1350,
    "tti": 50,
    "uplinkCapacity": 12,
    "downlinkCapacity": 100,
    "congestion": false,
    "readBufferSize": 2,
    "writeBufferSize": 2,
    "header": {
        "type": "wechat-video"
    }
}
"""

# wsSettings
TPL["ws"] = """
{
    "connectionReuse": true,
    "path": "/path",
    "headers": {
        "Host": "host.host.host"
    }
}
"""


# httpSettings
TPL["h2"] = """
{
    "host": [
        "host.com"
    ],
    "path": "/host"
}
"""

TPL["quic"] = """
{
  "security": "none",
  "key": "",
  "header": {
    "type": "none"
  }
}
"""

TPL["in_socks"] = """
{
    "tag":"socks-in",
    "port": 10808,
    "listen": "::",
    "protocol": "socks",
    "settings": {
        "auth": "noauth",
        "udp": true,
        "ip": "127.0.0.1"
    }
}
"""

TPL["in_http"] = """
{
    "tag":"http-in",
    "port": 8123,
    "listen": "::",
    "protocol": "http"
}
"""

TPL["in_mt"] = """
{
    "tag": "mt-in",
    "port": 6666,
    "protocol": "mtproto",
    "settings": {
        "users": [
            {
                "secret": ""
            }
        ]
    }
}
"""

TPL["out_mt"] = """
{
    "tag": "mt-out",
    "protocol": "mtproto",
    "proxySettings": {
        "tag": "proxy"
    }
}
"""

TPL["in_dns"] = """
{
  "port": 53,
  "tag": "dns-in",
  "protocol": "dokodemo-door",
  "settings": {
    "address": "1.1.1.1",
    "port": 53,
    "network": "tcp,udp"
  }
}
"""

TPL["conf_dns"] = """
{
    "hosts": {
        "geosite:category-ads": "127.0.0.1",
        "domain:googleapis.cn": "googleapis.com"
    },
    "servers": [
        "1.0.0.1",
        {
            "address": "1.2.4.8",
            "domains": [
                "geosite:cn"
            ],
            "port": 53
        }
    ]
}
"""

TPL["in_tproxy"] = """
{
    "tag":"tproxy-in",
    "port": 1080,
    "protocol": "dokodemo-door",
    "settings": {
        "network": "tcp,udp",
        "followRedirect": true
    },
    "streamSettings": {
        "sockopt": {
            "tproxy":"tproxy"
        }
    },
    "sniffing": {
        "enabled": true,
        "destOverride": [
            "http",
            "tls"
        ]
    }
}
"""

TPL["in_api"] = """
{
    "tag": "api",
    "port": 10085,
    "listen": "127.0.0.1",
    "protocol": "dokodemo-door",
    "settings": {
        "address": "127.0.0.1"
    }
}
"""

TPL["out_ss"] = """
{
    "email": "user@ss",
    "address": "",
    "method": "",
    "ota": false,
    "password": "",
    "port": 0
}
"""


def parseLink(link):
    if link.startswith(ssscheme):
        return parseSs(link)
    elif link.startswith(vmscheme):
        return parseVmess(link)
    else:
        print("ERROR: This script supports only vmess://(N/NG) and ss:// links")
        return None

def parseSs(sslink):
    RETOBJ = {
        "v": "2",
        "ps": "",
        "add": "",
        "port": "",
        "id": "",
        "aid": "",
        "net": "shadowsocks",
        "type": "",
        "host": "",
        "path": "",
        "tls": ""
    }
    if sslink.startswith(ssscheme):
        info = sslink[len(ssscheme):]
        
        if info.rfind("#") > 0:
            info, _ps = info.split("#", 2)
            RETOBJ["ps"] = urllib.parse.unquote(_ps)
        
        if info.find("@") < 0:
            # old style link
            #paddings
            blen = len(info)
            if blen % 4 > 0:
                info += "=" * (4 - blen % 4)

            info = base64.b64decode(info).decode()

            atidx = info.rfind("@")
            method, password = info[:atidx].split(":", 2)
            addr, port = info[atidx+1:].split(":", 2)
        else:
            atidx = info.rfind("@")
            addr, port = info[atidx+1:].split(":", 2)

            info = info[:atidx]
            blen = len(info)
            if blen % 4 > 0:
                info += "=" * (4 - blen % 4)

            info = base64.b64decode(info).decode()
            method, password = info.split(":", 2)

        RETOBJ["add"] = addr
        RETOBJ["port"] = port
        RETOBJ["aid"] = method
        RETOBJ["id"] = password
        return RETOBJ


def parseVmess(vmesslink):
    """
    return:
{
  "v": "2",
  "ps": "remark",
  "add": "4.3.2.1",
  "port": "1024",
  "id": "xxx",
  "aid": "64",
  "net": "tcp",
  "type": "none",
  "host": "",
  "path": "",
  "tls": ""
}
    """
    if vmesslink.startswith(vmscheme):
        bs = vmesslink[len(vmscheme):]
        #paddings
        blen = len(bs)
        if blen % 4 > 0:
            bs += "=" * (4 - blen % 4)

        vms = base64.b64decode(bs).decode()
        return json.loads(vms)
    else:
        raise Exception("vmess link invalid")

def load_TPL(stype):
    s = TPL[stype]
    return json.loads(s)

def fill_basic(_c, _v):
    _outbound = _c["outbounds"][0]
    _vnext = _outbound["settings"]["vnext"][0]

    _vnext["address"]               = _v["add"]
    _vnext["port"]                  = int(_v["port"])
    _vnext["users"][0]["id"]        = _v["id"]
    _vnext["users"][0]["alterId"]   = int(_v["aid"])

    _outbound["streamSettings"]["network"]  = _v["net"]

    if _v["tls"] == "tls":
        _outbound["streamSettings"]["security"] = "tls"
        _outbound["streamSettings"]["tlsSettings"] = {"allowInsecure": True}
        if _v["host"] != "":
            _outbound["streamSettings"]["tlsSettings"]["serverName"] = _v["host"] 


    return _c

def fill_shadowsocks(_c, _v):
    _ss = load_TPL("out_ss")
    _ss["email"] = _v["ps"] + "@ss"
    _ss["address"] = _v["add"]
    _ss["port"] = int(_v["port"])
    _ss["method"] = _v["aid"]
    _ss["password"] = _v["id"]

    _outbound = _c["outbounds"][0]
    _outbound["protocol"] = "shadowsocks"
    _outbound["settings"]["servers"] = [_ss]

    del _outbound["settings"]["vnext"] 
    del _outbound["streamSettings"]
    del _outbound["mux"]

    return _c

def fill_tcp_http(_c, _v):
    tcps = load_TPL("http")
    tcps["header"]["type"] = _v["type"]
    if _v["host"]  != "":
        # multiple host
        tcps["header"]["request"]["headers"]["Host"] = _v["host"].split(",")

    if _v["path"]  != "":
        tcps["header"]["request"]["path"] = [ _v["path"] ]

    _c["outbounds"][0]["streamSettings"]["tcpSettings"] = tcps
    return _c

def fill_kcp(_c, _v):
    kcps = load_TPL("kcp")
    kcps["header"]["type"] = _v["type"]
    _c["outbounds"][0]["streamSettings"]["kcpSettings"] = kcps
    return _c

def fill_ws(_c, _v):
    wss = load_TPL("ws")
    wss["path"] = _v["path"]
    wss["headers"]["Host"] = _v["host"]
    _c["outbounds"][0]["streamSettings"]["wsSettings"] = wss
    return _c

def fill_h2(_c, _v):
    h2s = load_TPL("h2")
    h2s["path"] = _v["path"]
    h2s["host"] = [ _v["host"] ]
    _c["outbounds"][0]["streamSettings"]["httpSettings"] = h2s
    return _c

def fill_quic(_c, _v):
    quics = load_TPL("quic")
    quics["header"]["type"] = _v["type"]
    quics["security"]       = _v["host"]
    quics["key"]            = _v["path"]
    _c["outbounds"][0]["streamSettings"]["quicSettings"] = quics
    return _c

def vmess2client(_t, _v):
    _net = _v["net"]
    _type = _v["type"]

    if _net == "shadowsocks":
        return fill_shadowsocks(_t, _v)

    _c = fill_basic(_t, _v)

    if _net == "kcp":
        return fill_kcp(_c, _v)
    elif _net == "ws":
        return fill_ws(_c, _v)
    elif _net == "h2":
        return fill_h2(_c, _v)
    elif _net == "quic":
        return fill_quic(_c, _v)
    elif _net == "tcp":
        if _type == "http":
            return fill_tcp_http(_c, _v)
        return _c
    else:
        pprint.pprint(_v)
        raise Exception("this link seem invalid to the script, please report to dev.")


def parse_multiple(lines):
    def genPath(ps, rand=False):
        # add random in case list "ps" share common names
        curdir = os.environ.get("PWD", '/tmp/')
        rnd = "-{}".format(random.randrange(100)) if rand else ""
        name = "{}{}.json".format(vc["ps"].replace("/", "_").replace(".", "-"), rnd)
        return os.path.join(curdir, name)

    for line in lines:
        vc = parseLink(line.strip())
        if vc is None:
            continue

        if int(vc["v"]) != 2:
            print("Version mismatched, skiped. This script only supports version 2.")
            continue

        cc = fill_inbounds(fill_dns(vmess2client(load_TPL("CLIENT"), vc)))

        jsonpath = genPath(vc["ps"])
        while os.path.exists(jsonpath):
            jsonpath = genPath(vc["ps"], True)

        print("Wrote: " + jsonpath)
        with open(jsonpath, 'w') as f:
            jsonDump(cc, f)

def jsonDump(obj, fobj):
    if option.update is not None:
        oconf = json.load(option.update)
        if "outbounds" not in oconf:
            raise KeyError("outbounds not found in {}".format(option.update.name))

        oconf["outbounds"][0] = obj["outbounds"][0]
        option.update.close()
        with open(option.update.name, 'w') as f:
            json.dump(oconf, f, indent=4)
        print("Updated")
        return

    if option.outbound:
        onlyoutbound = {"outbounds":obj["outbounds"]}
        json.dump(onlyoutbound, fobj, indent=4)
    else:
        json.dump(obj, fobj, indent=4)

def fill_inbounds(_c):
    _ins = option.inbounds.split(",")
    for _in in _ins:
        _proto, _port = _in.split(":", maxsplit=1)
        _tplKey = "in_"+_proto 
        if _tplKey in TPL:
            _inobj = load_TPL(_tplKey)

            if _proto == "dns":
                _c["dns"] = load_TPL("conf_dns")
                _c["routing"]["rules"].insert(0, {
                    "type": "field",
                    "inboundTag": ["dns-in"],
                    "outboundTag": "dns-out"
                })
                _c["outbounds"].append({
                    "protocol": "dns",
                    "tag": "dns-out"
                })
            
            elif _proto == "api":
                _c["api"] = {
                    "tag": "api",
                    "services": [ "HandlerService", "LoggerService", "StatsService" ]
                }
                _c["stats"] = {}
                _c["policy"] = {
                    "levels": { "0": { "statsUserUplink": True, "statsUserDownlink": True }},
                    "system": { "statsInboundUplink": True, "statsInboundDownlink": True }
                }
                _c["routing"]["rules"].insert(0, {
                    "type": "field",
                    "inboundTag": ["api"],
                    "outboundTag": "api"
                })

            elif _proto == "mt":
                mtinfo = _port.split(":", maxsplit=1)
                if len(mtinfo) == 2:
                    _port, _secret = mtinfo
                else:
                    _secret = hashlib.md5(str(random.random()).encode()).hexdigest()

                _inobj["settings"]["users"][0]["secret"] = _secret
                _c["outbounds"].append(load_TPL("out_mt"))
                _c["routing"]["rules"].insert(0, {
                    "type": "field",
                    "inboundTag": ["mt-in"],
                    "outboundTag": "mt-out"
                })

            _inobj["port"] = int(_port)
            _c["inbounds"].append(_inobj)
        else:
            print("Error Inbound: " + _in)

    return _c

def fill_dns(_c):
    if option.localdns != "":
        dns = {
            "address": option.localdns,
            "port": 53,
            "domains": ["geosite:cn"]
        }
        ## 当某个 DNS 服务器指定的域名列表匹配了当前要查询的域名，V2Ray 会优先使用这个 
        ## DNS 服务器进行查询，否则按从上往下的顺序进行查询。
        ## 
        _c["dns"]["servers"].insert(1, dns)

        ## 若要使 DNS 服务生效，需要配置路由功能中的 domainStrategy。
        _c["routing"]["domainStrategy"] = "IPOnDemand"
    
    return _c

def read_subscribe(sub_url):
    print("Reading from subscribe ...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'}
    req =urllib.request.Request(url=sub_url,headers=headers)
    with urllib.request.urlopen(req) as response:
        _subs = response.read()
        return base64.b64decode(_subs).decode().splitlines()

def select_multiple(lines):
    vmesses = []
    for _v in lines:
        _vinfo = parseLink(_v)
        if _vinfo is not None:
            vmesses.append({ "ps": "[{ps}] {add}:{port}/{net}".format(**_vinfo), "vm": _v })

    print("Found {} items.".format(len(vmesses)))

    for i, item in enumerate(vmesses):
        print("[{}] - {}".format(i+1, item["ps"]))

    print()

    if not sys.stdin.isatty() and os.path.exists('/dev/tty'):
        sys.stdin.close()
        sys.stdin = open('/dev/tty', 'r')

    if sys.stdin.isatty():
        sel = input("Choose >>> ")
        idx = int(sel) - 1
    elif int(option.select) > -1:
        idx = int(option.select) - 1
    else:
        raise Exception("Current session cant open a tty to select. Specify the index to --select argument.")

    item = vmesses[idx]["vm"]
    
    ln = parseLink(item)
    if ln is None:
        return
    cc = fill_inbounds(fill_dns(vmess2client(load_TPL("CLIENT"), ln)))
    jsonDump(cc, option.output)

def detect_stdin():
    if sys.stdin.isatty():
        return None
    stdindata = sys.stdin.read()
    option.subscribe = "-"
    try:
        lines = base64.b64decode(stdindata).decode().splitlines()
        return lines
    except (binascii.Error, UnicodeDecodeError):
        return stdindata.splitlines()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="vmess2json convert vmess link to client json config.")
    parser.add_argument('--parse_all',
                        action="store_true",
                        default=False,
                        help="parse all vmess:// lines (or base64 encoded) from stdin and write each into .json files")
    parser.add_argument('--subscribe',
                        action="store",
                        default="",
                        help="read from a subscribe url, display a menu to choose nodes")
    parser.add_argument('-o', '--output',
                        type=argparse.FileType('w'),
                        default=sys.stdout,
                        help="write to file. default to stdout")
    parser.add_argument('-u', '--update',
                        type=argparse.FileType('r'),
                        help="update a config.json, changes only the first outbound object.")
    parser.add_argument('--outbound',
                        action="store_true",
                        default=False,
                        help="output the outbound object only.")
    parser.add_argument('--inbounds',
                        action="store",
                        default="socks:1080,http:8123",
                        help="include inbounds objects, default: \"socks:1080,http:8123\". Available proto: socks,http,dns,mt,tproxy . "
                            "For mtproto with custom password:  mt:7788:xxxxxxxxxxxxxxx")
    parser.add_argument('--localdns',
                        action="store",
                        default="",
                        help="use domestic DNS server for geosite:cn list domains.")
    parser.add_argument('vmess',
                        nargs='?',
                        help="A vmess:// link. If absent, reads a line from stdin.")

    option = parser.parse_args()
    stdin_data = detect_stdin()
    
    if option.parse_all and stdin_data is not None:
        parse_multiple(stdin_data)
        sys.exit(0)

    # if stdin can be base64 decoded, subscribe from stdin is implicted.
    if len(option.subscribe) > 0:
        try:
            if stdin_data is None:
                select_multiple(read_subscribe(option.subscribe))
            else:
                select_multiple(stdin_data)
        except (EOFError, KeyboardInterrupt):
            print("Bye.")
        except:
            traceback.print_exc()
        finally:
            sys.exit(0)

    if option.vmess is None and stdin_data is None:
        parser.print_help()
        sys.exit(1)
    
    vmess = option.vmess if option.vmess is not None else stdin_data[0]
    vc = parseLink(vmess.strip())
    if vc is None:
        sys.exit(1)

    cc = fill_inbounds(fill_dns(vmess2client(load_TPL("CLIENT"), vc)))
    jsonDump(cc, option.output)
