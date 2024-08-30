import io
import pandas as pd

def populate_dropdown(data):
    return ["none"] + [item[0] for item in data]

def to_excel(df) -> bytes:
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1", index=False)
    writer.close()
    processed_data = output.getvalue()
    return processed_data

def get_excel_filename(name, state, district, block, village):
    file_name = f"{name}"
    if state != 'none':
        file_name += f" - {state}"
    if district != 'none':
        file_name += f" - {district}"
    if block != 'none':
        file_name += f" - {block}"
    if village != 'none':
        file_name += f" - {village}"
    file_name = file_name + '.xlsx'
    
    return file_name