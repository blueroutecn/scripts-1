#!/usr/bin/env python
# coding=utf-8

import os
import sys
from vavava import util
import play_list
util.set_default_utf8()

pjoin = os.path.join
pdirname = os.path.dirname
pabspath = os.path.abspath
user_path = os.environ['HOME']

class Config:
    def __init__(self, config=None):
        if os.path.islink(__file__):
            script_dir = pdirname(pabspath(os.readlink(__file__)))
        else:
            script_dir = pdirname(pabspath(__file__))
        config_file = config
        if config_file:
            config_file = pabspath(config_file)
        else:
            config_file = pjoin(script_dir, 'config.ini')
        import ConfigParser
        cfg = ConfigParser.ConfigParser()
        cfg.read(config_file)
        self.out_dir = cfg.get('default', 'out_dir')
        self.format = cfg.get('default', 'format')
        self.log = cfg.get('default', 'log')
        self.log_level = cfg.get('default', 'log_level')
        self.lib_dir = cfg.get('script', 'lib_dir')
        self.cmd = cfg.get('script', 'cmd')
        self.u2b_cmd = cfg.get('u2b', 'cmd')
        self.u2b_proxy = cfg.get('u2b', 'proxy')
        self.u2b_cache = cfg.get('u2b', 'cache')
        self.u2b_title_format = cfg.get('u2b', 'title_format', raw=True)
        self.u2b_create_dir = cfg.get('u2b', 'create_dir')
        self.flvcd = {}
        for k,v in cfg.items('flvcd'):
            self.flvcd[k] = v.lower() == 'true'
        lvlconvert = {
            'critical' : 50,
            'fatal' : 50,
            'error' : 40,
            'warning' : 30,
            'warn' : 30,
            'info' : 20,
            'debug' : 10,
            'notset' : 0
        }
        if self.log_level:
            self.log_level = lvlconvert[self.log_level.strip().lower()]
config = None
log = None

# sys.path.insert(0, config.lib_dir)
# common = __import__('common')
# download_urls = common.download_urls
import dl_helper
download_urls = dl_helper.download_urls

def dl_u2b(url, argv):
    cmd = config.u2b_cmd
    cmd += r' --proxy "%s"' % config.u2b_proxy
    cmd += r' --o "%s"' % config.u2b_title_format
    cmd += r' --cache-dir "%s"' % config.u2b_cache
    for arg in argv:
        cmd += ' ' + arg
    cmd += r' %s' % url
    log.debug('==> %s', cmd)
    os.system(cmd)

def dl_youkulixian(url):
    cmd = config.cmd
    os.chdir(config.out_dir)
    cmd += r' "%s"' % url
    os.system(cmd)

def dl_flvcd(url):
    import urllib
    from re import findall
    from vavava.httputil import HttpUtil
    parse_url = 'http://www.flvcd.com/parse.php?'
    parse_url += 'kw='+ urllib.quote(url)
    parse_url += '&flag=one'
    if config.format == 'super':
        parse_url += '&format=super'
    http = HttpUtil()
    http.add_header('Referer', parse_url)
    html = http.get(parse_url).decode('gb2312')
    try:
        m3u = findall(r'name="inf" value="(?P<as>[^"]*)"', html)[0]
        title = findall(u'<strong>当前解析视频：</strong>(?P<as>[^<]*)<strong>', html)[0]
    except:
        print 'not support'
        os.system('say "not support."')
        return
    title = title.strip()
    dl_urls(urls=[url for url in m3u.split('|')], title=title, refer=url)

def dl_urls(urls, title, refer=None):
    urllist = []
    for url in urls:
        if url.startswith('http'):
            urllist.append(url)
    ext = 'flv'
    if urllist[0].find('mp4') > 0:
        ext = 'mp4'
    result = download_urls(urllist, title, ext, odir=config.out_dir,
                  nthread=10, nperfile=True, refer=refer, merge=True)
    return result

def dl_dispatch(url):
    if url.find("youtube.com") >= 0:
        dl_u2b(url, sys.argv[2:])
    elif config.flvcd['default']:
        import re
        available_4flvcd = \
            lambda x: re.findall(r'(?P<as>[^\\/\.]*\.[^\\/\.]*)[\\|/]', x.lower())[0]
        site = available_4flvcd(url)
        if site not in config.flvcd or config.flvcd[site]:
            dl_flvcd(url)
        else:
            dl_youkulixian(url)

def read_list_file(file_name):
    urls = []
    with open(file_name, 'r') as ofp:
        lines = ofp.readlines()
        for line in lines:
            if not line.strip().startswith('#'):
                urls.append(line)
    return urls

def parse_args(config_file=None):
    import argparse
    usage = """./dlvideo [-m][-c config][-o output][-f format] url1 url2 ..."""
    parser=argparse.ArgumentParser(usage=usage, description='download net video', version='0.1')
    parser.add_argument('urls', nargs='+', help='urls')
    parser.add_argument('-c', '--config', default='config.ini')
    parser.add_argument('-o', '--odir')
    parser.add_argument('--list-page', dest='list_page', action='store_true')
    parser.add_argument('--list-file', dest='list_file', action='store_true')
    parser.add_argument('-f', '--format', help='video format:super, normal',choices=['super', 'normal'])
    args = parser.parse_args()
    print args
    return args

def init_args_config():
    config = Config()
    args = parse_args()
    if args.config != 'config.ini':
        config = Config(config=args.config)
        args = parse_args()
    log = util.get_logger(logfile=config.log, level=config.log_level)
    return args, config, log

def main():
    global log
    global config
    args, config, log = init_args_config()
    log.info('{}'.format(args))
    if args.odir:
        config.out_dir = args.odir
    if args.format:
        config.format = args.format
    if args.list_file:
        args.urls = read_list_file(args.list_file)
    if args.list_page:
        args.urls = play_list.YoukuFilter().handle(args.urls[0])
    for url in args.urls:
        try:
            dl_dispatch(url)
            log.info('[DLOK] %s', url)
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            log.error('==> exception happened: %s', url)
            log.exception(e)

if __name__ == "__main__":
    # signal_handler = util.SignalHandlerBase()
    try:
        main()
        os.system(r'say "download finished!!"')
    except KeyboardInterrupt as e:
        print 'stop by user'
        exit(0)
    except Exception as e:
        os.system(r'say "download failed!!"')
        raise
    finally:
        pass


