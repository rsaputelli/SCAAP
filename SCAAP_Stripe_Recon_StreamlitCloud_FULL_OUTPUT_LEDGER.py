
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import xlsxwriter

st.set_page_config(page_title="Stripe-TD Reconciliation", layout="wide")
st.title("Stripe Reconciliation to TD Bank (Streamlit Cloud Version)")

# File upload interface
reg_attendee_file = st.file_uploader("Upload Attendee Registration Excel", type=["xlsx"])
reg_exhibitor_file = st.file_uploader("Upload Exhibitor Registration Excel", type=["xlsx"])
unified_csv_file = st.file_uploader("Upload Unified Payments CSV", type=["csv"])
payouts_csv_file = st.file_uploader("Upload Payouts CSV", type=["csv"])
balance_history_file = st.file_uploader("Upload Balance History CSV (optional)", type=["csv"])
ledger_file = st.file_uploader("Upload Existing Ledger CSV", type=["csv"])

if st.button("Run Reconciliation"):
    try:
        # Load registrants
        reg_attendee = pd.read_excel(reg_attendee_file)
        reg_exhibitor = pd.read_excel(reg_exhibitor_file)
        reg_attendee["Category"] = "Attendee"
        reg_exhibitor["Category"] = "Exhibitor/Sponsor"
        registrants = pd.concat([
            reg_attendee[["Conf #", "Attendee Category", "Category"]],
            reg_exhibitor[["Conf #", "Attendee Category", "Category"]]
        ], ignore_index=True)
        registrants["Conf #"] = registrants["Conf #"].astype(str)

        # Load unified payments
        charges = pd.read_csv(unified_csv_file)
        charges.columns = charges.columns.str.strip().str.lower().str.replace(" ", "_")
        charges["attendeeid"] = charges["attendeeid_(metadata)"].astype(str)
        merged = charges.merge(registrants, left_on="attendeeid", right_on="Conf #", how="left")

        # Classify accounts
        def classify(row):
            if row["Category"] == "Attendee":
                return "4305 - Annual Meeting Reg"
            elif "Sponsor" in str(row["Attendee Category"]):
                return "4307 - Annual Meeting Sponsors"
            elif "Exhibit" in str(row["Attendee Category"]):
                return "4306 - Annual Meeting Exhibits"
            elif row["Category"] == "Exhibitor/Sponsor":
                return "4306 - Annual Meeting Exhibits"
            else:
                return "4305 - Annual Meeting Reg"

        merged["Revenue Account"] = merged.apply(classify, axis=1)
        captured = merged[merged["captured"] == True]
        grouped = captured.groupby("transfer").agg({"amount": "sum", "Revenue Account": lambda x: ', '.join(x.unique())}).reset_index()

        # Load payouts
        payouts = pd.read_csv(payouts_csv_file)
        payouts.columns = payouts.columns.str.strip().str.lower().str.replace(" ", "_")

        # Build fee lookup from balance history
        fee_lookup = {}
        if balance_history_file:
            bh_df = pd.read_csv(balance_history_file)
            fee_lookup = bh_df.groupby("Transfer")["Fee"].sum().to_dict()

        journal = []
        for transfer_id, group in captured.groupby("transfer"):
            payout_row = payouts[payouts["id"] == transfer_id]
            if payout_row.empty:
                continue
            date = payout_row["arrival_date_(utc)"].values[0]
            payout_amount = payout_row["amount"].values[0]
            stripe_fee = fee_lookup.get(transfer_id, 0.0)
            net = payout_amount
            desc = f"Stripe Payout {transfer_id}"
            for _, row in group.iterrows():
                revenue_account = row["Revenue Account"]
                amount = row["amount"]
                journal.append({
                    "Date": date,
                    "Account": revenue_account,
                    "Debit": None,
                    "Credit": round(amount, 2),
                    "Description": desc
                })
            journal.append({
                "Date": date,
                "Account": "5100 - Bank/CC/Merch Fees",
                "Debit": round(stripe_fee, 2),
                "Credit": None,
                "Description": desc
            })
            journal.append({
                "Date": date,
                "Account": "1001 - TD Checking",
                "Debit": round(net, 2),
                "Credit": None,
                "Description": desc
            })

        journal_df = pd.DataFrame(journal)

        # Inject refunds if applicable
        if balance_history_file:
            refund_rows = bh_df[bh_df["Type"].str.lower() == "refund"].copy()
            payout_date_map = payouts.set_index("id")["arrival_date_(utc)"].to_dict()
            for _, r in refund_rows.iterrows():
                transfer_id = r.get("Transfer")
                refund_amount = abs(r.get("Amount", 0))
                date = payout_date_map.get(transfer_id)
                if date and refund_amount > 0:
                    journal_df = pd.concat([journal_df, pd.DataFrame([{
                        "Date": date,
                        "Account": "XXXX - See Refunds Schedule",
                        "Debit": round(refund_amount, 2),
                        "Credit": None,
                        "Description": f"Stripe Payout {r.get('Transfer')}"
                    }])], ignore_index=True)

        
        journal_df.sort_values(by=["Date", "Description", "Credit", "Debit"], inplace=True)

        # Load ledger and filter out previously processed transfers
        if ledger_file:
            ledger_df = pd.read_csv(ledger_file)
            processed_ids = ledger_df["transfer"].astype(str).tolist()
            captured = captured[~captured["transfer"].astype(str).isin(processed_ids)]
        else:
            ledger_df = pd.DataFrame(columns=["transfer"])

        st.dataframe(journal_df)

        
        # Prepare additional sheets
        unmatched = merged[(merged["captured"] == True) & (merged["transfer"].isnull())]

        captured["transfer"] = captured["transfer"].astype(str)
        payouts["id"] = payouts["id"].astype(str)
        captured_merged = captured.merge(payouts[["id", "amount", "arrival_date_(utc)"]],
                                         left_on="transfer", right_on="id", how="left")
        captured_valid = captured_merged[captured_merged["arrival_date_(utc)"].notna()].copy()
        captured_deferred = captured_merged[captured_merged["arrival_date_(utc)"].isna()].copy()

        
        # --- FIXED Reconciliation Summary ---
        captured_valid["transfer"] = captured_valid["transfer"].astype(str)
        merged["transfer"] = merged["transfer"].astype(str)
        recon_merge = captured_valid.merge(
            merged[["transfer", "amount", "Revenue Account"]],
            on="transfer", how="left"
        )
        grouped_recon = recon_merge.groupby("transfer").agg({
            "amount": "sum"
        }).rename(columns={"amount": "Gross Amount"}).reset_index()

        grouped_recon = grouped_recon.merge(
            payouts[["id", "amount"]].rename(columns={"id": "transfer", "amount": "Net Deposit"}),
            on="transfer", how="left"
        )
        grouped_recon["Stripe Fees"] = grouped_recon["transfer"].map(fee_lookup)
        grouped_recon = grouped_recon.rename(columns={"transfer": "Stripe Payout ID"})
        grouped_recon = grouped_recon[["Stripe Payout ID", "Gross Amount", "Net Deposit", "Stripe Fees"]]

            "amount_x": "sum"
        }).rename(columns={"amount_x": "Gross Amount"}).reset_index()

        grouped_recon = grouped_recon.merge(
            payouts[["id", "amount"]].rename(columns={"id": "transfer", "amount": "Net Deposit"}),
            on="transfer", how="left"
        )

        grouped_recon["Stripe Fees"] = grouped_recon["transfer"].map(fee_lookup)
        grouped_recon = grouped_recon.rename(columns={"transfer": "Stripe Payout ID"})
        grouped_recon = grouped_recon[["Stripe Payout ID", "Gross Amount", "Net Deposit", "Stripe Fees"]]

        # Generate downloadable Excel

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            
            journal_df.to_excel(writer, sheet_name="Journal Entries", index=False)
            unmatched.to_excel(writer, sheet_name="Unmatched Stripe Txns", index=False)
            captured_deferred.to_excel(writer, sheet_name="Deferred Entries", index=False)
            grouped_recon.to_excel(writer, sheet_name="Reconciliation Summary", index=False)

            # Refunds Schedule if available
            if balance_history_file:
                refunds_df = bh_df[bh_df["Type"].str.lower() == "refund"].copy()
                refunds_df["Suggested Account"] = "XXXX - See Refunds Schedule"
                refunds_df["Stripe Payout ID"] = refunds_df["Transfer"]
                refunds_df["Description"] = "Refund for Stripe Charge " + refunds_df["Source"]

                refunds_df.rename(columns={
                    "Created (UTC)": "Date",
                    "Amount": "Gross Amount",
                    "Fee": "Fee Amount",
                    "Net": "Net Amount",
                    "attendeeid (metadata)": "Attendee ID",
                    "company (metadata)": "Company"
                }, inplace=True)

                refunds_schedule = refunds_df[[
                    "Date",
                    "Stripe Payout ID",
                    "Description",
                    "Gross Amount",
                    "Fee Amount",
                    "Net Amount",
                    "Attendee ID",
                    "Company",
                    "Suggested Account"
                ]]
                refunds_schedule.to_excel(writer, sheet_name="Refunds Schedule", index=False)

            workbook = writer.book
            sheet = writer.sheets["Journal Entries"]
            yellow_bg = workbook.add_format({'bg_color': '#FFFF99'})

            from xlsxwriter.utility import xl_col_to_name
            account_col_idx = journal_df.columns.get_loc("Account")
            account_col_letter = xl_col_to_name(account_col_idx)
            sheet.conditional_format(
                f"A2:{xl_col_to_name(len(journal_df.columns)-1)}{len(journal_df)+1}",
                {
                    "type": "formula",
                    "criteria": f'=ISNUMBER(SEARCH("XXXX", ${account_col_letter}2))',
                    "format": yellow_bg
                }
            )

            # Apply formatting and totals to currency columns
            currency_fmt = workbook.add_format({"num_format": "$#,##0.00"})
            bold_fmt = workbook.add_format({"bold": True})

            def format_sheet(sheet_name, df, money_cols):
                sheet = writer.sheets[sheet_name]
                for col in money_cols:
                    if col in df.columns:
                        idx = df.columns.get_loc(col)
                        col_letter = xl_col_to_name(idx)
                        sheet.set_column(idx, idx, 18, currency_fmt)
                        sheet.write(f"{col_letter}{len(df)+2}", f"=SUM({col_letter}2:{col_letter}{len(df)+1})", currency_fmt)
                sheet.write(f"A{len(df)+2}", "TOTALS", bold_fmt)

            format_sheet("Journal Entries", journal_df, ["Debit", "Credit"])
            format_sheet("Reconciliation Summary", grouped_recon, ["Gross Amount", "Net Deposit", "Stripe Fees"])

        
        st.download_button("Download Reconciliation Report", data=buffer.getvalue(), file_name="Stripe_Reconciliation_Output.xlsx")

        # Prepare updated ledger
        updated_ledger = pd.concat([ledger_df, captured_valid[["transfer"]]]).drop_duplicates()
        ledger_buffer = BytesIO()
        updated_ledger.to_csv(ledger_buffer, index=False)
        st.download_button("Download Updated Ledger", data=ledger_buffer.getvalue(), file_name="processed_transfers_ledger.csv")


    except Exception as e:
        st.error(f"Error: {e}")

