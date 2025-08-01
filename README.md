[README (1).md](https://g
# SCAAP Stripe Reconciliation App

This Streamlit app performs reconciliation of Stripe transactions with TD Bank deposits for SCAAP.

## Features

- Upload Stripe exports, payout data, and registration lists
- Classifies transactions into appropriate revenue accounts
- Calculates Stripe fees from Balance History file
- Injects refund transactions into the journal entry
- Skips transfers already processed (via uploaded ledger)
- Produces a full Excel output with:
  - ✅ Journal Entries
  - ✅ Unmatched Stripe Transactions
  - ✅ Deferred Entries
  - ✅ Reconciliation Summary
  - ✅ Refunds Schedule (if Balance History is uploaded)
- Exports a **new ledger** of processed transfers to prevent duplication in future runs

## How to Use

1. Upload the following files via the app interface:
   - **Attendee Registration Excel**
   - **Exhibitor Registration Excel**
   - **Unified Payments CSV**
   - **Payouts CSV**
   - **Balance History CSV**
   - **Processed Transfers Ledger CSV** (required to skip prior entries)

2. Click **"Run Reconciliation"**

3. Review the output journal entry

4. Click:
   - **"Download Reconciliation Report"** to get the full Excel output (multi-tab)
   - **"Download Updated Ledger"** to get an updated processed_transfers_ledger.csv

## Deployment Instructions (for Streamlit Cloud)

1. Push the following files to a GitHub repository:
   - `SCAAP_Stripe_Recon_StreamlitCloud_FULL_OUTPUT_LEDGER.py`
   - `requirements.txt`
   - `README.md`

2. Go to [https://streamlit.io/cloud](https://streamlit.io/cloud)

3. Click **New app** and connect your GitHub repo

4. Select `SCAAP_Stripe_Recon_StreamlitCloud_FULL_OUTPUT_LEDGER.py` as the entry point

5. Click **Deploy**

You're done! 🎉
