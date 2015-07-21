import scraperwiki
import lxml.html
import urllib2
import pdfquery

from StringIO import StringIO
from collections import defaultdict

ENTITLEMENTS_PAGE = "http://www.finance.gov.au/publications/parliamentarians-reporting/parliamentarians-expenditure-P34/"

# Read in a page
html = scraperwiki.scrape(ENTITLEMENTS_PAGE)

# Find list of links to expense reports on the page using css selectors
root = lxml.html.fromstring(html)
links = root.cssselect("tr td:first-child a")
urls = [link.get('href') for link in links]

# Download the PDFs
pdfs = [pdfquery.PDFQuery(StringIO(urllib2.urlopen(url).read())) for url in urls[:1]]
for pdf in pdfs: pdf.load()

# Find the relevant information in the PDFs
for pdf in pdfs:
	num_pages = pdf.doc.catalog['Pages'].resolve()['Count']
	for page in range(num_pages):
		page = 'LTPage[pageid="{}"]'.format(page)
		# Find all the boxes
		boxes = pdf.pq(page+' LTRect')
		
		# Group the boxes into horizontal lines
		horizontal_boxes = defaultdict(list)
		for box in boxes:
			horizontal_boxes[box.get('y0'), box.get('y1')].append(box)

		# Get the extent of the header boxes
		header_boxes = [
			( min([float(rect.get('x0')) for rect in header])
			, min([float(rect.get('y0')) for rect in header])
			, max([float(rect.get('x1')) for rect in header])
			, max([float(rect.get('y1')) for rect in header])
			) for header in horizontal_boxes.values()]

		# Find the text in all the text boxes
		headers = [[line.text.strip()
				for line in pdf.pq(page+' *:in_bbox("{}, {}, {}, {}")'.format(*box))
				if line.text
			] for box in header_boxes]
		
		print page
		for header, box in zip(headers, header_boxes):
			print header
			print box
		print

# Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
