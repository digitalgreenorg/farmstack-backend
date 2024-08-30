from queries.data import daas_woreda_ids

daas_woreda_ids_str = ', '.join(map(str, daas_woreda_ids))

def getMasterQuery(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT 
            gc.id as country_id, gs.id as state_id, 
            gd.id as district_id, gb.id as geographies_block, gv.id as village_id, 
            ph.id as people_household_id, ph.head_gender as head_gender
        FROM 
            geographies_country gc
            LEFT JOIN geographies_state gs ON gc.id = gs.country_id
            LEFT JOIN geographies_district gd ON gs.id = gd.state_id
            LEFT JOIN geographies_block gb ON gd.id = gb.district_id
            LEFT JOIN geographies_village gv ON gb.id = gv.block_id
            LEFT JOIN programs_project pp ON 1=1
            LEFT JOIN people_household ph ON ph.village_id = gv.id
            LEFT JOIN people_person p ON p.household_id = ph.id
        WHERE 
            ph.time_created BETWEEN '{start_date}' AND '{end_date}' 
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

def get_unique_farmers_attended_screenings_query(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT 
        COUNT(DISTINCT pma.person_id) as farmer_attended_screening,
        COUNT(DISTINCT pma.id) as total_screening
    FROM activities_personmeetingattendance as pma
    LEFT JOIN people_person as p ON pma.person_id = p.id
    LEFT JOIN geographies_village gv ON p.village_id = gv.id
    LEFT JOIN geographies_block gb ON gv.block_id = gb.id
    LEFT JOIN geographies_district gd ON gb.district_id = gd.id
    LEFT JOIN geographies_state gs ON gd.state_id = gs.id
    LEFT JOIN geographies_country gc ON gs.country_id = gc.id
    WHERE 
        pma.time_created BETWEEN '{start_date}' AND '{end_date}'  
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
    
def get_unique_farmers_adopting_practice_query(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT 
    COUNT(DISTINCT pap.person_id) as unique_farmers_adopting_practice ,
    COUNT(DISTINCT pap.id) as adoption_by_farmer
    FROM activities_personadoptpractice as pap
    LEFT JOIN people_person as p ON pap.person_id = p.id
    LEFT JOIN geographies_village gv ON p.village_id = gv.id
    LEFT JOIN geographies_block gb ON gv.block_id = gb.id
    LEFT JOIN geographies_district gd ON gb.district_id = gd.id
    LEFT JOIN geographies_state gs ON gd.state_id = gs.id
    LEFT JOIN geographies_country gc ON gs.country_id = gc.id
    WHERE 
        pap.time_created BETWEEN '{start_date}' AND '{end_date}' 
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
    
def get_unique_screenings_query(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT COUNT(DISTINCT scr.id) 
    FROM activities_screening as scr
    LEFT JOIN geographies_village gv ON scr.village_id = gv.id
    LEFT JOIN geographies_block gb ON gv.block_id = gb.id
    LEFT JOIN geographies_district gd ON gb.district_id = gd.id
    LEFT JOIN geographies_state gs ON gd.state_id = gs.id
    LEFT JOIN geographies_country gc ON gs.country_id = gc.id
    WHERE scr.time_created BETWEEN '{start_date}' AND '{end_date}' 
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

def get_videos_shown_in_screenings_query(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT COUNT(DISTINCT svs.video_id) 
    FROM activities_screening_videoes_screened svs
    JOIN activities_screening s ON svs.screening_id = s.id
    LEFT JOIN geographies_village gv ON s.village_id = gv.id
    LEFT JOIN geographies_block gb ON gv.block_id = gb.id
    LEFT JOIN geographies_district gd ON gb.district_id = gd.id
    LEFT JOIN geographies_state gs ON gd.state_id = gs.id
    LEFT JOIN geographies_country gc ON gs.country_id = gc.id
    WHERE s.time_created BETWEEN '{start_date}' AND '{end_date}' 
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

def get_videos_produced_query(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT COUNT(DISTINCT vv.id) 
    FROM videos_video as vv
    JOIN geographies_village gv ON vv.village_id = gv.id
    JOIN geographies_block gb ON gv.block_id = gb.id
    JOIN geographies_district gd ON gb.district_id = gd.id
    JOIN geographies_state gs ON gd.state_id = gs.id
    JOIN geographies_country gc ON gs.country_id = gc.id
    WHERE vv.time_created BETWEEN '{start_date}' AND '{end_date}' 
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

def getFarmerGroupReached(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT COUNT(DISTINCT pg.id) 
    FROM activities_screening_farmer_groups_targeted sfgt
    JOIN people_persongroup pg ON sfgt.persongroup_id = pg.id
    LEFT JOIN geographies_village gv ON pg.village_id = gv.id
    LEFT JOIN geographies_block gb ON gv.block_id = gb.id
    LEFT JOIN geographies_district gd ON gb.district_id = gd.id
    LEFT JOIN geographies_state gs ON gd.state_id = gs.id
    LEFT JOIN geographies_country gc ON gs.country_id = gc.id
    WHERE pg.time_created BETWEEN '{start_date}' AND '{end_date}' 
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
    

# Fetch adoption data
def getAdoptionQuery(start_date, end_date, country, state, district, block, village):
    query = f"""
    SELECT 
        COUNT(DISTINCT pap.id) AS adoption_count,
        MONTH(pap.date_of_adoption) AS month
    FROM 
        activities_personadoptpractice as pap
        LEFT JOIN people_person as p ON pap.person_id = p.id
        LEFT JOIN geographies_village gv ON p.village_id = gv.id
        LEFT JOIN geographies_block gb ON gv.block_id = gb.id
        LEFT JOIN geographies_district gd ON gb.district_id = gd.id
        LEFT JOIN geographies_state gs ON gd.state_id = gs.id
        LEFT JOIN geographies_country gc ON gs.country_id = gc.id    
    WHERE 
        pap.date_of_adoption BETWEEN '{start_date}' AND '{end_date}' 
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
    query += " GROUP BY MONTH(pap.date_of_adoption)"       
    return query

def getScreeningQuery(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT 
            COUNT(DISTINCT pma.id) AS screening_count,
            MONTH(pma.time_created) AS month
        FROM 
            activities_personmeetingattendance as pma
            LEFT JOIN people_person as p ON pma.person_id = p.id
            LEFT JOIN geographies_village gv ON p.village_id = gv.id
            LEFT JOIN geographies_block gb ON gv.block_id = gb.id
            LEFT JOIN geographies_district gd ON gb.district_id = gd.id
            LEFT JOIN geographies_state gs ON gd.state_id = gs.id
            LEFT JOIN geographies_country gc ON gs.country_id = gc.id
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
    query += " GROUP BY MONTH(pma.time_created)"     
    return query

def getAdoptionQueryByYear(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT 
            COUNT(DISTINCT pap.id) AS adoption_count,
            YEAR(pap.date_of_adoption) AS year,
            QUARTER(pap.date_of_adoption) AS quarter
        FROM 
            activities_personadoptpractice as pap
                LEFT JOIN people_person as p ON pap.person_id = p.id
                LEFT JOIN geographies_village gv ON p.village_id = gv.id
                LEFT JOIN geographies_block gb ON gv.block_id = gb.id
                LEFT JOIN geographies_district gd ON gb.district_id = gd.id
                LEFT JOIN geographies_state gs ON gd.state_id = gs.id
                LEFT JOIN geographies_country gc ON gs.country_id = gc.id     
        WHERE 
            pap.date_of_adoption BETWEEN  '{start_date}' AND '{end_date}' 
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
    query += " GROUP BY YEAR(pap.date_of_adoption), QUARTER(pap.date_of_adoption)"    
    return query    
        
def getScreeningQueryByYear(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT 
            COUNT(DISTINCT pma.id) AS screening_count,
            YEAR(pma.time_created) AS year,
            QUARTER(pma.time_created) AS quarter
        FROM 
            activities_personmeetingattendance as pma
            LEFT JOIN people_person as p ON pma.person_id = p.id
            LEFT JOIN geographies_village gv ON p.village_id = gv.id
            LEFT JOIN geographies_block gb ON gv.block_id = gb.id
            LEFT JOIN geographies_district gd ON gb.district_id = gd.id
            LEFT JOIN geographies_state gs ON gd.state_id = gs.id
            LEFT JOIN geographies_country gc ON gs.country_id = gc.id
        WHERE 
            pma.time_created BETWEEN '{start_date}' AND '{end_date}' 
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
    query += " GROUP BY YEAR(pma.time_created), QUARTER(pma.time_created)" 

    return query    

def getFarmersAttendingVideoScreeningByGender(start_date, end_date, country, state, district, block, village):
    query = f"""
        SELECT p.gender, COUNT(pma.id) AS attendance_count
        FROM activities_personmeetingattendance pma
        JOIN people_person p ON pma.person_id = p.id
        LEFT JOIN geographies_village gv ON p.village_id = gv.id
        LEFT JOIN geographies_block gb ON gv.block_id = gb.id
        LEFT JOIN geographies_district gd ON gb.district_id = gd.id
        LEFT JOIN geographies_state gs ON gd.state_id = gs.id
        LEFT JOIN geographies_country gc ON gs.country_id = gc.id
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
    query += " GROUP BY p.gender"    
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
    query += " GROUP BY p.gender"    
    return query


# NEW QUERIES
def getUniqueFarmersAttendedScreeningForGraph():
    query = """
            SELECT
                YEAR(time_created) AS year,
                MONTH(time_created) AS month,
                COUNT(DISTINCT person_id) AS farmersCount
            FROM
                activities_personmeetingattendance
            WHERE
                YEAR(time_created) = '2019'
            GROUP BY
                YEAR(time_created), MONTH(time_created)
            ORDER BY
                MONTH(time_created) ASC;
        """
    
    return query

def getUniqueFarmersWhoAdoptedPracticeForGraph():
    query = """
            SELECT
                YEAR(date_of_adoption) AS year,
                MONTH(date_of_adoption) AS month,
                COUNT(DISTINCT person_id) AS farmersCount
            FROM
                activities_personadoptpractice
            WHERE
                YEAR(date_of_adoption) = '2019'
            GROUP BY
                YEAR(date_of_adoption), MONTH(date_of_adoption)
            ORDER BY
                MONTH(date_of_adoption) ASC;
        """
    
    return query

def getUniqueFarmersUsingMonthAndYearForScreeningAndAdoptionGraph(start_date, end_date, country, state, district, block, village):
    query = """
        SELECT
            COALESCE(a.year, s.year) AS year,
            COALESCE(a.month, s.month) AS month,
            COALESCE(a.adoptionFarmerCount, 0) AS adoptionFarmerCount,
            COALESCE(s.screeningFarmerCount, 0) AS screeningFarmerCount
        FROM
    """

    query += f"""
        (
            SELECT
                YEAR(a.date_of_adoption) AS year,
                MONTH(a.date_of_adoption) AS month,
                COUNT(DISTINCT a.person_id) AS adoptionFarmerCount
            FROM
                activities_personadoptpractice a
            INNER JOIN
                people_person p ON a.person_id = p.id
            LEFT JOIN
                geographies_village gv ON p.village_id = gv.id
            LEFT JOIN
                geographies_block gb ON gv.block_id = gb.id
            LEFT JOIN
                geographies_district gd ON gb.district_id = gd.id
            LEFT JOIN 
                geographies_state gs ON gd.state_id = gs.id
            LEFT JOIN 
                geographies_country gc ON gs.country_id = gc.id
            WHERE
                YEAR(a.date_of_adoption) BETWEEN 2019 AND YEAR(CURDATE()) 
    """
    
    ## ADD FILTERS
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
            
    query += f"""
            GROUP BY
                        YEAR(a.date_of_adoption), MONTH(a.date_of_adoption)
                ) a
    """
    
    query += """
        LEFT JOIN
        (
            SELECT
                YEAR(s.time_created) AS year,
                MONTH(s.time_created) AS month,
                COUNT(DISTINCT s.person_id) AS screeningFarmerCount
            FROM
                activities_personmeetingattendance s
            INNER JOIN
                people_person p ON s.person_id = p.id
            LEFT JOIN
                geographies_village gv ON p.village_id = gv.id
            LEFT JOIN
                geographies_block gb ON gv.block_id = gb.id
            LEFT JOIN
                geographies_district gd ON gb.district_id = gd.id
            LEFT JOIN 
                geographies_state gs ON gd.state_id = gs.id
            LEFT JOIN 
                geographies_country gc ON gs.country_id = gc.id
            WHERE
                YEAR(s.time_created) BETWEEN 2019 AND YEAR(CURDATE()) 
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
            
    query += """
            GROUP BY
                YEAR(s.time_created), MONTH(s.time_created)
        ) s
    """
    
    query += """
        ON a.year = s.year AND a.month = s.month
        ORDER BY
            year ASC, month ASC;
    """
    
    return query

def getUniqueFarmersUsingYearForScreeningAndAdoptionGraph(start_date, end_date, country, state, district, block, village):
    query = """
     SELECT
                    COALESCE(a.year, s.year) AS year,
                    COALESCE(a.adoptionFarmerCount, 0) AS adoptionFarmerCount,
                    COALESCE(s.screeningFarmerCount, 0) AS screeningFarmerCount
                FROM
                    (SELECT
                        YEAR(a.date_of_adoption) AS year,
                        COUNT(DISTINCT a.person_id) AS adoptionFarmerCount
                    FROM
                        activities_personadoptpractice a
                    INNER JOIN
                        people_person p ON a.person_id = p.id
                    LEFT JOIN 
                        geographies_village gv ON p.village_id = gv.id
                    LEFT JOIN 
                        geographies_block gb ON gv.block_id = gb.id
                    LEFT JOIN 
                        geographies_district gd ON gb.district_id = gd.id
                    LEFT JOIN 
                        geographies_state gs ON gd.state_id = gs.id
                    LEFT JOIN 
                        geographies_country gc ON gs.country_id = gc.id
                    WHERE
                        YEAR(a.date_of_adoption) BETWEEN 2019 AND YEAR(CURDATE())
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
    query += """
     GROUP BY
                        YEAR(a.date_of_adoption)
                    ) a
    """
    query += """
    LEFT JOIN
                    (SELECT
                        YEAR(s.time_created) AS year,
                        COUNT(DISTINCT s.person_id) AS screeningFarmerCount
                    FROM
                        activities_personmeetingattendance s
                    INNER JOIN
                        people_person p ON s.person_id = p.id
                    LEFT JOIN 
                        geographies_village gv ON p.village_id = gv.id
                    LEFT JOIN 
                        geographies_block gb ON gv.block_id = gb.id
                    LEFT JOIN 
                        geographies_district gd ON gb.district_id = gd.id
                    LEFT JOIN 
                        geographies_state gs ON gd.state_id = gs.id
                    LEFT JOIN 
                        geographies_country gc ON gs.country_id = gc.id
                    WHERE
                        YEAR(s.time_created) BETWEEN 2019 AND YEAR(CURDATE()) 
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
    query += """
     GROUP BY
                        YEAR(s.time_created)
                    ) s
                ON a.year = s.year
                ORDER BY
                    year ASC;
    """
 
    
    return query