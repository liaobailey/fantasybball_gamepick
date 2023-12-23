import sys
import datetime
import pandas as pd
import numpy as np
import os
import streamlit as st
import pymongo

st.set_page_config(layout="wide")
st.write('load')

# Connect to MongoDB
@st.cache_data
def get_mongo_db():
    client = pymongo.MongoClient(st.secrets["db_uri"])
    db = client.nba
    collection = db.boxscores
    return collection

# Retrieve and display data
@st.cache_data
def main():
    collection = get_mongo_db()
    st.write('success')
    data = list(collection.find())
    df = pd.DataFrame(data)
    return df

df = main()
