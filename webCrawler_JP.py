# -*- coding: utf-8 -*-
"""
Created on Tue May  8 15:46:12 2018

@author: user
"""

from selenium import webdriver
from bs4 import BeautifulSoup as bs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

import datetime
import re
import time
import pymssql
    
global gvDate
global gvMenuId
global gvConn
global gvDriver

def insert_ContentData(content,dateid,threadId,menuid,index,url):
    global gvConn
    cursor = gvConn.cursor()
    sql = "EXEC [USP_InsertWebCrawlerContent] %s,%s,%s,%s,%s,%s"
    cursor.execute(sql, ( dateid, threadId, index, str(menuid), url, content ))
    #print(sql, ( '20180226',data.get('articleid'), '22',data.get('title'),data.get('nick'),data.get('content') ))
    gvConn.commit()
    cursor.close()

def sleeper():
    global gvDriver
   
    while True:
        # Get user input
        num = 3
 
        # Try to convert it to a float
        try:
            num = float(num)
        except ValueError:
            continue
 
        # Run our time.sleep() command,
        # and show the before and after time
        print('Before: %s' % time.ctime())
        time.sleep(num)
    #'''    
        SCROLL_PAUSE_TIME = 3 #0.5
        
        # Get scroll height
        last_height = gvDriver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down to bottom
            gvDriver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)
        
            # Calculate new scroll height and compare with last scroll height
            new_height = gvDriver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            break;
                
        print('After: %s\n' % time.ctime())    
        break;
        
def get_twitterBak():
    global gvDriver
    global gvDate
    thread_urls = []
    cursor = gvConn.cursor()
    cursor.execute("""
                        SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
                        SELECT url FROM [dbo].[T_WebCrawlerContent] WITH(NOLOCK) WHERE MENUID = 2 AND REPLACE(REPLACE(Content,char(13),''),char(10),'') = ''  
                """)
    row = cursor.fetchone()
    while row:
        #print("url=%s" % (row[0]))
        thread_urls.append(row[0])
        row = cursor.fetchone()
    
    for thread in thread_urls:
        if thread.find('status') < 0:
            continue
        
        gvDriver.get(thread)    
        try:   
            wait = WebDriverWait(gvDriver, 20);
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[lang='ja'] > span, div[lang='en'] > span, div[lang='ko'] > span, div[class='rn-13yce4e rn-fnigne rn-ndvcnb rn-gxnn5r rn-deolkf rn-q9ob72 rn-1471scf rn-1lw9tu2 rn-10u92zi rn-cygvgh rn-16dba41 rn-ad9z0x rn-1mnahxq rn-61z16t rn-p1pxzi rn-11wrixw rn-9aemit rn-1mdbw0j rn-gy4na3 rn-txxdd rn-bauka4 rn-1jeg54m rn-qvutc0'] > span")))
        except :
            continue
            
        #gvDriver.implicitly_wait(20)
        
        soup = bs(gvDriver.page_source, 'html.parser')
        titleList = soup.select("div[lang='ja'] > span, div[lang='en'] > span, div[lang='ko'] > span, div[class='rn-13yce4e rn-fnigne rn-ndvcnb rn-gxnn5r rn-deolkf rn-q9ob72 rn-1471scf rn-1lw9tu2 rn-10u92zi rn-cygvgh rn-16dba41 rn-ad9z0x rn-1mnahxq rn-61z16t rn-p1pxzi rn-11wrixw rn-9aemit rn-1mdbw0j rn-gy4na3 rn-txxdd rn-bauka4 rn-1jeg54m rn-qvutc0'] > span")
        #print(thread)
        
        contentTxt = ''
        for i in range(len(titleList)):
            tmpTxt = titleList[i].get_text()
            #print(tmpTxt)
            contentTxt = contentTxt + tmpTxt
        
        patten = re.compile(r"(\d+[0-9])$")
        threadId = patten.search(thread.replace("/0-","")).group()    
        
        insert_ContentData(contentTxt.replace("  ", "\r\n"),gvDate.strftime('%Y%m%d'),threadId,2,0,thread)
           
