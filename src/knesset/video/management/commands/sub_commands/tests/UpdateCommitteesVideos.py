#encoding: utf-8

import datetime
from django.test import TestCase
from BeautifulSoup import BeautifulSoup
from knesset.video.management.commands.sub_commands.UpdateCommitteesVideos import UpdateCommitteesVideos

class UpdateCommitteesVideos_test(UpdateCommitteesVideos):
    
    def __init__(self,
        testCase,committees,committees_index_page,committee_mainpage_soups,
        committee_videos_soups,committee_num_mms_videos,
        opts
    ):
        self._committees_index_page=committees_index_page
        self._testCase=testCase
        self._committee_mainpage_soups=committee_mainpage_soups
        self._committee_videos_soups=committee_videos_soups
        self._committee_num_mms_videos=committee_num_mms_videos
        self._opts=opts
        self.updateCommitteePortalKnessetBroadcastsUrlLog=[]
        self.saveVideoLog=[]
        UpdateCommitteesVideos.__init__(self,None,committees)
    
    def _get_committees_index_page(self):
        return self._committees_index_page
    
    def _get_committee_mainpage_soup(self,href):
        self._testCase.assertIn(href,self._committee_mainpage_soups)
        return self._committee_mainpage_soups[href]
    
    def _update_committee_portal_knesset_broadcasts_url(self,comm,url):
        self.updateCommitteePortalKnessetBroadcastsUrlLog.append((comm,url))
        
    def _get_committee_videos_soup(self,bcasturl):
        self._testCase.assertIn(bcasturl,self._committee_videos_soups)
        return self._committee_videos_soups[bcasturl]
    
    def _get_committee_num_mms_videos(self,comm,group,ignoreHide,embed_link):
        self._testCase.assertIn((comm.id,group,ignoreHide,embed_link),self._committee_num_mms_videos)
        return self._committee_num_mms_videos[(comm.id,group,ignoreHide,embed_link)]

    def _saveVideo(self,videoFields):
        self.saveVideoLog.append(videoFields)

    def _get_opt(self,opt):
        self._testCase.assertIn(opt,self._opts)
        return self._opts[opt]
    
    def _log(self,*args,**kwargs):
        pass
        #print args[1]
    
    def _check_timer(self,*args,**kwargs): pass

class Committee_test():
    
    def __init__(self,cid,name,portal_knesset_broadcasts_url):
        self.id=cid
        self.name=name
        self.portal_knesset_broadcasts_url=portal_knesset_broadcasts_url

