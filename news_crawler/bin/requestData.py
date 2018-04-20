import json


class RequestData(object):
    def __init__(self):
        self._clip_url_key = ''
        self._track_srcid = 0
        self._meta_id = ''
        self._clip_url = ''
        self._clip_title = ''
        self._source_type = ''
        self._source_url = []
        self._publish_time = '0000-00-00 00:00:00'
        self._view_count = 0
        self._clip_source = ''
        self._outer_clipurl = ''
        self._category = ''
        self._content = ''
    def setTrackSourceID(self, trackSourceId):
        self._track_srcid = trackSourceId

    def setMetaID(self, meta_id):
        self._meta_id = meta_id

    def setClipUrl(self, clip_url):
        self._clip_url = clip_url

    def setClipTitle(self, clip_title):
        self._clip_title = clip_title

    def setSouceType(self, source_type):
        self._source_type = source_type

    def setSourceUrl(self, source_url):
        self._source_url = source_url

    def setSourceTitle(self, source_title):
        self._source_title = source_title

    def setPublishTime(self, publish_time):
        #format: '0000-00-00 00:00:00'
        if publish_time:
            self._publish_time = publish_time

    def setViewCount(self, view_count):
        self._view_count = view_count

    def setClipSource(self,clipsrc):
        self._clip_source = clipsrc

    def setOuterClipurl(self,outerClipUrl):
        self._outer_clipurl = outerClipUrl

    def setCategory(self,category):
        self._category = category
    def setContent(self,content):
        self._content = content
    def setClipKey(self, key):
        self._clip_url_key = key
    def copyrd(self):
        rdnew = RequestData()
        rdnew._track_srcid =  self._track_srcid
        rdnew._meta_id = self._meta_id 
        rdnew._clip_url = self._clip_url 
        rdnew._clip_title = self._clip_title 
        rdnew._source_type = self._source_type 
        rdnew._source_url = self._source_url 
        rdnew._publish_time = self._publish_time 
        rdnew._view_count = self._view_count
        rdnew._clip_source = self._clip_source 
        rdnew._outer_clipurl = self._outer_clipurl 
        rdnew._category = self._category
        rdnew._content = self._content
        return rdnew
    def hostparseToStr(self):
        ###FORMAT:
        ###{
        ###    "trackSourceId": integer,  //爬虫目标网站（账号）的id
        ###    "metaUuid": "META_UUID",  //可选，不必填
        ###    "category": "video | image",     // 类型，视频or图片
        ###    "sourceType": "website",    //枚举：website，app，weibo，wechat, paper
        ###    "clipUrl": "CLIP_URL",   // 网页地址
        ###    "sourceUrl": ["SOURCE_URL1", "SOURCE_URL2"],   // 源地址
        ###    "clipTitle": "CLIP_TITLE",   // 网页标题
        ###    "publishTime": "yyyy-mm-dd HH:MM:ss",   // 发布日期
        ###    "viewCount": int,    // 点击（观看）数
        ###    "clipSource": "",    // 转载来源
        ###}
        self._clip_title = self._clip_title.replace('\"',"").replace('\n',"")
        s = {
            "clipUrlKey": self._clip_url_key,
            "trackSourceId": self._track_srcid,
            "metaUuid": self._meta_id,
            "category": self._category,
            "sourceType": self._source_type,
            "clipUrl": self._clip_url,
            "sourceUrl":self._source_url,
            "clipTitle": self._clip_title,
            "publishTime": self._publish_time,
            "viewCount": self._view_count,
            "clipSource": self._clip_source,
            "content":self._content}
        return json.dumps(s)

    def linkparseToStr(self):
        ###FORMAT:
        ###{
        ###     "trackSourceId": integer,  //爬虫目标网站（账号）的id
        ###     "metaUuid": "META_UUID",  //可选，不必填
        ###     "category": "video | image",     // 类型，视频or图片
        ###     "sourceType": "website",    //枚举：website，app，weibo，wechat, paper
        ###     "clipUrl": "CLIP_URL",   // 网页地址
        ###     "outerClipUrl": "OUTER_CLIP_URL",   // 源地址
        ###     "clipTitle": "CLIP_TITLE",   // 网页标题
        ###     "publishTime": "yyyy-mm-dd HH:MM:ss",   // 发布日期
        ###     "viewCount": int,    // 点击（观看）数
        ###     "clipSource": "",    // 转载来源
        ###}
        self._clip_title = self._clip_title.replace('\"',"") 
        s = {
              "trackSourceId": self._track_srcid,
              "metaUuid": self._meta_id,
              "category": self._category,
              "sourceType": self._source_type,
              "clipUrl": self._clip_url,
              "outerClipUrl": self._outer_clipurl,
              "clipTitle": self._clip_title,
              "publishTime": self._publish_time,
              "viewCount": self._view_count,
              "clipSource": self._clip_source
        }

        return json.dumps(s)

    def hostparseToJson(self):
        return json.loads(str(self.hostparseToStr()),strict=False)
    
    def linkparseToJson(self):
        return json.loads(str(self.linkparseToStr()),strict=False)
        
        
def main():
    rd = RequestData()
    print(rd.hostparseToStr())
    print(rd.hostparseToJson())


if __name__ == '__main__':
    main()
