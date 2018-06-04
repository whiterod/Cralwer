
from urllib.request import urlopen
from urllib.request import Request
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time
import json
import re
import pymssql
import datetime

global gvConn
global gvDate

def insert_ContentData(data,dateid,menuid):
    global gvConn
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertWebCrawlerContent] %s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid,data.get('articleid'), data.get('index'), str(menuid) ,data.get('url'),data.get('content') ))
    #print(sql, ( '20180226',data.get('articleid'), '22',data.get('title'),data.get('nick'),data.get('content') ))
    gvConn.commit()
    cursor.close()

def insert_CommentData(data,dateid,menuid):
    global gvConn
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertWebCrawlerComment] %s,%s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid, data.get('articleid'), str(menuid), data.get('commentid'), data.get('commentReplayID'), data.get('author'), data.get('comment') ))
    gvConn.commit()    
    cursor.close()

    
def startCrawling(pageLink):
    nextPage = ''
    for i in range(3):
        time.sleep(10)
        #print(pageLink + nextPage)
        jsonFile = requestJson(pageLink + nextPage)
        nextPage = jsonFile['after']
        jsonFile = jsonFile['children']
        for item in jsonFile:
            link = item['data']['permalink']
            #item['data']['title']
            contentUrl ='https://www.reddit.com'+link+'.json'
            requestContensJson(contentUrl)
            #author #댓글 글쓴이
            #body #댓글
            
def requestContensJson(url):
    text = None
    test = None
    hdr = { 'User-Agent' : 'super happy flair bot by /u/spladug' }
    req = Request(url, headers=hdr)
    file = urlopen(req)
    text = file.read()
    test = json.loads(text)
    
    for v in test:
        dataParse(v, url)
        '''
        data = v['data']['children']
        for i in data:
            #print(i['data'])
            if i['kind'] == 't1': #댓글
                d = i['data']
                insert_CommentData({'articleid' : '', 'commentid' : d['id'], 'commentReplayID' :  d['parent_id'], 'author' : d['author'], 'comment' : replaceText(d['body']), 'url' : url },gvDate.strftime('%Y%m%d'),1)
                #print(d['body'])
                
            else: #본문
                d = i['data']
                insert_ContentData({'articleid' : d['id'], 'index' : '0', 'title' : d['title'], 'content' : replaceText(d['selftext_html']), 'url' : url },gvDate.strftime('%Y%m%d'),1)
    
    #'''
    return None# test['data']

def dataParse(oriData, url):
    data = oriData['data']['children']
   
    for i in data:
        try:
            d = i['data']
            #print(i['data'])
            if i['kind'] == 't1': #댓글
                insert_CommentData({'articleid' : '', 'commentid' : d['id'], 'commentReplayID' :  d['parent_id'].replace('t1_','').replace('t3_',''), 'author' : d['author'], 'comment' : replaceText(d['body']), 'url' : url.replace('.json','') },gvDate.strftime('%Y%m%d'),1)
                #print(d['replies'])
                if d['replies'] != '':
                    dataParse(d['replies'], url)
                
            else: #본문
                insert_ContentData({'articleid' : d['id'], 'index' : '0', 'content' : replaceText(d['selftext']), 'url' : url.replace('.json','') },gvDate.strftime('%Y%m%d'),1)
        except KeyError as e:
            print(d)

def replaceText(text):
    if text is None:
        return ''
    text = text.replace('&nbsp;',' ')
    text = text.replace('&lt;','<')
    text = text.replace('&gt;','>')
    text = text.replace('&amp;','&')
    text = text.replace('&quot;','"')
    text = text.replace('&#39;',"'")
    #(&lt;\/?(\s|\S)*?&gt;)
    text = re.sub(r"(<script(\s|\S)*?<\/script>)|(<style(\s|\S)*?<\/style>)|(<!--(\s|\S)*?-->)|(<\/?(\s|\S)*?>)","",text)
    #print(text)
    return text
    
def requestJson(url):
    text = None
    test = None
    hdr = { 'User-Agent' : 'super happy flair bot by /u/spladug' }
    req = Request(url, headers=hdr)
    file = urlopen(req)
    text = file.read()
    test = json.loads(text)
    return test['data']


#reload(sys)
#sys.setdefaultencoding('utf-8')

def webCrawler():
    global gvDate
    global gvConn
    pageLink = 'https://www.reddit.com/r/test/new.json?limit=5&count=5&after='
    
    gvConn = pymssql.connect(server='', user='', password='', database='')
    cursor = gvConn.cursor()
    cursor.execute("""
                    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
                    SELECT	DATEPART(YEAR,DATEADD(HOUR,-1,GETDATE())) AS Y
                    ,		DATEPART(MONTH,DATEADD(HOUR,-1,GETDATE())) AS M
                    ,		DATEPART(DAY,DATEADD(HOUR,-1,GETDATE())) AS D
                    ,		DATEPART(HOUR,DATEADD(HOUR,-1,GETDATE())) AS H
                   """)
    row = cursor.fetchone()
    gvDate = datetime.datetime(row[0], row[1], row[2], row[3], 00)
    cursor.close()
    
    startCrawling(pageLink)
    gvConn.close()  


if __name__=='__main__':
    scheduler = BlockingScheduler()
    trigger = IntervalTrigger(hours=1)
    scheduler.add_job(webCrawler,trigger) 
    #scheduler.add_job(webCrawler,'interval',hours=1) 
    
    webCrawler();
    try:
        scheduler.start()
    except(KeyboardInterrupt, SystemExit):
        print("End")
        pass
    # 3분 이상
   
    #exit(1)