def get_twitter():
    global gvDriver
    global gvDate
    gvDriver.get('https://mobile.twitter.com/search?f=tweets&vertical=default&q=&src=typd')
    sleeper()
    gvDriver.implicitly_wait(60)
    wait = WebDriverWait(gvDriver, 60);
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class='rn-13yce4e rn-fnigne rn-ndvcnb rn-gxnn5r rn-deolkf rn-q9ob72 rn-1471scf rn-1lw9tu2 rn-gwet1z rn-cygvgh rn-16dba41 rn-ad9z0x rn-1mnahxq rn-61z16t rn-p1pxzi rn-11wrixw rn-wk8lta rn-9aemit rn-1mdbw0j rn-gy4na3 rn-bnwqim rn-bauka4 rn-q42fyq rn-qvutc0']")))
    soup = bs(gvDriver.page_source, 'html.parser')
    
    thread_list = gvDriver.find_elements_by_css_selector("div > a[role='link']")
    thread_urls = [ i.get_attribute('href') for i in thread_list ]
    for thread in thread_urls:
         try:
             if thread.find('status') < 0:
                 continue
             gvDriver.get(thread.replace("/video/1",""))    
             try:   
                 wait = WebDriverWait(gvDriver, 20);
                 wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[lang='ja'] > span, div[lang='en'] > span, div[lang='ko'] > span, div[class='rn-13yce4e rn-fnigne rn-ndvcnb rn-gxnn5r rn-deolkf rn-q9ob72 rn-1471scf rn-1lw9tu2 rn-10u92zi rn-cygvgh rn-16dba41 rn-ad9z0x rn-1mnahxq rn-61z16t rn-p1pxzi rn-11wrixw rn-9aemit rn-1mdbw0j rn-gy4na3 rn-txxdd rn-bauka4 rn-1jeg54m rn-qvutc0'] > span")))
             except :
                 continue
            
             soup = bs(gvDriver.page_source, 'html.parser')
             titleList = soup.select("div[lang='ja'] > span, div[lang='en'] > span, div[lang='ko'] > span, div[class='rn-13yce4e rn-fnigne rn-ndvcnb rn-gxnn5r rn-deolkf rn-q9ob72 rn-1471scf rn-1lw9tu2 rn-10u92zi rn-cygvgh rn-16dba41 rn-ad9z0x rn-1mnahxq rn-61z16t rn-p1pxzi rn-11wrixw rn-9aemit rn-1mdbw0j rn-gy4na3 rn-txxdd rn-bauka4 rn-1jeg54m rn-qvutc0'] > span")
             threadId = ''
             contentTxt = ''
             for i in range(len(titleList)):
                 tmpTxt = titleList[i].get_text()
             #print(tmpTxt)
             contentTxt = contentTxt + tmpTxt
            
             patten = re.compile(r"(\d+[0-9])$")
             threadId = patten.search(thread.replace("/0-","")).group()    
             #print(thread)
             #print(threadId)
             insert_ContentData(contentTxt.replace("  ", "\r\n"),gvDate.strftime('%Y%m%d'),threadId,2,0,thread)
         except:
             continue
       
        
def get_2ch():
    global gvDriver
    global gvDate
    isDone = 0
    gvDriver.get('http://find.2ch.sc/?STR=&TYPE=TITLE&COUNT=50&ENCODING=SJIS')
    gvDriver.implicitly_wait(10)
    soup = bs(gvDriver.page_source, 'html.parser')
    
    thread_list = gvDriver.find_elements_by_css_selector('dl > dt > a')
    thread_urls = [ i.get_attribute('href') for i in thread_list ]
    
    for thread in thread_urls:
        gvDriver.get(thread)    
        wait = WebDriverWait(gvDriver, 20);
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "dl > dd[class='net']")))
        gvDriver.implicitly_wait(20)
        
        threadId = re.compile(r"(\d+[0-9])").search(thread).group()
        
        soup = bs(gvDriver.page_source, 'html.parser')
        titleList = soup.select('dl > dt')
        contentsList = soup.select('dl > dd')
       
        for i in range(len(titleList)):
            dateTxt = titleList[i].get_text()
            contentTxt = contentsList[i].get_text()
            patten = re.compile(r"(19[0-9]{2}|2[0-9]{3})[\/](0[1-9]|1[012])[\/]([123]0|[012][1-9]|31)")
            
            try:
                date = patten.search(dateTxt).group()
            except:
                continue
        
            patten = re.compile(r"([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?")
            time = patten.search(dateTxt).group()
            
            patten = re.compile(r"^\w+")
            index = patten.search(dateTxt).group()
            
            dateValue = datetime.datetime(int(date[:4]), int(date[5:7]), int(date[8:10]), int(time[:2]), int(time[3:5]), int(time[-2:]))
            
            if (gvDate-dateValue) > datetime.timedelta(days = 14):
                isDone = 1
            
            insert_ContentData(contentTxt.replace("  ", "\r\n"),dateValue.strftime('%Y%m%d'),threadId,1,index,'')
        
        #if isDone > 0:
        #   break;
        break;
    
   
def webCrawler():
    global gvDriver
    global gvDate
    global gvConn
    start_time = time.time()
    #Chrome Options
    chromeOptions = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images":2, "profile.managed_default_content_settings.media_stream":2}
    chromeOptions.add_experimental_option("prefs",prefs)
    gvDriver = webdriver.Chrome(chrome_options=chromeOptions)
    #gvDriver = webdriver.Chrome('chromedriver.exe')
    gvDriver.implicitly_wait(10)
    
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
    
    get_twitter()
    get_2ch()
    get_twitterBak()

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
    # 3분 이상
    #'''
    #exit(1)

