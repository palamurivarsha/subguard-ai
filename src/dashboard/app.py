import os
from datetime import date, datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title='SubGuard AI', page_icon='🛡️', layout='wide')
API_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')


def display_date(value):
    if not value:
        return '—'
    try:
        return pd.to_datetime(value, utc=True).strftime('%b %d, %Y')
    except (ValueError, TypeError, OverflowError):
        return str(value)


def format_money(value, currency='USD'):
    try:
        number = float(value)
        return f'${number:,.2f}' if currency == 'USD' else f'{number:,.2f} {currency}'
    except (TypeError, ValueError):
        return '—'


def as_date(value):
    if not value:
        return None
    try:
        return pd.to_datetime(value, utc=True).date()
    except (ValueError, TypeError, OverflowError):
        return None


def deadline_status(value):
    target = as_date(value)
    if target is None:
        return 'Unknown'
    remaining = (target - datetime.now(timezone.utc).date()).days
    if remaining < 0:
        return f'Overdue by {-remaining} day(s)'
    if remaining == 0:
        return 'Due today'
    return f'In {remaining} day(s)'


def safe_cancellation_link(value):
    if not value:
        return None
    parsed = urlparse(str(value))
    if parsed.scheme != 'https' or not parsed.hostname:
        return None
    if parsed.hostname.lower() in {'example.com', 'www.example.com'}:
        return None
    return str(value)


@st.cache_data(ttl=30)
def fetch_data(endpoint):
    try:
        response = requests.get(f'{API_URL}{endpoint}', timeout=10)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            st.error(f'Unexpected response from {endpoint}: expected a list.')
            return []
        return payload
    except (requests.RequestException, ValueError) as exc:
        st.error(f'Could not load {endpoint}: {exc}')
        return []


def cancel_trial(trial_id):
    response = requests.patch(f'{API_URL}/db/free-trials/{trial_id}/cancel', timeout=15)
    response.raise_for_status()
    return response.json()


def show_table(records, columns=None, empty='No records available.'):
    if not records:
        st.info(empty)
        return
    frame = pd.DataFrame(records)
    if columns:
        available = [col for col in columns if col in frame.columns]
        if available:
            frame = frame[available]
    st.dataframe(frame, use_container_width=True, hide_index=True)


st.title('🛡️ SubGuard AI')
st.caption('Intelligent subscription monitoring · Synthetic-data demonstration')
st.info('Demo only: predicted charges and trial deadlines are estimates. Marking a trial canceled here does not cancel it with the subscription provider.')

subscriptions = fetch_data('/db/subscriptions')
risks = fetch_data('/db/risk-scores')
predictions = fetch_data('/predictions')
anomalies = fetch_data('/anomalies')
explanations = fetch_data('/explanations')
trials = fetch_data('/db/free-trials')
reminders = fetch_data('/db/trial-reminders')

active_subscriptions = [s for s in subscriptions if str(s.get('status', 'active')).lower() == 'active']
monthly_total = sum(float(s.get('next_predicted_amount') or s.get('average_amount') or 0) for s in active_subscriptions if str(s.get('billing_frequency', '')).upper() == 'MONTHLY')
medium_high = sum(1 for r in risks if str(r.get('risk_level', r.get('risk_category', ''))).upper() in {'MEDIUM', 'HIGH', 'CRITICAL'})
active_trials = [t for t in trials if str(t.get('status', '')).lower() == 'active']

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric('Active subscriptions', len(active_subscriptions))
m2.metric('Expected monthly spend', format_money(monthly_total))
m3.metric('Medium/high risk', medium_high)
m4.metric('Historical anomalies', len(anomalies))
m5.metric('Active trial records', len(active_trials))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    'Subscriptions', 'Upcoming Renewals', 'Anomalies & Risk',
    'AI Explanations', 'Free Trials & Alerts'
])

with tab1:
    st.subheader('Detected subscriptions')
    show_table(subscriptions, [
        'merchant_name', 'billing_frequency', 'average_amount',
        'next_predicted_amount', 'next_predicted_charge_date',
        'detection_confidence', 'status'
    ], 'No subscriptions were returned by the API.')
    if subscriptions:
        merchants = sorted({str(s.get('merchant_name', '')) for s in subscriptions if s.get('merchant_name')})
        selected = st.selectbox('View merchant details', merchants)
        record = next((s for s in subscriptions if s.get('merchant_name') == selected), None)
        if record:
            st.json(record)

