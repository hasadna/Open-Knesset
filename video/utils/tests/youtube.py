#encoding: utf-8
from django.test import TestCase
from video.utils.youtube import GetYoutubeVideos
import datetime
from dateutil.tz import tzutc

class testYoutube(TestCase):

    def testGetYoutubeVideosParse(self):
        videos=GetYoutubeVideos(videos_json=YOUTUBE_TEST_JSON_DATA).videos
        self.assertEqual(len(videos),2)
        self.assertEqual(videos[0]['embed_url'],u'https://www.youtube.com/v/IyLnwCYFG8I?version=3&f=videos&app=youtube_gdata')
        self.assertEqual(videos[0]['description'],u'www.facebook.com \u05d7"\u05db \u05d3\u05d1 \u05d7\u05e0\u05d9\u05df \u05e0\u05d5\u05d0\u05dd \u05d1\u05de\u05dc\u05d9\u05d0\u05d4 \u05dc\u05e4\u05e0\u05d9 \u05d4\u05d0\u05d9\u05e9\u05d5\u05e8 \u05d4\u05e1\u05d5\u05e4\u05d9 \u05e9\u05dc \u05d7\u05d5\u05e7 \u05d4\u05d7\u05e8\u05dd - \u05d4\u05d5\u05d0 \u05d7\u05d5\u05e7 \u05d4\u05d2\u05e0\u05ea \u05d4\u05d4\u05ea\u05e0\u05d7\u05dc\u05d5\u05d9\u05d5\u05ea, \u05d9\u05d5\u05dd \u05e9\u05e0\u05d9, \u05d4-11 \u05d1\u05d9\u05d5\u05dc\u05d9 2011')
        self.assertEqual(videos[0]['author'],u'DovKhenin')
        self.assertEqual(videos[0]['title'],u'\u05d7"\u05db \u05d3\u05d1 \u05d7\u05e0\u05d9\u05df \u05e2\u05dc \u05d7\u05d5\u05e7 \u05d4\u05d7\u05e8\u05dd \u05d1\u05de\u05dc\u05d9\u05d0\u05ea \u05d4\u05db\u05e0\u05e1\u05ea')
        self.assertEqual(videos[0]['embed_url_autoplay'],u'https://www.youtube.com/v/IyLnwCYFG8I?version=3&f=videos&app=youtube_gdata&autoplay=1')
        self.assertEqual(videos[0]['link'],u'https://www.youtube.com/watch?v=IyLnwCYFG8I&feature=youtube_gdata')
        self.assertEqual(videos[0]['id'],u'http://gdata.youtube.com/feeds/api/videos/IyLnwCYFG8I')
        self.assertEqual(videos[0]['thumbnail480x360'],u'http://i.ytimg.com/vi/IyLnwCYFG8I/0.jpg')
        self.assertEqual(videos[0]['published'],datetime.datetime(2011, 7, 11, 18, 11, 18, tzinfo=tzutc()))
        self.assertEqual(videos[0]['thumbnail90x120'],"http://i.ytimg.com/vi/IyLnwCYFG8I/1.jpg")
        self.assertEqual(videos[1]['embed_url'], u'https://www.youtube.com/v/PaaEToi3wHE?version=3&f=videos&app=youtube_gdata')
        self.assertEqual(videos[1]['description'], u'\u05d7"\u05db \u05d3\u05d1 \u05d7\u05e0\u05d9\u05df \u05d1\u05e8\u05d0\u05d9\u05d5\u05df \u05d1\u05e1\u05d5\u05d2\u05e8\u05d9\u05dd \u05d7\u05e9\u05d1\u05d5\u05df, \u05d1\u05e2\u05e7\u05d1\u05d5\u05ea \u05d4\u05d4\u05e4\u05d2\u05e0\u05d4 \u05d1\u05e9\u05d1\u05ea: \u05e2\u05dc \u05e4\u05ea\u05e8\u05d5\u05e0\u05d5\u05ea \u05d0\u05e4\u05e9\u05e8\u05d9\u05d9\u05dd \u05dc\u05de\u05e6\u05d5\u05e7\u05ea \u05d4\u05d3\u05d9\u05d5\u05e8, \u05e7\u05e4\u05d9\u05d8\u05dc\u05d9\u05d6\u05dd \u05de\u05d5\u05dc \u05de\u05d3\u05d9\u05e0\u05ea \u05e8\u05d5\u05d5\u05d7\u05d4, \u05d5\u05de\u05db\u05dc\u05d5\u05dc \u05d4\u05d3\u05d1\u05e8\u05d9\u05dd \u05d1\u05d4\u05dd \u05e2\u05d5\u05e1\u05e7\u05ea \u05d4\u05de\u05d7\u05d0\u05d4 - \u05de\u05e2\u05d1\u05e8 \u05dc\u05e9\u05db\u05e8 \u05d4\u05d3\u05d9\u05e8\u05d4')
        self.assertEqual(videos[1]['author'], u'23tv')
        self.assertEqual(videos[1]['title'], u'\u05d7"\u05db \u05d3\u05d1 \u05d7\u05e0\u05d9\u05df: "\u05d4\u05e4\u05ea\u05e8\u05d5\u05df \u05d4\u05d9\u05d7\u05d9\u05d3 - \u05d4\u05d7\u05d6\u05e8\u05ea \u05d4\u05d3\u05d9\u05d5\u05e8 \u05d4\u05e6\u05d9\u05d1\u05d5\u05e8\u05d9"')
        self.assertEqual(videos[1]['embed_url_autoplay'], u'https://www.youtube.com/v/PaaEToi3wHE?version=3&f=videos&app=youtube_gdata&autoplay=1')
        self.assertEqual(videos[1]['link'], u'https://www.youtube.com/watch?v=PaaEToi3wHE&feature=youtube_gdata')
        self.assertEqual(videos[1]['id'], u'http://gdata.youtube.com/feeds/api/videos/PaaEToi3wHE')
        self.assertEqual(videos[1]['thumbnail480x360'], u'http://i.ytimg.com/vi/PaaEToi3wHE/0.jpg')
        self.assertEqual(videos[1]['published'],datetime.datetime(2011, 7, 25, 13, 11, 47, tzinfo=tzutc()))
        self.assertEqual(videos[1]['thumbnail90x120'],"http://i.ytimg.com/vi/PaaEToi3wHE/1.jpg")

    def testGetYoutubeVideos(self):
        videos=GetYoutubeVideos(q='"gangnam style"',max_results=2).videos
        self.assertEqual(len(videos),2)
        video=videos[1]
        self.assertIsNotNone(video['description'])
        self.assertIsNotNone(video['author'])
        self.assertIsNotNone(video['title'])
        self.assertIsNotNone(video['link'])
        self.assertIsNotNone(video['id'])
        self.assertIsNotNone(video['published'])
        title_and_desc = (video['title'] + video['description']).lower()
        self.assertIn('gangnam',title_and_desc)
        self.assertIn('style',title_and_desc)

    def testGetYoutubeVideoIdUrl(self):
        videos=GetYoutubeVideos(youtube_id_url='http://gdata.youtube.com/feeds/api/videos/4SA3ecqrGvM').videos
        self.assertEqual(len(videos),1)
        self.assertEqual(videos[0]['embed_url'],u'http://www.youtube.com/v/4SA3ecqrGvM?version=3&f=videos&app=youtube_gdata')
        self.assertEqual(videos[0]['description'], u'\u05e2\u05d5\u05d3 \u05e1\u05e8\u05d8\u05d5\u05e0\u05d9\u05dd: http://Tapi.co.il\r\n\u05d0\u05d7\u05d3 \u05d4\u05e1\u05e8\u05d8\u05d5\u05e0\u05d9\u05dd \u05d4\u05db\u05d9 \u05d7\u05de\u05d5\u05d3\u05d9\u05dd, \u05d7\u05ea\u05d5\u05dc \u05e7\u05d8\u05df \u05d7\u05de\u05d5\u05d3 \u05d5\u05de\u05e6\u05d7\u05d9\u05e7 \u05de\u05d5\u05e4\u05ea\u05e2.')
        self.assertEqual(videos[0]['author'], u'tapild')
        self.assertEqual(videos[0]['thumbnail90x120'], u'http://i.ytimg.com/vi/4SA3ecqrGvM/1.jpg')
        self.assertEqual(videos[0]['title'], u'\u05d7\u05ea\u05d5\u05dc\u05d9\u05dd \u05de\u05e6\u05d7\u05d9\u05e7\u05d9\u05dd \u05d7\u05de\u05d5\u05d3\u05d9\u05dd | \u05d4\u05d7\u05ea\u05d5\u05dc \u05d4\u05de\u05d5\u05e4\u05ea\u05e2 | \u05d7\u05ea\u05d5\u05dc \u05d7\u05de\u05d5\u05d3 \u05de\u05e6\u05d7\u05d9\u05e7')
        self.assertEqual(videos[0]['embed_url_autoplay'], u'http://www.youtube.com/v/4SA3ecqrGvM?version=3&f=videos&app=youtube_gdata&autoplay=1')
        self.assertEqual(videos[0]['link'], u'http://www.youtube.com/watch?v=4SA3ecqrGvM&feature=youtube_gdata')
        self.assertEqual(videos[0]['published'], datetime.datetime(2010, 12, 30, 18, 13, tzinfo=tzutc()))
        self.assertEqual(videos[0]['id'], u'http://gdata.youtube.com/feeds/api/videos/4SA3ecqrGvM')
        self.assertEqual(videos[0]['thumbnail480x360'], u'http://i.ytimg.com/vi/4SA3ecqrGvM/0.jpg')

