from queries.data import daas_woreda_ids

daas_woreda_ids_str = ', '.join(map(str, daas_woreda_ids))

# Location queries
def getRegions():
    query = f"""
        SELECT DISTINCT
            gs.state_name
        FROM 
            geographies_block gb
        JOIN 
            geographies_district gd ON gb.district_id = gd.id
        JOIN 
            geographies_state gs ON gd.state_id = gs.id
        JOIN 
            geographies_village gv ON gv.block_id = gb.id
        WHERE gd.id IN ({daas_woreda_ids_str})
    """
    return  query

# Location queries
def getWoredas(selected_region):
    query =  f"""
        SELECT 
            district_name 
        FROM 
            geographies_district 
        WHERE 
            state_id = (
                SELECT 
                    id 
                FROM 
                    geographies_state 
                WHERE 
                    state_name = "{selected_region}"
            )
            AND 
            id IN ({daas_woreda_ids_str})
        """

    return query

# Location queries
def getKebeles(selected_woreda):
    query = f"""
        SELECT 
            block_name 
        FROM 
            geographies_block 
        WHERE 
            district_id = (
                SELECT 
                    id 
                FROM 
                    geographies_district 
                WHERE 
                    district_name = "{selected_woreda}" AND id IN ({daas_woreda_ids_str})
            )
    """
    
    return query

# Location queries
def getVillages(selected_kebele):
    query = f"""
        SELECT
            village_name
        FROM
            geographies_village
        WHERE
            block_id IN (
            SELECT
                gb.id
            FROM
                geographies_block gb
            JOIN geographies_district gd ON
                gb.district_id = gd.id
            WHERE
                gb.block_name = "{selected_kebele}" AND gd.id IN ({daas_woreda_ids_str})
        )
        """
     
    return query