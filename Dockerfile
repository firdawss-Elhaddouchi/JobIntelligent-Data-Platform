FROM apache/airflow:2.8.1

USER airflow

RUN pip install --no-cache-dir \
    emoji \
    requests \
    boto3 \
    pandas \
    psycopg2-binary