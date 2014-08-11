from django.db import connection, transaction
from itertools import groupby
from operator import itemgetter
from datetime import datetime, timedelta
#,datetime(g[4]),datetime(g[5])
def getAllAgendaPartyVotes():
    cursor = connection.cursor()
    cursor.execute(PARTY_QUERY)
    results = dict(map(lambda (key,group):(key,map(lambda g:(g[1],float(g[2]),float(g[3])),list(group))),
                       groupby(cursor.fetchall(),key=itemgetter(0))))
    return results

PARTY_QUERY = """
SELECT a.agendaid,
       a.partyid,
       round(coalesce(cast(coalesce(v.totalvotevalue,0.0)/a.totalscore*100.0 as numeric),0.0),2) score,
       round(coalesce(cast(coalesce(v.numvotes,0.0)/a.totalvolume*100.0 as numeric),0.0),2) volume,
       a.start_date, a.end_date
FROM   (SELECT agid                   agendaid,
               m.id                   partyid,
               sc * m.number_of_seats totalscore,
               numvotes * m.number_of_seats totalvolume, m.start_date, m.end_date
        FROM   (SELECT agenda_id               agid,
                       SUM(abs(score * importance)) sc,
                       COUNT(*) numvotes
                FROM   agendas_agendavote
                GROUP  BY agenda_id) agendavalues
               left outer join mks_party m
                 on 1=1) a
       left outer join (SELECT agenda_id, 
                          partyid, 
                          SUM(forvotes) - SUM(againstvotes) totalvotevalue ,
                          SUM(numvotes) numvotes
                   FROM   (SELECT a.agenda_id, 
                                  p.partyid, 
                                  CASE p.vtype 
                                    WHEN 'for' THEN p.numvotes * a.VALUE 
                                    ELSE 0 
                                  END forvotes, 
                                  CASE p.vtype 
                                    WHEN 'against' THEN p.numvotes * a.VALUE 
                                    ELSE 0 
                                  END againstvotes,
                                  p.numvotes numvotes
                           FROM   (SELECT m.current_party_id      partyid, 
                                          v.vote_id voteid, 
                                          v.TYPE    vtype, 
                                          COUNT(*)  numvotes 
                                   FROM   laws_voteaction v 
                                          inner join mks_member m 
                                            ON v.member_id = m.id 
                                   WHERE  v.TYPE IN ( 'for', 'against' ) 
                                   GROUP  BY m.current_party_id, 
                                             v.vote_id, 
                                             v.TYPE) p 
                                  inner join (SELECT vote_id, 
                                                     agenda_id, 
                                                     score * importance as VALUE 
                                              FROM   agendas_agendavote) a 
                                    ON p.voteid = a.vote_id) b  
                   GROUP  BY agenda_id, 
                             partyid 
                             ) v 
         ON a.agendaid = v.agenda_id 
            AND a.partyid = v.partyid 
ORDER BY agendaid,score desc"""

def agendas_mks_grade():
    cursor = connection.cursor()
    cursor.execute(MK_QUERY)
    results = dict(map(lambda (key,group):(key,map(lambda g:(g[1],float(g[2]),float(g[3]),int(g[4])),list(group))),
                       groupby(cursor.fetchall(),key=itemgetter(0))))
    return results

