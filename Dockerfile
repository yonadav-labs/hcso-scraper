FROM alpine:latest

RUN apk add --update python3 py3-pip 
RUN apk add --update tzdata

WORKDIR /scrapearrests

# Install deps
COPY scrape/requirements.txt .
RUN pip3 install -r /scrapearrests/requirements.txt

# Copy script which should be run
COPY scrape .

RUN chmod +x /scrapearrests/main.py

# Run the cron every day at 8
ENV TZ=US/Eastern
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN echo '00 08  *  *  *   python3 /scrapearrests/scraper.py' > /var/spool/cron/crontabs/root

CMD crond -l 2 -f