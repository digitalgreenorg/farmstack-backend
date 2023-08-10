from typing import Any


class DatahubService:
    @classmethod
    def create_dashboard_response(cls, df: Any):
        obj = {
            "total_no_of_records" : len(df),
            "male_count": (df['Gender'] == 1).sum(),
            "female_count": (df['Gender'] == 0).sum(),
            "constituencies" :(df['Constituency']).nunique(),
            "counties" :(df['County']).nunique(),
            "sub_counties" :(df['Sub County']).nunique(),
            "farming_practices" : {
                "crop_production": (df['Crop Production']).sum(),
                "livestock_production": (df['Livestock Production']).sum(),
            },
            "livestock_and_poultry_production" : {
                "cows" : (df[['Other Dual Cattle', 'Cross breed Cattle', 'Cattle boma']]).sum(axis=1).sum(),
                "goats" : df[['Small East African Goats', 'Somali Goat', 'Other Goat']].sum(axis=1).sum(),
                "chickens" : df[['Chicken -Indigenous', 'Chicken -Broilers', 'Chicken -Layers']].sum(axis=1).sum(),
                "ducks" : df[['Ducks']].sum(axis=1).sum(),
            },
            "financial_livelihood" : {
                "lenders" : (df['Moneylender']).sum(),
                "relatives" : (df['Family']).sum(),
                "traders" : 0,
                "agents" :0,
                "institutional":0
            },
            "water_sources" :{
                "borewell" : 0,
                "irrigation" : (df['Total Area Irrigation']).sum(),
                "rainwater" : (df['Rain']).sum(),

            },
            "insurance_information" :{
                "insured_crops" : (df['Do you insure your crops?']).sum(),
                "insured_machinery" : (df['Do you insure your farm buildings and other assets?']).sum(),
            }
        }
        return obj
