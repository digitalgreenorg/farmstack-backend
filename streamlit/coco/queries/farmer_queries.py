from queries.data import daas_woreda_ids

daas_woreda_ids_str = ', '.join(map(str, daas_woreda_ids))

def getUniqueFarmersAttendedScreeningsExportQuery(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT
        p.id, p.person_name, p.father_name, p.age, p.gender, p.phone_no, vd.youtubeid, vd.title, gs.state_name, gd.district_name, gb.block_name, gv.village_name
    FROM activities_personmeetingattendance AS pma
    LEFT JOIN people_person AS p ON pma.person_id = p.id
    LEFT JOIN activities_screening AS ac_sc ON pma.screening_id = ac_sc.id
    LEFT JOIN activities_screening_videoes_screened AS ac_sc_vd_sc ON ac_sc_vd_sc.screening_id = ac_sc.id
    LEFT JOIN videos_video AS vd ON ac_sc_vd_sc.video_id = vd.id
    LEFT JOIN geographies_village AS gv ON p.village_id = gv.id
    LEFT JOIN geographies_block AS gb ON gv.block_id = gb.id
    LEFT JOIN geographies_district AS gd ON gb.district_id = gd.id
    LEFT JOIN geographies_state AS gs ON gd.state_id = gs.id
    LEFT JOIN geographies_country AS gc ON gs.country_id = gc.id
    WHERE pma.time_created BETWEEN '{start_date}' AND '{end_date}'
    """
    
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
    
    if country != 'none':
        query += f" AND gc.country_name = '{country}'"
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"
    query += f" GROUP BY p.id"
    return query

def getUniqueFarmersAttendedScreeningsCountQuery(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT COUNT(DISTINCT p.id)
        FROM activities_personmeetingattendance AS pma
        LEFT JOIN people_person AS p ON pma.person_id = p.id
        LEFT JOIN activities_screening AS ac_sc ON pma.screening_id = ac_sc.id
        LEFT JOIN activities_screening_videoes_screened AS ac_sc_vd_sc ON ac_sc_vd_sc.screening_id = ac_sc.id
        LEFT JOIN videos_video AS vd ON ac_sc_vd_sc.video_id = vd.id
        LEFT JOIN geographies_village AS gv ON p.village_id = gv.id
        LEFT JOIN geographies_block AS gb ON gv.block_id = gb.id
        LEFT JOIN geographies_district AS gd ON gb.district_id = gd.id
        LEFT JOIN geographies_state AS gs ON gd.state_id = gs.id
        LEFT JOIN geographies_country AS gc ON gs.country_id = gc.id
        WHERE pma.time_created BETWEEN '{start_date}' AND '{end_date}'
    """
    
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
    
    if country != 'none':
        query += f" AND gc.country_name = '{country}'"
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"
    
    return query

def getTotalFarmersParticipationCountQuery(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT COUNT(DISTINCT pma.id)
        FROM activities_personmeetingattendance AS pma
        LEFT JOIN people_person AS p ON pma.person_id = p.id
        LEFT JOIN activities_screening AS ac_sc ON pma.screening_id = ac_sc.id
        LEFT JOIN activities_screening_videoes_screened AS ac_sc_vd_sc ON ac_sc_vd_sc.screening_id = ac_sc.id
        LEFT JOIN videos_video AS vd ON ac_sc_vd_sc.video_id = vd.id
        LEFT JOIN geographies_village AS gv ON p.village_id = gv.id
        LEFT JOIN geographies_block AS gb ON gv.block_id = gb.id
        LEFT JOIN geographies_district AS gd ON gb.district_id = gd.id
        LEFT JOIN geographies_state AS gs ON gd.state_id = gs.id
        LEFT JOIN geographies_country AS gc ON gs.country_id = gc.id
        WHERE pma.time_created BETWEEN '{start_date}' AND '{end_date}'
    """
    
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
    
    if country != 'none':
        query += f" AND gc.country_name = '{country}'"
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"
    
    return query

def getUniqueFarmersAttendedScreeningsQuery(start_date, end_date, country, state, district, block, village, offset, limit):
    query = f"""
    SELECT
        p.id, p.person_name, p.father_name, p.age, p.gender, p.phone_no, vd.youtubeid, vd.title, gs.state_name, gd.district_name, gb.block_name, gv.village_name
    FROM activities_personmeetingattendance AS pma
    LEFT JOIN people_person AS p ON pma.person_id = p.id
    LEFT JOIN activities_screening AS ac_sc ON pma.screening_id = ac_sc.id
    LEFT JOIN activities_screening_videoes_screened AS ac_sc_vd_sc ON ac_sc_vd_sc.screening_id = ac_sc.id
    LEFT JOIN videos_video AS vd ON ac_sc_vd_sc.video_id = vd.id
    LEFT JOIN geographies_village AS gv ON p.village_id = gv.id
    LEFT JOIN geographies_block AS gb ON gv.block_id = gb.id
    LEFT JOIN geographies_district AS gd ON gb.district_id = gd.id
    LEFT JOIN geographies_state AS gs ON gd.state_id = gs.id
    LEFT JOIN geographies_country AS gc ON gs.country_id = gc.id
    WHERE pma.time_created BETWEEN '{start_date}' AND '{end_date}'
    """
     # use daas woredas, use distnict p.id, add video link dissimination date
    query += f" AND gd.id IN ({daas_woreda_ids_str})"
     
    if country != 'none':
        query += f" AND gc.country_name = '{country}'"
    if state != 'none':
        query += f" AND gs.state_name = '{state}'"
    if district != 'none':
        query += f" AND gd.district_name = '{district}'"
    if block != 'none':
        query += f" AND gb.block_name = '{block}'"
    if village != 'none':
        query += f" AND gv.village_name = '{village}'"
    query += f" GROUP BY p.id "
    query += f" LIMIT {limit} OFFSET {offset};"
    return query