YOUTUBE_TEST_JSON_DATA=ur"""{
    "version":"1.0","encoding":"UTF-8",
    "feed":{
        "xmlns":"http://www.w3.org/2005/Atom","xmlns$media":"http://search.yahoo.com/mrss/",
        "xmlns$openSearch":"http://a9.com/-/spec/opensearchrss/1.0/",
        "xmlns$gd":"http://schemas.google.com/g/2005","xmlns$yt":"http://gdata.youtube.com/schemas/2007",
        "id":{"$t":"http://gdata.youtube.com/feeds/api/videos"},
        "updated":{"$t":"2011-11-26T21:53:07.494Z"},
        "category":[{"scheme":"http://schemas.google.com/g/2005#kind","term":"http://gdata.youtube.com/schemas/2007#video"}],
        "title":{"$t":"YouTube Videos matching query: דב חנין","type":"text"},
        "logo":{"$t":"http://www.youtube.com/img/pic_youtubelogo_123x63.gif"},
        "link":[
            {"rel":"alternate","type":"text/html","href":"https://www.youtube.com"},
            {"rel":"http://schemas.google.com/g/2005#feed","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos"},
            {"rel":"http://schemas.google.com/g/2005#batch","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos/batch"},
            {"rel":"self","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos?alt=json&q=%D7%93%D7%91+%D7%97%D7%A0%D7%99%D7%9F&start-index=1&max-results=2"},
            {"rel":"next","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos?alt=json&q=%D7%93%D7%91+%D7%97%D7%A0%D7%99%D7%9F&start-index=3&max-results=2"}
        ],
        "author":[{"name":{"$t":"YouTube"},"uri":{"$t":"http://www.youtube.com/"}}],
        "generator":{"$t":"YouTube data API","version":"2.1","uri":"http://gdata.youtube.com"},
        "openSearch$totalResults":{"$t":260},
        "openSearch$startIndex":{"$t":1},
        "openSearch$itemsPerPage":{"$t":2},
        "entry":[
            {
                "id":{"$t":"http://gdata.youtube.com/feeds/api/videos/IyLnwCYFG8I"},
                "published":{"$t":"2011-07-11T18:11:18.000Z"},
                "updated":{"$t":"2011-11-19T05:19:08.000Z"},
                "category":[{"scheme":"http://schemas.google.com/g/2005#kind","term":"http://gdata.youtube.com/schemas/2007#video"},{"scheme":"http://gdata.youtube.com/schemas/2007/categories.cat","term":"News","label":"News & Politics"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"חוק החרם"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"דב חנין"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"חדש"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"כנסת"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"הכנסת"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"הגנת ההתנחלויות"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"התנחלויות"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"דמוקרטיה"}],
                "title":{"$t":"ח\"כ דב חנין על חוק החרם במליאת הכנסת","type":"text"},
                "content":{"$t":"www.facebook.com ח\"כ דב חנין נואם במליאה לפני האישור הסופי של חוק החרם - הוא חוק הגנת ההתנחלויות, יום שני, ה-11 ביולי 2011","type":"text"},
                "link":[{"rel":"alternate","type":"text/html","href":"https://www.youtube.com/watch?v=IyLnwCYFG8I&feature=youtube_gdata"},{"rel":"http://gdata.youtube.com/schemas/2007#video.responses","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos/IyLnwCYFG8I/responses"},{"rel":"http://gdata.youtube.com/schemas/2007#video.related","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos/IyLnwCYFG8I/related"},{"rel":"http://gdata.youtube.com/schemas/2007#mobile","type":"text/html","href":"https://m.youtube.com/details?v=IyLnwCYFG8I"},{"rel":"self","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos/IyLnwCYFG8I"}],
                "author":[{"name":{"$t":"DovKhenin"},"uri":{"$t":"https://gdata.youtube.com/feeds/api/users/dovkhenin"}}],
                "gd$comments":{"gd$feedLink":{"href":"https://gdata.youtube.com/feeds/api/videos/IyLnwCYFG8I/comments","countHint":13}},
                "media$group":{
                    "media$category":[{"$t":"News","label":"News & Politics","scheme":"http://gdata.youtube.com/schemas/2007/categories.cat"}],
                    "media$content":[{"url":"https://www.youtube.com/v/IyLnwCYFG8I?version=3&f=videos&app=youtube_gdata","type":"application/x-shockwave-flash","medium":"video","isDefault":"true","expression":"full","duration":446,"yt$format":5},{"url":"rtsp://v1.cache6.c.youtube.com/CiILENy73wIaGQnCGwUmwOciIxMYDSANFEgGUgZ2aWRlb3MM/0/0/0/video.3gp","type":"video/3gpp","medium":"video","expression":"full","duration":446,"yt$format":1},{"url":"rtsp://v2.cache2.c.youtube.com/CiILENy73wIaGQnCGwUmwOciIxMYESARFEgGUgZ2aWRlb3MM/0/0/0/video.3gp","type":"video/3gpp","medium":"video","expression":"full","duration":446,"yt$format":6}],
                    "media$description":{"$t":"www.facebook.com ח\"כ דב חנין נואם במליאה לפני האישור הסופי של חוק החרם - הוא חוק הגנת ההתנחלויות, יום שני, ה-11 ביולי 2011","type":"plain"},
                    "media$keywords":{"$t":"חוק החרם, דב חנין, חדש, כנסת, הכנסת, הגנת ההתנחלויות, התנחלויות, דמוקרטיה"},
                    "media$player":[{"url":"https://www.youtube.com/watch?v=IyLnwCYFG8I&feature=youtube_gdata_player"}],
                    "media$thumbnail":[{"url":"http://i.ytimg.com/vi/IyLnwCYFG8I/0.jpg","height":360,"width":480,"time":"00:03:43"},{"url":"http://i.ytimg.com/vi/IyLnwCYFG8I/1.jpg","height":90,"width":120,"time":"00:01:51.500"},{"url":"http://i.ytimg.com/vi/IyLnwCYFG8I/2.jpg","height":90,"width":120,"time":"00:03:43"},{"url":"http://i.ytimg.com/vi/IyLnwCYFG8I/3.jpg","height":90,"width":120,"time":"00:05:34.500"}],
                    "media$title":{"$t":"ח\"כ דב חנין על חוק החרם במליאת הכנסת","type":"plain"},
                    "yt$duration":{"seconds":"446"}
                },
                "gd$rating":{"average":4.7777777,"max":5,"min":1,"numRaters":36,"rel":"http://schemas.google.com/g/2005#overall"},
                "yt$statistics":{"favoriteCount":"3","viewCount":"1422"}
            },{
                "id":{"$t":"http://gdata.youtube.com/feeds/api/videos/PaaEToi3wHE"},
                "published":{"$t":"2011-07-25T13:11:47.000Z"},
                "updated":{"$t":"2011-11-15T20:08:00.000Z"},
                "category":[{"scheme":"http://schemas.google.com/g/2005#kind","term":"http://gdata.youtube.com/schemas/2007#video"},{"scheme":"http://gdata.youtube.com/schemas/2007/categories.cat","term":"Entertainment","label":"Entertainment"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"דב חנין"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"סוגרים חשבון"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"מחאת האוהלים"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"דיור ציבורי"},{"scheme":"http://gdata.youtube.com/schemas/2007/keywords.cat","term":"חדש"}],
                "title":{"$t":"ח\"כ דב חנין: \"הפתרון היחיד - החזרת הדיור הציבורי\"","type":"text"},
                "content":{"$t":"ח\"כ דב חנין בראיון בסוגרים חשבון, בעקבות ההפגנה בשבת: על פתרונות אפשריים למצוקת הדיור, קפיטליזם מול מדינת רווחה, ומכלול הדברים בהם עוסקת המחאה - מעבר לשכר הדירה","type":"text"},
                "link":[{"rel":"alternate","type":"text/html","href":"https://www.youtube.com/watch?v=PaaEToi3wHE&feature=youtube_gdata"},{"rel":"http://gdata.youtube.com/schemas/2007#video.responses","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos/PaaEToi3wHE/responses"},{"rel":"http://gdata.youtube.com/schemas/2007#video.related","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos/PaaEToi3wHE/related"},{"rel":"http://gdata.youtube.com/schemas/2007#mobile","type":"text/html","href":"https://m.youtube.com/details?v=PaaEToi3wHE"},{"rel":"self","type":"application/atom+xml","href":"https://gdata.youtube.com/feeds/api/videos/PaaEToi3wHE"}],
                "author":[{"name":{"$t":"23tv"},"uri":{"$t":"https://gdata.youtube.com/feeds/api/users/23tv"}}],
                "gd$comments":{"gd$feedLink":{"href":"https://gdata.youtube.com/feeds/api/videos/PaaEToi3wHE/comments","countHint":3}},
                "media$group":{"media$category":[{"$t":"Entertainment","label":"Entertainment","scheme":"http://gdata.youtube.com/schemas/2007/categories.cat"}],"media$content":[{"url":"https://www.youtube.com/v/PaaEToi3wHE?version=3&f=videos&app=youtube_gdata","type":"application/x-shockwave-flash","medium":"video","isDefault":"true","expression":"full","duration":235,"yt$format":5},{"url":"rtsp://v6.cache2.c.youtube.com/CiILENy73wIaGQlxwLeIToSmPRMYDSANFEgGUgZ2aWRlb3MM/0/0/0/video.3gp","type":"video/3gpp","medium":"video","expression":"full","duration":235,"yt$format":1},{"url":"rtsp://v4.cache2.c.youtube.com/CiILENy73wIaGQlxwLeIToSmPRMYESARFEgGUgZ2aWRlb3MM/0/0/0/video.3gp","type":"video/3gpp","medium":"video","expression":"full","duration":235,"yt$format":6}],"media$description":{"$t":"ח\"כ דב חנין בראיון בסוגרים חשבון, בעקבות ההפגנה בשבת: על פתרונות אפשריים למצוקת הדיור, קפיטליזם מול מדינת רווחה, ומכלול הדברים בהם עוסקת המחאה - מעבר לשכר הדירה","type":"plain"},"media$keywords":{"$t":"דב חנין, סוגרים חשבון, מחאת האוהלים, דיור ציבורי, חדש"},"media$player":[{"url":"https://www.youtube.com/watch?v=PaaEToi3wHE&feature=youtube_gdata_player"}],"media$thumbnail":[{"url":"http://i.ytimg.com/vi/PaaEToi3wHE/0.jpg","height":360,"width":480,"time":"00:01:57.500"},{"url":"http://i.ytimg.com/vi/PaaEToi3wHE/1.jpg","height":90,"width":120,"time":"00:00:58.750"},{"url":"http://i.ytimg.com/vi/PaaEToi3wHE/2.jpg","height":90,"width":120,"time":"00:01:57.500"},{"url":"http://i.ytimg.com/vi/PaaEToi3wHE/3.jpg","height":90,"width":120,"time":"00:02:56.250"}],"media$title":{"$t":"ח\"כ דב חנין: \"הפתרון היחיד - החזרת הדיור הציבורי\"","type":"plain"},"yt$duration":{"seconds":"235"}},
                "gd$rating":{"average":5.0,"max":5,"min":1,"numRaters":11,"rel":"http://schemas.google.com/g/2005#overall"},
                "yt$statistics":{"favoriteCount":"0","viewCount":"537"}
            }
        ]
    }
}"""