class testUpdateCommitteesVideos(TestCase):
    
    maxDiff=None
    
    def testUpdateCommitteesVideos(self):
        he1=u'ועדת העבודה, הרווחה והבריאות'
        he2=u'ועדה לענייני ביקורת המדינה'
        he3=u'ועדה מיוחדת לבעיית העובדים הזרים'
        he4=u'ועדת המדע והטכנולוגיה'
        committees=[
            Committee_test(1,he1,''),
            Committee_test(2,he2,'http://portal.knesset.gov.il/Com10bikoret/he-IL/CommitteeBroadcast/default.htm'),
            Committee_test(3,he3,''),
            Committee_test(4,he4,''),
        ]
        obj=UpdateCommitteesVideos_test(
            testCase=self, 
            committees=committees, 
            committees_index_page=self.COMMITTEES_INDEX_PAGE, 
            committee_mainpage_soups={
                'http://portal.knesset.gov.il/com28avoda/he-il':BeautifulSoup(self.COMMITTEE1_MAINPAGE),
                'http://www.knesset.gov.il/committees/heb/vaada.asp?vaada=15':BeautifulSoup(self.COMMITTEE3_MAINPAGE),
                'http://portal.knesset.gov.il/com13mada/he-il':BeautifulSoup(self.COMMITTEE4_MAINPAGE),
            }, 
            committee_videos_soups={
                'http://portal.knesset.gov.il/Com28avoda/he-IL/CommitteeBroadcast/default.htm':BeautifulSoup(self.COMMITTEE1_VIDEOS),
                'http://portal.knesset.gov.il/Com10bikoret/he-IL/CommitteeBroadcast/default.htm':BeautifulSoup(self.COMMITTEE2_VIDEOS),
                'http://www.knesset.gov.il/committees/heb/vaadaonline.asp?vaada=15':BeautifulSoup(self.COMMITTEE3_VIDEOS),
                'http://portal.knesset.gov.il/Com13mada/he-IL/CommitteeBroadcast/default.htm':BeautifulSoup(self.COMMITTEE4_VIDEOS),
            }, 
            committee_num_mms_videos={
                (1, 'mms', True, u'mms://212.235.5.241/committeeArchive/work/work_2011122195347.asf'):0,
                (1, 'mms', True, u'mms://212.235.5.241/committeeArchive/work/work_2011122095048.asf'):0,
                (2, 'mms', True, u'mms://212.235.5.241/committeeArchive/bikoret/bikoret_201112218497.asf'):1,
                (2, 'mms', True, u'mms://212.235.5.241/committeeArchive/bikoret/bikoret_20111220104810.asf'):0,
                (3, 'mms', True, u'mms://212.235.5.241/committeeArchive/samim/samim_20111226113358.asf'):0,
                (4, 'mms', True, u'mms://212.235.5.241/committeeArchive/science/science_20121295433.asf'):0,
            },
            opts={
                'with-history':False,
            }
        )
        self.assertIn(
            (committees[0], 
            u'http://portal.knesset.gov.il/Com28avoda/he-IL/CommitteeBroadcast/default.htm'),
            obj.updateCommitteePortalKnessetBroadcastsUrlLog
        )
        self.assertIn(
            (committees[2], 
            u'http://www.knesset.gov.il/committees/heb/vaadaonline.asp?vaada=15'),
            obj.updateCommitteePortalKnessetBroadcastsUrlLog
        )
        self.assertIn(
            (committees[3], 
            u'http://portal.knesset.gov.il/Com13mada/he-IL/CommitteeBroadcast/default.htm'),
            obj.updateCommitteePortalKnessetBroadcastsUrlLog
        )
        self.assertEqual(len(obj.updateCommitteePortalKnessetBroadcastsUrlLog),3)
        self.assertEqual(len(obj.saveVideoLog), 5, 'len(saveVideoLog) = '+str(len(obj.saveVideoLog))+' saveVideoLog = '+str(obj.saveVideoLog))
        v=obj.saveVideoLog[0]
        self.assertEqual(v['embed_link'], 'mms://212.235.5.241/committeeArchive/work/work_2011122195347.asf')
        self.assertEqual(v['group'], 'mms')
        self.assertEqual(v['content_object'], committees[0])
        vtitle=u"""הצעת חוק גיל פרישה (תיקון מס' 3) (ביטול העלאת גיל הפרישה לאישה), התשע"ב-2011 של חה"כ אילן גילאון, חה"כ חיים כץ, חה"כ מוחמד ברכה, חה"כ דליה איציק, חה"כ ציפי חוטובלי, חה"כ זהבה גלאון, חה"כ משה גפני, חה"כ יעקב אדרי, חה"כ ציון פיניאן, חה"כ שלי יחימוביץ', חה"כ חנא סוייד, חה"כ דב חנין, חה"כ עפו אגבאריה, חה"כ ניצן הורוביץ."""
        self.assertEqual(v['title'], vtitle, "\n'"+v['title']+"'\n!=\n'"+vtitle+"'")
        self.assertEqual(v['source_type'], 'mms-knesset-portal')
        self.assertEqual(v['published'], datetime.datetime(2011, 12, 21, 9, 53, 47))
        v=obj.saveVideoLog[1]
        self.assertEqual(v['embed_link'], 'mms://212.235.5.241/committeeArchive/work/work_2011122095048.asf')
        self.assertEqual(v['group'], 'mms')
        self.assertEqual(v['content_object'], committees[0])
        vtitle=u"""הצעת חוק לתיקון פקודת הרוקחים (בחינת רישוי ברוקחות), התש"ע-2010 של חה"כ אריה אלדד.  (פ/2334)"""
        self.assertEqual(v['title'], vtitle, "\n'"+v['title']+"'\n!=\n'"+vtitle+"'")
        self.assertEqual(v['source_type'], 'mms-knesset-portal')
        self.assertEqual(v['published'], datetime.datetime(2011, 12, 20, 9, 50, 48))
        v=obj.saveVideoLog[2]
        self.assertEqual(v['embed_link'], 'mms://212.235.5.241/committeeArchive/bikoret/bikoret_20111220104810.asf')
        self.assertEqual(v['group'], 'mms')
        self.assertEqual(v['content_object'], committees[1])
        vtitle=u"""התחדשות עירונית באמצעות פינוי-בינוי ועיבוי הבנייה - דוח מבקר המדינה 61ב', עמ' 667."""
        self.assertEqual(v['title'], vtitle, "\n'"+v['title']+"'\n!=\n'"+vtitle+"'")
        self.assertEqual(v['source_type'], 'mms-knesset-portal')
        self.assertEqual(v['published'], datetime.datetime(2011, 12, 20, 10, 48, 10))
        v=obj.saveVideoLog[3]
        self.assertEqual(v['embed_link'], 'mms://212.235.5.241/committeeArchive/samim/samim_20111226113358.asf')
        self.assertEqual(v['group'], 'mms')
        self.assertEqual(v['content_object'], committees[2])
        vtitle=u"""בחינת התמודדות המדינה, עם הקושי בהשמת עובדי סיעוד זרים אצל מעסיקים סיעודיים קשים (מעקב)"""
        self.assertEqual(v['title'], vtitle, "\n'"+v['title']+"'\n!=\n'"+vtitle+"'")
        self.assertEqual(v['source_type'], 'mms-knesset-portal')
        v=obj.saveVideoLog[4]
        self.assertEqual(v['embed_link'], u'mms://212.235.5.241/committeeArchive/science/science_20121295433.asf')
        self.assertEqual(v['group'], 'mms')
        self.assertEqual(v['content_object'], committees[3])
        vtitle=u""""Darknet"- תשתית פשע מאורגן באינטרנט - בהשתתפות: ד"ר נמרוד קוזלובסקי, עו"ד, מומחה בתחום משפט האינטרנט ואבטחת מידע"""
        self.assertEqual(v['title'], vtitle, "\n'"+v['title']+"'\n!=\n'"+vtitle+"'")
        self.assertEqual(v['source_type'], 'mms-knesset-portal')

    COMMITTEES_INDEX_PAGE=u"""
        <tr><td colspan=7><img src="/images/arrow-s-green.gif" align="middle"> <b>ועדת העבודה, הרווחה והבריאות</b>
        </td></tr>
        <tr valign=top>
        <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
        <td><a href="http://portal.knesset.gov.il/com28avoda/he-il" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">פורטל הוועדה</a></td>
        </tr>
        <tr><td colspan=7><img src="/images/arrow-s-green.gif" align="middle"> <b>ועדה לענייני ביקורת המדינה</b>
        <!---->
        </td></tr>
        <tr valign=top>
        <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
        <td><a href="http://portal.knesset.gov.il/com10bikoret/he-il" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">פורטל הוועדה</a></td>
        </tr>
        <tr><td colspan=7><img src="/images/arrow-s-green.gif" align="middle"> <b>ועדה מיוחדת לבעיית העובדים הזרים</b>
        <!---->
        </td></tr>
        <tr valign=top>
        <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
        <td><a href="vaada.asp?vaada=15" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">מידע כללי</a></td>
        <td><a href="/agenda/heb/vaada.asp?vaada=15" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">סדר יום</a></td>
        <td><a href="/spokesman/heb/template.asp?ComId=15" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">הודעות לעיתונות</a></td>
        <td><a href="/protocols/heb/protocol_search.aspx?comID=15" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">פרוטוקולי הישיבות</a></td>
        <td></td>
        <td></td>
        </tr>
        <tr><td colspan=7 height=2></td></tr>
        <tr><td colspan=7><img src="/images/arrow-s-green.gif" align="middle"> <b>ועדת  המדע  והטכנולוגיה</b>
        <!---->
        </td></tr>
        <tr valign=top>
        <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
        <td><a href="http://portal.knesset.gov.il/com13mada/he-il" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">פורטל הוועדה</a></td>
        <td><a href="/agenda/heb/vaada.asp?vaada=13" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">סדר יום</a></td>
        <td><a href="http://portal.knesset.gov.il/com13mada/he-il/Messages/" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">הודעות לעיתונות</a></td>
        <td><a href="http://portal.knesset.gov.il/com13mada/he-il/Protocols/" onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">פרוטוקולי הישיבות</a></td>
        <td><a href="#" onclick="javascript:window.open('SubCommittees.asp?c_id=13','','width=600,height=450,scrollbars=yes,toolbar=1,directories=no,status=no,menubar=yes,resizable=yes')"  onmouseout="this.style.color='#2962B9'" onmouseover="this.style.color='#55B561';">ועדות משנה</a></td>
        <td></td></tr>
    """
    
    COMMITTEE1_MAINPAGE=u"""
        <td style="padding-right:2px;">
            <a id="_ctl0_cphContent_ciBroadcastCom_hplExplainTitle" class="Text9" href="/Com28avoda/he-IL/CommitteeBroadcast/default.htm">ועדות משודרות</a><br />
            <span id="_ctl0_cphContent_ciBroadcastCom_lblExplainText" class="Text10">חיפוש היסטורית ועדות משודרות</span>
        </td>
    """
    
    COMMITTEE1_VIDEOS=u"""
        <tr style="border-style:None;">
            <td>
                    <img id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_imgNewRow" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/work/work_2011122195347.asf,21/12/2011 09:53:47 1. הצעת חוק גיל פרישה (תיקון מס`` 3) (בי...');" src="../../Images/grid_row.gif" border="0" />
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_lblMeetingStart" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/work/work_2011122195347.asf,21/12/2011 09:53:47 1. הצעת חוק גיל פרישה (תיקון מס`` 3) (בי...');">21/12/2011 09:53:47</span>                                
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_lblSubject" title="1. הצעת חוק גיל פרישה (תיקון מס`` 3) (ביטול העלאת גיל הפרישה לאישה), התשע”ב-2011
 של חה”כ אילן גילאון, חה”כ חיים כץ, חה”כ מוחמד ברכה, חה”כ דליה איציק, חה”כ ציפי חוטובלי, חה”כ זהבה גלאון, חה”כ משה גפני, חה”כ יעקב אדרי, חה”כ ציון פיניאן, חה”כ שלי יחימוביץ``, חה”כ חנא סוייד, חה”כ דב חנין, חה”כ עפו אגבאריה, חה”כ ניצן הורוביץ.  " onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/work/work_2011122195347.asf,21/12/2011 09:53:47 1. הצעת חוק גיל פרישה (תיקון מס`` 3) (בי...');">1. הצעת חוק גיל פרישה (תיקון מס`` 3) (ביטול העלאת גיל הפרישה לאישה), התשע"ב-2011
 של חה"כ אילן גילאון, חה"כ חיים כץ, חה"כ מוחמד ברכה, חה"כ דליה איציק, חה"כ ציפי חוטובלי, חה"כ זהבה גלאון, חה"כ משה גפני, חה"כ יעקב אדרי, חה"כ ציון פיניאן, חה"כ שלי יחימוביץ``, חה"כ חנא סוייד, חה"כ דב חנין, חה"כ עפו אגבאריה, חה"כ ניצן הורוביץ.  </span>
                </td>
        </tr><tr style="border-style:None;">
                       <td>
                    <img id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl3_imgNewRow" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/work/work_2011122095048.asf,20/12/2011 09:50:48 הצעת חוק לתיקון פקודת הרוקחים (בחינת ריש...');" src="../../Images/grid_row.gif" border="0" />
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl3_lblMeetingStart" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/work/work_2011122095048.asf,20/12/2011 09:50:48 הצעת חוק לתיקון פקודת הרוקחים (בחינת ריש...');">20/12/2011 09:50:48</span>                                
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl3_lblSubject" title="הצעת חוק לתיקון פקודת הרוקחים (בחינת רישוי ברוקחות), התש”ע-2010 של חה”כ אריה אלדד.  (פ/2334)" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/work/work_2011122095048.asf,20/12/2011 09:50:48 הצעת חוק לתיקון פקודת הרוקחים (בחינת ריש...');">הצעת חוק לתיקון פקודת הרוקחים (בחינת רישוי ברוקחות), התש"ע-2010 של חה"כ אריה אלדד.  (פ/2334)</span>
                </td>
    """
    
    COMMITTEE2_MAINPAGE=u"""
        <td style="padding-right:2px;">
            <a id="_ctl0_cphContent_ciBroadcastCom_hplExplainTitle" class="Text9" href="/Com10bikoret/he-IL/CommitteeBroadcast/default.htm">ועדות משודרות</a><br />
            <span id="_ctl0_cphContent_ciBroadcastCom_lblExplainText" class="Text10">חיפוש היסטורית ועדות משודרות</span>
        </td>
    """
    
    COMMITTEE2_VIDEOS=u"""
                <td>
                    <img id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_imgNewRow" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/bikoret/bikoret_201112218497.asf,21/12/2011 08:49:07 חברת נמל אשדוד בע&quot;מ - סדרי קבלת עובדים ב...');" src="../../Images/grid_row.gif" border="0" />
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_lblMeetingStart" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/bikoret/bikoret_201112218497.asf,21/12/2011 08:49:07 חברת נמל אשדוד בע&quot;מ - סדרי קבלת עובדים ב...');">21/12/2011 08:49:07</span>                                
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_lblSubject" title="חברת נמל אשדוד בע”מ - סדרי קבלת עובדים בכירים - דו”ח מבקר המדינה 60א``, עמ`` 427." onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/bikoret/bikoret_201112218497.asf,21/12/2011 08:49:07 חברת נמל אשדוד בע&quot;מ - סדרי קבלת עובדים ב...');">חברת נמל אשדוד בע"מ - סדרי קבלת עובדים בכירים - דו"ח מבקר המדינה 60א``, עמ`` 427.</span>
                </td>
        </tr><tr style="border-style:None;">
            <td>
                    <img id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl3_imgNewRow" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/bikoret/bikoret_20111220104810.asf,20/12/2011 10:48:10 התחדשות עירונית באמצעות פינוי-בינוי ועיב...');" src="../../Images/grid_row.gif" border="0" />
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl3_lblMeetingStart" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/bikoret/bikoret_20111220104810.asf,20/12/2011 10:48:10 התחדשות עירונית באמצעות פינוי-בינוי ועיב...');">20/12/2011 10:48:10</span>                                
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl3_lblSubject" title="התחדשות עירונית באמצעות פינוי-בינוי ועיבוי הבנייה - דוח מבקר המדינה 61ב``, עמ`` 667." onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/bikoret/bikoret_20111220104810.asf,20/12/2011 10:48:10 התחדשות עירונית באמצעות פינוי-בינוי ועיב...');">התחדשות עירונית באמצעות פינוי-בינוי ועיבוי הבנייה - דוח מבקר המדינה 61ב``, עמ`` 667.</span>
                </td>
    """
    
    COMMITTEE3_MAINPAGE=u"""
        <tr>
            <td valign="top" width="100%" class="tdlink" align="right" height="4"><BR><A HREF="/committees/heb/vaadaonline.asp?vaada=15" class="sslink"><B>חיפוש בהיסטורית ועדות משודרות</B></A><p></td>
        </tr>
    """
    
    COMMITTEE3_VIDEOS=u"""
        <TABLE WIDTH=90% BORDER=0 CELLSPACING=1 CELLPADDING=2 style="font-size:10pt">
        <TR>
        <Td><a href="javascript:SetPlayerFileName('mms://212.235.5.241/committeeArchive/samim/samim_20111226113358.asf','בחינת התמודדות המדינה, עם הקושי בהשמת עובדי סיעוד זרים אצל מעסיקים סיעודיים קשים (מעקב)')" style="text-decoration:none"> <IMG SRC="/images/arrow-red.gif" border="0" align="middle">&nbsp;‏יום שני ‏26 ‏דצמבר ‏2011 &nbsp;בחינת התמודדות המדינה, עם הקושי בהשמת עובדי סיעוד זרים אצל מעסיקים סיעודיים קשים (מעקב)</A></tD>
        </TR>
        
        </TABLE>
    """
    
    COMMITTEE4_MAINPAGE=u"""
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr valign="top">
                <td id="_ctl0_cphContent_ciBroadcastCom_tdImg" width="45" height="43" align="center" style="background-position:center top;background-repeat:no-repeat;background-image:url(/KnessetCommitteeCMS/Images/Com13mada/speech.gif);">
                    <img id="_ctl0_cphContent_ciBroadcastCom_imgIcon" src="/KnessetCommitteeCMS/Images/Com13mada/Inquiry_Committee.gif" border="0" />            
                </td>
            
                <td style="padding-right:2px;">
                    <a id="_ctl0_cphContent_ciBroadcastCom_hplExplainTitle" class="Text9" href="/Com13mada/he-IL/CommitteeBroadcast/default.htm">ועדות משודרות</a><br />
                    <span id="_ctl0_cphContent_ciBroadcastCom_lblExplainText" class="Text10">חיפוש היסטורית ועדות משודרות</span>
                </td>
            </tr>
        </table>
    """
    
    COMMITTEE4_VIDEOS=u"""
        <tr>
            <td>
                    <img id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_imgNewRow" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/science/science_20121295433.asf,02/01/2012 09:54:33 &quot;Darknet&quot;- תשתית פשע מאורגן באינטרנט - ב...');" src="../../Images/grid_row.gif" border="0" />
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_lblMeetingStart" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/science/science_20121295433.asf,02/01/2012 09:54:33 &quot;Darknet&quot;- תשתית פשע מאורגן באינטרנט - ב...');">02/01/2012 09:54:33</span>                                
                    <span id="_ctl0_cphContent_grdLastWeeklyBroadcast__ctl2_lblSubject" title="”Darknet”- תשתית פשע מאורגן באינטרנט - בהשתתפות: ד”ר נמרוד קוזלובסקי, עו”ד, מומחה בתחום משפט האינטרנט ואבטחת מידע" onclick="javascript:return SetPlayerFileName('mms://212.235.5.241/committeeArchive/science/science_20121295433.asf,02/01/2012 09:54:33 &quot;Darknet&quot;- תשתית פשע מאורגן באינטרנט - ב...');">"Darknet"- תשתית פשע מאורגן באינטרנט - בהשתתפות: ד"ר נמרוד קוזלובסקי, עו"ד, מומחה בתחום משפט האינטרנט ואבטחת מידע</span>
                </td>
        </tr>
    """
    

