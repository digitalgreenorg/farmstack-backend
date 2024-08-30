from queries.data import daas_woreda_ids

daas_woreda_ids_str = ', '.join(map(str, daas_woreda_ids))

def getVideosList(start_date, end_date, state, district, block, village, page=1, items_per_page=10):
    offset = (page - 1) * items_per_page
    query = f"""
        SELECT DISTINCT
            vv.id AS 'Video ID',
            vv.title AS 'Video Title',
            DATE_FORMAT(vv.time_created, '%Y-%m-%d %H:%i:%s') AS 'Video Created',
            vv.youtubeid AS 'Youtube ID',
            gs.state_name AS 'Region Name',
            gd.district_name AS 'Woreda Name',
            gb.block_name AS 'Kebele Name',
            gv.village_name AS 'Village Name',
            vl.language_name AS 'Language'
        FROM
            digitalgreen.videos_video vv
            JOIN digitalgreen.videos_language vl ON vv.language_id = vl.id
            JOIN digitalgreen.geographies_village gv ON gv.id = vv.village_id
            JOIN digitalgreen.geographies_block gb ON gb.id = gv.block_id
            JOIN digitalgreen.geographies_district gd ON gd.id = gb.district_id
            JOIN digitalgreen.geographies_state gs ON gs.id = gd.state_id
            JOIN digitalgreen.geographies_country gc ON gc.id = gs.country_id
        WHERE
            vv.time_created BETWEEN '{start_date}' AND '{end_date}'
            AND gc.id = 2
  
    """
    
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
    
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"

    query += " GROUP BY vv.id"
    query += f" LIMIT {items_per_page} OFFSET {offset};"

    return query

def getVideosListForExport(start_date, end_date, state, district, block, village):
    query = f"""
        SELECT DISTINCT
            vv.id AS 'Video ID',
            vv.title AS 'Video Title',
            DATE_FORMAT(vv.time_created, '%Y-%m-%d %H:%i:%s') AS 'Video Created',
            vv.youtubeid AS 'Youtube ID',
            gs.state_name AS 'Region Name',
            gd.district_name AS 'Woreda Name',
            gb.block_name AS 'Kebele Name',
            gv.village_name AS 'Village Name',
            vl.language_name AS 'Language'
        FROM
            digitalgreen.videos_video vv
            JOIN digitalgreen.videos_language vl ON vv.language_id = vl.id
            JOIN digitalgreen.geographies_village gv ON gv.id = vv.village_id
            JOIN digitalgreen.geographies_block gb ON gb.id = gv.block_id
            JOIN digitalgreen.geographies_district gd ON gd.id = gb.district_id
            JOIN digitalgreen.geographies_state gs ON gs.id = gd.state_id
            JOIN digitalgreen.geographies_country gc ON gc.id = gs.country_id
        WHERE
            vv.time_created BETWEEN '{start_date}' AND '{end_date}'
            AND gc.id = 2
  
    """
    
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
    
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"

    query += " GROUP BY vv.id"

    return query

