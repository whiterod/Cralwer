# -*- coding: utf-8 -*-
"""
Created on Mon Feb 12 11:29:17 2018

@author: KJH
"""
from selenium import webdriver
from bs4 import BeautifulSoup as bs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from operator import eq
from urllib.request import urlopen
from urllib.request import Request

import datetime
import json
import time
import pymssql
import re

global gvDate
global gvMenuId
global gvMinArticleid
global gvConn
global gvDriver

def insert_ContentData(data,dateid,menuid):
    global gvConn
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertWebCrawlerContent] %s,%s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid,data.get('articleid'), data.get('index'),str(menuid) ,data.get('url'),data.get('title'), data.get('content') ))
    gvConn.commit()
    cursor.close()

def insert_CommentData(data,dateid,menuid):
    global gvConn
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertWebCrawlerComment] %s,%s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid,data.get('articleid'), str(menuid) ,data.get('commentid'), data.get('commentReplayID'),data.get('nick'),data.get('comment') ))
    gvConn.commit()    
    cursor.close()


def get_RedditBak():
    global gvDriver
    global gvDate
    thread_urls = []
    cursor = gvConn.cursor()
    cursor.execute("""
                        SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
                        SELECT url FROM [dbo].[T_WebCrawlerContent] WITH(NOLOCK) WHERE TITLE IS NULL
                """)
    row = cursor.fetchone()
    while row:
        thread_urls.append(row[0])
        row = cursor.fetchone()
    
    for thread in thread_urls:
        requestContensJson(thread+'.json')
        
def createSTS_Comment():
    global gvConn
    global gvMenuId
    cursor = gvConn.cursor()
    sql = """
    IF OBJECT_ID('STS_Comment')		IS NOT NULL		DROP TABLE STS_Comment
    
    SELECT Articleid, ISNULL( STUFF(
    ( 
    	SELECT CHAR(10) + C.Comment + '  ('+ C.NickName + ' ) '
    	FROM [T_WebCrawlerComment] C WITH(NOLOCK)
    	WHERE  A.Articleid = C.Articleid 
    	AND ( LTRIM(RTRIM(C.Comment)) NOT IN (
    			SELECT [NAME] FROM [T_MasterWord] WHERE [type] = 99
    			UNION ALL
    			SELECT [NAME] FROM [T_RelatedWords] WHERE [type] = 99
    		))
    	AND LTRIM(RTRIM(ISNULL(C.Comment, ''))) <> ''  
    	FOR XML PATH('') 
    ),1,1,''
    ), '') AS Comment 
    INTO STS_Comment
    FROM [T_WebCrawlerComment] A
    GROUP BY Articleid
    
    CREATE CLUSTERED INDEX CX__Comment ON STS_Comment(Articleid)
    """
    cursor.execute(sql)
    gvConn.commit()    
    cursor.close()

def get_content():
    global gvMinArticleid
    global gvMenuId
    global gvDriver

    base_url = 'http://www.mobirum.com/article/'
    gvDriver.get(base_url + 'list?bbsId='+str(gvMenuId)+'&cafeId=TEST&sort=DATE')
    soup = bs(gvDriver.page_source, 'html.parser')
   
    article_list = gvDriver.find_elements_by_css_selector('p[class="c_atc_tt"] > a')
    article_urls = [ i.get_attribute('href') for i in article_list ]
    
    for article in article_urls:
        if article is None:
            continue
       
        gvDriver.get(article)
        
        try:
            wait = WebDriverWait(gvDriver, 60);
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class='c_atc_head']")))
        except: 
            continue
        
        element = gvDriver.find_element_by_class_name('bt_more')
        gvDriver.execute_script("arguments[0].click();", element)
        gvDriver.implicitly_wait(10)
        
        soup = bs(gvDriver.page_source, 'html.parser')
        
        if len(soup.select('div[class="c_atc_head"]')) < 1:
            continue
        
        patten = re.compile(r"\w*$")
        articleID = patten.search(article).group()    
        
        dateTxt = soup.select('article span[class="tx tx_time"]')[0].get_text().strip()
        date = datetime.datetime(int(dateTxt[:4]), int(dateTxt[5:7]), int(dateTxt[8:10]), int(dateTxt[11:13]), int(dateTxt[-2:]))
        title = soup.select('strong[class="titleArea"]')[0].get_text().replace("  ", " ").strip()
        
        if title.find('공지') > 0:
            continue
        
        if eq(str(gvMenuId),'1630') or eq(str(gvMenuId),'213') or eq(str(gvMenuId),'240') or eq(str(gvMenuId),'227'):
            if (gvDate-date) > datetime.timedelta(days = 7):
                break
        else :
            if (gvDate-date) > datetime.timedelta(days = 14):
                break
            
            
        if eq(str(gvMenuId),'1630') or eq(str(gvMenuId),'213') or eq(str(gvMenuId),'240') or eq(str(gvMenuId),'227'):
            comments = soup.select('span[id="articleReply"] div[class="c_atc_content"]')
            commentNick = soup.select('span[id="articleReply"] div[class="c_tx_info"] strong')    
        else :
            comments = soup.select('div[class="c_comments_wrap"] ul li div[class="c_cmt_tx contentArea"]')
            commentNick = soup.select('div[class="c_comments_wrap"] ul li div[class="c_tx_info"] strong')
        
        i = 0
        for tags in comments:
            insert_CommentData({'articleid' : articleID, 'commentid' : str(i), 'nick' : replaceText(commentNick[i].get_text().strip()), 'comment' : replaceText(comments[i].get_text().strip()), 'commentReplayID' :''},date.strftime('%Y%m%d'),gvMenuId)
            i=i+1
        
        gvDriver.switch_to_frame(gvDriver.find_element_by_tag_name("iframe"));
        soup = bs(gvDriver.page_source, 'html.parser')
        
        contents = soup.select('div[id="content"] p')
              
        for tags in contents:
            content = '\r\n'.join([ replaceText(tags.get_text().strip()) for tags in contents ])
        
        insert_ContentData({'articleid' : articleID, 'title' : title, 'index':'0', 'url' : article, 'content' : content},date.strftime('%Y%m%d'),gvMenuId)
        #'''
        

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

