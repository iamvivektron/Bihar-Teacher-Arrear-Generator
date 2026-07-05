import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Arrear Bill Generator", page_icon="💸", layout="wide")

st.title("💸 Advanced Arrear Bill Generator")
st.write("Set your rates, review your monthly data in the grid, and generate the final arrear PDF.")

# --- UI: Configuration ---
st.header("1. Arrear Configuration")
col1, col2, col3, col4 = st.columns(4)

with col1:
    start_month = st.date_input("Start Month", value=datetime(2024, 3, 1))
with col2:
    months_to_calc = st.number_input("Number of Months", value=12, step=1)
with col3:
    hra_pct = st.number_input("HRA Rate (%)", value=5.0, step=1.0)
with col4:
    nps_pct = st.number_input("NPS Rate (%)", value=10.0, step=1.0)

st.subheader("Dearness Allowance (DA) Rates")
da_col1, da_col2 = st.columns(2)
with da_col1:
    da_h1 = st.number_input("DA % (Jan - Jun)", value=50.0, step=1.0)
with da_col2:
    da_h2 = st.number_input("DA % (Jul - Dec)", value=53.0, step=1.0)

# --- Logic: Generate Initial Data ---
def generate_base_data(start_date, months):
    data = []
    current_date = start_date
    for _ in range(months):
        month_str = current_date.strftime("%b-%y")
        # Determine DA based on month (Jan-Jun vs Jul-Dec)
        current_da_rate = da_h1 if current_date.month <= 6 else da_h2
        
        data.append({
            "Month": month_str,
            "Basic_Due": 28000,          # Default starting basic
            "Basic_Drawn": 28000,        # Default drawn basic
            "DA_Rate_Due": current_da_rate,
            "DA_Drawn": 14000,           # Placeholder
            "HRA_Drawn": 1120,           # Placeholder
            "NPS_Drawn": 4200            # Placeholder
        })
        current_date += relativedelta(months=1)
    return pd.DataFrame(data)

if 'base_df' not in st.session_state or st.sidebar.button("Reset Data Grid"):
    st.session_state.base_df = generate_base_data(start_month, months_to_calc)

# --- UI: Interactive Data Grid ---
st.header("2. Input Data (Editable)")
st.info("💡 Edit the 'Basic_Due' column for the month your increment occurs. Enter your actual drawn values. The app will calculate the rest.")

edited_df = st.data_editor(
    st.session_state.base_df,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)

# --- Logic: Core Arrear Calculations ---
# Calculate Due Amounts
edited_df['DA_Due'] = (edited_df['Basic_Due'] * (edited_df['DA_Rate_Due'] / 100)).round()
edited_df['HRA_Due'] = (edited_df['Basic_Due'] * (hra_pct / 100)).round()

# Calculate Arrears
edited_df['Basic_Arrear'] = edited_df['Basic_Due'] - edited_df['Basic_Drawn']
edited_df['DA_Arrear'] = edited_df['DA_Due'] - edited_df['DA_Drawn']
edited_df['HRA_Arrear'] = edited_df['HRA_Due'] - edited_df['HRA_Drawn']

# NPS is calculated on (Basic Due + DA Due) minus what was already drawn
edited_df['NPS_Due'] = ((edited_df['Basic_Due'] + edited_df['DA_Due']) * (nps_pct / 100)).round()
edited_df['NPS_Arrear'] = edited_df['NPS_Due'] - edited_df['NPS_Drawn']

# Net Payable (Sum of Arrears minus NPS Deduction Arrear)
edited_df['Net_Payable'] = edited_df['Basic_Arrear'] + edited_df['DA_Arrear'] + edited_df['HRA_Arrear'] - edited_df['NPS_Arrear']

# Display Final Calculations
st.header("3. Calculation Result")
display_cols = ['Month', 'Basic_Due', 'DA_Due', 'HRA_Due', 'Basic_Drawn', 'DA_Drawn', 'HRA_Drawn', 'Basic_Arrear', 'DA_Arrear', 'HRA_Arrear', 'NPS_Arrear', 'Net_Payable']
final_df = edited_df[display_cols]
st.dataframe(final_df, use_container_width=True, hide_index=True)

