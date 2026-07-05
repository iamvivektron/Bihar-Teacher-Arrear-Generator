import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

st.set_page_config(page_title="Arrear Bill Generator", page_icon="💸", layout="wide")

st.title("💸 Arrear Bill Generator")
st.write("Upload your previous salary details, apply the revised rates, and generate your arrear bill PDF.")

# --- STEP 1: DEFINE NEW RATES ---
st.header("1. Set Revised Rates (The 'Due' Criteria)")
col1, col2, col3 = st.columns(3)

with col1:
    new_da_pct = st.number_input("Revised DA %", value=50.0, step=1.0)
with col2:
    new_hra_pct = st.number_input("Revised HRA %", value=27.0, step=1.0)
with col3:
    new_nps_pct = st.number_input("Revised NPS Deduction %", value=10.0, step=1.0)

# --- STEP 2: UPLOAD RECEIPTS ---
st.header("2. Upload Salary Data")
st.info("Your Excel file should have the following columns: Month, Basic_Drawn, DA_Drawn, HRA_Drawn, NPS_Drawn")

uploaded_file = st.file_uploader("Upload Yearly Salary Receipt (.xlsx)", type=["xlsx"])

if uploaded_file:
    # Read the uploaded Excel file
    try:
        df = pd.read_excel(uploaded_file)
        st.success("File uploaded successfully!")
        
        # --- STEP 3: PERFORM CALCULATIONS ---
        st.header("3. Calculation Preview")
        
        # Calculate Due Amounts
        # Assuming Basic remains the same, but allowances change. 
        df['DA_Due'] = df['Basic_Drawn'] * (new_da_pct / 100)
        df['HRA_Due'] = df['Basic_Drawn'] * (new_hra_pct / 100)
        
        # NPS is usually calculated on (Basic + DA)
        df['NPS_Due'] = (df['Basic_Drawn'] + df['DA_Due']) * (new_nps_pct / 100)
        
        # Calculate Arrears (Due - Drawn)
        df['DA_Arrear'] = df['DA_Due'] - df['DA_Drawn']
        df['HRA_Arrear'] = df['HRA_Due'] - df['HRA_Drawn']
        
        # NPS deduction arrear (If deduction increases, payable amount decreases)
        df['NPS_Arrear_Deduction'] = df['NPS_Due'] - df['NPS_Drawn']
        
        # Net Arrear Payable per month
        df['Net_Arrear_Payable'] = df['DA_Arrear'] + df['HRA_Arrear'] - df['NPS_Arrear_Deduction']
        
        # Show the calculated dataframe to the user
        st.dataframe(df.style.format("{:.2f}", subset=['DA_Due', 'DA_Arrear', 'Net_Arrear_Payable']))
        
        # Calculate Totals
        total_payable = df['Net_Arrear_Payable'].sum()
        st.metric(label="Total Net Arrear Payable", value=f"₹ {total_payable:,.2f}")
        
        # --- STEP 4: GENERATE PDF ---
        st.header("4. Download Official Bill")
        
        if st.button("Generate PDF Bill"):
            pdf_buffer = io.BytesIO()
            # Landscape orientation to fit the table
            doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, alignment=1, spaceAfter=20)
            story.append(Paragraph("Official Arrear Bill Statement", title_style))
            story.append(Paragraph(f"Revised Rates Applied: DA @ {new_da_pct}%, HRA @ {new_hra_pct}%, NPS @ {new_nps_pct}%", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Prepare data for PDF Table
            # Converting DataFrame to a list of lists for ReportLab
            table_data = [df.columns.to_list()] # Header row
            for index, row in df.iterrows():
                # Round and convert to string for clean PDF display
                formatted_row = [str(round(val, 2)) if isinstance(val, (int, float)) else str(val) for val in row]
                table_data.append(formatted_row)
                
            # Add Total Row
            total_row = ["TOTAL"] + [""] * (len(df.columns) - 2) + [f"₹ {total_payable:,.2f}"]
            table_data.append(total_row)
            
            # Create PDF Table
            pdf_table = Table(table_data)
            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F46E5")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-2), colors.HexColor("#F3F4F6")),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E5E7EB")),
            ]))
            
            story.append(pdf_table)
            doc.build(story)
            
            st.download_button(
                label="📥 Download Arrear Bill (PDF)",
                data=pdf_buffer.getvalue(),
                file_name="Arrear_Bill.pdf",
                mime="application/pdf"
            )
            
    except Exception as e:
        st.error(f"Error processing the file: {e}")
        st.write("Please ensure your Excel file has the exact columns mentioned above.")
