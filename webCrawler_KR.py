# -*- coding: utf-8 -*-
"""
Created on Mon Feb 12 11:29:17 2018

@author: KJH
"""

from selenium import webdriver
from bs4 import BeautifulSoup as bs
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from operator import eq
import datetime
import urllib.request
import json
import time
import pymssql
    
global gvDate
global gvMenuId
global gvMinArticleid
global gvConn
global gvDriver

def insert_ContentData(data,dateid,menuid):
    global gvConn
    global gvMenuId
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertNaverCafeContent] %s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid,data.get('articleid'), str(gvMenuId) ,data.get('title'),data.get('nick'),data.get('content') ))
    #print(sql, ( '20180226',data.get('articleid'), '22',data.get('title'),data.get('nick'),data.get('content') ))
    gvConn.commit()
    cursor.close()

def insert_CommentData(data,dateid,menuid):
    global gvConn
    global gvMenuId
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertNaverCafeComment] %s,%s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid,data.get('articleid'), str(gvMenuId) ,data.get('commentid'),data.get('commentReplayID'),data.get('nick'),data.get('comment') ))
    gvConn.commit()    
    cursor.close()

def requestComment(clubID, articleID, page):
    commentURL = "http://cafe.naver.com/CommentView.nhn?search.clubid=" + str(clubID) + "&search.articleid=" + str(articleID) + "&search.page=" + str(page)
    #commentJson = None
    # 가져오기.
    try:
        requestResult = (urllib.request.urlopen(commentURL).read()).decode("utf-8")
    except:
        print("CONNECT ERROR")
        return None

    # JSON으로 파싱하기.
    try:
        commentJson = json.loads(requestResult)
    except:
        print("JSON ERROR")
        return None

    # 정상적으로 파싱됬나?
    commentResult = commentJson.get("result")
       
    if commentResult is None:
        print("ERROR DATA IS NONE")
        return None
    
    return commentResult


def createSTS_Comment():
    global gvConn
    global gvMenuId
    cursor = gvConn.cursor()
    sql = """
    IF OBJECT_ID('STS_Comment')		IS NOT NULL		DROP TABLE STS_Comment
    
    SELECT Articleid, ISNULL( STUFF(
    ( 
    	SELECT CHAR(10) + C.Comment + '  ('+ C.NickName + ' ) '
    	FROM [T_NaverCafeComment] C WITH(NOLOCK)
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
    FROM [T_NaverCafeComment] A
    GROUP BY Articleid
    
    CREATE CLUSTERED INDEX CX__Comment ON STS_Comment(Articleid)
    """
    cursor.execute(sql)
    gvConn.commit()    
    cursor.close()

