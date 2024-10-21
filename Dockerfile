# Use the official Python image as base
FROM python:3.13-slim

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y gosu
RUN rm -rf /var/lib/apt/lists/

RUN pip install jupyter 
RUN pip install pandas numpy matplotlib seaborn
RUN pip install flask django prettytable
RUN pip install cryptography

RUN mkdir /data
WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start Jupyter Notebook
CMD ["/entrypoint.sh"]
