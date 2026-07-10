# Copyright (c) 2025 victor256sd
# All rights reserved.

import streamlit as st
import streamlit_authenticator as stauth
import openai
from openai import OpenAI
import os
import time
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from cryptography.fernet import Fernet
import re
from st_copy import copy_button
import requests
from typing import List, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

# Disable the button called via on_click attribute.
def disable_button():
    st.session_state.disabled = True        

# Definitive CSS selectors for Streamlit 1.45.1+
st.markdown("""
<style>
    div[data-testid="stToolbar"] {
        display: none !important;
    }
    div[data-testid="stDecoration"] {
        display: none !important;
    }
    div[data-testid="stStatusWidget"] {
        visibility: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

def search_everything(query: str, page_size: int = 100) -> List:
    # Execute a NewsAPI Everything search.
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWS_API_KEY,
    }

    response = requests.get(
        NEWS_API_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"NewsAPI Error: {data}")

    return data.get("articles", [])

def deduplicate_articles(articles: List[Dict]) -> List:
    # Deduplicate by URL.
    seen_urls = set()
    unique_articles = []

    for article in articles:
        url = article.get("url")

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)
        unique_articles.append(article)

    return unique_articles

def parse_date(article: Dict) -> datetime:
    # Parse NewsAPI publishedAt field.
    published = article.get("publishedAt")

    if not published:
        return datetime.min.replace(tzinfo=None)

    try:
        return datetime.fromisoformat(
            published.replace("Z", "+00:00")
        )
    except Exception:
        return datetime.min.replace(tzinfo=None)

def execute_primary_search() -> List:
    # Run the broad query.
    print("Running primary search...")

    articles = search_everything(PRIMARY_QUERY)

    print(f"Primary search returned {len(articles)} articles")

    return articles

def execute_fallback_searches() -> List:
    # Run targeted searches if primary search is too sparse.
    print("Running fallback searches...")

    articles = []

    for query in FALLBACK_QUERIES:
        try:
            print(f"Searching: {query}")
            results = search_everything(query, page_size=50)
            articles.extend(results)

        except Exception as e:
            print(f"Error with query {query}: {e}")

    print(f"Fallback searches returned {len(articles)} raw articles")

    return articles

def build_news_feed(final_count: int, threshold: int) -> List:
    # Strategy:
    # 1. Run one comprehensive query.
    # 2. Deduplicate.
    # 3. If fewer than threshold articles,
    #    execute targeted fallback searches.
    # 4. Deduplicate again.
    # 5. Sort newest first.
    # 6. Return top N.
    articles = execute_primary_search()
    articles = deduplicate_articles(articles)

    print(
        f"Unique articles after primary search: {len(articles)}"
    )

    if len(articles) < threshold:

        print(
            f"Only {len(articles)} articles found. "
            f"Threshold is {threshold}. "
            f"Using fallback searches."
        )

        fallback_articles = execute_fallback_searches()
        articles.extend(fallback_articles)
        articles = deduplicate_articles(articles)

        print(
            f"Unique articles after fallback: {len(articles)}"
        )

    articles.sort(
        key=parse_date,
        reverse=True
    )
    return articles[:final_count]

def print_results(results: List[Dict]):
    st.sidebar.markdown("## Cellular Analysis News")

    for index, article in enumerate(results, start=1):
        description = article.get("description", "")
        st.sidebar.markdown(
            f"""
            **{index}. {article.get('title')}**<br>
            **Source:** {article.get('source', {}).get('name', 'Unknown')}  
            **Published:** {format_published_date(article.get('publishedAt'))}<br> 
            **URL:** {article.get('url')}  
            **Summary:** {description}
            """, unsafe_allow_html=True)

# Make user-friendly date/time from News API date/time.
def format_published_date(date_str):

    if not date_str:
        return "Unknown"

    try:
        # Convert UTC string from NewsAPI
        utc_dt = datetime.fromisoformat(
            date_str.replace("Z", "+00:00")
        )

        # Convert to local timezone
        local_dt = utc_dt.astimezone(
            ZoneInfo("America/Los_Angeles")
        )

        return local_dt.strftime(
            "%B %d, %Y, %I:%M %p %Z"
        )

    except Exception:
        return date_str

# Load config file with user credentials.
with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

# Initiate authentication.
authenticator = stauth.Authenticate(
    config['credentials'],
)

# Call user login form.
result_auth = authenticator.login("main")
    
# If login successful, continue to aitam page.
if st.session_state.get('authentication_status'):
    authenticator.logout('Logout', 'main')
    st.write(f'Welcome *{st.session_state.get('name')}* !')

    # # Initialize chat history.
    # if "ai_response" not in st.session_state:
    #     st.session_state.ai_response = []
    
    # Model list, Vector store ID, assistant IDs (one for initial upload eval, 
    # the second for follow-up user questions).
    MODEL_LIST = ["gpt-4o-mini"] #, "gpt-4.1-nano", "gpt-4.1", "o4-mini"] "gpt-5-nano"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    VECTOR_STORE_ID = st.secrets["VECTOR_STORE_ID"]
    NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
    INSTRUCTION_ENCRYPTED = b'gAAAAABoiGk68zBaXY7_218kkk0sL8NsNW_cYRvoM2Z026FCZvFJe_7BmWs4YnFRzTMJC5SrCr1BI6p-ojSzH0x843GR-fCWe475f6mKlOfLqC_uueWNiTmPM_8_C--4MCHUXa-GVKI4SlmC76qf2HWpF6ZMhdaWw2xRwT2lJ3kRwpSYBiZbUgGOHsly62_CqnDmwiC0YNOTdUaYdqPoNa5LgVRyeCUnINgt0bey1snq3GI_v44-bS7mJqMGC85mVabdNkOVpgVQw60SCY3ELBRDBfzkWKp0vYw3qQIJJe40KKaZep_GkkI3d8i9t0v9vFDwA2XLaXq07h65Cuvl0ikE1dcwa_shB9dRe9XZsOrDhswZ8djr990AfkHpIOcLnC540VJNiMRwA4ztwMkKVcIFALD75S_7ijtUj4lzvDF4EhI28kcFGP4SmIV1NtONPfUs057PufLiY9lK_jVf-9Y5FGp0GLVdqZZHz1Hz7eSZjE7EideqnhoNMPYGLo7u0wZR1pvLRsQzJvTMbjZQcPLruooC2Fg3x4vWzBY7MTTtW-bKvOecVshZc-6HNcJzMunm4T3-X1A_eSnMAkUMWHczzIFYO-2DGAPoZ1U__6fm_lZMGYeBCmiIXmeoxUhe4TWfqHdSf06h7tc96YX71PfVomiRiDXGc8xyns1VZZFGQaKvr9L8bP4uTK-q4LUgbhT-zxOFqWMuWorOYbW-sTysoR3NhDNJTkepfFISSKYSShua11fvDe13IlBr30Gss2GbV9VE6a39T1vSMShb_xdWkfGPhkX0aGRT46BAj_zHrgi00K176a8Wgn4YPQ_h1Hku_QXpA2o9to6p08tjVMTQ4CRU90RAkm9oMpOcpjDLzqZMW9U8m6g4xbJzZJdezJbj04VYwipNRB6-UKCXgjoGrLYOxoTQiuNIhg7MeD2ZR3w3GH5LWQg03CCUDVyPmzPGuPnRC3cTCJgfvbDbCASx2CMVFTne5OtdEiDAJ0WtC3CCHn9lAl8buIpazUIPTY7VGiIVpRp1rJmAtPLlhwkROTSpws-GDMbS27fybpaEgP6kX_fb-HEvQklA5VDCh5Yu3faEtDcohTqSFVBAautT1fdwQ-xLsH6AgTi15r8LIWL66tfd4RdT8JQ8V3rtZzcDy0MpLah38zWlKDNlQV3ZW3RbFA_f9-bRmQGvc3b9k-HJUH46jNkMAH5O_LsuKwv5kurzGBBn3I-a70JaKLISZeRRZn3PyphKEYUwCP5-6OTGdf-MSCpNVJ7pVmzSqwDeNKpxY48MWB1Wv3c4ERHbZc9Yk9ZK4zBSXXCSWvLmbbHarkpMiMtaRXbJwififJiySx7W3XW1JP6DBkK9fppM9RTYStCq2JFiK50IoFO66-izKe8aehnGBt-eb2ctR5fmkHiuqxo5CRzWcMBOCv40upxHPZlt7S-79h3ZZ7lY8SOiemTbVVugfCFmsh6MgeHOeN6ipkk5jXGzgizxClT8pT-cLRGkF77hWJzceUFF_1N8YEhTAxS7qIzeZL2a2r4YQIdDYziUo5M_iRRFgT6BQSVl8YKbWQU_DsJ1QVPfv0GC0frHkZ7rx3M5zyOKvkGmmAw4rKPUq7NcwypZTIWspVk-8N1l49h8XcruVt-2cnNug_DbgwcwyWwKyGCFCDjnTSRGLUHT7wMXv5UKdgMu9N7-GKMMgF0j_SWxuCvFyziCN-e_WifNGnkuRnN6qPhC8jeHhWkGzqZBFYvAcOG0M65wiKpK0pFGopcU2HwkBxHZUfEnGBAFsE26pl8Re4h8cnH-FKHR9JVV6NstYkBTcsa0ZMFxij1A4niuqa2YowPRICThLxLnGjwmhQtdtWTVDLr1A1Mhv3SeOaDO1g_PjBq0PVsQD4i2rTsbuKTiVibvhATsb0ZIwlpd2iRvQ30QOPoCpS2_WtWpcM-4O9VCxyh55OAf905KjiyhVWSWu4v-ie3k4bTyWGdr2VaeUKHw_vNi0PXwea4fHBchO4RjJ-NBeGeayR-O2MP3qnE4X9zJi6oGTi-2UaJFElArCct0Uiv3tHoiW4w8uqooUPBRFNDsdvNPan2-PMs8qjG0iuAqE9Ak6zqPUvaoCeRcI-eucrH-IAN_ymXPZcYc3ZJLAG1gXnYiGZ8CRacDC91sgqfyoW08pRStYNEWZN77KdAGRK_2ESntIveAV97JjJMdPwtGOIyp6nTRJZxoY1WEw8BFw5jyW4K4vdgcBZiI4VzdGjxU0aN2whgHKxqJrg8wCmXA4rvpihUw8907jY0P1lL6SH6ksNA_ko1PEeSfysaBk0KPz2XAjj2ihBkjXJueGsEYyo7glSaYk7Tky50yXH2mqRDcCIabJa0scFANLmEYPf2t8WgEuciP9DuaM4QJmRcNqR1AhcAN24n7DslvoPTUie9IGazQR781c-rfNGVN352npJ_YkDZi9XVrxHgrzq82vAmuwY_V03V6D5fHThce_oe4cYwFTeqfxyqI3YvaP2BXxZ9__0FIqP_Tc1t64j-7_VpqB10YtJBme9ZnB-l8wGZJHw6I5Na7T4vQdmOCQGtDZNK_aF29sF4eQCBmtAE1fOQ65HBkqboG5KetTGjj1-YH3PCQ93gu_Ueh5YLeI6ZvBXs3fE0j2dwYlwvU4WeAPkm_Ayv58_GaGTT93MwXfls-veIe8-QZpl_2FacxCA_MNxpMn0U0bgUd8l-3VY9FyLPlTGb10AHSoQizKG9EaooAE80yEu5P2su-hhUCWAyyZE89wUWM_gUyTs8bgYI18dBCGR2VNn3vge2CRMxyxCNx-vtTnx-Jkl4PeqU8C2H5a6oFLX0E8mEEjK7fCgRAf07IczA97MVwjVAdrCfuy9z1D0jIq8-vgKnObCudASP10gEY_tS-N60hB7Z35lPRaBdySgy40UrjFTD1zoPGQ5gmmhqXLMmCtq25WqtobJmJqcvaJ7rAMtSuEQQeSaaKad5aBJJAzSRrtsVVMGzbfMIPJHznOoCE7_LfspZqs4UalB2rmwKZaWTDtjsTds8K7cDiOI-kjHROK8Rx0f3rIffxRGxvaWwWa93t4669XzPaDG7-DaG23rcR0S4pXpqTJ9a1jf_nXpzjI7te9--nLt_UdFbXC5pz8PPbFrYJ8e5yYbTazPXj4ZewfTsFAdnRzWYhSf1Xma-4TyXBYkxLwXSOewJbmohB_1RvQvVnRCohhA_ZSBisDh00_rDYs3-qb2XUYj_8-OYvuU8biRaFNOJ5xxMLksMdKqwjf-y6jWE9Smdjwe1h37j4PngG4wqF9_BGhq3uyNXUx-JDGSNcDlXD1_T1d0ezvMOGhMnC0wd0JQDie2jFIN63hmZ-c1ew3_pRDqxQZTTezrGWFFEBUnN8b07WngGNJp046zrTm1KRrqeIOOvF6Jei4NynuxAfQnsp5ngkZ2Dq0w0OgbGso_KMHYYELtINwOwoAeLwUCyeYnUMmYce-ujogWVVjZUe7iEhMH4X1-ANyIR0HdaymbUbob2egSg8LT1Ha8UwA0Ex8BQK'

    key = st.secrets['INSTRUCTION_KEY'].encode()
    f = Fernet(key)
    INSTRUCTION = f.decrypt(INSTRUCTION_ENCRYPTED).decode()

    # Set page layout and title.
    st.set_page_config(page_title="Tripbot AI", page_icon=":airplane:", layout="wide", initial_sidebar_state="collapsed")
    st.header(":airplane: Tripbot")
    st.markdown("TripBot helps employees quickly get answers to common travel policy questions using the company’s official policy documents. It prioritizes SDSURF travel policy first and refers to CSU travel policy only when SDSURF policy does not address the topic. TripBot is here to make travel guidance easier to understand, but for unusual, unclear, or department-specific situations, users should confirm with the appropriate team.")
    
    # Field for OpenAI API key.
    openai_api_key = os.environ.get("OPENAI_API_KEY", None)

    # Retrieve user-selected openai model.
    model: str = st.selectbox("Model", options=MODEL_LIST)
        
    # If there's no openai api key, stop.
    if not openai_api_key:
        st.error("Please enter your OpenAI API key!")
        st.stop()

    # Initialize state once
    if "cleaned_response" not in st.session_state:
        st.session_state.cleaned_response = None
    
    if "file_list_str" not in st.session_state:
        st.session_state.file_list_str = None

    #--------------------------------------------------
    # Setup sidebar.
    #--------------------------------------------------
    NEWS_API_URL = "https://newsapi.org/v2/everything"

    # Minimum number of articles we want before using fallback searches
    MIN_ARTICLE_THRESHOLD = 10
    
    # Final number of results to return
    FINAL_RESULT_COUNT = 10
    
    # Primary broad query
    PRIMARY_QUERY = """
        "visa requirements update" OR
        "passport validity requirements" OR
        "entry requirements update" OR
        "electronic travel authorization" OR
        "travel requirement" OR
        "visa policy change" OR
        "border entry rules" OR
        "travel advisory" OR
        "destination risk" OR
        "travel warning" OR
        "security alert travelers" OR
        "civil unrest travel" OR
        "travel safety alert" OR
        "international travel risk" OR
        "travel health advisory" OR
        "vaccination requirements travel" OR
        "disease outbreak travel" OR
        "CDC travel health notice" OR
        "WHO travel advisory" OR
        "malaria travel guidance" OR
        "yellow fever travel requirement" OR
        "airline strike" OR
        "airport disruption" OR
        "flight cancellations" OR
        "airport closure" OR
        "air traffic control delays" OR
        "airport security strike" OR
        "major flight delays" OR
        "rail strike" OR
        "train strike" OR
        "public transport strike" OR
        "transit disruption" OR
        "rail service disruption" OR
        "transportation strike"
    """
    
    # Fallback queries if the broad search doesn't return enough relevant results  
    FALLBACK_QUERIES = [
        'travel visa news',
        'passport rules',
        'international entry rules',
        'country entry requirements',
        'immigration travel update',
        'border control travel',
        'unsafe travel destination',
        'country safety warning',
        'embassy travel alert',
        'government travel advisory',
        'overseas security alert',
        'travel caution',
        'traveler health alert',
        'international health advisory',
        'travel vaccination news',
        'health risks travelers',
        'disease alert travelers',
        'medical travel guidance',
        'travel disruption',
        'air travel delays',
        'airport delays',
        'flight disruption news',
        'airline operations update',
        'transport strike airport',
        'commuter disruption',
        'transport delays',
        'train delays',
        'metro strike',
        'bus strike',
        'public transit update',
    ]

    try:
        results = build_news_feed(final_count=10, threshold=10)
        print_results(results)
    except Exception as e:
        st.sidebar.markdown(f"*Unable to fetch news.* Error: {e}")

    #--------------------------------------------------
    
    # Create new form to search aitam library vector store.    
    with st.form(key="qa_form", clear_on_submit=False, height=300):
        query = st.text_area("**Ask about travel policies and procedures:**", height="stretch")
        submit = st.form_submit_button("Send")
        
    # If submit button is clicked, query the aitam library.            
    if submit:
        # If form is submitted without a query, stop.
        if not query:
            st.error("Enter a question to search travel policies!")
            st.stop()            
        # Setup output columns to display results.
        # answer_col, sources_col = st.columns(2)
        # Create new client for this submission.
        client2 = OpenAI(api_key=openai_api_key)
        # Query the aitam library vector store and include internet
        # serach results.
        with st.spinner('Searching...'):
            response2 = client2.responses.create(
                instructions = INSTRUCTION,
                input = query,
                model = model,
                temperature = 0.6,
                # text={
                #     "verbosity": "low"
                # },
                tools = [{
                            "type": "file_search",
                            "vector_store_ids": [VECTOR_STORE_ID],
                }],
                include=["file_search_call.results"],
                # include=["output[*].file_search_call.search_results"]
            )
        # Write response to the answer column.    
        # with answer_col:
        try:
            cleaned_response = re.sub(r'【.*?†.*?】', '', response2.output_text) #output[1].content[0].text)
        except:
            cleaned_response = re.sub(r'【.*?†.*?】', '', response2.output[1].content[0].text)
        st.write("*The guidance and recommendations provided by this application are AI generated and informed by organizational travel policies and general best practices. They are intended for informational support only and do not constitute official policy interpretations, legal advice, or final approval decisions. Users should consult their organization’s travel policy documents, HR representatives, or legal advisors before making travel arrangements or submitting expenses based on the output. This tool is designed to assist, not replace, professional judgment or formal policy review.*")
        st.markdown("#### Response")
        st.markdown(cleaned_response)

        st.markdown("#### Sources")
        # Extract annotations from the response, and print source files.
        annotations = response2.output[1].content[0].annotations
        retrieved_files = set([response2.filename for response2 in annotations])
        file_list_str = ", ".join(retrieved_files)
        st.markdown(f"**File(s):** {file_list_str}")

        # Persist response across refreshes/reruns
        st.session_state.cleaned_response = cleaned_response
        st.session_state.file_list_str = file_list_str

        # Add a small copy icon button
        copy_button(
            text=cleaned_response + "\n\nFile(s): " + file_list_str,
            tooltip="Copy this text",
            copied_label="Copied!",
            icon="st",
        )

    if st.session_state.cleaned_response:
        st.write("*The guidance and recommendations provided by this application are AI generated and informed by organizational travel policies and general best practices. They are intended for informational support only and do not constitute official policy interpretations, legal advice, or final approval decisions. Users should consult their organization’s travel policy documents, HR representatives, or legal advisors before making travel arrangements or submitting expenses based on the output. This tool is designed to assist, not replace, professional judgment or formal policy review.*")
        st.markdown("#### Response")
        st.markdown(st.session_state.cleaned_response)
        
        if st.session_state.file_list_str:
            st.markdown("#### Sources")
            st.markdown(f"**File(s):** {st.session_state.file_list_str}")

        # Add a small copy icon button
        copy_button(
            text=st.session_state.cleaned_response + "\n\nFile(s): " + st.session_state.file_list_str,
            tooltip="Copy this text",
            copied_label="Copied!",
            icon="st",
        )

        # st.session_state.ai_response = cleaned_response
        # Write files used to generate the answer.
        # with sources_col:
        #     st.markdown("#### Sources")
        #     # Extract annotations from the response, and print source files.
        #     annotations = response2.output[1].content[0].annotations
        #     retrieved_files = set([response2.filename for response2 in annotations])
        #     file_list_str = ", ".join(retrieved_files)
        #     st.markdown(f"**File(s):** {file_list_str}")

            # st.markdown("#### Token Usage")
            # input_tokens = response2.usage.input_tokens
            # output_tokens = response2.usage.output_tokens
            # total_tokens = input_tokens + output_tokens
            # input_tokens_str = f"{input_tokens:,}"
            # output_tokens_str = f"{output_tokens:,}"
            # total_tokens_str = f"{total_tokens:,}"

            # st.markdown(
            #     f"""
            #     <p style="margin-bottom:0;">Input Tokens: {input_tokens_str}</p>
            #     <p style="margin-bottom:0;">Output Tokens: {output_tokens_str}</p>
            #     """,
            #     unsafe_allow_html=True
            # )
            # st.markdown(f"Total Tokens: {total_tokens_str}")

            # if model == "gpt-4.1-nano":
            #     input_token_cost = .1/1000000
            #     output_token_cost = .4/1000000
            # elif model == "gpt-4o-mini":
            #     input_token_cost = .15/1000000
            #     output_token_cost = .6/1000000
            # elif model == "gpt-4.1":
            #     input_token_cost = 2.00/1000000
            #     output_token_cost = 8.00/1000000
            # elif model == "o4-mini":
            #     input_token_cost = 1.10/1000000
            #     output_token_cost = 4.40/1000000

            # cost = input_tokens*input_token_cost + output_tokens*output_token_cost
            # formatted_cost = "${:,.4f}".format(cost)
            
            # st.markdown(f"**Total Cost:** {formatted_cost}")

    # elif not submit:
    #         st.markdown("#### Response")
    #         st.markdown(st.session_state.ai_response)

elif st.session_state.get('authentication_status') is False:
    st.error('Username/password is incorrect')

elif st.session_state.get('authentication_status') is None:
    st.warning('Please enter your username and password')