def getComment(articleID,dateid):
    clubID = 0#CafeNum
    # 첫페이지 가져와요.
    commentResult = requestComment(clubID, articleID, 1)
    if commentResult is None:
        return None
            
    # 변수 확인!!!
    commentTotalCount = commentResult["totalCount"]
    commentCountPerPage = commentResult["countPerPage"]
    commentPage = 0
    if commentTotalCount > 0:
        commentPage = ((commentTotalCount - 1) // commentCountPerPage) + 1;
    
    for page in range(1, commentPage + 1):
        if commentResult is None:
            commentResult = requestComment(clubID, articleID, page)
        #else:
            #print(str(page) + " IS AREADY")
        
        if commentResult is None:
            continue
        
        # 개별 댓글 수집
        commentLists = commentResult["list"]
        for eachComment in commentLists:
            commentID = eachComment["commentid"]
            #eachCommentDate = eachComment["writedt"]
            commentUserNickname = eachComment["writernick"]
            #eachCommentUserID = eachComment["writerid"]
            commentContent = eachComment["content"].replace("\t", " ")
            commentReplayID = eachComment["refcommentid"]
            commentIsReply = eachComment["refComment"]
            #commentISDeleted = eachComment["deleted"]
            
            if commentIsReply == True:
                insert_CommentData({'articleid' : articleID, 'commentid' : str(commentID), 'nick' : commentUserNickname, 'comment' : commentContent, 'commentReplayID' : commentReplayID},dateid,gvMenuId)
            else:
                insert_CommentData({'articleid' : articleID, 'commentid' : str(commentID), 'nick' : commentUserNickname, 'comment' : commentContent, 'commentReplayID' : ''},dateid,gvMenuId)
        
        commentResult = None # 비우면 다음 루프때 받을거야.

def get_content(page):
    global gvMinArticleid
    global gvMenuId
    #driver = webdriver.Chrome('chromedriver.exe')
    #driver = webdriver.PhantomJS('phantomjs.exe')
    global gvDriver
    #https://m.cafe.naver.com/ArticleAllListAjax.nhn?search.clubid=&search.menuid=22
    base_url = 'https://m.cafe.naver.com/ArticleAllListAjax.nhn'
    gvDriver.get(base_url + '&search.menuid='+str(gvMenuId)+'&search.page='+str(page))
    soup = bs(gvDriver.page_source, 'html.parser')
   
    article_list = gvDriver.find_elements_by_css_selector('li[class="board_box"] > a')
    article_urls = [ i.get_attribute('data-article-id') for i in article_list ]
    
    base_url + '&search.menuid='+str(gvMenuId)
    
    #<div class="user_area"> <span class="time">18.02.20.</span> <span class="time">18:13</span>
    for article in article_urls:
        if article is None:
            continue
        
        if int(article) < int(gvMinArticleid) and int(gvMinArticleid) > 0:
            break;
        
        gvDriver.get('https://m.cafe.naver.com/ArticleRead.nhn?clubid=&articleid='+article+'&menuid='+str(gvMenuId))
        soup = bs(gvDriver.page_source, 'html.parser')
        
            
        if len(soup.select('h2[class="tit"]')) < 1:
            continue
        
        dateTxt = soup.select('span[class="date font_l"]')[0].get_text()
        date = datetime.datetime(int(dateTxt[:4]), int(dateTxt[5:7]), int(dateTxt[8:10]), int(dateTxt[12:14]), int(dateTxt[-2:]))
        
        if eq(str(gvMenuId),'22') or eq(str(gvMenuId),'62'):
            if (date - gvDate) > datetime.timedelta(hours = 1):
                continue
            if (date - gvDate) < datetime.timedelta(hours = 0):
                if int(gvMinArticleid) == 0:
                    gvMinArticleid = article
                    break
        else :
            if (gvDate-date) > datetime.timedelta(days = 14):
                break
            
        title = soup.select('h2[class="tit"]')[0].get_text()
        nick = soup.select('div[class="post_title"] span[class="end_user_nick"]')[0].get_text()
        #print(title)
        if gvMenuId == 1 or gvMenuId == 18 :
            contents = soup.select('div[class="NHN_Writeform_Main"] p')
        else :   
            contents = soup.select('div[id="postContent"] > p, div[id="postContent"] > span, div[id="postContent"] > div')
            
        for tags in contents:
            content = '\r\n'.join([ tags.get_text().strip() for tags in contents ])
            
        content = content.replace("\r\n\r\n", "\r\n")
        content = content.replace("&lt;br /&gt;", "\r\n")
        #commentIDs = soup.select('div[class="section_comment"] ul li span[class="name ellip"]')
    
        comments = soup.select('div[class="section_comment"] ul li p')
        
        if len(comments) > 0:
            getComment(article,date.strftime('%Y%m%d'))
       
        #print(content)
        insert_ContentData({'articleid' : article, 'title' : title, 'nick' : nick, 'content' : content},date.strftime('%Y%m%d'),gvMenuId)
        

def set_menu(menuId):
    global gvMenuId
    global gvMinArticleid
    
    gvMenuId = menuId
    gvMinArticleid = 0
    if eq(str(gvMenuId),'22') or eq(str(gvMenuId),'62'):
        for i in range(1,100):
            get_content(i)
            if int(gvMinArticleid) > 0:
                break;
    else:
        get_content(1)
        


def webCrawler():
    global gvDriver
    global gvDate
    global gvConn
    start_time = time.time()
    #Chrome Options
    chromeOptions = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images":2}
    chromeOptions.add_experimental_option("prefs",prefs)
    gvDriver = webdriver.Chrome(chrome_options=chromeOptions)
    #gvDriver = webdriver.Chrome('chromedriver.exe')
    gvDriver.implicitly_wait(10)
    
    # 로그인 전용 화면
    gvDriver.get('https://nid.naver.com/nidlogin.login')
    # 아이디와 비밀번호 입력
    gvDriver.find_element_by_name('id').send_keys('')
    gvDriver.find_element_by_name('pw').send_keys('')
    gvDriver.find_element_by_css_selector('#frmNIDLogin > fieldset > input').click()
    # 로그인 버튼 클릭
    gvDriver.implicitly_wait(3)
    #'''
    
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
    
    set_menu(1)
    set_menu(18)
    set_menu(114)
    set_menu(261)
    set_menu(62)
    set_menu(22)
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
    # 3분 이상
   
    #exit(1)

