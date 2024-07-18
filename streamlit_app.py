import streamlit as st
from streamlit_player import st_player
import boto3

import time
import requests
from datetime import datetime


# Title of the app
st.title("Audio Player with Play and Stop and Sentiment Analysis")

from st_files_connection import FilesConnection

# Create connection object and retrieve file contents.
# Specify input format is a csv and to cache the result for 600 seconds.
conn = st.connection('s3', type=FilesConnection)
df = conn.read("s3://mytestbucket126/csv_files/dog.csv", input_format="csv", ttl=600)

# Access AWS credentials from st.secrets
access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
region = st.secrets["AWS_DEFAULT_REGION"]
S3_BUCKET_NAME = "mytestbucket126"  # Corrected bucket name
WAV_FILE_KEY = "audio/audio.wav"  # Corrected path

# Upload audio file
uploaded_file = conn._instance.read_bytes("s3://mytestbucket126/audio/audio.wav")
uploaded_file_name = "audio.wav"

# Create an S3 client and download the WAV file
s3 = boto3.client(
    "s3",
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key,
    region_name=region,
)
wav_file = s3.get_object(Bucket=S3_BUCKET_NAME, Key=WAV_FILE_KEY)["Body"].read()


# Function to start the transcription job with sentiment analysis
def start_transcription_and_analysis():
    transcribe = boto3.client(
        "transcribe",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )
    comprehend = boto3.client(
        "comprehend",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region
    )

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    transcription_job_name = f"wav-transcription-{timestamp}"

    transcribe.start_transcription_job(
        TranscriptionJobName=transcription_job_name,
        Media={"MediaFileUri": f"s3://{S3_BUCKET_NAME}/{WAV_FILE_KEY}"},
        MediaFormat="wav",
        LanguageCode="en-US"
    )

    # Wait for the transcription job to complete
    with st.spinner('Transcribing...'):
        while True:
            result = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            if result['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            time.sleep(10)  # Wait for 10 seconds before checking again

    # Get the transcription and analyze sentiment
    if result['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcription_uri = result['TranscriptionJob']['Transcript']['TranscriptFileUri']
        response = requests.get(transcription_uri)
        transcription_text = response.json()['results']['transcripts'][0]['transcript']

        # Use Comprehend to analyze sentiment
        sentiment_analysis = comprehend.detect_sentiment(Text=transcription_text,
                                                          LanguageCode="en")

        sentiment = sentiment_analysis["Sentiment"]
        confidence_score = sentiment_analysis["SentimentScore"].get('POSITIVE', 0.0)  # Handle missing key

        # Display results
        st.text_area('Transcription:', value=transcription_text, height=200)
        st.write(f"Sentiment: {sentiment} (Confidence: {confidence_score:.2f})")
    else:
        st.error("Transcription job failed")


for row in df.itertuples():
    st.write(f"{row.Owner} has a :{row.Pet}:")
# Check if a file is uploaded
if uploaded_file is not None:
    # Get the file details (optional)
    file_details = {
        "File Name": uploaded_file_name,
        "File Type": "audio/wav",
        "File Size": len(uploaded_file)
    }

    # Save the uploaded file to a local file (optional, for debugging)
    with open(uploaded_file_name, "wb") as f:
        f.write(uploaded_file)

    # Adding start and stop buttons
    if st.button("Start"):
        if uploaded_file is not None:
            # Play the audio
            st.audio(uploaded_file, format="audio/wav")

            # Start transcription job with sentiment analysis
            start_transcription_and_analysis()
        else:
            st.error("Please upload an audio file first.")

if st.button("Stop"):
    st.stop()
