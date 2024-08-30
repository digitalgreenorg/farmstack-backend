def get_unique_farmers_attended_screenings_query(start_date, end_date, country, state, district, block, village, project, offset, limit):
    query = f"""
    SELECT
        p.id, p.person_name, p.father_name, p.age, p.gender, p.phone_no, gs.state_name, gd.district_name, gb.block_name, gv.village_name, vd.title
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
    query += f" GROUP BY p.id, p.person_name, p.father_name, p.age, p.gender, p.phone_no, gs.state_name, gd.district_name, gb.block_name, gv.village_name"
    query += f" LIMIT {limit} OFFSET {offset};"
    return query

def getFarmersAdoptRateByGender(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT p.gender, COUNT(pap.id) AS attendance_count
        FROM activities_personadoptpractice pap
        JOIN people_person p ON pap.person_id = p.id
        LEFT JOIN geographies_village gv ON p.village_id = gv.id
        LEFT JOIN geographies_block gb ON gv.block_id = gb.id
        LEFT JOIN geographies_district gd ON gb.district_id = gd.id
        LEFT JOIN geographies_state gs ON gd.state_id = gs.id
        LEFT JOIN geographies_country gc ON gs.country_id = gc.id
        WHERE pap.time_created BETWEEN '{start_date}' AND '{end_date}' 
    """
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
    query += " GROUP BY p.gender"    
    return query
