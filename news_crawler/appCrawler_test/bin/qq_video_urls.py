#!/usr/bin/env python
#coding = utf-8
import simplejson as json
import requests
import re
def get_html(url):
    return requests.get(url).text
def match1(text, pattern):
    match = re.search(pattern, text)
    if match:
        print 'match success! match string is ' + match.group()
        return match.group()
    else:
        return None
def matchall(text, patterns):
    ret = []
    for pattern in patterns:
        match = re.findall(pattern, text)
        ret += match

    return ret
def qq_download_by_vid(vid, title, output_dir='.', merge=True, info_only=False):
    info_api = 'http://vv.video.qq.com/getinfo?otype=json&appver=3%2E2%2E19%2E333&platform=11&defnpayver=1&vid=' + vid
    info = get_html(info_api)
    #print info
    video_json = json.loads(info[13:-1])
    parts_vid = video_json['vl']['vi'][0]['vid']
    parts_ti = video_json['vl']['vi'][0]['ti']
    parts_prefix = video_json['vl']['vi'][0]['ul']['ui'][0]['url']
    parts_formats = video_json['fl']['fi']
    # find best quality
    # only looking for fhd(1080p) and shd(720p) here.
    # 480p usually come with a single file, will be downloaded as fallback.
    best_quality = ''
    for part_format in parts_formats:
        if part_format['name'] == 'fhd':
            best_quality = 'fhd'
            break

        if part_format['name'] == 'shd':
            best_quality = 'shd'

    for part_format in parts_formats:
        if (not best_quality == '') and (not part_format['name'] == best_quality):
            continue
        part_format_id = part_format['id']
        part_format_sl = part_format['sl']
        if part_format_sl == 0:
            part_urls= []
            total_size = 0
            try:
                # For fhd(1080p), every part is about 100M and 6 minutes
                # try 100 parts here limited download longest single video of 10 hours.
                for part in range(1,100):
                    filename = vid + '.p' + str(part_format_id % 1000) + '.' + str(part) + '.mp4'
                    key_api = "http://vv.video.qq.com/getkey?otype=json&platform=11&format=%s&vid=%s&filename=%s" % (part_format_id, parts_vid, filename)
                    #print(filename)
                    #print(key_api)
                    part_info = get_html(key_api)
                    key_json = json.loads(part_info[13:-1])
                    #print(key_json)
                    vkey = key_json['key']
                    url = '%s/%s?vkey=%s' % (parts_prefix, filename, vkey)
                    part_urls.append(url)
            except:
                pass
            if not info_only:
                return part_urls
        else:
            fvkey = video_json['vl']['vi'][0]['fvkey']
            mp4 = video_json['vl']['vi'][0]['cl'].get('ci', None)
            if mp4:
                mp4 = mp4[0]['keyid'].replace('.10', '.p') + '.mp4'
            else:
                mp4 = video_json['vl']['vi'][0]['fn']
            url = '%s/%s?vkey=%s' % ( parts_prefix, mp4, fvkey )
            if not info_only:
                return [url]
def get_downloadurls_by_content(content):
    vids = matchall(content, [r'\bvid=(\w+)'])
    urls = []
    for vid in vids:
        urls += qq_download_by_vid(vid, vid)
    return urls