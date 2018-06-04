# -*- coding: utf-8 -*-
"""
Created on Mon Feb 12 11:29:17 2018

@author: user
"""
from selenium import webdriver
from bs4 import BeautifulSoup as bs
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
import datetime
import time
import pymssql
    
global gvDate
global gvMenuId
global gvMinArticleid
global gvConn
global gvDriver

def insert_ContentData(data,dateid,menuid,word):
    global gvConn
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertWebCrawlerAlert] %s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid,data.get('articleid'), str(word) , str(menuid) ,data.get('viewCount'),data.get('commentCount') ))
    #print(sql, ( '20180226',data.get('articleid'), '22',data.get('title'),data.get('nick'),data.get('content') ))
    gvConn.commit()
    cursor.close()
    
def get_content(articleid,word):
    article = articleid[0]
    menuId = articleid[1]
    #driver = webdriver.Chrome('chromedriver.exe')
    #driver = webdriver.PhantomJS('phantomjs.exe')
    global gvDriver
    gvDriver.get('https://m.cafe.naver.com/ArticleRead.nhn?clubid=&articleid='+str(article)+'&menuid='+str(menuId))
    soup = bs(gvDriver.page_source, 'html.parser')
        
    if len(soup.select('h2[class="tit"]')) < 1:
        return
    
    dateTxt = soup.select('span[class="date font_l"]')[0].get_text()
    date = datetime.datetime(int(dateTxt[:4]), int(dateTxt[5:7]), int(dateTxt[8:10]), int(dateTxt[12:14]), int(dateTxt[-2:]))
            
    viewCount = soup.select('div[class="post_title"] em')[0].get_text().replace(",", "").replace("만", "0000")
    
    if len(soup.select('div[class="section_comment"] em')) < 1:
        commentCount = '0'
    else :
        commentCount = soup.select('div[class="section_comment"] em')[0].get_text().replace(",", "")
        
    #print(commentCount)
    insert_ContentData({'articleid' : str(article), 'viewCount' : viewCount, 'commentCount' : commentCount},date.strftime('%Y%m%d'),str(menuId),word)
   
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
    gvDriver.implicitly_wait(10)
    
    #'''
    words = []
    gvConn = pymssql.connect(server='', user='', password='', database='', charset='UTF-8')
    cursor = gvConn.cursor()
    cursor.execute("""
                        SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
                        SELECT UniqueID FROM T_MasterWord WHERE TYPE = 5
                """)
    row = cursor.fetchone()
    while row:
        print("UniqueID=%d" % (row[0]))
        words.append(row[0])
        row = cursor.fetchone()
    #conn.commit()
    #'''
    
    #exec[dbo].[] '20180406', '20180420', 364, '', false
    now = datetime.datetime.now()
    startdate = (now + datetime.timedelta(days=-14)).strftime('%Y%m%d')
    endDate = now.strftime('%Y%m%d')
    
    sql = "EXEC [USP_SelectNaverCafe] %s,%s,%s,%s,%s"
    for word in words:    
        articleids = []
        #print(word)
        cursor.execute(sql, (startdate,endDate,word,'','false' )) 
        row = cursor.fetchone()
        while row:
            articleids.append([row[2], row[7]])
            row = cursor.fetchone()
        for articleid in articleids:
            get_content(articleid,word)
    
    # 작업 완료    
    #'''
    
    gvDriver.close()
    gvDriver.quit()
    gvConn.close()  
    elapsed_time = time.time() - start_time
    
    print(str(datetime.datetime.now()) + " : " + str(elapsed_time))

if __name__=='__main__':
    scheduler = BlockingScheduler()
    trigger = IntervalTrigger(hours=1)
    scheduler.add_job(webCrawler,trigger) 
    
    webCrawler();
    
    try:
        scheduler.start()
    except(KeyboardInterrupt, SystemExit):
        print("End")
        pass
    

