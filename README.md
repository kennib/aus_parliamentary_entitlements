[View the data here](./parliamentary_entitlements.csv)

This is a scraper that runs on [Morph](https://morph.io). To get started [see the documentation](https://morph.io/documentation)

Alternatively you can clone this repository and run docker:

```
docker build -t kennib/entitlements
docker run -v ${PWD}:/usr/scraper -it kennib/entitlements
```

Or you can just use your own environment:

```
pip install -r requirements.txt
python2.7 scraper.py
```
