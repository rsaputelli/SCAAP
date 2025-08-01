[README (1).md](https://github.com/user-attachments/files/21549509/README.1.md)

# SCAAP Stripe Reconciliation App

This Streamlit app performs reconciliation of Stripe transactions with TD Bank deposits for SCAAP.

## Features

- Upload Stripe exports, payout data, and registration lists
- Classifies transactions into appropriate revenue accounts
- Calculates Stripe fees from Balance History file
- Injects refund transactions into the journal entry
- Produces a full Excel output with:
  - ✅ Journal Entries
  - ✅ Unmatched Stripe Transactions
  - ✅ Deferred Entries
  - ✅ Reconciliation Summary
  - ✅ Refunds Schedule (if Balance History is uploaded)

## How to Use

1. Upload the following files via the app interface:
   - **Attendee Registration Excel**
   - **Exhibitor Registration Excel**
   - **Unified Payments CSV**
   - **Payouts CSV**
   - *(Optional)* Balance History CSV
   - *(Optional)* Ledger CSV

2. Click **"Run Reconciliation"**

3. Review the output journal entry

4. Click **"Download Reconciliation Report"** to download a multi-tab Excel file

## Deployment Instructions (for Streamlit Cloud)

1. Push the following files to a GitHub repository:
   - `SCAAP_Stripe_Recon_StreamlitCloud_FULL_OUTPUT.py`
   - `requirements.txt`
   - `README.md`

2. Go to [https://streamlit.io/cloud](https://streamlit.io/cloud)

3. Click **New app** and connect your GitHub repo

4. Select `SCAAP_Stripe_Recon_StreamlitCloud_FULL_OUTPUT.py` as the entry point

5. Click **Deploy**

You're done! 🎉