def set_menu(menuId):
    global gvMenuId
    global gvMinArticleid
    
    gvMenuId = menuId
    gvMinArticleid = 0
    get_content()


def requestJson(url):
    text = None
    test = None
    hdr = { 'User-Agent' : 'super happy flair bot by /u/spladug' }
    req = Request(url, headers=hdr)
    file = urlopen(req)
    text = file.read()
    test = json.loads(text)
    return test['data']

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

    return None

def dataParse(oriData, url):
    data = oriData['data']['children']
    global gvDate
    for i in data:
        try:
            d = i['data']
            #print(i['data'])
            if i['kind'] == 't1': #댓글
                permalink = d['permalink'].replace('/r/TEST/comments/','')
                patten = re.compile(r"^\S{6}(?=\/)")
                articleid = patten.search(permalink).group()
                insert_CommentData({'articleid' : articleid, 'commentid' : d['id'], 'commentReplayID' :  d['parent_id'].replace('t1_','').replace('t3_',''), 'nick' : d['author'], 'comment' : replaceText(d['body']), 'url' : url.replace('.json','') },gvDate.strftime('%Y%m%d'),'1')
                #print(d['replies'])
                if d['replies'] != '':
                    dataParse(d['replies'], url)
                
            else: #본문
                insert_ContentData({'articleid' : d['id'], 'index' : '0', 'title' : d['title'], 'content' : replaceText(d['selftext']), 'url' : url.replace('.json','') }, gvDate.strftime('%Y%m%d'),'1')
        except KeyError as e:
            print(d)

    
def startRedditCrawling(pageLink):
    nextPage = ''
    for i in range(3):
        time.sleep(10)
        jsonFile = requestJson(pageLink + nextPage)
        nextPage = jsonFile['after']
        jsonFile = jsonFile['children']
        for item in jsonFile:
            link = item['data']['permalink']
            contentUrl ='https://www.reddit.com'+link+'.json'
            requestContensJson(contentUrl)

def webCrawler():
    global gvDriver
    global gvDate
    global gvConn
    start_time = time.time()
    
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
    
    pageLink = 'https://www.reddit.com/r/'
    startRedditCrawling(pageLink)
    get_RedditBak();
    
    #Chrome Options
    chromeOptions = webdriver.ChromeOptions()
    chromeOptions.add_argument('--no-sandbox')
    prefs = {"profile.managed_default_content_settings.images":2}
    chromeOptions.add_experimental_option("prefs",prefs)
    gvDriver = webdriver.Chrome(chrome_options=chromeOptions)
    #gvDriver = webdriver.Chrome('chromedriver.exe')
    gvDriver.implicitly_wait(10)
    
    #207 - 뉴스, 208 - 업데이트, 719 - 개발자노트, 227 - 자개, 1630 - 팁, 213 - 버그리포트, 240 - 제안
    #gvMenuId = 62
    #get_content(1)
    
    set_menu(208)
    set_menu(719)
    set_menu(227)
    set_menu(1630)
    set_menu(213)
    set_menu(240)
    #'''
    
    createSTS_Comment()
    gvDriver.close()
    gvDriver.quit()
    gvConn.close()  
    elapsed_time = time.time() - start_time
    
    print(str(datetime.datetime.now()) + " : " + str(elapsed_time))
    
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
    #'''    
    # 3분 이상
    
    #exit(1)

