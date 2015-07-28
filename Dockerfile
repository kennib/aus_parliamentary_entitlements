FROM python:2.7

RUN mkdir /usr/scraper
WORKDIR /usr/scraper

ADD requirements.txt /usr/scraper/
RUN pip install -r requirements.txt

ADD scraper.py /usr/scraper/
CMD ["python", "scraper.py"]