MK_QUERY = """
SELECT a.agendaid, 
       v.memberid, 
       Round(Coalesce(CAST(Coalesce(v.totalvotevalue, 0.0) / a.totalscore * 100.0 AS 
                  NUMERIC),0.0), 2 
       ) score,
       Round(Coalesce(CAST(Coalesce(v.numvotes,0.0) / a.numvotes * 100.0 AS
                  NUMERIC),0.0), 2
       ) volume,
       CAST(Coalesce(v.numvotes,0) AS NUMERIC) numvotes 
FROM   (SELECT agenda_id                    agendaid, 
               SUM(Abs(score * importance)) totalscore,
               COUNT(*) numvotes
        FROM   agendas_agendavote 
        GROUP  BY agenda_id) a 
       LEFT OUTER JOIN (SELECT agenda_id, 
                               memberid, 
                               SUM(forvotes) - SUM(againstvotes) totalvotevalue,
                               SUM(numvotes) numvotes
                        FROM   (SELECT a.agenda_id, 
                                       p.memberid, 
                                       CASE p.vtype 
                                         WHEN 'for' THEN p.numvotes * a.VALUE 
                                         ELSE 0 
                                       END forvotes, 
                                       CASE p.vtype 
                                         WHEN 'against' THEN 
                                         p.numvotes * a.VALUE 
                                         ELSE 0 
                                       END againstvotes, 
                                       p.numvotes numvotes 
                                FROM   (SELECT m.id      memberid, 
                                               v.vote_id voteid, 
                                               v.TYPE    vtype, 
                                               COUNT(*)  numvotes 
                                        FROM   laws_voteaction v 
                                               INNER JOIN mks_member m 
                                                 ON v.member_id = m.id 
                                        WHERE  v.TYPE IN ( 'for', 'against' ) 
                                        GROUP  BY m.id, 
                                                  v.vote_id, 
                                                  v.TYPE) p 
                                       INNER JOIN (SELECT vote_id, 
                                                          agenda_id, 
                                                          score * importance AS 
                                                          VALUE 
                                                   FROM   agendas_agendavote) a 
                                         ON p.voteid = a.vote_id) b 
                        GROUP  BY agenda_id, 
                                  memberid) v 
         ON a.agendaid = v.agenda_id 
ORDER  BY agendaid, 
          score DESC""" 

def getAgendaEditorIds():
    cursor = connection.cursor()
    cursor.execute("""SELECT agenda_id,user_id FROM agendas_agenda_editors ORDER BY agenda_id""")
    results = dict(map(lambda (key,group):(key,map(itemgetter(1),list(group))),
                       groupby(cursor.fetchall(),key=itemgetter(0))))
    return results

BASE_AGENDA_QUERY = """ 
INSERT INTO agendas_summaryagenda (month,summary_type,agenda_id,score,votes,for_votes,against_votes,db_created,db_updated)
SELECT  %(monthfunc)s,v.time) as month,
        'AG' as summary_type,
        a.agenda_id               agid,
        SUM(abs(a.score * a.importance)) sc,
        COUNT(*) numvotes,
        COUNT(*) numforvotes,
        COUNT(*) numagainstvotes,
        %(nowfunc)s,%(nowfunc)s
FROM   agendas_agendavote a
INNER JOIN laws_vote v ON a.vote_id = v.id
GROUP  BY %(monthfunc)s,v.time),a.agenda_id """

BASE_MK_QUERY = """
INSERT INTO agendas_summaryagenda (summary_type,agenda_id,mk_id,month,score,votes,for_votes,against_votes,db_created,db_updated)
SELECT 'MK' as summary_type,
       agenda_id,
       memberid,
       %(monthfunc)s,time) as month,
       SUM(forvotes) - SUM(againstvotes) totalvotevalue,
       SUM(numvotes) numvotes,
       SUM(numforvotes) numforvotes,
       SUM(numagainstvotes) numagainstvotes,
       %(nowfunc)s,%(nowfunc)s
FROM
  (SELECT a.agenda_id,
          p.memberid,
          a.time,
          CASE p.vtype
              WHEN 'for' THEN a.VALUE
              ELSE 0
          END forvotes,
          CASE p.vtype
              WHEN 'against' THEN a.VALUE
              ELSE 0
          END againstvotes,
          1 as numvotes,
          CASE p.vtype
              WHEN 'for' THEN 1
              ELSE 0
          END numforvotes,
          CASE p.vtype
              WHEN 'against' THEN 1
              ELSE 0
          END numagainstvotes          
   FROM
     (SELECT DISTINCT
             m.id memberid,
             v.vote_id voteid,
             v.TYPE vtype
      FROM laws_voteaction v
      INNER JOIN mks_member m ON v.member_id = m.id
      WHERE v.TYPE IN ('for',
                       'against')
      GROUP BY m.id,
               v.vote_id,
               v.TYPE) p
   INNER JOIN
     (SELECT a.vote_id,
             a.agenda_id,
             a.score * a.importance AS VALUE,
             v.time as time
      FROM agendas_agendavote a
      JOIN laws_vote v ON a.vote_id = v.id
) a ON p.voteid = a.vote_id) b
GROUP BY agenda_id,
         memberid,
         %(monthfunc)s,time)
"""
