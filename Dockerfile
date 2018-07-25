FROM alpine:latest

RUN apk add --update python3 py3-pip 
RUN apk add --update tzdata

# Copy script which should be run
COPY scrape /scrapearrests
RUN pip3 install -r /scrapearrests/requirements.txt

RUN chmod +x /scrapearrests/main.py

# Run the cron every day at 8
ENV TZ=US/Eastern
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN echo '00 08  *  *  *   python3 /scrapearrests/main.py' > /var/spool/cron/crontabs/root

CMD crond -l 2 -f