with tab2:
    st.subheader('Upcoming and overdue renewals')
    st.caption('Predictions are based on historical synthetic transactions; they are not verified billing schedules.')
    renewal_rows = []
    for item in active_subscriptions:
        next_date = item.get('next_predicted_charge_date')
        renewal_rows.append({
            'Merchant': item.get('merchant_name'),
            'Frequency': item.get('billing_frequency'),
            'Predicted charge date': display_date(next_date),
            'Expected amount': format_money(item.get('next_predicted_amount')),
            'Status': deadline_status(next_date),
            '_sort': as_date(next_date) or date.max,
        })
    renewal_rows.sort(key=lambda row: row['_sort'])
    for row in renewal_rows:
        row.pop('_sort', None)
    show_table(renewal_rows, empty='No renewal predictions found in the subscriptions table.')
    with st.expander('Detailed prediction model output'):
        show_table(predictions, empty='No prediction CSV records found.')

with tab3:
    st.subheader('Renewal risk scores')
    st.caption('Risk scores indicate review priority, not the probability of a charge.')
    show_table(risks, empty='No risk scores returned by MySQL.')
    st.subheader('Historical anomalies')
    show_table(anomalies, empty='No anomaly records found.')

with tab4:
    st.subheader('AI-generated subscription explanations')
    st.caption('LLM explanations may be replaced by validated rule-based fallbacks.')
    if explanations:
        for index, record in enumerate(explanations):
            merchant = record.get('merchant_name', record.get('merchant', f'Explanation {index + 1}'))
            with st.expander(str(merchant), expanded=index == 0):
                for key, value in record.items():
                    if isinstance(value, (str, int, float)) and key.lower() in {'explanation', 'validated_explanation', 'llm_explanation', 'reason', 'summary', 'message'}:
                        st.write(value)
                st.json(record)
    else:
        st.info('No explanation records returned by the API.')

with tab5:
    st.subheader('Free-trial tracking')
    st.caption('Cancellation deadlines and URLs in demo data are not provider-verified.')
    trial_rows = []
    for trial in trials:
        deadline = trial.get('cancellation_deadline_at_utc')
        trial_rows.append({
            'Trial ID': trial.get('trial_id'),
            'Service': trial.get('service_name'),
            'Status': trial.get('status'),
            'Expected renewal': format_money(trial.get('renewal_amount'), trial.get('currency', 'USD')),
            'Deadline (UTC)': str(deadline) if deadline else '—',
            'Deadline status': deadline_status(deadline),
            'Billing period': trial.get('billing_period'),
        })
    show_table(trial_rows, empty='No trial records returned by MySQL.')

    st.subheader('Confirm Trial Cancellation')
    if 'cancellation_success' in st.session_state:
        st.success(st.session_state.pop('cancellation_success'))
    if not active_trials:
        st.info('No active trial records need cancellation confirmation.')
    for trial in active_trials:
        trial_id = trial.get('trial_id')
        service = trial.get('service_name', 'Unknown service')
        with st.expander(f'Manage cancellation — {service} (Trial #{trial_id})'):
            st.write(f"Cancellation deadline (UTC): {trial.get('cancellation_deadline_at_utc', 'Unknown')}")
            link = safe_cancellation_link(trial.get('cancellation_url'))
            if link:
                st.markdown(f'[Open supplied cancellation page]({link})')
                st.caption('Verify the destination with the provider before entering account details.')
            else:
                st.warning('No verified provider cancellation link is available. Cancel directly with the provider.')
            confirmed = st.checkbox(
                'I confirm that I canceled this trial with the subscription provider',
                key=f'confirm_trial_{trial_id}'
            )
            if st.button('Mark as Canceled', key=f'cancel_trial_{trial_id}', disabled=not confirmed):
                try:
                    result = cancel_trial(trial_id)
                    st.session_state['cancellation_success'] = (
                        f"{result.get('service_name', service)} marked canceled in SubGuard AI. "
                        'This does not cancel the provider subscription.'
                    )
                    fetch_data.clear()
                    st.rerun()
                except (requests.RequestException, ValueError) as exc:
                    st.error(f'Could not update trial #{trial_id}: {exc}')

    st.subheader('Reminder Delivery History')
    show_table(reminders, empty='No reminder delivery records found.')
    st.caption('A sent status may mean SMTP accepted the message; it does not guarantee inbox delivery.')

st.divider()
st.caption('SubGuard AI · Local portfolio prototype · Not connected to a real bank or subscription provider')