def getVideosPageStat():
    query = f"""
    SELECT
    gs.state_name 'State Name',
    COUNT(DISTINCT gd.id) AS 'Total District',
    COUNT(DISTINCT gb.id) AS 'Total Kebele',
    COUNT(DISTINCT gv.id) AS 'Total Village Person Groups',
    COUNT(DISTINCT ppg.id) AS 'Total Person Groups',
    COUNT(DISTINCT pp.id) AS 'Total Farmers',
    COUNT(DISTINCT scr.id) AS 'Number of Screenings',
    COUNT(DISTINCT vv.id) AS 'Number of Videos Screened',
    COUNT(pp.id) AS 'Total Viewers',
    COUNT(DISTINCT pp.id) AS 'Number of Unique viewers',
    COUNT(DISTINCT CASE WHEN pp.gender = 'M' THEN pma.person_id END) AS Male,
    COUNT(DISTINCT CASE WHEN pp.gender = 'F' THEN pma.person_id END) AS Female
    FROM
    digitalgreen.activities_screening scr
    JOIN digitalgreen.activities_screening_videoes_screened svs ON svs.screening_id = scr.id
    JOIN digitalgreen.videos_video vv ON vv.id = svs.video_id
    JOIN digitalgreen.activities_personmeetingattendance pma ON pma.screening_id = scr.id
    JOIN digitalgreen.people_person pp ON pp.id = pma.person_id
    JOIN digitalgreen.people_persongroup ppg ON ppg.id = pp.group_id
    JOIN digitalgreen.geographies_village gv ON gv.id = ppg.village_id
    JOIN digitalgreen.geographies_block gb ON gb.id = gv.block_id
    JOIN digitalgreen.geographies_district gd ON gd.id = gb.district_id
    JOIN digitalgreen.geographies_state gs ON gs.id = gd.state_id
    JOIN digitalgreen.geographies_country gc ON gc.id = gs.country_id
    WHERE
    gd.id IN (507, 514)
    AND pp.partner_id IN (85)
    AND scr.date BETWEEN '2019-09-01' AND '2024-01-25'
    GROUP BY
    gs.state_name

    UNION ALL

    SELECT
        gs.state_name 'State Name',
        COUNT(DISTINCT gd.id) AS 'Total District',
        COUNT(DISTINCT gb.id) AS 'Total Kebele',
        COUNT(DISTINCT gv.id) AS 'Total Village Person Groups',
        COUNT(DISTINCT ppg.id) AS 'Total Person Groups',
        COUNT(DISTINCT pp.id) AS 'Total Farmers',
        COUNT(DISTINCT scr.id) AS 'Number of Screenings',
        COUNT(DISTINCT vv.id) AS '# of Videos Screened',
        COUNT(pp.id) AS 'Total Viewers',
        COUNT(DISTINCT pp.id) AS 'Number of Unique viewers',
        COUNT(DISTINCT CASE WHEN pp.gender = 'M' THEN pma.person_id END) AS Male,
        COUNT(DISTINCT CASE WHEN pp.gender = 'F' THEN pma.person_id END) AS Female
    FROM
        digitalgreen.activities_screening scr
    JOIN digitalgreen.activities_screening_videoes_screened svs ON
        svs.screening_id = scr.id
    JOIN digitalgreen.videos_video vv ON
        vv.id = svs.video_id
    JOIN digitalgreen.activities_personmeetingattendance pma ON
        pma.screening_id = scr.id
    JOIN digitalgreen.people_person pp ON
        pp.id = pma.person_id
    JOIN digitalgreen.people_persongroup ppg ON
        ppg.id = pp.group_id
    JOIN digitalgreen.geographies_village gv ON
        gv.id = ppg.village_id
    JOIN digitalgreen.geographies_block gb ON
        gb.id = gv.block_id
    JOIN digitalgreen.geographies_district gd ON
        gd.id = gb.district_id
    JOIN digitalgreen.geographies_state gs ON
        gs.id = gd.state_id
    JOIN digitalgreen.geographies_country gc ON
        gc.id = gs.country_id
    WHERE
        gd.id IN (527, 529, 535, 426, 425, 531, 525, 491, 509, 526, 445, 434, 447, 436, 528, 541, 506, 524, 467, 456, 533, 534, 512, 532, 508, 521, 550, 551, 560, 444, 418, 424, 446, 473, 437, 422, 438, 420, 450, 417, 475, 431, 470, 455, 454, 471, 421, 472, 517, 459, 423, 558, 552, 557, 555, 554, 559, 565, 495, 540, 474, 476, 503, 502, 485, 504, 497, 443, 449, 448, 442, 439, 429, 530, 548, 562, 561, 490, 481, 510, 563, 564, 460, 461, 482, 484, 477, 478, 483, 479, 465, 462, 452, 453, 469, 451, 498, 542, 543, 544, 545, 546)
        AND scr.date BETWEEN '2019-09-01' AND '2024-01-25'
    GROUP BY
        gs.state_name;
    """

    return query

def getNumberOfTotalVideosProducedQuery(start_date, end_date, state, district, block, village):
    query = f"""
        SELECT
            COUNT(DISTINCT vv.id) AS 'Distinct Video Count'
        FROM
            digitalgreen.videos_video vv
        JOIN digitalgreen.geographies_village gv ON
            gv.id = vv.village_id
        JOIN digitalgreen.geographies_block gb ON
            gb.id = gv.block_id
        JOIN digitalgreen.geographies_district gd ON
            gd.id = gb.district_id
        JOIN digitalgreen.geographies_state gs ON
            gs.id = gd.state_id
        JOIN digitalgreen.geographies_country gc ON
            gc.id = gs.country_id
        WHERE
            vv.time_created BETWEEN '{start_date}' AND '{end_date}'
  
        """
        
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
    
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"
    return query

def getNumberOfLanguagesUsedInVideoProductionQuery(start_date, end_date, state, district, block, village):
    query = f"""
        SELECT COUNT(DISTINCT vl.language_name) AS 'Language Count'
        FROM
            digitalgreen.videos_video vv
        JOIN digitalgreen.videos_language vl ON
            vv.language_id = vl.id
        JOIN digitalgreen.geographies_village gv ON
            gv.id = vv.village_id
        JOIN digitalgreen.geographies_block gb ON
            gb.id = gv.block_id
        JOIN digitalgreen.geographies_district gd ON
            gd.id = gb.district_id
        JOIN digitalgreen.geographies_state gs ON
            gs.id = gd.state_id
        JOIN digitalgreen.geographies_country gc ON
            gc.id = gs.country_id
        WHERE
            vv.time_created BETWEEN '{start_date}' AND '{end_date}'
  
    """
    
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"

    return query