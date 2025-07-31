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
    MODEL_LIST = ["gpt-4o-mini"] #, "gpt-4.1-nano", "gpt-4.1", "o4-mini"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    VECTOR_STORE_ID = st.secrets["VECTOR_STORE_ID"]
    INSTRUCTION_ENCRYPTED = b'gAAAAABoiGk68zBaXY7_218kkk0sL8NsNW_cYRvoM2Z026FCZvFJe_7BmWs4YnFRzTMJC5SrCr1BI6p-ojSzH0x843GR-fCWe475f6mKlOfLqC_uueWNiTmPM_8_C--4MCHUXa-GVKI4SlmC76qf2HWpF6ZMhdaWw2xRwT2lJ3kRwpSYBiZbUgGOHsly62_CqnDmwiC0YNOTdUaYdqPoNa5LgVRyeCUnINgt0bey1snq3GI_v44-bS7mJqMGC85mVabdNkOVpgVQw60SCY3ELBRDBfzkWKp0vYw3qQIJJe40KKaZep_GkkI3d8i9t0v9vFDwA2XLaXq07h65Cuvl0ikE1dcwa_shB9dRe9XZsOrDhswZ8djr990AfkHpIOcLnC540VJNiMRwA4ztwMkKVcIFALD75S_7ijtUj4lzvDF4EhI28kcFGP4SmIV1NtONPfUs057PufLiY9lK_jVf-9Y5FGp0GLVdqZZHz1Hz7eSZjE7EideqnhoNMPYGLo7u0wZR1pvLRsQzJvTMbjZQcPLruooC2Fg3x4vWzBY7MTTtW-bKvOecVshZc-6HNcJzMunm4T3-X1A_eSnMAkUMWHczzIFYO-2DGAPoZ1U__6fm_lZMGYeBCmiIXmeoxUhe4TWfqHdSf06h7tc96YX71PfVomiRiDXGc8xyns1VZZFGQaKvr9L8bP4uTK-q4LUgbhT-zxOFqWMuWorOYbW-sTysoR3NhDNJTkepfFISSKYSShua11fvDe13IlBr30Gss2GbV9VE6a39T1vSMShb_xdWkfGPhkX0aGRT46BAj_zHrgi00K176a8Wgn4YPQ_h1Hku_QXpA2o9to6p08tjVMTQ4CRU90RAkm9oMpOcpjDLzqZMW9U8m6g4xbJzZJdezJbj04VYwipNRB6-UKCXgjoGrLYOxoTQiuNIhg7MeD2ZR3w3GH5LWQg03CCUDVyPmzPGuPnRC3cTCJgfvbDbCASx2CMVFTne5OtdEiDAJ0WtC3CCHn9lAl8buIpazUIPTY7VGiIVpRp1rJmAtPLlhwkROTSpws-GDMbS27fybpaEgP6kX_fb-HEvQklA5VDCh5Yu3faEtDcohTqSFVBAautT1fdwQ-xLsH6AgTi15r8LIWL66tfd4RdT8JQ8V3rtZzcDy0MpLah38zWlKDNlQV3ZW3RbFA_f9-bRmQGvc3b9k-HJUH46jNkMAH5O_LsuKwv5kurzGBBn3I-a70JaKLISZeRRZn3PyphKEYUwCP5-6OTGdf-MSCpNVJ7pVmzSqwDeNKpxY48MWB1Wv3c4ERHbZc9Yk9ZK4zBSXXCSWvLmbbHarkpMiMtaRXbJwififJiySx7W3XW1JP6DBkK9fppM9RTYStCq2JFiK50IoFO66-izKe8aehnGBt-eb2ctR5fmkHiuqxo5CRzWcMBOCv40upxHPZlt7S-79h3ZZ7lY8SOiemTbVVugfCFmsh6MgeHOeN6ipkk5jXGzgizxClT8pT-cLRGkF77hWJzceUFF_1N8YEhTAxS7qIzeZL2a2r4YQIdDYziUo5M_iRRFgT6BQSVl8YKbWQU_DsJ1QVPfv0GC0frHkZ7rx3M5zyOKvkGmmAw4rKPUq7NcwypZTIWspVk-8N1l49h8XcruVt-2cnNug_DbgwcwyWwKyGCFCDjnTSRGLUHT7wMXv5UKdgMu9N7-GKMMgF0j_SWxuCvFyziCN-e_WifNGnkuRnN6qPhC8jeHhWkGzqZBFYvAcOG0M65wiKpK0pFGopcU2HwkBxHZUfEnGBAFsE26pl8Re4h8cnH-FKHR9JVV6NstYkBTcsa0ZMFxij1A4niuqa2YowPRICThLxLnGjwmhQtdtWTVDLr1A1Mhv3SeOaDO1g_PjBq0PVsQD4i2rTsbuKTiVibvhATsb0ZIwlpd2iRvQ30QOPoCpS2_WtWpcM-4O9VCxyh55OAf905KjiyhVWSWu4v-ie3k4bTyWGdr2VaeUKHw_vNi0PXwea4fHBchO4RjJ-NBeGeayR-O2MP3qnE4X9zJi6oGTi-2UaJFElArCct0Uiv3tHoiW4w8uqooUPBRFNDsdvNPan2-PMs8qjG0iuAqE9Ak6zqPUvaoCeRcI-eucrH-IAN_ymXPZcYc3ZJLAG1gXnYiGZ8CRacDC91sgqfyoW08pRStYNEWZN77KdAGRK_2ESntIveAV97JjJMdPwtGOIyp6nTRJZxoY1WEw8BFw5jyW4K4vdgcBZiI4VzdGjxU0aN2whgHKxqJrg8wCmXA4rvpihUw8907jY0P1lL6SH6ksNA_ko1PEeSfysaBk0KPz2XAjj2ihBkjXJueGsEYyo7glSaYk7Tky50yXH2mqRDcCIabJa0scFANLmEYPf2t8WgEuciP9DuaM4QJmRcNqR1AhcAN24n7DslvoPTUie9IGazQR781c-rfNGVN352npJ_YkDZi9XVrxHgrzq82vAmuwY_V03V6D5fHThce_oe4cYwFTeqfxyqI3YvaP2BXxZ9__0FIqP_Tc1t64j-7_VpqB10YtJBme9ZnB-l8wGZJHw6I5Na7T4vQdmOCQGtDZNK_aF29sF4eQCBmtAE1fOQ65HBkqboG5KetTGjj1-YH3PCQ93gu_Ueh5YLeI6ZvBXs3fE0j2dwYlwvU4WeAPkm_Ayv58_GaGTT93MwXfls-veIe8-QZpl_2FacxCA_MNxpMn0U0bgUd8l-3VY9FyLPlTGb10AHSoQizKG9EaooAE80yEu5P2su-hhUCWAyyZE89wUWM_gUyTs8bgYI18dBCGR2VNn3vge2CRMxyxCNx-vtTnx-Jkl4PeqU8C2H5a6oFLX0E8mEEjK7fCgRAf07IczA97MVwjVAdrCfuy9z1D0jIq8-vgKnObCudASP10gEY_tS-N60hB7Z35lPRaBdySgy40UrjFTD1zoPGQ5gmmhqXLMmCtq25WqtobJmJqcvaJ7rAMtSuEQQeSaaKad5aBJJAzSRrtsVVMGzbfMIPJHznOoCE7_LfspZqs4UalB2rmwKZaWTDtjsTds8K7cDiOI-kjHROK8Rx0f3rIffxRGxvaWwWa93t4669XzPaDG7-DaG23rcR0S4pXpqTJ9a1jf_nXpzjI7te9--nLt_UdFbXC5pz8PPbFrYJ8e5yYbTazPXj4ZewfTsFAdnRzWYhSf1Xma-4TyXBYkxLwXSOewJbmohB_1RvQvVnRCohhA_ZSBisDh00_rDYs3-qb2XUYj_8-OYvuU8biRaFNOJ5xxMLksMdKqwjf-y6jWE9Smdjwe1h37j4PngG4wqF9_BGhq3uyNXUx-JDGSNcDlXD1_T1d0ezvMOGhMnC0wd0JQDie2jFIN63hmZ-c1ew3_pRDqxQZTTezrGWFFEBUnN8b07WngGNJp046zrTm1KRrqeIOOvF6Jei4NynuxAfQnsp5ngkZ2Dq0w0OgbGso_KMHYYELtINwOwoAeLwUCyeYnUMmYce-ujogWVVjZUe7iEhMH4X1-ANyIR0HdaymbUbob2egSg8LT1Ha8UwA0Ex8BQK'

    key = st.secrets['INSTRUCTION_KEY'].encode()
    f = Fernet(key)
    INSTRUCTION = f.decrypt(INSTRUCTION_ENCRYPTED).decode()

    # Set page layout and title.
    st.set_page_config(page_title="Tripbot AI", page_icon=":airplane:", layout="wide")
    st.header(":airplane: Tripbot")
    
    # Field for OpenAI API key.
    openai_api_key = os.environ.get("OPENAI_API_KEY", None)

    # Retrieve user-selected openai model.
    model: str = st.selectbox("Model", options=MODEL_LIST)
        
    # If there's no openai api key, stop.
    if not openai_api_key:
        st.error("Please enter your OpenAI API key!")
        st.stop()
    
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
        answer_col, sources_col = st.columns(2)
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
                tools = [{
                            "type": "file_search",
                            "vector_store_ids": [VECTOR_STORE_ID],
                }],
                include=["output[*].file_search_call.search_results"]
            )
        # Write response to the answer column.    
        with answer_col:
            cleaned_response = re.sub(r'【.*?†.*?】', '', response2.output[1].content[0].text)
            st.markdown("#### Response")
            st.markdown(cleaned_response)
            # st.session_state.ai_response = cleaned_response
        # Write files used to generate the answer.
        with sources_col:
            st.markdown("#### Sources")
            # Extract annotations from the response, and print source files.
            annotations = response2.output[1].content[0].annotations
            retrieved_files = set([response2.filename for response2 in annotations])
            file_list_str = ", ".join(retrieved_files)
            st.markdown(f"**File(s):** {file_list_str}")

            st.markdown("#### Token Usage")
            input_tokens = response2.usage.input_tokens
            output_tokens = response2.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            input_tokens_str = f"{input_tokens:,}"
            output_tokens_str = f"{output_tokens:,}"
            total_tokens_str = f"{total_tokens:,}"

            st.markdown(
                f"""
                <p style="margin-bottom:0;">Input Tokens: {input_tokens_str}</p>
                <p style="margin-bottom:0;">Output Tokens: {output_tokens_str}</p>
                """,
                unsafe_allow_html=True
            )
            st.markdown(f"Total Tokens: {total_tokens_str}")

            if model == "gpt-4.1-nano":
                input_token_cost = .1/1000000
                output_token_cost = .4/1000000
            elif model == "gpt-4o-mini":
                input_token_cost = .15/1000000
                output_token_cost = .6/1000000
            elif model == "gpt-4.1":
                input_token_cost = 2.00/1000000
                output_token_cost = 8.00/1000000
            elif model == "o4-mini":
                input_token_cost = 1.10/1000000
                output_token_cost = 4.40/1000000

            cost = input_tokens*input_token_cost + output_tokens*output_token_cost
            formatted_cost = "${:,.4f}".format(cost)
            
            st.markdown(f"**Total Cost:** {formatted_cost}")

    # elif not submit:
    #         st.markdown("#### Response")
    #         st.markdown(st.session_state.ai_response)

elif st.session_state.get('authentication_status') is False:
    st.error('Username/password is incorrect')

elif st.session_state.get('authentication_status') is None:
    st.warning('Please enter your username and password')