# Totals
total_net = final_df['Net_Payable'].sum()
st.metric("Total Net Arrear Payable", f"₹ {total_net:,.2f}")

# --- UI: PDF Generation ---
st.header("4. Generate Official Bill")
employee_name = st.text_input("Employee Name", "VIVEK KUMAR")
pran_no = st.text_input("PRAN No", "110189089661")
school_name = st.text_input("School Name", "U.M.S. KAJRASAN DIGHWALIA")

if st.button("Generate PDF Bill"):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    styles = getSampleStyleSheet()
    
    # Header Information
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, leading=14)
    story.append(Paragraph(f"<b>NAME:</b> {employee_name} &nbsp;&nbsp;&nbsp;&nbsp; <b>PRAN:</b> {pran_no}", header_style))
    story.append(Paragraph(f"<b>NAME OF THE SCHOOL:</b> {school_name}", header_style))
    story.append(Paragraph("<b>BILL FOR PAYMENT OF ARREARS</b>", ParagraphStyle('Title', parent=styles['Heading2'], alignment=1)))
    story.append(Spacer(1, 10))
    
    # Constructing the complex nested table headers
    table_data = [
        ["MONTH-", "AMOUNT DUE", "", "", "AMOUNT DRAWN", "", "", "ARREARS", "", "", "DEDUCTIONS", "NET PAYABLE"],
        ["YEAR", "BASIC", "DA", "HRA", "BASIC", "DA", "HRA", "BASIC", "DA", "HRA", "NPS", "TOTAL"],
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    ]
    
    # Adding data rows
    for index, row in final_df.iterrows():
        table_data.append([
            str(row['Month']),
            str(int(row['Basic_Due'])), str(int(row['DA_Due'])), str(int(row['HRA_Due'])),
            str(int(row['Basic_Drawn'])), str(int(row['DA_Drawn'])), str(int(row['HRA_Drawn'])),
            str(int(row['Basic_Arrear'])), str(int(row['DA_Arrear'])), str(int(row['HRA_Arrear'])),
            str(int(row['NPS_Arrear'])), str(int(row['Net_Payable']))
        ])
        
    # Adding totals row
    table_data.append([
        "TOTAL",
        str(int(final_df['Basic_Due'].sum())), str(int(final_df['DA_Due'].sum())), str(int(final_df['HRA_Due'].sum())),
        str(int(final_df['Basic_Drawn'].sum())), str(int(final_df['DA_Drawn'].sum())), str(int(final_df['HRA_Drawn'].sum())),
        str(int(final_df['Basic_Arrear'].sum())), str(int(final_df['DA_Arrear'].sum())), str(int(final_df['HRA_Arrear'].sum())),
        str(int(final_df['NPS_Arrear'].sum())), str(int(final_df['Net_Payable'].sum()))
    ])
    
    # PDF Table Styling
    pdf_table = Table(table_data, colWidths=[60, 50, 50, 40, 50, 50, 40, 50, 50, 40, 60, 70])
    pdf_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,2), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        # Span the complex headers
        ('SPAN', (1,0), (3,0)), # AMOUNT DUE
        ('SPAN', (4,0), (6,0)), # AMOUNT DRAWN
        ('SPAN', (7,0), (9,0)), # ARREARS
        ('BACKGROUND', (0,0), (-1,2), colors.lightgrey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), # Total row bold
    ]))
    
    story.append(pdf_table)
    story.append(Spacer(1, 30))
    story.append(Paragraph("SIGNATURE AND SEAL OF THE HEADMASTER", ParagraphStyle('Sign', parent=styles['Normal'], alignment=2)))
    
    doc.build(story)
    
    st.download_button(
        label="📥 Download Official Arrear Bill (PDF)",
        data=pdf_buffer.getvalue(),
        file_name=f"Arrear_Bill_{employee_name.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )
